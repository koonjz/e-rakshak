import os
from typing import List, Dict, Any
from neo4j import GraphDatabase

class Neo4jGraphManager:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "").strip()
        self.username = os.getenv("NEO4J_USERNAME", "").strip()
        self.password = os.getenv("NEO4J_PASSWORD", "").strip()
        
        self.driver = None
        self.available = False
        self.error_message = None
        
        if not self.uri or not self.username or not self.password:
            self.error_message = "Credentials missing"
            return
            
        try:
            # Connect to Neo4j
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            # Verify connectivity (ping)
            self.driver.verify_connectivity()
            self.available = True
        except Exception as e:
            self.error_message = str(e)
            self.available = False
            if self.driver:
                try:
                    self.driver.close()
                except:
                    pass
                self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def sync_posts_and_coordination(self, posts: List[Dict[str, Any]], clusters: List[Dict[str, Any]]):
        """
        Synchronizes posts, accounts, and coordination edges to Neo4j using MERGE queries.
        """
        if not self.available or not self.driver:
            return False
            
        try:
            with self.driver.session() as session:
                # 1. Sync Account and Post nodes, and POSTED relationships
                for post in posts:
                    username = post.get("username", "")
                    platform = post.get("platform", "Unknown")
                    post_id = post.get("id", "")
                    text = post.get("text", "")
                    snippet = text[:100] + ("..." if len(text) > 100 else "")
                    threat = post.get("threat_category", "Neutral")
                    timestamp = post.get("timestamp", "")
                    
                    if not username or not post_id:
                        continue
                        
                    # Create/Merge Account and Post, and POSTED relationship
                    session.run(
                        """
                        MERGE (a:Account {username: $username})
                        ON CREATE SET a.platform = $platform
                        MERGE (p:Post {id: $post_id})
                        ON CREATE SET p.text_snippet = $snippet, p.threat_category = $threat, p.timestamp = $timestamp
                        MERGE (a)-[:POSTED]->(p)
                        """,
                        username=username, platform=platform, post_id=post_id, snippet=snippet, threat=threat, timestamp=timestamp
                    )
                    
                # 2. Sync COORDINATES_WITH relationships between accounts in the same cluster
                for cluster in clusters:
                    member_accounts = cluster.get("member_accounts", [])
                    heuristics = cluster.get("heuristics", [])
                    heuristic_label = ", ".join(heuristics) if heuristics else "Coordinated"
                    suspicion_score = cluster.get("suspicion_score", 50)
                    
                    # Create pairwise coordinates relationship
                    n_members = len(member_accounts)
                    for i in range(n_members):
                        for j in range(i + 1, n_members):
                            u1 = member_accounts[i]
                            u2 = member_accounts[j]
                            
                            # Sort to ensure undirected uniqueness
                            u1, u2 = sorted([u1, u2])
                            
                            session.run(
                                """
                                MATCH (a1:Account {username: $u1})
                                MATCH (a2:Account {username: $u2})
                                MERGE (a1)-[r:COORDINATES_WITH]->(a2)
                                SET r.heuristic = $heuristic, r.suspicion_score = $suspicion_score
                                """,
                                u1=u1, u2=u2, heuristic=heuristic_label, suspicion_score=suspicion_score
                            )
            return True
        except Exception as e:
            print(f"Neo4j Sync Error: {e}")
            return False

    def get_network_graph(self) -> Dict[str, Any]:
        """
        Queries Neo4j database to build the account nodes and coordination edges list for visualization.
        """
        if not self.available or not self.driver:
            return {"status": "graph_db_unavailable", "nodes": [], "edges": []}
            
        try:
            nodes = []
            edges = []
            
            with self.driver.session() as session:
                # Query account nodes with post counts and max suspicion
                nodes_result = session.run(
                    """
                    MATCH (a:Account)
                    OPTIONAL MATCH (a)-[:POSTED]->(p:Post)
                    WITH a, count(p) AS post_count
                    OPTIONAL MATCH (a)-[r:COORDINATES_WITH]-()
                    WITH a, post_count, max(r.suspicion_score) AS max_suspicion
                    RETURN a.username AS username, a.platform AS platform, post_count AS post_count, coalesce(max_suspicion, 0) AS suspicion
                    """
                )
                for record in nodes_result:
                    nodes.append({
                        "id": record["username"],
                        "label": record["username"],
                        "platform": record["platform"],
                        "post_count": record["post_count"],
                        "suspicion": record["suspicion"]
                    })
                    
                # Query coordination edges
                edges_result = session.run(
                    """
                    MATCH (a:Account)-[r:COORDINATES_WITH]->(b:Account)
                    RETURN a.username AS source, b.username AS target, r.heuristic AS heuristic, r.suspicion_score AS suspicion_score
                    """
                )
                for record in edges_result:
                    edges.append({
                        "from": record["source"],
                        "to": record["target"],
                        "heuristic": record["heuristic"],
                        "suspicion_score": record["suspicion_score"]
                    })
                    
            return {
                "status": "success",
                "nodes": nodes,
                "edges": edges
            }
        except Exception as e:
            print(f"Neo4j Fetch Error: {e}")
            return {
                "status": "graph_db_error",
                "detail": str(e),
                "nodes": [],
                "edges": []
            }

# Singleton instance
graph_manager = Neo4jGraphManager()
