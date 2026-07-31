import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.abspath(os.path.join(current_dir, "..", ".env"))
load_dotenv(dotenv_path=dotenv_path)

# Enforce stdout to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def main():
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    session_path = os.path.abspath(os.path.join(current_dir, "..", "telegram_session"))
    
    from telethon import TelegramClient
    client = TelegramClient(session_path, int(api_id), api_hash)
    await client.connect()
    
    print("\nFetching latest 3 messages from @divyabhaskar...")
    async for msg in client.iter_messages("divyabhaskar", limit=3):
        if not msg.text:
            continue
        print(f"Message ID: {msg.id}")
        print(f"Timestamp:  {msg.date.isoformat()}")
        print(f"Text Snippet: \"{msg.text.strip().replace(chr(10), ' ')[:100]}...\"")
        print("-" * 40)
        
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
