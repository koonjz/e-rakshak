import os
import sys
import asyncio
from dotenv import load_dotenv
from datetime import datetime

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Resolve absolute path to root .env
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.abspath(os.path.join(current_dir, "..", ".env"))
load_dotenv(dotenv_path=dotenv_path)

# Enforce stdout to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def dump_dates():
    print("=== DUMPING RAW TELEGRAM MESSAGES FOR DATE CHECK ===")
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    
    if not api_id or not api_hash:
        print("ERROR: Credentials missing.")
        return
        
    session_path = os.path.abspath(os.path.join(current_dir, "..", "telegram_session"))
    from telethon import TelegramClient
    client = TelegramClient(session_path, int(api_id), api_hash)
    
    await client.connect()
    if not await client.is_user_authorized():
        print("ERROR: Session not authorized.")
        await client.disconnect()
        return
        
    channel = "gujaratsamacharofficial"
    print(f"Fetching last 5 messages from @{channel}...")
    
    try:
        async for message in client.iter_messages(channel, limit=5):
            if not message.text:
                continue
            print(f"\nMessage ID: {message.id}")
            print(f"Raw Date:   {message.date} (timezone: {message.date.tzinfo})")
            print(f"ISO Format: {message.date.isoformat()}")
            print(f"Text Snippet: \"{message.text.strip().replace(chr(10), ' ')[:120]}...\"")
    except Exception as e:
        print(f"Error: {e}")
        
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(dump_dates())
