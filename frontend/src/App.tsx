import { useState, useEffect, useRef } from 'react'

interface HealthResponse {
  status: string;
  timestamp: number;
  service: string;
  version: string;
}

interface Post {
  id: string;
  username: string;
  platform: string;
  timestamp: string;
  text: string;
  language: string;
  threat_category: string;
  engagement: { likes: number; shares: number; comments: number };
  geo: { city: string; latitude: number; longitude: number };
  user_profile?: { account_created_date: string; follower_count: number; following_count: number };
}

interface TrendPoint {
  timestamp: string;
  post_count: number;
  top_keywords: Record<string, number>;
  geo_distribution: Record<string, number>;
  lang_distribution: Record<string, number>;
  rolling_baseline: number;
  is_spike: boolean;
}

interface Cluster {
  cluster_id: string;
  member_accounts: string[];
  heuristics: string[];
  suspicion_score: number;
  matched_posts: {
    id: string;
    username: string;
    timestamp: string;
    text: string;
    threat_category: string;
    platform: string;
  }[];
}

interface AlertItem {
  id: string;
  type: 'post' | 'cluster';
  title: string;
  description: string;
  timestamp: string;
  severity: 'high' | 'critical';
}

// Global set to track already-alerted unique post/cluster IDs across polling cycles
const globalAlertedIds = new Set<string>();

function CoordinationNetworkGraph() {
  const [networkData, setNetworkData] = useState<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] });
  const [neo4jAvailable, setNeo4jAvailable] = useState<boolean | null>(null);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [hoveredNode, setHoveredNode] = useState<any | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const draggingNodeRef = useRef<any | null>(null);

  const fetchGraphData = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/network-graph');
      if (res.ok) {
        const data = await res.json();
        setNeo4jAvailable(!!data.neo4j_available);
        if (data.nodes) {
          // Initialize coordinates if not set, keep existing if already there to avoid jarring jumps
          const width = 720;
          const height = 480;
          setNetworkData(prev => {
            const nodes = data.nodes.map((n: any) => {
              const prevNode = prev.nodes.find(pn => pn.id === n.id);
              return {
                ...n,
                x: prevNode ? prevNode.x : width / 2 + (Math.random() - 0.5) * 300,
                y: prevNode ? prevNode.y : height / 2 + (Math.random() - 0.5) * 300,
                vx: prevNode ? prevNode.vx : 0,
                vy: prevNode ? prevNode.vy : 0
              };
            });
            return { nodes, edges: data.edges || [] };
          });
        }
      }
    } catch (err) {
      console.error("Failed to fetch graph data", err);
      setNeo4jAvailable(false);
    }
  };

  useEffect(() => {
    fetchGraphData();
    const interval = setInterval(fetchGraphData, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || networkData.nodes.length === 0) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    const nodes = networkData.nodes;
    const edges = networkData.edges;

    const width = canvas.width;
    const height = canvas.height;

    // Physics parameters
    const repulsion = 1200;
    const springLength = 140;
    const springK = 0.05;
    const gravity = 0.04;
    const damping = 0.82;

    const tick = () => {
      // 1. Repulsion force between pairs
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const n1 = nodes[i];
          const n2 = nodes[j];
          const dx = n2.x - n1.x;
          const dy = n2.y - n1.y;
          const distSq = dx * dx + dy * dy || 1;
          const dist = Math.sqrt(distSq);

          if (dist < 320) {
            let currentRepulsion = repulsion;
            const isN1Coordinated = n1.suspicion >= 75;
            const isN2Coordinated = n2.suspicion >= 75;
            
            if (isN1Coordinated && isN2Coordinated) {
              const isConnected = edges.some(e => 
                (e.from === n1.id && e.to === n2.id) || 
                (e.from === n2.id && e.to === n1.id)
              );
              if (!isConnected) {
                // Drastically push apart different clusters so they separate visually
                currentRepulsion = repulsion * 7;
              } else {
                // Keep same-cluster nodes closer but distinct
                currentRepulsion = repulsion * 0.75;
              }
            } else if (isN1Coordinated || isN2Coordinated) {
              // Push coordinated clusters away from background noise
              currentRepulsion = repulsion * 4;
            } else {
              // Faded background nodes repel each other gently
              currentRepulsion = repulsion * 0.3;
            }

            const force = currentRepulsion / distSq;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;

            n1.vx -= fx;
            n1.vy -= fy;
            n2.vx += fx;
            n2.vy += fy;
          }
        }
      }

      // 2. Attractive force along edges (springs)
      edges.forEach((edge) => {
        const n1 = nodes.find(n => n.id === edge.from);
        const n2 = nodes.find(n => n.id === edge.to);
        if (!n1 || !n2) return;

        const dx = n2.x - n1.x;
        const dy = n2.y - n1.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;

        const displacement = dist - springLength;
        const force = springK * displacement;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        n1.vx += fx;
        n1.vy += fy;
        n2.vx -= fx;
        n2.vy -= fy;
      });

      // 3. Gravity center force & update node coordinates
      const cx = width / 2;
      const cy = height / 2;

      nodes.forEach((node) => {
        if (node === draggingNodeRef.current) return;

        const dx = cx - node.x;
        const dy = cy - node.y;

        node.vx += dx * gravity;
        node.vy += dy * gravity;

        node.vx *= damping;
        node.vy *= damping;
        
        node.x += node.vx;
        node.y += node.vy;

        // Keep inside bounds
        node.x = Math.max(30, Math.min(width - 30, node.x));
        node.y = Math.max(30, Math.min(height - 30, node.y));
      });

      // 4. Draw Layout
      ctx.clearRect(0, 0, width, height);

      // Draw grid backing
      ctx.strokeStyle = '#0e0e11';
      ctx.lineWidth = 1;
      const step = 40;
      for (let x = 0; x < width; x += step) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += step) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Draw Edges
      edges.forEach((edge) => {
        const n1 = nodes.find(n => n.id === edge.from);
        const n2 = nodes.find(n => n.id === edge.to);
        if (!n1 || !n2) return;

        ctx.beginPath();
        ctx.moveTo(n1.x, n1.y);
        ctx.lineTo(n2.x, n2.y);
        
        if (edge.suspicion_score >= 75) {
          ctx.strokeStyle = 'rgba(239, 68, 68, 0.45)'; // Rose
          ctx.lineWidth = 2.5;
        } else {
          ctx.strokeStyle = 'rgba(245, 158, 11, 0.35)'; // Amber
          ctx.lineWidth = 1.5;
        }
        ctx.stroke();
      });

      // Draw Nodes
      nodes.forEach((node) => {
        const isHovered = hoveredNode && hoveredNode.id === node.id;
        const isSelected = selectedNode && selectedNode.id === node.id;
        const isCoordinated = node.suspicion >= 75;
        
        if (!isCoordinated) {
          // Render background noise node small and faded, with no halos or text
          const radius = 3;
          ctx.beginPath();
          ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
          ctx.fillStyle = 'rgba(63, 63, 70, 0.15)'; // Very faint Zinc
          ctx.fill();
          return;
        }

        const radius = 12 + Math.min(node.post_count * 2.5, 12);
        
        // Glowing ring for highly suspicious accounts
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius + 6, 0, 2 * Math.PI);
        ctx.fillStyle = 'rgba(239, 68, 68, 0.15)';
        ctx.fill();
        
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius + 4, 0, 2 * Math.PI);
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.45)';
        ctx.lineWidth = 1.2;
        ctx.stroke();

        // Selection ring
        if (isSelected) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, radius + 5, 0, 2 * Math.PI);
          ctx.strokeStyle = '#6366f1'; // Indigo 500
          ctx.lineWidth = 2.5;
          ctx.stroke();
        } else if (isHovered) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, radius + 4, 0, 2 * Math.PI);
          ctx.strokeStyle = '#a5b4fc'; // Indigo 300
          ctx.lineWidth = 1.8;
          ctx.stroke();
        }

        // Platform center dot coloring
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
        let platformColor = '#71717a';
        switch (node.platform.toLowerCase()) {
          case 'x': platformColor = '#ffffff'; break;
          case 'youtube': platformColor = '#ef4444'; break;
          case 'instagram': platformColor = '#ec4899'; break;
          case 'facebook': platformColor = '#3b82f6'; break;
          case 'telegram': platformColor = '#06b6d4'; break;
        }
        ctx.fillStyle = platformColor;
        ctx.fill();

        // Node Label
        ctx.font = isHovered ? 'bold 10px monospace' : '9px monospace';
        ctx.fillStyle = isHovered ? '#ffffff' : '#e4e4e7';
        ctx.textAlign = 'center';
        ctx.fillText(node.label, node.x, node.y - radius - 8);
      });

      animationFrameId = requestAnimationFrame(tick);
    };

    animationFrameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationFrameId);
  }, [networkData, hoveredNode, selectedNode]);

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (draggingNodeRef.current) {
      draggingNodeRef.current.x = x;
      draggingNodeRef.current.y = y;
      return;
    }

    let foundHover: any = null;
    for (const node of networkData.nodes) {
      if (node.suspicion < 75) continue; // Ignore non-coordinated background accounts
      const radius = 12 + Math.min(node.post_count * 2.5, 12);
      const dx = node.x - x;
      const dy = node.y - y;
      if (dx * dx + dy * dy <= (radius + 8) * (radius + 8)) {
        foundHover = node;
        break;
      }
    }
    setHoveredNode(foundHover);
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    let clickedNode: any = null;
    for (const node of networkData.nodes) {
      if (node.suspicion < 75) continue; // Ignore non-coordinated background accounts
      const radius = 12 + Math.min(node.post_count * 2.5, 12);
      const dx = node.x - x;
      const dy = node.y - y;
      if (dx * dx + dy * dy <= (radius + 8) * (radius + 8)) {
        clickedNode = node;
        break;
      }
    }

    if (clickedNode) {
      setSelectedNode(clickedNode);
      draggingNodeRef.current = clickedNode;
      clickedNode.vx = 0;
      clickedNode.vy = 0;
    } else {
      setSelectedNode(null);
    }
  };

  const handleMouseUp = () => {
    draggingNodeRef.current = null;
  };

  const getCoordinatesWith = () => {
    if (!selectedNode) return [];
    return networkData.edges
      .filter(e => e.from === selectedNode.id || e.to === selectedNode.id)
      .map(e => {
        const partner = e.from === selectedNode.id ? e.to : e.from;
        return {
          username: partner,
          heuristic: e.heuristic,
          suspicion: e.suspicion_score
        };
      });
  };

  const partners = getCoordinatesWith();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 w-full">
      {/* Network Canvas Panel */}
      <div className="lg:col-span-8 bg-zinc-900/40 border border-zinc-900 rounded-xl p-5 backdrop-blur-md shadow-xl flex flex-col">
        <div className="flex justify-between items-center mb-3 border-b border-zinc-900 pb-2">
          <div>
            <h3 className="text-xs font-extrabold uppercase tracking-widest text-zinc-400 font-mono flex items-center gap-2">
              🕸️ Coordinated Campaign Network Graph
            </h3>
            <p className="text-[10px] text-zinc-500 font-mono">
              Visualizes (:Account)-[:COORDINATES_WITH]-{"->"} (:Account) relationships synced to Neo4j database
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-1.5 h-1.5 rounded-full ${neo4jAvailable ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500 animate-pulse'}`} />
            <span className="text-[10px] font-mono text-zinc-500">
              NEO4J: {neo4jAvailable ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
        </div>

        {neo4jAvailable === false && networkData.nodes.length === 0 ? (
          <div className="h-[480px] border border-dashed border-zinc-800 rounded bg-zinc-950/20 flex flex-col items-center justify-center p-6 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-lg text-rose-500">
              ⚠️
            </div>
            <div className="max-w-md">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">Neo4j Graph Database Unreachable</h4>
              <p className="text-[10px] text-zinc-400 font-mono mt-2 leading-relaxed">
                The Graph Database sync is currently offline. Please configure your <code className="text-indigo-400 font-bold bg-zinc-900 px-1 py-0.5 rounded">NEO4J_URI</code>, <code className="text-indigo-400 font-bold bg-zinc-900 px-1 py-0.5 rounded">NEO4J_USERNAME</code>, and <code className="text-indigo-400 font-bold bg-zinc-900 px-1 py-0.5 rounded">NEO4J_PASSWORD</code> inside your <code className="text-white">.env</code> file and restart the API server.
              </p>
            </div>
          </div>
        ) : (
          <div className="bg-zinc-950 border border-zinc-900 rounded overflow-hidden flex justify-center items-center h-[480px]">
            <canvas
              ref={canvasRef}
              width={720}
              height={480}
              onMouseMove={handleMouseMove}
              onMouseDown={handleMouseDown}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              className="w-full h-full max-h-[480px] max-w-[720px] cursor-grab active:cursor-grabbing"
            />
          </div>
        )}
      </div>

      {/* Selected Account Sidebar */}
      <div className="lg:col-span-4 bg-zinc-900/40 border border-zinc-900 rounded-xl p-5 backdrop-blur-md shadow-xl flex flex-col h-[550px]">
        <div className="mb-3 border-b border-zinc-900 pb-2">
          <h3 className="text-xs font-extrabold uppercase tracking-widest text-indigo-400 font-mono">
            ℹ️ Node Inspector
          </h3>
        </div>

        {!selectedNode ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-4 text-zinc-500 text-xs italic font-mono space-y-2">
            <svg className="w-8 h-8 text-zinc-700 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"></path>
            </svg>
            <span>Click any account node on the left to inspect network coordination relationships.</span>
          </div>
        ) : (
          <div className="flex-1 flex flex-col space-y-4 font-mono text-[11px] overflow-y-auto pr-1">
            {/* Account Card */}
            <div className="p-3.5 bg-zinc-950 border border-zinc-900 rounded-lg space-y-2.5">
              <div className="flex justify-between items-center">
                <span className="font-bold text-white text-xs break-all">{selectedNode.id}</span>
                <span className={`text-[9px] font-extrabold px-2 py-0.5 rounded uppercase ${
                  selectedNode.platform.toLowerCase() === 'youtube' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                  selectedNode.platform.toLowerCase() === 'telegram' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' :
                  selectedNode.platform.toLowerCase() === 'instagram' ? 'bg-pink-500/10 text-pink-400 border border-pink-500/20' :
                  'bg-zinc-800 text-zinc-400'
                }`}>
                  {selectedNode.platform}
                </span>
              </div>
              
              <div className="space-y-1 text-zinc-400">
                <div className="flex justify-between">
                  <span>Ingested Posts:</span>
                  <span className="text-white font-semibold">{selectedNode.post_count}</span>
                </div>
                <div className="flex justify-between">
                  <span>Max Suspicion score:</span>
                  <span className={`font-semibold ${selectedNode.suspicion >= 75 ? 'text-rose-500' : 'text-amber-500'}`}>
                    {selectedNode.suspicion}%
                  </span>
                </div>
              </div>
            </div>

            {/* Coordination details */}
            <div className="flex-1 flex flex-col space-y-2">
              <span className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">
                Coordinated Account Links ({partners.length})
              </span>
              
              {partners.length === 0 ? (
                <div className="flex-1 py-6 flex items-center justify-center border border-dashed border-zinc-800 rounded text-zinc-600 italic">
                  No coordination links detected.
                </div>
              ) : (
                <div className="flex-1 overflow-y-auto space-y-2 max-h-[260px] pr-1">
                  {partners.map((p: any, idx: number) => (
                    <div key={idx} className="p-3 bg-zinc-950 border border-zinc-900 rounded-lg space-y-1.5">
                      <div className="flex justify-between items-center">
                        <span className="text-zinc-200 font-bold break-all">{p.username}</span>
                        <span className="text-rose-500 text-[10px] font-bold">{p.suspicion}%</span>
                      </div>
                      <div className="text-[9px] text-zinc-500 leading-normal">
                        <span className="text-zinc-600 font-bold block uppercase text-[8px] tracking-wide">Triggered Heuristics:</span>
                        <span className="text-zinc-400 font-mono italic break-words">{p.heuristic}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function App() {
  // Connection states
  const [connectionStatus, setConnectionStatus] = useState<'checking' | 'online' | 'offline'>('checking')
  const [healthData, setHealthData] = useState<HealthResponse | null>(null)
  const [latency, setLatency] = useState<number | null>(null)

  // Crawler and Database states
  const [crawlerActive, setCrawlerActive] = useState(false)
  const [crawlerModeSelection, setCrawlerModeSelection] = useState<'mock' | 'youtube' | 'instagram' | 'facebook' | 'telegram' | 'twitter'>('mock')
  const [crawlerKeywords, setCrawlerKeywords] = useState('')
  const [lookbackDays, setLookbackDays] = useState<number>(7)
  const [crawlerWarning, setCrawlerWarning] = useState<string | null>(null)
  const [backendCrawlerMode, setBackendCrawlerMode] = useState<'mock' | 'youtube' | 'instagram' | 'facebook' | 'telegram' | 'twitter'>('mock')
  const [youtubeKeyLoaded, setYoutubeKeyLoaded] = useState(false)
  const [metaTokenLoaded, setMetaTokenLoaded] = useState(false)
  const [telegramAuthLoaded, setTelegramAuthLoaded] = useState(false)
  const [twitterAuthLoaded, setTwitterAuthLoaded] = useState(false)
  const [queueSize, setQueueSize] = useState(0)
  const [postsFeed, setPostsFeed] = useState<Post[]>([])
  const [coordinationClusters, setCoordinationClusters] = useState<Cluster[]>([])
  const [trendsData, setTrendsData] = useState<TrendPoint[]>([])
  const [activeAlerts, setActiveAlerts] = useState<AlertItem[]>([])
  
  // Incidents states
  const [activeTab, setActiveTab] = useState<'monitor' | 'incidents' | 'network' | 'assistant'>('monitor')
  const [incidents, setIncidents] = useState<any[]>([])
  const [expandedIncident, setExpandedIncident] = useState<string | null>(null)

  // AI Assistant states
  const [chatHistory, setChatHistory] = useState<any[]>([])
  const [chatInput, setChatInput] = useState<string>('')
  const [isSendingQuery, setIsSendingQuery] = useState<boolean>(false)

  
  // Incident filter states
  const [filterIncidentSeverity, setFilterIncidentSeverity] = useState<string>('All')
  const [filterIncidentCategory, setFilterIncidentCategory] = useState<string>('All')
  const [filterIncidentKeyword, setFilterIncidentKeyword] = useState<string>('')
  const [exportLimitInput, setExportLimitInput] = useState<string>('10')

  // Interactive Sandbox state
  const [textInput, setTextInput] = useState("Alert: We will block the roads near Surat bypass tomorrow morning. Join the protest!")
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<{
    language: string;
    threatCategory: string;
    sentimentScore: number;
    confidence: number;
    threatScore: number;
  } | null>(null)

  // Image analysis states
  const [selectedImageFile, setSelectedImageFile] = useState<File | null>(null)
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null)
  const [isAnalyzingImage, setIsAnalyzingImage] = useState(false)
  const [imageAnalysisResult, setImageAnalysisResult] = useState<{
    status: string;
    extracted_text?: string;
    detected_language?: string;
    threat_category?: string;
    confidence?: number;
    text_extraction_confidence?: number;
    message?: string;
  } | null>(null)

  // Filter states
  const [filterLanguage, setFilterLanguage] = useState<string>('All')
  const [filterThreatLevel, setFilterThreatLevel] = useState<string>('All')
  const [filterCity, setFilterCity] = useState<string>('All')
  const [filterKeyword, setFilterKeyword] = useState<string>('')

  // UI state
  const [expandedCluster, setExpandedCluster] = useState<string | null>(null)
  const [hoveredTrendPoint, setHoveredTrendPoint] = useState<TrendPoint | null>(null)

  // Check backend server connection
  const checkConnection = async () => {
    const startTime = performance.now()
    try {
      const res = await fetch('http://127.0.0.1:8000/api/health')
      if (res.ok) {
        const data = await res.json()
        const endTime = performance.now()
        setLatency(Math.round(endTime - startTime))
        setHealthData(data)
        setConnectionStatus('online')
      } else {
        throw new Error()
      }
    } catch {
      setConnectionStatus('offline')
      setHealthData(null)
      setLatency(null)
    }
  }

  const checkCrawlerStatus = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/crawler/status')
      if (res.ok) {
        const data = await res.json()
        setCrawlerActive(data.active)
        setBackendCrawlerMode(data.mode || 'mock')
        setQueueSize(data.queue_size)
        setYoutubeKeyLoaded(!!data.youtube_key_loaded)
        setMetaTokenLoaded(!!data.meta_token_loaded)
        setTelegramAuthLoaded(!!data.telegram_auth_loaded)
        setTwitterAuthLoaded(!!data.twitter_auth_loaded)
      }
    } catch (err) {
      console.error('Failed to get crawler status', err)
    }
  }

  // Fetch trends data
  const fetchTrends = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/trends?interval=day')
      if (res.ok) {
        const data = await res.json()
        setTrendsData(data)
      }
    } catch (err) {
      console.error('Failed to fetch trends data', err)
    }
  }

  // Fetch coordination clusters
  const fetchCoordination = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/coordination')
      if (res.ok) {
        const data = await res.json()
        setCoordinationClusters(data)
        
        // Check for high-severity clusters (suspicion >= 75)
        data.forEach((cluster: Cluster) => {
          if (cluster.suspicion_score >= 75 && !globalAlertedIds.has(cluster.cluster_id)) {
            globalAlertedIds.add(cluster.cluster_id)
            const alertTime = new Date().toLocaleTimeString()
            const triggerList = cluster.heuristics.join(', ')
            setActiveAlerts(prev => [
              {
                id: cluster.cluster_id,
                type: 'cluster',
                title: `Coordinated Campaign Flagged`,
                description: `Campaign ${cluster.cluster_id} detected with suspicion score of ${cluster.suspicion_score}% (Triggers: ${triggerList})`,
                timestamp: alertTime,
                severity: 'critical'
              },
              ...prev
            ])

            // Auto dismiss after 6 seconds if not acknowledged
            setTimeout(() => {
              setActiveAlerts(prev => prev.filter(a => a.id !== cluster.cluster_id))
            }, 6000)
          }
        })
      }
    } catch (err) {
      console.error('Failed to fetch coordination clusters', err)
    }
  }

  // Fetch persistent incidents from backend
  const fetchIncidents = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/incidents')
      if (res.ok) {
        const data = await res.json()
        setIncidents(data)
      }
    } catch (err) {
      console.error('Failed to fetch incidents', err)
    }
  }

  // Export incident report as dynamic PDF file download
  const handleExportReport = (incident: any) => {
    window.open(`http://127.0.0.1:8000/api/incidents/${incident.incident_id}/pdf`, '_blank');
  }

  // Start/Stop Crawler
  const toggleCrawler = async () => {
    if (crawlerActive) {
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/crawler/stop`, { method: 'POST' })
        if (res.ok) {
          setCrawlerWarning(null)
          checkCrawlerStatus()
        }
      } catch (err) {
        console.error('Failed to stop crawler', err)
      }
    } else {
      let endpoint = 'start'
      let query = `?lookback_days=${lookbackDays}`
      if (crawlerModeSelection !== 'mock') {
        endpoint = 'start-live'
        query = `?platform=${crawlerModeSelection}&keywords=${encodeURIComponent(crawlerKeywords)}&lookback_days=${lookbackDays}`
      }
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/crawler/${endpoint}${query}`, { method: 'POST' })
        if (res.ok) {
          const data = await res.json()
          if (data.status === 'pending_meta_review' || data.status === 'pending_auth') {
            alert(data.message)
          }
          if (data.warning) {
            setCrawlerWarning(data.warning)
          } else {
            setCrawlerWarning(null)
          }
          checkCrawlerStatus()
        }
      } catch (err) {
        console.error(`Failed to start ${crawlerModeSelection} crawler`, err)
      }
    }
  }

  // Poll new crawled posts from backend
  const pollPosts = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/crawler/posts?limit=30')
      if (res.ok) {
        const newPosts: Post[] = await res.json()
        if (newPosts.length > 0) {
          // Prepend new posts and limit history to last 100
          setPostsFeed(prev => {
            const updated = [...newPosts, ...prev]
            return updated.slice(0, 100)
          })

          // Check for critical threats (Incitement to Violence) in newly polled posts
          newPosts.forEach(post => {
            if (post.threat_category === 'Incitement to Violence' && !globalAlertedIds.has(post.id)) {
              globalAlertedIds.add(post.id)
              const alertTime = new Date(post.timestamp).toLocaleTimeString()
              setActiveAlerts(prev => [
                {
                  id: post.id,
                  type: 'post',
                  title: `Incitement Threat Detected`,
                  description: `User ${post.username} on ${post.platform} posted: "${post.text.slice(0, 80)}..." in ${post.geo.city}`,
                  timestamp: alertTime,
                  severity: 'high'
                },
                ...prev
              ])

              // Auto dismiss after 6 seconds if not acknowledged
              setTimeout(() => {
                setActiveAlerts(prev => prev.filter(a => a.id !== post.id))
              }, 6000)
            }
          })

          // Refresh trends, coordination, and incidents data when new posts are ingested
          fetchTrends()
          fetchCoordination()
          fetchIncidents()
        }
      }
    } catch (err) {
      console.error('Failed to poll posts', err)
    }
  }

  // Ad-hoc classifier sandbox test
  const handleAnalyzeText = async () => {
    if (!textInput.trim()) return
    setIsAnalyzing(true)
    try {
      const response = await fetch('http://127.0.0.1:8000/api/classify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: textInput }),
      })
      
      if (response.ok) {
        const data = await response.json()
        setAnalysisResult({
          language: data.language,
          threatCategory: data.threat_category,
          sentimentScore: data.sentiment_score,
          confidence: data.confidence,
          threatScore: Math.round((1 - data.sentiment_score) * 100)
        })
      }
    } catch (err) {
      console.error("Classifier API failure", err)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedImageFile(file)
      if (imagePreviewUrl) {
        URL.revokeObjectURL(imagePreviewUrl)
      }
      setImagePreviewUrl(URL.createObjectURL(file))
    }
  }

  const handleAnalyzeImage = async () => {
    if (!selectedImageFile) return
    setIsAnalyzingImage(true)
    setImageAnalysisResult(null)
    
    const formData = new FormData()
    formData.append('file', selectedImageFile)
    
    try {
      const res = await fetch('http://127.0.0.1:8000/api/analyze-image', {
        method: 'POST',
        body: formData
      })
      if (res.ok) {
        const data = await res.json()
        setImageAnalysisResult(data)
      } else {
        console.error('Failed to analyze image')
      }
    } catch (err) {
      console.error('Failed to connect to image analysis API', err)
    } finally {
      setIsAnalyzingImage(false)
    }
  }

  const handleSendAssistantQuery = async (customQuestion?: string) => {
    const question = customQuestion !== undefined ? customQuestion : chatInput;
    if (!question.trim()) return;

    if (customQuestion === undefined) {
      setChatInput('');
    }

    const newUserMessage = { role: 'user', content: question };
    setChatHistory(prev => [...prev, newUserMessage]);
    setIsSendingQuery(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/assistant/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question })
      });
      if (res.ok) {
        const data = await res.json();
        const newAssistantMessage = {
          role: 'assistant',
          content: data.answer,
          dataUsed: data.data_used
        };
        setChatHistory(prev => [...prev, newAssistantMessage]);
      } else {
        const newAssistantMessage = {
          role: 'assistant',
          content: "Failed to communicate with assistant API server.",
          dataUsed: null
        };
        setChatHistory(prev => [...prev, newAssistantMessage]);
      }
    } catch (err) {
      const newAssistantMessage = {
        role: 'assistant',
        content: `Error: Could not connect to the API server.`,
        dataUsed: null
      };
      setChatHistory(prev => [...prev, newAssistantMessage]);
    } finally {
      setIsSendingQuery(false);
    }
  }

  // Prepopulate dashboard by draining some initial mock posts if database has them
  const prepopulateLocalFeed = async () => {
    // Attempt to pull a few initial posts already classified on main.py startup
    try {
      // Start backend crawler task briefly to push posts if database starts completely fresh
      // Wait, trends data has everything pre-populated. Let's seed initial 20 posts from local sample
      const res = await fetch('http://127.0.0.1:8000/api/crawler/posts?limit=15')
      if (res.ok) {
        const initialPosts = await res.json()
        setPostsFeed(initialPosts)
      }
    } catch (err) {
      console.error(err)
    }
  }

  // Initial dashboard mount loops
  useEffect(() => {
    checkConnection()
    checkCrawlerStatus()
    fetchTrends()
    fetchCoordination()
    fetchIncidents()
    prepopulateLocalFeed()

    // Status intervals
    const connInterval = setInterval(checkConnection, 15000)
    const statusInterval = setInterval(checkCrawlerStatus, 5000)
    const incidentsInterval = setInterval(fetchIncidents, 5000)
    
    return () => {
      clearInterval(connInterval)
      clearInterval(statusInterval)
      clearInterval(incidentsInterval)
    }
  }, [])

  // Poll posts only when crawler is active
  useEffect(() => {
    let pollInterval: NodeJS.Timeout
    if (crawlerActive) {
      pollInterval = setInterval(pollPosts, 3000)
    }
    return () => {
      if (pollInterval) clearInterval(pollInterval)
    }
  }, [crawlerActive])

  // Filter posts feed
  const filteredFeed = postsFeed.filter(post => {
    // Language Filter
    if (filterLanguage !== 'All' && post.language.toLowerCase() !== filterLanguage.toLowerCase()) {
      return false
    }
    // Threat level Filter
    if (filterThreatLevel !== 'All' && post.threat_category.toLowerCase() !== filterThreatLevel.toLowerCase()) {
      return false
    }
    // City Filter
    if (filterCity !== 'All' && post.geo.city.toLowerCase() !== filterCity.toLowerCase()) {
      return false
    }
    // Keyword Filter
    if (filterKeyword.trim() !== '') {
      const keyword = filterKeyword.toLowerCase()
      const matchesText = post.text.toLowerCase().includes(keyword)
      const matchesUser = post.username.toLowerCase().includes(keyword)
      if (!matchesText && !matchesUser) {
        return false
      }
    }
    return true
  })

  const sortedFilteredFeed = [...filteredFeed].sort((a, b) => {
    const fA = a.user_profile?.follower_count;
    const fB = b.user_profile?.follower_count;
    
    const hasA = typeof fA === 'number' && fA !== null && fA !== undefined;
    const hasB = typeof fB === 'number' && fB !== null && fB !== undefined;
    
    if (hasA && hasB) {
      if (fB !== fA) {
        return fB - fA;
      }
    } else if (hasA && !hasB) {
      return -1;
    } else if (!hasA && hasB) {
      return 1;
    }
    
    const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
    const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
    if (timeB !== timeA) {
      return timeB - timeA;
    }
    
    return a.id.localeCompare(b.id);
  });

  // Filter incidents list
  const filteredIncidents = incidents.filter(inc => {
    // Severity Filter
    if (filterIncidentSeverity !== 'All' && inc.severity.toLowerCase() !== filterIncidentSeverity.toLowerCase()) {
      return false
    }
    // Category Filter
    if (filterIncidentCategory !== 'All' && inc.threat_category.toLowerCase() !== filterIncidentCategory.toLowerCase()) {
      return false
    }
    // Keyword Filter
    if (filterIncidentKeyword.trim() !== '') {
      const query = filterIncidentKeyword.toLowerCase()
      const matchesID = inc.incident_id.toLowerCase().includes(query)
      const matchesSummary = inc.summary.toLowerCase().includes(query)
      const matchesGeo = inc.affected_geo.toLowerCase().includes(query)
      if (!matchesID && !matchesSummary && !matchesGeo) {
        return false
      }
    }
    return true
  })

  const getIncidentFollowerCount = (inc: any): number | undefined => {
    if (!inc.related_posts || inc.related_posts.length === 0) return undefined;
    const counts = inc.related_posts
      .map((p: any) => p.user_profile?.follower_count)
      .filter((c: any) => typeof c === 'number' && c !== null && c !== undefined);
    if (counts.length === 0) return undefined;
    return Math.max(...counts);
  };

  const sortedFilteredIncidents = [...filteredIncidents].sort((a, b) => {
    const fA = getIncidentFollowerCount(a);
    const fB = getIncidentFollowerCount(b);
    
    const hasA = typeof fA === 'number';
    const hasB = typeof fB === 'number';
    
    if (hasA && hasB) {
      if (fB !== fA) {
        return fB - fA;
      }
    } else if (hasA && !hasB) {
      return -1;
    } else if (!hasA && hasB) {
      return 1;
    }
    
    const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
    const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
    if (timeB !== timeA) {
      return timeB - timeA;
    }
    
    return a.incident_id.localeCompare(b.incident_id);
  });

  // Cities extracted from constants for filter dropdown
  const citiesList = ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Gandhinagar", "Bhavnagar", "Jamnagar", "Junagadh", "Anand", "Nadiad"]

  // Dismiss a high-severity warning alert banner
  const dismissAlert = (id: string) => {
    setActiveAlerts(prev => prev.filter(alert => alert.id !== id))
  }

  // Custom SVG Trends line chart logic
  const renderSVGChart = () => {
    if (trendsData.length === 0) {
      return (
        <div className="h-full flex items-center justify-center text-zinc-500 text-xs italic">
          No trends data loaded. Start crawler to record ingestion.
        </div>
      )
    }

    const width = 640
    const height = 180
    const padding = 25
    const chartWidth = width - 2 * padding
    const chartHeight = height - 2 * padding
    const maxVal = Math.max(...trendsData.map(pt => pt.post_count), 15)

    // Compute coordinate points
    const points = trendsData.map((pt, i) => {
      const x = padding + (i * chartWidth) / (trendsData.length - 1)
      const y = height - padding - (pt.post_count * chartHeight) / maxVal
      return { x, y, pt }
    })

    // Construct path line
    const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
    // Construct gradient area fill path
    const areaPath = `${linePath} L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`

    return (
      <div className="relative w-full h-[200px]">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full text-zinc-700">
          <defs>
            <linearGradient id="chartGlow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#818cf8" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#818cf8" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => {
            const yGrid = padding + ratio * chartHeight
            return (
              <line 
                key={idx}
                x1={padding} 
                y1={yGrid} 
                x2={width - padding} 
                y2={yGrid} 
                stroke="#27272a" 
                strokeWidth="1"
                strokeDasharray="4"
              />
            )
          })}

          {/* Area Fill */}
          <path d={areaPath} fill="url(#chartGlow)" />

          {/* Line Path */}
          <path d={linePath} fill="none" stroke="#6366f1" strokeWidth="2.5" strokeLinecap="round" />

          {/* Interactive dots and Spikes */}
          {points.map((p, idx) => {
            const isSpike = p.pt.is_spike
            return (
              <g 
                key={idx}
                onMouseEnter={() => setHoveredTrendPoint(p.pt)}
                onMouseLeave={() => setHoveredTrendPoint(null)}
                className="cursor-pointer"
              >
                {isSpike && (
                  <>
                    <circle cx={p.x} cy={p.y} r="10" fill="#ef4444" className="animate-ping opacity-40" />
                    <circle cx={p.x} cy={p.y} r="5" fill="#f43f5e" stroke="#ef4444" strokeWidth="1.5" />
                  </>
                )}
                
                {/* General dot hover target */}
                <circle 
                  cx={p.x} 
                  cy={p.y} 
                  r={isSpike ? "5" : "3.5"} 
                  fill={isSpike ? "#f43f5e" : "#4f46e5"} 
                  className="opacity-0 hover:opacity-100 transition-opacity" 
                />
              </g>
            )
          })}
        </svg>

        {/* Custom chart tooltip overlay */}
        {hoveredTrendPoint && (
          <div className="absolute top-2 left-1/2 transform -translate-x-1/2 z-20 bg-zinc-950/95 border border-zinc-800 p-2.5 rounded-lg text-[10px] font-mono shadow-2xl min-w-[180px] space-y-1">
            <div className="flex justify-between border-b border-zinc-800 pb-1">
              <span className="text-zinc-500">Date:</span>
              <span className="text-white font-semibold">{hoveredTrendPoint.timestamp}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Volume:</span>
              <span className="text-indigo-400 font-semibold">{hoveredTrendPoint.post_count} posts</span>
            </div>
            {hoveredTrendPoint.is_spike && (
              <div className="text-rose-400 font-semibold flex items-center gap-0.5 animate-pulse text-[9px]">
                ⚠️ ANOMALY VOLUME SPIKE DETECTED
              </div>
            )}
            <div className="text-zinc-400 mt-1">
              <span className="text-[9px] uppercase tracking-wide text-zinc-500 block font-semibold">Top Keywords</span>
              <span className="text-white block truncate">
                {Object.keys(hoveredTrendPoint.top_keywords).join(', ') || 'None'}
              </span>
            </div>
          </div>
        )}
      </div>
    )
  }

  // Get color badges for threat categories
  const getThreatBadgeStyle = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'incitement to violence':
      case 'incitement':
        return 'bg-rose-500/10 text-rose-400 border border-rose-500/20 shadow-md shadow-rose-950/20'
      case 'fake news':
      case 'fake_news':
        return 'bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-500/20'
      case 'inflammatory':
        return 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
      default:
        return 'bg-zinc-800 text-zinc-400 border border-zinc-700'
    }
  }

  // Get border outline style for post cards
  const getPostCardStyle = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'incitement to violence':
      case 'incitement':
        return 'border-rose-950/80 bg-rose-950/10 hover:border-rose-500/40'
      case 'fake news':
      case 'fake_news':
        return 'border-fuchsia-950/80 bg-fuchsia-950/10 hover:border-fuchsia-500/40'
      case 'inflammatory':
        return 'border-amber-950/80 bg-amber-950/10 hover:border-amber-500/40'
      default:
        return 'border-zinc-800 bg-zinc-900/40 hover:border-zinc-700'
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans flex flex-col relative selection:bg-rose-600/30 selection:text-rose-300 overflow-x-hidden">
      
      {/* Law-enforcement monitoring terminal grid overlays */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#000000_1px,transparent_1px),linear-gradient(to_bottom,#080808_1px,transparent_1px)] bg-[size:1.5rem_1.5rem] pointer-events-none opacity-45" />
      <div className="absolute top-0 right-0 w-[40rem] h-[40rem] bg-rose-500/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 left-0 w-[30rem] h-[30rem] bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />



      {/* Main Console Header */}
      <header className="relative border-b border-zinc-900 bg-zinc-900/40 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-zinc-950 border border-rose-900/50 flex items-center justify-center shadow-lg shadow-rose-900/5">
              <span className="text-rose-500 text-lg font-bold font-mono animate-pulse">⚙</span>
            </div>
            <div>
              <h1 className="text-md font-extrabold uppercase tracking-widest text-white flex items-center gap-2 font-mono">
                THREAT ANALYST CONSOLE
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  LIVE FEED
                </span>
              </h1>
              <p className="text-xs text-zinc-500 font-mono">Ingested queue anomalies: Gujarat cities cluster check</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Health pill */}
            <div className={`flex items-center space-x-2 px-3 py-1.5 rounded bg-zinc-950 border text-[11px] font-mono ${
              connectionStatus === 'online' 
                ? 'border-emerald-500/20 text-emerald-400' 
                : 'border-rose-500/20 text-rose-400 animate-pulse'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${
                connectionStatus === 'online' ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
              }`} />
              <span>{connectionStatus === 'online' ? `API ONLINE (${latency}ms)` : 'API OFFLINE'}</span>
            </div>

            {/* Live stream status */}
            <div className={`flex items-center space-x-2 px-3 py-1.5 rounded bg-zinc-950 border text-[11px] font-mono ${
              crawlerActive ? 'border-indigo-500/20 text-indigo-400' : 'border-zinc-800 text-zinc-500'
            }`}>
              <span>CRAWLER QUEUE: {queueSize} ITEMS</span>
            </div>

            {/* Ingestion stream control button */}
            <button 
              onClick={toggleCrawler}
              disabled={connectionStatus !== 'online'}
              className={`px-4 py-1.5 rounded text-xs font-bold font-mono transition-all cursor-pointer disabled:opacity-50 ${
                crawlerActive 
                  ? 'bg-rose-950 border border-rose-500 hover:bg-rose-900 text-white' 
                  : 'bg-zinc-950 border border-indigo-500 hover:bg-zinc-900 text-indigo-400'
              }`}
            >
              {crawlerActive ? '■ HALT STREAMING' : '▶ INGEST LIVE STREAM'}
            </button>
          </div>
        </div>
      </header>

      {/* Tab Switcher */}
      <div className="max-w-7xl mx-auto px-6 pt-6 w-full flex border-b border-zinc-900 z-10 relative">
        <button
          onClick={() => setActiveTab('monitor')}
          className={`px-6 py-2.5 font-mono text-xs font-bold uppercase tracking-widest border-b-2 cursor-pointer transition-all ${
            activeTab === 'monitor' 
              ? 'border-indigo-500 text-indigo-400 bg-indigo-950/10' 
              : 'border-transparent text-zinc-500 hover:text-zinc-300'
          }`}
        >
          🖥️ Live Monitor
        </button>
        <button
          onClick={() => setActiveTab('incidents')}
          className={`px-6 py-2.5 font-mono text-xs font-bold uppercase tracking-widest border-b-2 cursor-pointer transition-all flex items-center gap-2 ${
            activeTab === 'incidents' 
              ? 'border-rose-500 text-rose-400 bg-rose-950/10' 
              : 'border-transparent text-zinc-500 hover:text-zinc-300'
          }`}
        >
          🚨 Incident Log
          <span className={`px-2 py-0.5 rounded text-[10px] ${incidents.length > 0 ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 'bg-zinc-900 text-zinc-600'}`}>
            {incidents.length}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('network')}
          className={`px-6 py-2.5 font-mono text-xs font-bold uppercase tracking-widest border-b-2 cursor-pointer transition-all flex items-center gap-2 ${
            activeTab === 'network' 
              ? 'border-indigo-500 text-indigo-400 bg-indigo-950/10' 
              : 'border-transparent text-zinc-500 hover:text-zinc-300'
          }`}
        >
          🕸️ Coordination Network
        </button>
        <button
          onClick={() => setActiveTab('assistant')}
          className={`px-6 py-2.5 font-mono text-xs font-bold uppercase tracking-widest border-b-2 cursor-pointer transition-all flex items-center gap-2 ${
            activeTab === 'assistant' 
              ? 'border-emerald-500 text-emerald-400 bg-emerald-950/10' 
              : 'border-transparent text-zinc-500 hover:text-zinc-300'
          }`}
        >
          💬 AI Assistant
        </button>
      </div>

      {/* Main Content Layout */}
      {activeTab === 'incidents' ? (
        <main className="flex-1 max-w-7xl mx-auto px-6 py-6 w-full relative z-10 space-y-6">
          <div className="bg-zinc-900/40 border border-zinc-900 rounded-xl p-5 backdrop-blur-md shadow-xl flex flex-col space-y-4">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 border-b border-zinc-900 pb-4">
              <div>
                <h3 className="text-xs font-extrabold uppercase tracking-widest text-zinc-400 font-mono">
                  🚨 Persistent Critical Threat Incidents ({sortedFilteredIncidents.length} matched)
                </h3>
                <p className="text-[10px] text-zinc-500 font-mono">Generated from Incitement and Coordination threshold triggers</p>
              </div>
            </div>

            {/* Incident filter controls */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 p-3 rounded-lg bg-zinc-950/60 border border-zinc-900/50">
              {/* Severity dropdown */}
              <div>
                <label className="block text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 font-mono">Severity Level</label>
                <select 
                  value={filterIncidentSeverity}
                  onChange={(e) => setFilterIncidentSeverity(e.target.value)}
                  className="w-full text-[11px] font-mono bg-zinc-900 border border-zinc-800 rounded p-1 text-zinc-300"
                >
                  <option value="All">ALL SEVERITIES</option>
                  <option value="HIGH">HIGH</option>
                  <option value="CRITICAL">CRITICAL</option>
                </select>
              </div>

              {/* Category dropdown */}
              <div>
                <label className="block text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 font-mono">Incident Type</label>
                <select 
                  value={filterIncidentCategory}
                  onChange={(e) => setFilterIncidentCategory(e.target.value)}
                  className="w-full text-[11px] font-mono bg-zinc-900 border border-zinc-800 rounded p-1 text-zinc-300"
                >
                  <option value="All">ALL TYPES</option>
                  <option value="Incitement to Violence">Incitement to Violence</option>
                  <option value="Coordinated Amplification">Coordinated Amplification</option>
                </select>
              </div>

              {/* Text query filter */}
              <div>
                <label className="block text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 font-mono">Search Incident Log</label>
                <input 
                  type="text"
                  placeholder="Query summary/location/ID..."
                  value={filterIncidentKeyword}
                  onChange={(e) => setFilterIncidentKeyword(e.target.value)}
                  className="w-full text-[11px] font-mono bg-zinc-900 border border-zinc-800 rounded p-1 text-zinc-300 placeholder:text-zinc-700"
                />
              </div>

              {/* Excel Export controls */}
              <div>
                <label className="block text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 font-mono">Export Top N</label>
                <div className="flex gap-2">
                  <input 
                    type="number"
                    min="1"
                    value={exportLimitInput}
                    onChange={(e) => setExportLimitInput(e.target.value)}
                    className="w-16 text-[11px] font-mono bg-zinc-900 border border-zinc-800 rounded p-1 text-zinc-300 text-center"
                  />
                  <button
                    disabled={!/^[1-9]\d*$/.test(exportLimitInput)}
                    onClick={() => {
                      const limit = parseInt(exportLimitInput, 10);
                      window.open(`http://127.0.0.1:8000/api/incidents/export?n=${limit}`, '_blank');
                    }}
                    className="flex-1 px-3 py-1 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white border border-zinc-800 text-[10px] font-bold font-mono rounded cursor-pointer transition-all disabled:opacity-40 disabled:cursor-not-allowed uppercase"
                  >
                    Download Excel
                  </button>
                </div>
              </div>
            </div>

            {/* List of incidents */}
            <div className="space-y-4 overflow-y-auto max-h-[580px] pr-2">
              {sortedFilteredIncidents.length === 0 ? (
                <div className="h-48 flex items-center justify-center text-zinc-600 text-xs italic">
                  No incident records matched current filters.
                </div>
              ) : (
                sortedFilteredIncidents.map((inc) => {
                  const isCritical = inc.severity === 'CRITICAL'
                  const isExpanded = expandedIncident === inc.incident_id
                  return (
                    <div 
                      key={inc.incident_id}
                      className={`rounded-lg border bg-zinc-950/40 hover:bg-zinc-950/60 transition-all ${
                        isCritical ? 'border-rose-950/80 hover:border-rose-500/30' : 'border-amber-950/80 hover:border-amber-500/30'
                      }`}
                    >
                      {/* Summary Row */}
                      <div 
                        onClick={() => setExpandedIncident(isExpanded ? null : inc.incident_id)}
                        className="p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-3 cursor-pointer select-none"
                      >
                        <div className="space-y-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-mono font-extrabold text-xs text-white">{inc.incident_id}</span>
                            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded font-mono ${
                              isCritical ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            }`}>
                              {inc.severity}
                            </span>
                            <span className="text-[10px] text-zinc-500 font-mono">
                              {inc.threat_category}
                            </span>
                          </div>
                          <h4 className="text-xs font-bold text-zinc-200 mt-1 leading-snug">{inc.summary}</h4>
                        </div>

                        <div className="flex items-center gap-4 text-[10px] font-mono text-zinc-500">
                          {getIncidentFollowerCount(inc) !== undefined && (
                            <div>👥 REACH: <strong className="text-zinc-400">{getIncidentFollowerCount(inc)?.toLocaleString()}</strong></div>
                          )}
                          <div>📍 {inc.affected_geo}</div>
                          <div>📅 {new Date(inc.timestamp).toLocaleString()}</div>
                          <div className="text-zinc-600 text-xs font-bold w-4 text-center">
                            {isExpanded ? '▲' : '▼'}
                          </div>
                        </div>
                      </div>

                      {/* Expanded Section */}
                      {isExpanded && (
                        <div className="px-4 pb-4 border-t border-zinc-900 pt-4 space-y-4">
                          {/* Related Posts */}
                          <div className="space-y-2">
                            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest block font-mono">
                              Matched Source Posts ({inc.related_posts.length})
                            </span>
                            <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                              {inc.related_posts.map((rp: any, idx: number) => (
                                <div key={idx} className="p-3 rounded bg-zinc-900/60 border border-zinc-900 space-y-1.5">
                                  <div className="flex justify-between items-center text-[10px] font-mono">
                                    <div className="flex items-center gap-2">
                                      <span className="font-bold text-zinc-300">{rp.username}</span>
                                      <span className="text-zinc-600 font-normal">on</span>
                                      <span className="text-indigo-400 uppercase font-semibold text-[9px]">{rp.platform}</span>
                                    </div>
                                    <span className="text-zinc-500 text-[9px]">
                                      {new Date(rp.timestamp).toLocaleTimeString()}
                                    </span>
                                  </div>
                                  <p className="text-xs text-zinc-400 leading-relaxed font-sans">{rp.text}</p>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Duty Officer Template */}
                          <div className="space-y-2">
                            <div className="flex justify-between items-center">
                              <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest block font-mono">
                                Suggested Escalation Template
                              </span>
                              <button 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  navigator.clipboard.writeText(inc.suggested_escalation_template);
                                  alert("Escalation template copied to clipboard!");
                                }}
                                className="text-[9px] font-mono text-indigo-400 hover:text-indigo-300 underline cursor-pointer bg-transparent border-none"
                              >
                                Copy Template
                              </button>
                            </div>
                            <pre className="p-3 rounded bg-zinc-950 border border-zinc-900 font-mono text-[10px] text-rose-400/90 whitespace-pre-wrap leading-relaxed overflow-x-auto shadow-inner">
                              {inc.suggested_escalation_template}
                            </pre>
                          </div>

                          {/* Action Row */}
                          <div className="flex justify-end pt-2">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleExportReport(inc);
                              }}
                              className="px-4 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white border border-zinc-800 text-xs font-bold font-mono rounded cursor-pointer transition-all flex items-center gap-1.5"
                            >
                              📥 Export as Report (.pdf)
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </main>
      ) : activeTab === 'network' ? (
        <main className="flex-1 max-w-7xl mx-auto px-6 py-6 w-full relative z-10">
          <CoordinationNetworkGraph />
        </main>
      ) : activeTab === 'assistant' ? (
        <main className="flex-1 max-w-7xl mx-auto px-6 py-6 w-full relative z-10">
          <div className="bg-zinc-900/40 border border-zinc-900 rounded-xl p-5 backdrop-blur-md shadow-xl flex flex-col h-[600px]">
            {/* Header */}
            <div className="border-b border-zinc-900 pb-3 flex justify-between items-center">
              <div>
                <h3 className="text-xs font-extrabold uppercase tracking-widest text-zinc-400 font-mono flex items-center gap-2">
                  💬 Data-Aware AI Assistant
                </h3>
                <p className="text-[10px] text-zinc-500 font-mono">
                  Powered by Gemini 1.5 Flash • Rule-Based Factual Grounding
                </p>
              </div>
            </div>

            {/* Chat message area */}
            <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-2 scrollbar-thin scrollbar-thumb-zinc-800">
              {chatHistory.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center space-y-4 text-zinc-500 font-mono text-[10px]">
                  <span className="text-3xl">🤖</span>
                  <div className="max-w-md">
                    <p className="font-bold text-zinc-400">Welcome to the Threat Intelligence Assistant</p>
                    <p className="text-zinc-600 mt-1 leading-relaxed">
                      Ask deterministic questions about incidents, threat trends, bot coordination clusters, or system status. The assistant will retrieve live database context to answer.
                    </p>
                  </div>
                  
                  {/* Suggestion Chips */}
                  <div className="flex flex-wrap gap-2 justify-center max-w-lg mt-4">
                    {[
                      "How many incidents in Rajkot?",
                      "Summarize the coordination clusters",
                      "What's the current threat trend?",
                      "Overall system status",
                      "Lookup cluster CLUSTER_01"
                    ].map((s, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSendAssistantQuery(s)}
                        className="px-3 py-1.5 rounded-full bg-zinc-950 border border-zinc-800 hover:border-indigo-500 hover:text-indigo-400 text-zinc-400 font-bold transition-all cursor-pointer"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                chatHistory.map((msg: any, idx: number) => (
                  <div
                    key={idx}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-2xl rounded-lg p-3.5 font-sans text-xs space-y-2 leading-relaxed ${
                        msg.role === 'user'
                          ? 'bg-indigo-600 text-white rounded-br-none'
                          : 'bg-zinc-950/80 border border-zinc-900 text-zinc-300 rounded-bl-none'
                      }`}
                    >
                      <span className="block text-[8px] font-mono uppercase tracking-widest font-extrabold text-zinc-500">
                        {msg.role === 'user' ? 'Analyst' : 'Assistant'}
                      </span>
                      <p className="whitespace-pre-wrap select-text">{msg.content}</p>
                      
                      {msg.dataUsed && Object.keys(msg.dataUsed).length > 0 && (
                        <div className="pt-2 border-t border-zinc-900 font-mono text-[9px]">
                          <details className="cursor-pointer group">
                            <summary className="text-indigo-400 font-bold hover:text-indigo-300 select-none">
                              🔍 View Real System Data Backing Answer
                            </summary>
                            <pre className="mt-2 bg-zinc-950/90 border border-zinc-900 rounded p-2.5 overflow-auto max-h-[160px] text-indigo-300 select-text">
                              {JSON.stringify(msg.dataUsed, null, 2)}
                            </pre>
                          </details>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
              {isSendingQuery && (
                <div className="flex justify-start">
                  <div className="bg-zinc-950/80 border border-zinc-900 rounded-lg p-3 rounded-bl-none text-zinc-500 font-mono text-[10px] flex items-center gap-2">
                    <span className="animate-spin inline-block w-3.5 h-3.5 border-2 border-indigo-500 border-t-transparent rounded-full" />
                    Assistant is querying live database...
                  </div>
                </div>
              )}
            </div>

            {/* Input area */}
            <div className="border-t border-zinc-900 pt-3 flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !isSendingQuery) {
                    handleSendAssistantQuery(chatInput);
                  }
                }}
                placeholder="Ask about incidents, trends, bot clusters, or system status..."
                className="flex-1 text-[11px] font-mono bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-zinc-300 placeholder:text-zinc-700 focus:border-indigo-500 focus:outline-none"
              />
              <button
                onClick={() => handleSendAssistantQuery(chatInput)}
                disabled={isSendingQuery || !chatInput.trim()}
                className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-[11px] font-bold uppercase tracking-wider transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                Send
              </button>
            </div>
          </div>
        </main>
      ) : (
        <main className="flex-1 max-w-7xl mx-auto px-6 py-6 w-full grid grid-cols-1 lg:grid-cols-12 gap-6 relative z-10">
        
        {/* Left Side: Filter and Ingestion Feed */}
        <section className="lg:col-span-8 space-y-6 flex flex-col min-h-[500px]">
          
          {/* 🛰️ Data Ingestion Source & Mode Controller */}
          <div className="bg-zinc-900/40 border border-zinc-900 rounded-xl p-5 backdrop-blur-md shadow-xl flex flex-col space-y-4">
            <div className="flex justify-between items-center border-b border-zinc-900 pb-3">
              <div>
                <h3 className="text-xs font-extrabold uppercase tracking-widest text-zinc-400 font-mono flex items-center gap-2">
                  <span className="animate-pulse text-indigo-500">🛰️</span> Ingestion Stream Control Panel
                </h3>
                <p className="text-[10px] text-zinc-500 font-mono">
                  Current Mode: <span className="text-indigo-400 font-bold uppercase">{backendCrawlerMode === 'youtube' ? 'Live YouTube Crawler' : backendCrawlerMode === 'instagram' ? 'Live Instagram Crawler' : backendCrawlerMode === 'facebook' ? 'Live Facebook Crawler' : backendCrawlerMode === 'telegram' ? 'Live Telegram Crawler' : backendCrawlerMode === 'twitter' ? 'Live X Crawler' : 'Mock Ingestion Feed'}</span>
                  {crawlerActive ? (
                    <span className="ml-2 px-1.5 py-0.5 rounded text-[8px] bg-rose-500/10 text-rose-400 border border-rose-500/20 font-bold animate-pulse">ACTIVE STREAMING</span>
                  ) : (
                    <span className="ml-2 px-1.5 py-0.5 rounded text-[8px] bg-zinc-800 text-zinc-400 border border-zinc-700 font-bold">STANDBY</span>
                  )}
                </p>
              </div>
              <span className="text-[10px] text-zinc-500 font-mono">QUEUE: {queueSize} ITEMS</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end">
              {/* Ingestion Mode Select */}
              <div className="md:col-span-4">
                <label className="block text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 font-mono">Select Source Mode</label>
                <select
                  value={crawlerModeSelection}
                  onChange={(e) => setCrawlerModeSelection(e.target.value as 'mock' | 'youtube' | 'instagram' | 'facebook' | 'telegram' | 'twitter')}
                  disabled={crawlerActive}
                  className="w-full text-[11px] font-mono bg-zinc-900 border border-zinc-800 rounded p-2 text-zinc-300 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option value="mock">MOCK SANDBOX FEED (DEFAULT)</option>
                  <option value="youtube">LIVE YOUTUBE MODE (REAL-TIME)</option>
                  <option value="instagram">LIVE INSTAGRAM MODE (REAL-TIME)</option>
                  <option value="facebook">LIVE FACEBOOK MODE (REAL-TIME)</option>
                  <option value="telegram">LIVE TELEGRAM MODE (REAL-TIME)</option>
                  <option value="twitter">LIVE X MODE (REAL-TIME)</option>
                </select>
              </div>

              {/* YouTube Keyword Search Input */}
              <div className="md:col-span-3">
                <label className="block text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 font-mono">
                  Live Search Query / Keywords
                </label>
                <input
                  type="text"
                  placeholder="e.g. Gujarat, protest, blockades"
                  value={crawlerKeywords}
                  onChange={(e) => setCrawlerKeywords(e.target.value)}
                  disabled={crawlerActive || crawlerModeSelection === 'mock'}
                  className="w-full text-[11px] font-mono bg-zinc-900 border border-zinc-800 rounded p-2 text-zinc-300 placeholder:text-zinc-700 disabled:opacity-40 disabled:cursor-not-allowed"
                />
              </div>

              {/* Lookback Window Input */}
              <div className="md:col-span-2">
                <label className="block text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 font-mono">
                  Lookback (Days)
                </label>
                <input
                  type="number"
                  min={1}
                  value={lookbackDays}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10);
                    if (!isNaN(val)) {
                      setLookbackDays(Math.max(val, 1));
                    } else {
                      setLookbackDays(7);
                    }
                  }}
                  disabled={crawlerActive}
                  className="w-full text-[11px] font-mono bg-zinc-900 border border-zinc-800 rounded p-2 text-zinc-300 placeholder:text-zinc-700 disabled:opacity-40 disabled:cursor-not-allowed text-center font-bold"
                />
              </div>

              {/* Action Start / Stop Button */}
              <div className="md:col-span-3">
                {((crawlerModeSelection === 'instagram' || crawlerModeSelection === 'facebook') && !metaTokenLoaded) ? (
                  <button
                    disabled={true}
                    className="w-full py-2 rounded text-[11px] font-extrabold font-mono bg-zinc-950 border border-amber-500/20 text-amber-500/60 tracking-widest cursor-not-allowed uppercase"
                  >
                    AWAITING ACCESS
                  </button>
                ) : (crawlerModeSelection === 'twitter' && !twitterAuthLoaded) ? (
                  <button
                    disabled={true}
                    className="w-full py-2 rounded text-[11px] font-extrabold font-mono bg-zinc-950 border border-amber-500/20 text-amber-500/60 tracking-widest cursor-not-allowed uppercase"
                  >
                    PAID API REQ
                  </button>
                ) : (crawlerModeSelection === 'telegram' && !telegramAuthLoaded) ? (
                  <button
                    disabled={true}
                    className="w-full py-2 rounded text-[11px] font-extrabold font-mono bg-zinc-950 border border-rose-500/20 text-rose-500/60 tracking-widest cursor-not-allowed uppercase"
                  >
                    AWAITING AUTH
                  </button>
                ) : (
                  <button
                    onClick={toggleCrawler}
                    disabled={connectionStatus !== 'online'}
                    className={`w-full py-2 rounded text-xs font-bold font-mono transition-all cursor-pointer disabled:opacity-50 tracking-widest ${
                      crawlerActive
                        ? 'bg-rose-950 border border-rose-500 hover:bg-rose-900 text-white font-extrabold shadow-lg shadow-rose-900/10'
                        : 'bg-zinc-950 border border-indigo-500 hover:bg-zinc-900 text-indigo-400 font-extrabold shadow-lg shadow-indigo-900/5'
                    }`}
                  >
                    {crawlerActive ? '■ HALT STREAM' : '▶ START STREAM'}
                  </button>
                )}
              </div>
            </div>

            {/* Pending platform approval state warning banner */}
            {(crawlerModeSelection === 'instagram' || crawlerModeSelection === 'facebook') && !metaTokenLoaded && (
              <div className="p-3 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg text-[11px] font-mono flex items-start gap-2.5">
                <span className="text-sm">⚠️</span>
                <div>
                  <div className="font-bold uppercase tracking-wider text-[10px]">Awaiting Platform API Approval</div>
                  <div className="text-zinc-400 text-[9px] mt-0.5">
                    Instagram/Facebook crawler feeds are in review/scaffold mode. Active scraping is disabled pending Meta App Review for public content access permissions (<code className="bg-zinc-950 px-1 py-0.5 rounded text-amber-300">pages_public_content_access</code>).
                  </div>
                </div>
              </div>
            )}

            {/* Pending Twitter / X token warning banner */}
            {crawlerModeSelection === 'twitter' && !twitterAuthLoaded && (
              <div className="p-3 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg text-[11px] font-mono flex items-start gap-2.5">
                <span className="text-sm">⚠️</span>
                <div>
                  <div className="font-bold uppercase tracking-wider text-[10px]">Paid API Tier Required</div>
                  <div className="text-zinc-400 text-[9px] mt-0.5">
                    X (Twitter) crawler requires purchased API credits. Active scraping is disabled because <code className="bg-zinc-950 px-1 py-0.5 rounded text-amber-300">TWITTER_BEARER_TOKEN</code> is not configured in `.env` (no free tier available as of Feb 2026).
                  </div>
                </div>
              </div>
            )}

            {/* Pending Telegram authorization warning banner */}
            {crawlerModeSelection === 'telegram' && !telegramAuthLoaded && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg text-[11px] font-mono flex items-start gap-2.5">
                <span className="text-sm">⚠️</span>
                <div>
                  <div className="font-bold uppercase tracking-wider text-[10px]">Awaiting Telegram Ingestion Auth</div>
                  <div className="text-zinc-400 text-[9px] mt-0.5">
                    Telegram MTProto client is not configured or authenticated. Please ensure <code className="bg-zinc-950 px-1 py-0.5 rounded text-rose-300">TELEGRAM_API_ID</code> & <code className="bg-zinc-950 px-1 py-0.5 rounded text-rose-300">TELEGRAM_API_HASH</code> are added to `.env` and run the interactive CLI helper <code className="bg-zinc-950 px-1 py-0.5 rounded text-rose-300">login_telegram.py</code> to verify the session.
                  </div>
                </div>
              </div>
            )}
            {/* API limit notice banner */}
            {crawlerWarning && (
              <div className="p-3 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg text-[11px] font-mono flex items-start gap-2.5">
                <span className="text-sm">⚠️</span>
                <div>
                  <div className="font-bold uppercase tracking-wider text-[10px]">API Window Limit Notice</div>
                  <div className="text-zinc-400 text-[9px] mt-0.5">{crawlerWarning}</div>
                </div>
              </div>
            )}
          </div>
          
          {/* Trends Anomaly Chart */}
          <div className="bg-zinc-900/40 border border-zinc-900 rounded-xl p-5 backdrop-blur-md shadow-xl flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-extrabold uppercase tracking-widest text-zinc-400 font-mono">
                📈 Historical Volume & Spike Detection (30 Days)
              </h3>
              <span className="text-[10px] text-zinc-500 font-mono">Aggregate: DAILY WINDOWS</span>
            </div>
            <div className="p-2.5 rounded bg-zinc-950/60 border border-zinc-900/50">
              {renderSVGChart()}
            </div>
          </div>

          {/* Live Feed Controller */}
          <div className="bg-zinc-900/40 border border-zinc-900 rounded-xl p-5 backdrop-blur-md shadow-xl flex-1 flex flex-col space-y-4">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 border-b border-zinc-900 pb-4">
              <div>
                <h3 className="text-xs font-extrabold uppercase tracking-widest text-zinc-400 font-mono">
                  🚨 Real-time Social Ingestion Feed ({filteredFeed.length} matched)
                </h3>
                <p className="text-[10px] text-zinc-500 font-mono">Parsed via BaseCrawler queue stream</p>
              </div>

              {/* Feed reset or count stats */}
              {postsFeed.length > 0 && (
                <button 
                  onClick={() => { setPostsFeed([]); setActiveAlerts([]); }}
                  className="text-[9px] font-mono text-zinc-500 hover:text-zinc-300 uppercase underline"
                >
                  Clear Feed Buffer
                </button>
              )}
            </div>

            {/* Filter controls row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-3 rounded-lg bg-zinc-950/60 border border-zinc-900/50">
              {/* Threat dropdown */}
              <div>
                <label className="block text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 font-mono">Threat Category</label>
                <select 
                  value={filterThreatLevel}
                  onChange={(e) => setFilterThreatLevel(e.target.value)}
                  className="w-full text-[11px] font-mono bg-zinc-900 border border-zinc-800 rounded p-1 text-zinc-300"
                >
                  <option value="All">ALL LEVELS</option>
                  <option value="Neutral">Neutral</option>
                  <option value="Inflammatory">Inflammatory</option>
                  <option value="Incitement to Violence">Incitement</option>
                  <option value="Fake News">Fake News</option>
                </select>
              </div>

              {/* Language dropdown */}
              <div>
                <label className="block text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 font-mono">Language</label>
                <select 
                  value={filterLanguage}
                  onChange={(e) => setFilterLanguage(e.target.value)}
                  className="w-full text-[11px] font-mono bg-zinc-900 border border-zinc-800 rounded p-1 text-zinc-300"
                >
                  <option value="All">ALL LANGUAGES</option>
                  <option value="English">English</option>
                  <option value="Hindi">Hindi</option>
                  <option value="Gujarati">Gujarati</option>
                  <option value="Hinglish">Hinglish</option>
                  <option value="Gujlish">Gujlish</option>
                </select>
              </div>

              {/* City dropdown */}
              <div>
                <label className="block text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 font-mono">City / Location</label>
                <select 
                  value={filterCity}
                  onChange={(e) => setFilterCity(e.target.value)}
                  className="w-full text-[11px] font-mono bg-zinc-900 border border-zinc-800 rounded p-1 text-zinc-300"
                >
                  <option value="All">ALL CITIES</option>
                  {citiesList.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>

              {/* Keyword text search */}
              <div>
                <label className="block text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5 font-mono">Keyword Search</label>
                <input 
                  type="text"
                  placeholder="Query text/user..."
                  value={filterKeyword}
                  onChange={(e) => setFilterKeyword(e.target.value)}
                  className="w-full text-[11px] font-mono bg-zinc-900 border border-zinc-800 rounded p-1 text-zinc-300 placeholder:text-zinc-700"
                />
              </div>
            </div>

            {/* Scrollable feed list */}
            <div className="flex-1 overflow-y-auto max-h-[420px] pr-2 space-y-3">
              {filteredFeed.length === 0 ? (
                <div className="h-48 flex flex-col items-center justify-center text-zinc-600 text-xs italic space-y-1">
                  <span>No matching posts in console feed buffer.</span>
                  {!crawlerActive && <span className="text-[10px] text-indigo-400 not-italic">Click "Ingest Live Stream" above to stream posts.</span>}
                </div>
              ) : (
                sortedFilteredFeed.map((post) => (
                  <div 
                    key={post.id} 
                    className={`p-3 rounded-lg border transition-all duration-200 flex flex-col gap-2 ${getPostCardStyle(post.threat_category)}`}
                  >
                    <div className="flex items-center justify-between text-[10px]">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-zinc-200 font-mono">{post.username}</span>
                        <span className="text-zinc-600 font-mono">on</span>
                        <span className="font-semibold text-zinc-400 uppercase tracking-wide font-mono text-[9px]">
                          {post.platform}
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded font-mono ${getThreatBadgeStyle(post.threat_category)}`}>
                          {post.threat_category}
                        </span>
                        <span className="text-zinc-500 font-mono text-[9px]">
                          {new Date(post.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>

                    <p className="text-xs text-zinc-300 font-sans leading-relaxed">{post.text}</p>

                    <div className="flex justify-between items-center border-t border-zinc-900/60 pt-2 text-[9px] font-mono text-zinc-500">
                      <div>
                        📍 {post.geo.city} <span className="text-[8px] text-zinc-600">({post.geo.latitude}, {post.geo.longitude})</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span>LANG: <strong className="text-zinc-400">{post.language.toUpperCase()}</strong></span>
                        {post.user_profile && (
                          <span>FOLLOWERS: <strong className="text-zinc-400">{post.user_profile.follower_count}</strong></span>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        {/* Right Side: Coordination Panels & Small Sandbox */}
        <section className="lg:col-span-4 space-y-6">
          
          {/* Critical Incident Log Panel (Dedicated Region) */}
          <div className="bg-zinc-900/40 border border-zinc-900 rounded-xl p-5 backdrop-blur-md shadow-xl flex flex-col">
            <div className="flex items-center justify-between mb-3 border-b border-zinc-900 pb-2">
              <h3 className="text-xs font-extrabold uppercase tracking-widest text-rose-500 font-mono flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full bg-rose-500 ${activeAlerts.length > 0 ? 'animate-pulse' : 'opacity-30'}`} />
                🚨 Critical Incident Alerter
              </h3>
              <span className="text-[9px] font-mono text-zinc-500">
                {activeAlerts.length} ACTIVE
              </span>
            </div>

            <div className="space-y-3">
              {activeAlerts.length === 0 ? (
                <div className="py-6 flex flex-col items-center justify-center border border-dashed border-zinc-800 rounded bg-zinc-950/20 text-emerald-500 text-[10px] font-mono tracking-wider">
                  <span className="animate-pulse">● SYSTEMS STABLE / NO ALERTS</span>
                </div>
              ) : (
                <>
                  <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
                    {activeAlerts.slice(0, 3).map((alert) => (
                      <div 
                        key={alert.id}
                        className="p-3 rounded border border-rose-950/80 bg-rose-950/20 flex items-start gap-2.5 transition-all duration-300"
                      >
                        <div className="flex-shrink-0 w-6 h-6 rounded bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-[10px]">
                          ⚠️
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between text-[8px] font-mono">
                            <span className="font-bold text-rose-500 uppercase tracking-widest">
                              {alert.type === 'cluster' ? 'CAMPAIGN' : 'POST'}
                            </span>
                            <span className="text-zinc-500">{alert.timestamp}</span>
                          </div>
                          <h4 className="text-[10px] font-bold text-white mt-0.5">{alert.title}</h4>
                          <p className="text-[9px] text-zinc-400 mt-1 leading-relaxed font-mono truncate">{alert.description}</p>
                          <button 
                            onClick={() => dismissAlert(alert.id)}
                            className="mt-1.5 text-[8px] font-bold text-zinc-300 hover:text-white bg-rose-950/40 hover:bg-rose-900 border border-rose-500/20 px-2 py-0.5 rounded cursor-pointer transition-all"
                          >
                            DISMISS
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                  {activeAlerts.length > 3 && (
                    <div className="text-right text-[9px] font-mono text-zinc-500 pt-1 pr-1">
                      + {activeAlerts.length - 3} more active warning flags collapsed
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Coordination Clusters Card Deck */}
          <div className="bg-zinc-900/40 border border-zinc-900 rounded-xl p-5 backdrop-blur-md shadow-xl flex flex-col">
            <div className="flex items-center justify-between mb-3 border-b border-zinc-900 pb-2">
              <h3 className="text-xs font-extrabold uppercase tracking-widest text-rose-500 font-mono flex items-center gap-1">
                🛡️ Coordinated bot networks
              </h3>
              <span className="text-[9px] text-zinc-500 font-mono">Size &gt;= 3</span>
            </div>

            <div className="space-y-4 max-h-[360px] overflow-y-auto pr-1">
              {coordinationClusters.length === 0 ? (
                <div className="h-32 flex items-center justify-center text-zinc-600 text-xs italic">
                  No active bot campaigns flagged.
                </div>
              ) : (
                coordinationClusters.map((cluster) => {
                  const isHighThreat = cluster.suspicion_score >= 75
                  return (
                    <div 
                      key={cluster.cluster_id}
                      className={`p-3.5 rounded-lg border bg-zinc-950/60 transition-all ${
                        isHighThreat ? 'border-rose-900/70 hover:border-rose-500/50' : 'border-zinc-800 hover:border-zinc-700'
                      }`}
                    >
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-xs font-extrabold uppercase text-white font-mono">{cluster.cluster_id.toUpperCase()}</span>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[9px] text-zinc-500 font-mono">Suspicion:</span>
                          <span className={`text-[10px] font-bold font-mono ${isHighThreat ? 'text-rose-500' : 'text-amber-500'}`}>
                            {cluster.suspicion_score}%
                          </span>
                        </div>
                      </div>

                      {/* Suspicion score bar */}
                      <div className="h-1 w-full bg-zinc-900 rounded-full overflow-hidden mb-2.5">
                        <div 
                          className={`h-full rounded-full ${isHighThreat ? 'bg-rose-500' : 'bg-amber-500'}`} 
                          style={{ width: `${cluster.suspicion_score}%` }} 
                        />
                      </div>

                      {/* Triggered heuristics badges */}
                      <div className="flex flex-wrap gap-1 mb-3">
                        {cluster.heuristics.map((h, i) => (
                          <span key={i} className="text-[8px] font-bold uppercase tracking-wider bg-zinc-900 border border-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded font-mono">
                            {h.replace('_', ' ')}
                          </span>
                        ))}
                      </div>

                      {/* Members lists */}
                      <div className="text-[9px] font-mono mb-3">
                        <span className="text-zinc-500 block mb-1 uppercase font-bold">Bots In Campaign:</span>
                        <div className="flex flex-wrap gap-1.5">
                          {cluster.member_accounts.map((user, idx) => (
                            <span key={idx} className="bg-zinc-900 text-zinc-300 px-1 py-0.5 rounded border border-zinc-850">
                              {user}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Collapsible matched posts list */}
                      <div>
                        <button
                          onClick={() => setExpandedCluster(expandedCluster === cluster.cluster_id ? null : cluster.cluster_id)}
                          className="w-full text-center text-[10px] font-mono text-zinc-500 hover:text-white bg-zinc-900/80 hover:bg-zinc-900 py-1.5 rounded transition-all border border-zinc-900"
                        >
                          {expandedCluster === cluster.cluster_id ? '▲ Hide Campaign Posts' : `▼ View Coordinated Posts (${cluster.matched_posts.length})`}
                        </button>

                        {expandedCluster === cluster.cluster_id && (
                          <div className="mt-2.5 space-y-2 border-t border-zinc-900 pt-2.5 max-h-[160px] overflow-y-auto pr-1">
                            {cluster.matched_posts.map((mp, i) => (
                              <div key={i} className="p-2 rounded bg-zinc-900 border border-zinc-850 space-y-1">
                                <div className="flex justify-between text-[8px] font-mono text-zinc-500">
                                  <span className="font-bold text-zinc-300">{mp.username}</span>
                                  <span>{new Date(mp.timestamp).toLocaleTimeString()}</span>
                                </div>
                                <p className="text-[10px] text-zinc-400 font-sans leading-tight">{mp.text}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </div>

          {/* Classification Sandbox (Secondary Panel) */}
          <div className="bg-zinc-900/40 border border-zinc-900 rounded-xl p-5 backdrop-blur-md shadow-xl flex flex-col">
            <h3 className="text-xs font-extrabold uppercase tracking-widest text-zinc-400 mb-3 font-mono">
              🧪 Ad-hoc NLP sandbox
            </h3>
            
            <div className="space-y-3">
              <textarea 
                rows={2}
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-900 rounded p-2 text-xs font-mono text-zinc-300 focus:outline-none focus:border-zinc-800"
                placeholder="Type sample threat text..."
              />

              <button
                onClick={handleAnalyzeText}
                disabled={isAnalyzing || !textInput.trim() || connectionStatus !== 'online'}
                className="w-full py-1.5 bg-indigo-950 hover:bg-indigo-900 border border-indigo-500 text-indigo-400 font-bold text-xs rounded transition-all cursor-pointer font-mono disabled:opacity-50"
              >
                {isAnalyzing ? 'RUNNING CLASSIFIER...' : 'RUN CLASSIFICATION'}
              </button>

              {analysisResult && (
                <div className="p-3 rounded bg-zinc-950 border border-zinc-900 font-mono text-[10px] space-y-1.5">
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Detected Language</span>
                    <span className="text-white font-semibold">{analysisResult.language}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Category Label</span>
                    <span className="text-zinc-200 font-semibold">{analysisResult.threatCategory}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Confidence</span>
                    <span className="text-indigo-400 font-semibold">{Math.round(analysisResult.confidence * 100)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Sentiment Score</span>
                    <span className={analysisResult.sentimentScore < 0.3 ? 'text-rose-400' : 'text-emerald-400'}>
                      {analysisResult.sentimentScore}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Ad-hoc Image & Meme OCR Sandbox */}
          <div className="bg-zinc-900/40 border border-zinc-900 rounded-xl p-5 backdrop-blur-md shadow-xl flex flex-col">
            <h3 className="text-xs font-extrabold uppercase tracking-widest text-zinc-400 mb-3 font-mono flex items-center gap-1.5">
              🖼️ Ad-hoc image & meme sandbox
            </h3>

            <div className="space-y-3 font-mono text-xs">
              {/* Image upload drag & drop box */}
              <label className="flex flex-col items-center justify-center border-2 border-zinc-850 border-dashed rounded-lg p-4 cursor-pointer hover:border-zinc-700 transition-all bg-zinc-950/40 hover:bg-zinc-950/80">
                <svg className="w-6 h-6 text-zinc-500 mb-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                </svg>
                <span className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider text-center">
                  {selectedImageFile ? selectedImageFile.name : 'Select or drop image'}
                </span>
                <span className="text-[8px] text-zinc-500 mt-0.5">Supports PNG, JPG, WEBP</span>
                <input 
                  type="file" 
                  accept="image/*" 
                  className="hidden" 
                  onChange={handleImageChange}
                  disabled={isAnalyzingImage}
                />
              </label>

              {/* Preview image */}
              {imagePreviewUrl && (
                <div className="relative border border-zinc-900 rounded overflow-hidden bg-zinc-950 flex justify-center p-2.5 max-h-[140px]">
                  <img 
                    src={imagePreviewUrl} 
                    alt="Preview" 
                    className="max-h-[120px] object-contain rounded" 
                  />
                </div>
              )}

              <button
                onClick={handleAnalyzeImage}
                disabled={isAnalyzingImage || !selectedImageFile || connectionStatus !== 'online'}
                className="w-full py-1.5 bg-indigo-950 hover:bg-indigo-900 border border-indigo-500 text-indigo-400 font-bold text-xs rounded transition-all cursor-pointer font-mono disabled:opacity-50 uppercase tracking-widest"
              >
                {isAnalyzingImage ? 'ANALYZING MEME...' : 'ANALYZE IMAGE'}
              </button>

              {/* Graceful setup instructions if Tesseract is missing and visual results not yet run */}
              {imageAnalysisResult && imageAnalysisResult.status === 'pending_setup' && (
                <div className="p-3.5 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg text-[9px] leading-relaxed">
                  <div className="font-extrabold uppercase text-[10px] tracking-wider mb-1 flex items-center gap-1">
                    ⚠️ Tesseract OCR Binary Missing
                  </div>
                  <p className="text-zinc-400 font-mono select-text whitespace-pre-wrap">
                    {imageAnalysisResult.message}
                  </p>
                </div>
              )}

              {/* Extraction result displays */}
              {imageAnalysisResult && imageAnalysisResult.status === 'success' && (
                <div className="space-y-3 font-mono text-[10px]">
                  
                  {/* Inline Tesseract missing warning */}
                  {imageAnalysisResult.ocr_status === 'tesseract_not_found' && (
                    <div className="p-3 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg leading-normal">
                      <div className="font-extrabold uppercase text-[9px] tracking-wider mb-1 flex items-center gap-1">
                        ⚠️ Tesseract OCR Binary Missing (OCR Disabled)
                      </div>
                      <p className="text-zinc-400 text-[9px] font-mono leading-relaxed select-text">
                        Tesseract was not found. Image text extraction is disabled. Install Tesseract to enable OCR.
                      </p>
                    </div>
                  )}

                  {imageAnalysisResult.ocr_status === 'success' && (
                    <div className="p-2.5 bg-zinc-950 border border-zinc-900 rounded select-text">
                      <span className="text-zinc-500 block uppercase font-bold tracking-wider text-[8px] mb-1">Extracted Text</span>
                      {imageAnalysisResult.extracted_text ? (
                        <p className="text-zinc-200 whitespace-pre-wrap font-sans break-all leading-normal">{imageAnalysisResult.extracted_text}</p>
                      ) : (
                        <span className="text-zinc-600 italic">No text detected in image.</span>
                      )}
                    </div>
                  )}

                  {imageAnalysisResult.ocr_status === 'success' && imageAnalysisResult.extracted_text && (
                    <div className="p-3 rounded bg-zinc-950 border border-zinc-900 space-y-1.5">
                      <div className="flex justify-between">
                        <span className="text-zinc-500">Detected Language</span>
                        <span className="text-white font-semibold">{imageAnalysisResult.detected_language}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-zinc-500">Category Label</span>
                        <span className="text-zinc-200 font-semibold">{imageAnalysisResult.threat_category}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-zinc-500">Classifier Confidence</span>
                        <span className="text-indigo-400 font-semibold">{Math.round((imageAnalysisResult.confidence || 0) * 100)}%</span>
                      </div>
                      
                      {/* OCR confidence indicator bar */}
                      <div className="pt-1.5 border-t border-zinc-900 space-y-1">
                        <div className="flex justify-between">
                          <span className="text-zinc-500">OCR Confidence</span>
                          <span className="text-emerald-400 font-semibold">{Math.round((imageAnalysisResult.text_extraction_confidence || 0) * 100)}%</span>
                        </div>
                        <div className="h-1 w-full bg-zinc-900 rounded-full overflow-hidden">
                          <div 
                            className="h-full rounded-full bg-emerald-500"
                            style={{ width: `${Math.round((imageAnalysisResult.text_extraction_confidence || 0) * 100)}%` }} 
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Visual classification labels */}
                  {imageAnalysisResult.visual_labels && imageAnalysisResult.visual_labels.length > 0 && (
                    <div className="p-3 rounded bg-zinc-950 border border-zinc-900 space-y-2.5">
                      <span className="text-zinc-500 block uppercase font-bold tracking-wider text-[8px] border-b border-zinc-900 pb-1">Visual Classifications (CLIP)</span>
                      {imageAnalysisResult.visual_labels.map((vl: any, idx: number) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex justify-between">
                            <span className="text-zinc-400 font-semibold">{vl.label}</span>
                            <span className="text-indigo-400 font-semibold">{Math.round(vl.score * 100)}%</span>
                          </div>
                          <div className="h-1 w-full bg-zinc-900 rounded-full overflow-hidden">
                            <div 
                              className="h-full rounded-full bg-indigo-500" 
                              style={{ width: `${Math.round(vl.score * 100)}%` }} 
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Combined Overall Assessment */}
                  {imageAnalysisResult.overall_assessment && (
                    <div className={`p-3 rounded border font-sans text-xs ${
                      imageAnalysisResult.overall_assessment.includes("Disagreement")
                        ? 'bg-amber-950/20 border-amber-900/60 text-amber-300'
                        : imageAnalysisResult.overall_assessment.includes("active threat")
                        ? 'bg-rose-950/20 border-rose-900/60 text-rose-300'
                        : 'bg-zinc-900/60 border-zinc-800 text-zinc-300'
                    }`}>
                      <span className="text-[8px] uppercase tracking-wider font-bold block mb-1 font-mono text-zinc-500">Combined Assessment</span>
                      <p className="font-semibold leading-relaxed">{imageAnalysisResult.overall_assessment}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>
        
      </main>)}
    </div>
  )
}

export default App
