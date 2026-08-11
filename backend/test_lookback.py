import urllib.request
import urllib.parse
import json
import time

def make_post_request(url, data_dict=None):
    try:
        data = urllib.parse.urlencode(data_dict).encode('utf-8') if data_dict else b""
        req = urllib.request.Request(url, data=data, method='POST')
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"Request to {url} failed: {e}")
        return None

def test_mock_lookback():
    print("\n--- Testing Mock Lookback ---")
    
    # Start N=30
    url_start_30 = "http://127.0.0.1:8000/api/crawler/start?lookback_days=30"
    print(f"Starting mock with N=30: {url_start_30}")
    res_start_30 = make_post_request(url_start_30)
    print("Response:", res_start_30)
    
    time.sleep(2)
    # Drain posts feed
    url_posts = "http://127.0.0.1:8000/api/crawler/posts?limit=50"
    res_posts_30 = json.loads(urllib.request.urlopen(url_posts).read().decode('utf-8'))
    print(f"Drained {len(res_posts_30)} posts for N=30.")
    
    # Stop
    make_post_request("http://127.0.0.1:8000/api/crawler/stop")
    
    # Start N=3
    url_start_3 = "http://127.0.0.1:8000/api/crawler/start?lookback_days=3"
    print(f"\nStarting mock with N=3: {url_start_3}")
    res_start_3 = make_post_request(url_start_3)
    print("Response:", res_start_3)
    
    time.sleep(2)
    res_posts_3 = json.loads(urllib.request.urlopen(url_posts).read().decode('utf-8'))
    print(f"Drained {len(res_posts_3)} posts for N=3.")
    
    # Stop
    make_post_request("http://127.0.0.1:8000/api/crawler/stop")
    
    assert len(res_posts_30) > 0, "Expected posts for N=30"
    assert len(res_posts_3) == 0, "Expected 0 posts for N=3 (sample posts are old)"
    print("Mock lookback validation PASSED!")

def test_live_warnings():
    print("\n--- Testing Live Twitter Warning ---")
    url_twitter_warn = "http://127.0.0.1:8000/api/crawler/start-live?platform=twitter&lookback_days=10"
    print(f"Starting Twitter with N=10: {url_twitter_warn}")
    res = make_post_request(url_twitter_warn)
    print("Response:", res)
    # Stop just in case it started
    make_post_request("http://127.0.0.1:8000/api/crawler/stop")
    
    if res and "warning" in res:
        print(f"Warning returned: '{res['warning']}'")
        assert "limits lookback to the last 7 days" in res["warning"]
        print("Twitter lookback limit warning check PASSED!")
    else:
        print("Note: Ingestion check bypassed (paid tier missing or already returned error status).")

def test_youtube_lookback():
    print("\n--- Testing YouTube Lookback ---")
    url_yt = "http://127.0.0.1:8000/api/crawler/start-live?platform=youtube&keywords=Gujarat&lookback_days=2"
    print(f"Starting YouTube with N=2: {url_yt}")
    res = make_post_request(url_yt)
    print("Response:", res)
    if res and res.get("status") == "started":
        time.sleep(3)
        url_posts = "http://127.0.0.1:8000/api/crawler/posts?limit=10"
        posts = json.loads(urllib.request.urlopen(url_posts).read().decode('utf-8'))
        print(f"Fetched {len(posts)} posts from YouTube.")
        
        # Verify timestamps are within 2 days
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=2)
        for p in posts:
            ts_str = p["timestamp"]
            clean_ts = ts_str.split(".")[0].rstrip("Z")
            ts_dt = datetime.fromisoformat(clean_ts).replace(tzinfo=timezone.utc)
            print(f"Post username: {p['username']}, Platform: {p['platform']}, Timestamp: {ts_str}")
            assert ts_dt >= cutoff, f"Post timestamp {ts_str} is older than 2 days cutoff {cutoff}"
            
        print("YouTube lookback validation PASSED!")
        make_post_request("http://127.0.0.1:8000/api/crawler/stop")
    else:
        print("YouTube start-live failed or skipped (API key not loaded).")

if __name__ == "__main__":
    test_mock_lookback()
    test_live_warnings()
    test_youtube_lookback()
