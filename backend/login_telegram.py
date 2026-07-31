import os
import sys
import asyncio
from dotenv import load_dotenv

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Resolve absolute path to root .env
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.abspath(os.path.join(current_dir, "..", ".env"))
load_dotenv(dotenv_path=dotenv_path)

# Enforce stdout to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def main():
    print("=== Telegram Interactive Login Flow ===")
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    
    if not api_id or not api_hash:
        print("ERROR: TELEGRAM_API_ID or TELEGRAM_API_HASH is missing in .env.")
        print("Please configure them in your .env file first.")
        return
        
    try:
        api_id = int(api_id)
    except ValueError:
        print("ERROR: TELEGRAM_API_ID must be an integer.")
        return
        
    session_path = os.path.abspath(os.path.join(current_dir, "..", "telegram_session"))
    print(f"Session file will be saved to: {session_path}.session")
    
    from telethon import TelegramClient
    client = TelegramClient(session_path, api_id, api_hash)
    
    print("Connecting to Telegram...")
    await client.connect()
    
    # client.start() prompts user interactively if not authorized
    if not await client.is_user_authorized():
        print("Sign-in required. Telethon will now prompt for phone number and authorization code.")
        phone = input("Enter your phone number (e.g. +91XXXXXXXXXX): ")
        await client.send_code_request(phone)
        code = input("Enter the code sent to your Telegram app: ")
        try:
            await client.sign_in(phone, code)
        except Exception as e:
            print(f"Sign-in failed: {e}")
            if "password" in str(e).lower():
                pwd = input("Two-Step Verification password is required. Enter password: ")
                await client.sign_in(password=pwd)
            else:
                return

    if await client.is_user_authorized():
        print("SUCCESS: Telegram session authenticated successfully!")
    else:
        print("FAILED: Could not authorize user.")
        
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
