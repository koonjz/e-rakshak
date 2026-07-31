import asyncio
import sys
import json
import urllib.request
import urllib.error
from crawler.mock import MockCrawler

async def test_mock_crawler_isolation():
    print("=== Testing MockCrawler in Isolation ===")
    crawler = MockCrawler()
    print(f"Dataset path: {crawler.data_path}")
    print(f"Loaded posts count: {len(crawler.posts)}")
    
    if not crawler.posts:
        print("FAIL: No posts loaded!")
        sys.exit(1)
        
    print("\nStreaming first 3 posts (isolation test)...")
    count = 0
    async for post in crawler.stream_posts():
        print(f"[{post['id']}] Platform: {post['platform']} | Lang: {post['language']} | Category: {post['threat_category']}")
        print(f"Text: {post['text']}")
        print("-" * 40)
        count += 1
        if count >= 3:
            break
    print("Isolation test PASSED.\n")

def call_api(path: str, method: str = "GET", data: dict = None) -> dict:
    url = f"http://127.0.0.1:8000{path}"
    req_data = None
    headers = {}
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code} on {url}: {e.reason}")
        return {}
    except Exception as e:
        print(f"Connection Error on {url}: {e}")
        return {}

def test_api_integration():
    print("=== Testing FastAPI Crawler Endpoints ===")
    
    # 1. Check Status
    status = call_api("/api/crawler/status")
    print(f"Initial Status: {status}")
    if not status:
        print("FAIL: Cannot contact backend API. Is uvicorn running?")
        sys.exit(1)
        
    # 2. Start Crawler
    start_res = call_api("/api/crawler/start", method="POST")
    print(f"Start API response: {start_res}")
    
    # Check status again
    status = call_api("/api/crawler/status")
    print(f"Status after starting: {status}")
    
    # 3. Wait for posts to accumulate in queue
    print("Waiting 4 seconds for queue to fill...")
    import time
    time.sleep(4)
    
    # Check status to see queue size
    status = call_api("/api/crawler/status")
    print(f"Status before draining: {status}")
    
    # 4. Fetch/drain posts
    posts = call_api("/api/crawler/posts?limit=5")
    print(f"Fetched {len(posts)} posts from queue:")
    for post in posts:
        print(f" - [{post['id']}] {post['text'][:60]}...")
        
    # 5. Stop Crawler
    stop_res = call_api("/api/crawler/stop", method="POST")
    print(f"Stop API response: {stop_res}")
    
    # Check final status
    status = call_api("/api/crawler/status")
    print(f"Final status: {status}")
    print("API Integration test PASSED.\n")

if __name__ == "__main__":
    # Configure UTF-8 console output for emojis
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass  # Fallback for environments where stdout cannot be reconfigured
        
    # Run isolation test
    asyncio.run(test_mock_crawler_isolation())
    
    # Run api integration test
    test_api_integration()
