import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.abspath(os.path.join(current_dir, "..", ".env"))
load_dotenv(dotenv_path=dotenv_path)

async def test_extra_channels():
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    session_path = os.path.abspath(os.path.join(current_dir, "..", "telegram_session"))
    
    from telethon import TelegramClient
    client = TelegramClient(session_path, int(api_id), api_hash)
    await client.connect()
    
    extra_channels = ["deshgujarat", "gujaratsamachar", "sandesh_news", "divyabhaskar"]
    for ch in extra_channels:
        print(f"\nChecking @{ch}...")
        try:
            async for msg in client.iter_messages(ch, limit=2):
                print(f"  Msg ID: {msg.id} Date: {msg.date}")
                print(f"  Text: {msg.text.strip().replace(chr(10), ' ')[:100]}...")
        except Exception as e:
            print(f"  Failed: {e}")
            
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_extra_channels())
