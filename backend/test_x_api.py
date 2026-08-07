import os
import json
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crawler.social_stubs import TwitterCrawler

def main():
    # Load env variables
    load_dotenv()
    
    token = os.getenv("TWITTER_BEARER_TOKEN")
    print(f"Loaded TWITTER_BEARER_TOKEN exists: {bool(token)}")
    
    print("\n--- Testing X (Twitter) Crawler ---")
    crawler = TwitterCrawler()
    res = crawler.fetch_posts(keywords=["gujarat"])
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
