import re
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any

def clean_words(text: str) -> set:
    """
    Cleans punctuation and returns a set of lowercased tokens from text.
    """
    return set(re.findall(r'\w+', text.lower()))

def jaccard_similarity(s1: set, s2: set) -> float:
    """
    Computes Jaccard index between two word sets.
    """
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)

def parse_iso_time(ts: str) -> datetime:
    """
    Parses ISO timestamps safely.
    """
    try:
        if ts.endswith("Z"):
            ts = ts[:-1]
        if "+" in ts:
            ts = ts.split("+")[0]
        return datetime.fromisoformat(ts)
    except:
        return datetime.now()

def check_profile_suspicious(profile: Dict[str, Any], post_time: datetime) -> bool:
    """
    Checks user profile signals for bot-like activity.
    """
    if not profile:
        return False
        
    created_str = profile.get("account_created_date", "")
    followers = profile.get("follower_count", 100)
    following = profile.get("following_count", 100)
    
    # Heuristic 1: Account age is extremely new (created within 60 days of the post)
    is_new = False
    if created_str:
        try:
            created_date = datetime.strptime(created_str, "%Y-%m-%d")
            age_days = (post_time - created_date).days
            if 0 <= age_days <= 60:
                is_new = True
        except:
            pass
            
    # Heuristic 2: Abnormal follower/following ratio (very few followers, high following count)
    is_bad_ratio = (followers < 30) and (following > 400)
    
    return is_new or is_bad_ratio

def detect_coordinated_behavior(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyzes posts to cluster together coordinated campaigns and botnets.
    
    Returns:
        List of dictionaries representing detected coordination clusters.
    """
    n = len(posts)
    # Parse times and clean word sets beforehand for efficiency
    parsed_posts = []
    for post in posts:
        parsed_posts.append({
            "post_ref": post,
            "username": post.get("username", ""),
            "time": parse_iso_time(post.get("timestamp", "")),
            "words": clean_words(post.get("text", "")),
            "threat_category": post.get("threat_category", "neutral"),
            "user_profile": post.get("user_profile", {})
        })
        
    # Build adjacency list for coordination edges
    adj = defaultdict(list)
    edge_types = defaultdict(set) # key: (i, j) edge index pair -> values: set of heuristic strings
    
    # Bucketize posts by timestamp relative to min time to optimize comparisons
    times = [p["time"] for p in parsed_posts]
    if not times:
        return []
    epoch = min(times)
    
    # 20-minute buckets with 10-minute overlap step
    bucket_width = 1200.0  # 20 minutes in seconds
    bucket_step = 600.0    # 10 minutes in seconds
    buckets = defaultdict(list)
    
    for idx, p in enumerate(parsed_posts):
        rel_seconds = (p["time"] - epoch).total_seconds()
        k1 = int(rel_seconds // bucket_step)
        k2 = k1 - 1
        buckets[k1].append(idx)
        buckets[k2].append(idx)
        
    compared_pairs = set()
    
    for bucket_indices in buckets.values():
        n_bucket = len(bucket_indices)
        for i_local in range(n_bucket):
            for j_local in range(i_local + 1, n_bucket):
                idx_i = bucket_indices[i_local]
                idx_j = bucket_indices[j_local]
                
                # Coordination requires different user accounts
                if parsed_posts[idx_i]["username"] == parsed_posts[idx_j]["username"]:
                    continue
                    
                pair_key = (min(idx_i, idx_j), max(idx_i, idx_j))
                if pair_key in compared_pairs:
                    continue
                compared_pairs.add(pair_key)
                
                i, j = pair_key
                p1 = parsed_posts[i]
                p2 = parsed_posts[j]
                
                time_diff = abs((p1["time"] - p2["time"]).total_seconds())
                if time_diff > 600:
                    continue
                    
                text_sim = jaccard_similarity(p1["words"], p2["words"])
                
                is_connected = False
                reasons = set()
                
                # Heuristic 1: Near-duplicate/templated text posted within 10 minutes
                if text_sim >= 0.70 and time_diff <= 600:
                    is_connected = True
                    reasons.add("templated_text")
                    
                # Heuristic 2: Synchronized posting within 10 seconds
                if time_diff <= 10:
                    has_semantic_link = (text_sim > 0.15) or (p1["threat_category"] != "neutral" and p2["threat_category"] != "neutral")
                    if has_semantic_link:
                      is_connected = True
                      reasons.add("synchronized_burst")
                      
                if is_connected:
                    adj[i].append(j)
                    adj[j].append(i)
                    edge_types[pair_key].update(reasons)
                
    # Find connected components in the graph
    visited = [False] * n
    components = []
    
    for i in range(n):
        if not visited[i] and i in adj:
            # BFS to find component
            comp = []
            queue = [i]
            visited[i] = True
            
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for neighbor in adj[curr]:
                    if not visited[neighbor]:
                        visited[neighbor] = True
                        queue.append(neighbor)
                        
            # Only keep components of size >= 3 to represent campaigns
            if len(comp) >= 3:
                components.append(comp)
                
    # Formulate output clusters
    clusters = []
    for idx, comp in enumerate(components):
        cluster_id = f"cluster_{idx + 1:02d}"
        
        member_posts = [parsed_posts[node] for node in comp]
        member_accounts = sorted(list(set(p["username"] for p in member_posts)))
        
        # Collect matched posts detail
        matched_posts_details = []
        for mp in member_posts:
            p_ref = mp["post_ref"]
            matched_posts_details.append({
                "id": p_ref.get("id"),
                "username": p_ref.get("username"),
                "timestamp": p_ref.get("timestamp"),
                "text": p_ref.get("text"),
                "threat_category": p_ref.get("threat_category", "Neutral"),
                "platform": p_ref.get("platform")
            })
            
        # Detect heuristics triggered in this cluster
        heuristics_triggered = set()
        for u in range(len(comp)):
            for v in range(u + 1, len(comp)):
                node1, node2 = comp[u], comp[v]
                edge_key = (min(node1, node2), max(node1, node2))
                if edge_key in edge_types:
                    heuristics_triggered.update(edge_types[edge_key])
                    
        # Check suspicious profile signals
        suspicious_members_count = 0
        for mp in member_posts:
            if check_profile_suspicious(mp["user_profile"], mp["time"]):
                suspicious_members_count += 1
                
        if suspicious_members_count > 0:
            heuristics_triggered.add("suspicious_profiles")
            
        # Compute suspicion score (0 to 100)
        base_score = 40
        if "templated_text" in heuristics_triggered:
            base_score += 20
        if "synchronized_burst" in heuristics_triggered:
            base_score += 20
            
        # Add profile ratio penalty
        ratio_penalty = int((suspicious_members_count / len(comp)) * 20)
        suspicion_score = min(base_score + ratio_penalty, 100)
        
        # Extra boost if all profiles are extreme bots
        is_botnet = all(
            (mp["user_profile"].get("follower_count", 100) < 30) and 
            (mp["user_profile"].get("following_count", 0) > 400)
            for mp in member_posts
        )
        if is_botnet:
            suspicion_score = max(suspicion_score, 95)
            
        clusters.append({
            "cluster_id": cluster_id,
            "member_accounts": member_accounts,
            "heuristics": sorted(list(heuristics_triggered)),
            "suspicion_score": suspicion_score,
            "matched_posts": matched_posts_details
        })
        
    # Sort clusters by suspicion score descending
    clusters.sort(key=lambda c: c["suspicion_score"], reverse=True)
    return clusters
