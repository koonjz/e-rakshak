import sys
import os
import json
import urllib.request
import urllib.error

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analytics.coordination import detect_coordinated_behavior

def test_coordination_isolation():
    print("=== Testing coordination clustering in Isolation ===")
    
    # Load dataset sample posts
    data_path = os.path.join("..", "data", "sample_posts.json")
    if not os.path.exists(data_path):
        data_path = os.path.join("data", "sample_posts.json")
        
    with open(data_path, "r", encoding="utf-8") as f:
        posts = json.load(f)
        
    print(f"Loaded {len(posts)} posts from {data_path}.")
    
    # Run behavior detection
    clusters = detect_coordinated_behavior(posts)
    print(f"Detected {len(clusters)} coordination clusters in isolation.")
    
    for c in clusters:
        print(f"\nCluster ID:      {c['cluster_id']}")
        print(f"Member Accounts: {c['member_accounts']}")
        print(f"Suspicion Score: {c['suspicion_score']}")
        print(f"Heuristics:      {c['heuristics']}")
        print(f"Posts Count:     {len(c['matched_posts'])}")
        for mp in c['matched_posts']:
            print(f"  - [{mp['username']}]: {mp['text'][:60]}...")
            
    # Check that we have at least our 2 seeded clusters
    assert len(clusters) >= 2
    
    # Verify cluster contents
    c1 = next((c for c in clusters if "@bot_agent_01" in c["member_accounts"]), None)
    c2 = next((c for c in clusters if "@sync_user_a" in c["member_accounts"]), None)
    
    assert c1 is not None, "Failed to detect Seeded Cluster 1 (chemical leak)"
    assert c2 is not None, "Failed to detect Seeded Cluster 2 (Rajkot violence)"
    
    # Verify seeded cluster heuristics
    assert "templated_text" in c1["heuristics"]
    assert "synchronized_burst" in c2["heuristics"]
    assert "suspicious_profiles" in c1["heuristics"]
    
    print("\nCoordination isolation test PASSED.\n")

def call_api(path: str) -> dict:
    url = f"http://127.0.0.1:8000{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code} on {url}: {e.reason}")
        return []
    except Exception as e:
        print(f"Connection Error on {url}: {e}")
        return []

def test_api_coordination_integration():
    print("=== Testing FastAPI Coordination Endpoint Integration ===")
    
    clusters = call_api("/api/coordination")
    if not clusters:
        print("FAIL: Cannot contact coordination API. Is uvicorn running?")
        sys.exit(1)
        
    print(f"Retrieved {len(clusters)} coordination clusters from API.")
    print("Top Cluster details:")
    print(json.dumps(clusters[0], indent=2))
    
    print("\nAPI Coordination Integration test PASSED.\n")

if __name__ == "__main__":
    # Ensure UTF-8 console output
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
        
    test_coordination_isolation()
    test_api_coordination_integration()
