import os
import sys
import asyncio
from dotenv import load_dotenv

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load .env variables
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.abspath(os.path.join(current_dir, "..", ".env"))
load_dotenv(dotenv_path=dotenv_path)

# Enforce stdout to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from backend.crawler.social_stubs import TelegramCrawler

def test_telegram_crawler():
    print("=== Testing TelegramCrawler Isolation ===")
    
    crawler = TelegramCrawler()
    
    # Check if variables are configured
    if not crawler.api_id or not crawler.api_hash:
        print("WARNING: TELEGRAM_API_ID or TELEGRAM_API_HASH is not defined in .env.")
        print("Skipping actual Telegram connection check.")
        return
        
    session_file = os.path.abspath(os.path.join(current_dir, "..", "telegram_session.session"))
    if not os.path.exists(session_file):
        print("WARNING: telegram_session.session file does not exist. Run login_telegram.py first.")
        return
        
    print("Fetching messages from public channels...")
    posts = crawler.fetch_posts(keywords=[])
    
    if isinstance(posts, dict) and posts.get("status") == "pending_auth":
        print(f"Auth Status: {posts['message']}")
        return
        
    print(f"Retrieved {len(posts)} messages from Telegram.")
    
    if posts:
        print("\nSample Ingested Telegram Post:")
        sample = posts[0]
        print(f"  ID:        {sample['id']}")
        print(f"  Channel:   {sample['username']}")
        print(f"  Timestamp: {sample['timestamp']}")
        print(f"  Text:      {sample['text'].strip()[:200]}...")
        print(f"  Geo:       {sample.get('geo')}")
        print("\nVerification checks PASSED.")
    else:
        print("No messages retrieved (or public channels returned empty).")

if __name__ == "__main__":
    test_telegram_crawler()
