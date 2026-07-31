import os
import sys
import asyncio
from dotenv import load_dotenv
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.abspath(os.path.join(current_dir, "..", ".env"))
load_dotenv(dotenv_path=dotenv_path)

# Enforce stdout to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def main():
    print("=== Checking System vs. Telegram Dates ===")
    print("Python datetime.now():", datetime.now())
    print("Python datetime.utcnow():", datetime.utcnow())
    
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    session_path = os.path.abspath(os.path.join(current_dir, "..", "telegram_session"))
    
    from telethon import TelegramClient
    client = TelegramClient(session_path, int(api_id), api_hash)
    await client.connect()
    
    # Let's check latest posts in multiple channels
    channels = [
        "abpasmitanews", "abpasmita", "tv9gujaratiofficial", "tv9gujarati", 
        "sandeshnews", "sandeshnews24", "divyabhaskarofficial", "divyabhaskar", 
        "vtvgujaratinofficial", "vtvgujarati_news", "gujaratsamacharofficial",
        "telegram", "durov"
    ]
    for ch in channels:
        print(f"\nFetching latest message from @{ch}...")
        try:
            async for msg in client.iter_messages(ch, limit=1):
                print(f"  Msg ID: {msg.id}")
                print(f"  Date:   {msg.date} (ISO: {msg.date.isoformat() if msg.date else None})")
                text = msg.text.strip().replace('\n', ' ') if msg.text else ''
                print(f"  Text:   \"{text[:100]}...\"")
        except Exception as e:
            print(f"  Failed for @{ch}: {e}")
            
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
