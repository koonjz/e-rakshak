import os
import json
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crawler.social_stubs import InstagramCrawler, FacebookCrawler

def main():
    # Load env variables
    load_dotenv()
    
    token = os.getenv("META_ACCESS_TOKEN")
    print(f"Loaded META_ACCESS_TOKEN exists: {bool(token)}")
    
    print("\n--- Testing Instagram Crawler ---")
    ig = InstagramCrawler()
    ig_res = ig.fetch_posts(keywords=["gujarat"])
    print(json.dumps(ig_res, indent=2))
    
    print("\n--- Testing Facebook Crawler ---")
    fb = FacebookCrawler()
    fb_res = fb.fetch_posts(keywords=["gujarat"])
    print(json.dumps(fb_res, indent=2))

if __name__ == "__main__":
    main()
