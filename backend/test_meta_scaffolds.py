import urllib.request
import json
import time
import sys

# Configure stdout to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def test_meta_scaffolds():
    print("=== Testing Facebook and Instagram Review Scaffolds ===")
    
    # 1. Start live crawler for Instagram (credentials are missing)
    try:
        url = "http://127.0.0.1:8000/api/crawler/start-live?platform=instagram&keywords=Gujarat"
        req = urllib.request.Request(url, data=b"", method="POST")
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode())
            print(f"Instagram Start Response: {data}")
            assert data["status"] == "pending_meta_review", "Instagram crawler should report pending review."
            assert "Awaiting Meta App Review approval" in data["message"], "Review notice missing."
            
        # 2. Start live crawler for Facebook (credentials are missing)
        url_fb = "http://127.0.0.1:8000/api/crawler/start-live?platform=facebook&keywords=Gujarat"
        req_fb = urllib.request.Request(url_fb, data=b"", method="POST")
        with urllib.request.urlopen(req_fb) as res:
            data_fb = json.loads(res.read().decode())
            print(f"Facebook Start Response: {data_fb}")
            assert data_fb["status"] == "pending_meta_review", "Facebook crawler should report pending review."
            
        # 3. Check status details
        status_url = "http://127.0.0.1:8000/api/crawler/status"
        with urllib.request.urlopen(status_url) as res:
            status_data = json.loads(res.read().decode())
            print(f"Status Response: {status_data}")
            assert status_data["meta_token_loaded"] is False, "meta_token_loaded should be False."
            
        print("\nFacebook and Instagram review scaffold tests PASSED.")
        
    except Exception as e:
        print(f"Meta Scaffolds test FAILED: {e}")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    test_meta_scaffolds()
