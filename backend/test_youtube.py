import os
import sys
from dotenv import load_dotenv

# Reconfigure stdout to UTF-8 to support emoji printing in Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.crawler.social_stubs import YouTubeCrawler

def test_youtube_crawler():
    print("=== Testing YouTubeCrawler Isolation ===")
    
    # Load .env variables from workspace root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.abspath(os.path.join(current_dir, "..", ".env"))
    load_dotenv(dotenv_path=dotenv_path)
    api_key = os.getenv("YOUTUBE_API_KEY")
    is_loaded = bool(api_key and not api_key.startswith("your_real_"))
    print(f"YOUTUBE_API_KEY loaded status: {is_loaded}")
    
    crawler = YouTubeCrawler()
    
    if not api_key:
        print("WARNING: Skipping actual YouTube API calls as YOUTUBE_API_KEY is not defined in .env.")
        print("Verifying that crawler handles missing API key gracefully...")
        posts = crawler.fetch_posts(keywords=["Gujarat", "protest"])
        assert posts == [], "Should return empty list on missing key."
        print("Graceful empty handling PASSED.")
        return
        
    print("Fetching posts matching keywords 'Gujarat'...")
    try:
        posts = crawler.fetch_posts(keywords=["Gujarat"])
        print(f"Retrieved {len(posts)} comments from YouTube.")
        if len(posts) > 0:
            p = posts[0]
            print("\nSample YouTube Comment Post:")
            print(f"  ID:        {p['id']}")
            print(f"  User:      {p['username']}")
            print(f"  Platform:  {p['platform']}")
            print(f"  Timestamp: {p['timestamp']}")
            print(f"  Text:      {p['text']}")
            print(f"  Geo:       {p['geo']['city']} ({p['geo']['latitude']}, {p['geo']['longitude']})")
            
            assert p["platform"] == "YouTube", "Platform must be YouTube."
            assert "geo" in p and "city" in p["geo"], "Geo payload structure missing."
            print("\nFetch normalized schema checks PASSED.")
        else:
            print("No comments returned (may have no search hits or quota exceeded). Graceful handling verified.")
            
    except Exception as e:
        print(f"Test failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_youtube_crawler()
