import urllib.request
import json
import time
import sys

# Reconfigure stdout to UTF-8 to support emoji printing in Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def test_api_youtube():
    print("=== Testing FastAPI YouTube Ingestion Endpoint ===")
    
    # 1. Start live crawler
    try:
        url = "http://127.0.0.1:8000/api/crawler/start-live?keywords=Gujarat,protest"
        req = urllib.request.Request(url, data=b"", method="POST")
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode())
            print(f"Start Response: {data}")
            assert data["status"] == "started", "Failed to start live YouTube mode."
            
        # 2. Check status
        status_url = "http://127.0.0.1:8000/api/crawler/status"
        with urllib.request.urlopen(status_url) as res:
            status_data = json.loads(res.read().decode())
            print(f"Status Response: {status_data}")
            assert status_data["active"] is True, "Crawler should be active."
            assert status_data["mode"] == "youtube", "Crawler mode should be 'youtube'."
            
        # 3. Wait for comments to stream and be classified
        print("Waiting 5 seconds for comment streams...")
        time.sleep(5)
        
        # 4. Read queued posts
        posts_url = "http://127.0.0.1:8000/api/crawler/posts?limit=10"
        with urllib.request.urlopen(posts_url) as res:
            posts = json.loads(res.read().decode())
            print(f"Ingested {len(posts)} comments from queue.")
            for p in posts[:2]:
                print(f"  Comment text: {p.get('text')}")
                print(f"  Threat category: {p.get('threat_category')}")
                print(f"  Language: {p.get('language')}")
                
        # 5. Stop crawler
        stop_url = "http://127.0.0.1:8000/api/crawler/stop"
        stop_req = urllib.request.Request(stop_url, data=b"", method="POST")
        with urllib.request.urlopen(stop_req) as res:
            stop_data = json.loads(res.read().decode())
            print(f"Stop Response: {stop_data}")
            assert stop_data["status"] == "stopped", "Failed to stop crawler."
            
        print("\nFastAPI YouTube Ingestion E2E checks PASSED.")
        
    except Exception as e:
        print(f"API YouTube Ingestion Test FAILED: {e}")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    test_api_youtube()
