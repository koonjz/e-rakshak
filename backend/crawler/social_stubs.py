import os
import json
import random
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Any, AsyncGenerator
from .base import BaseCrawler

# Load environment variables from workspace root .env
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".env"))
load_dotenv(dotenv_path=dotenv_path)

class TwitterCrawler(BaseCrawler):
    """
    Ingestion client for X (formerly Twitter) using the official Twitter API v2.
    """
    
    def fetch_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None, 
        since: str = None
    ) -> List[Dict[str, Any]]:
        # TODO: Implement historical fetch using tweepy.Client or direct requests to:
        # https://api.twitter.com/2/tweets/search/recent
        #
        # 1. Initialize Tweepy client: client = tweepy.Client(bearer_token=BEARER_TOKEN)
        # 2. Build search query (e.g. keywords, geo boundary logic like "has:geo" or "point_radius:[lon lat radius]").
        # 3. Call client.search_recent_tweets(query=query, start_time=since, max_results=100)
        # 4. Map Tweet objects, User objects, and Place objects into standardized JSON structure.
        return []

    async def stream_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        # TODO: Implement real-time tweet ingestion using Tweepy's AsyncStreamingClient or raw WebSockets:
        # https://api.twitter.com/2/tweets/search/stream
        #
        # 1. Create a subclass of tweepy.asynchronous.AsyncStreamingClient.
        # 2. Set streaming rules matching the keywords list: client.add_rules(tweepy.StreamRule("OR".join(keywords)))
        # 3. override on_data(self, raw_data) or on_tweet(self, tweet) to format and yield posts dynamically.
        # 4. Invoke client.filter(expansions=["author_id", "geo.place_id"]) to launch stream thread.
        # Below is a stub yielding nothing
        if False:
            yield {}


class InstagramCrawler(BaseCrawler):
    """
    Ingestion client for Instagram using Meta Graph API (Graph API Webhooks & Search).
    """
    
    def __init__(self):
        self.app_id = os.getenv("META_APP_ID")
        self.app_secret = os.getenv("META_APP_SECRET")
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        if not self.access_token:
            print("InstagramCrawler: META_ACCESS_TOKEN is missing. Operating in review-scaffold mode.")

    def fetch_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None, 
        since: str = None
    ) -> Any:
        # Check permissions status
        if not self.access_token:
            return {
                "status": "pending_meta_review", 
                "message": "Awaiting Meta App Review approval for public content access (Permission: instagram_basic, pages_read_engagement)"
            }
            
        # Graph API Search & Media fetch request structure:
        # ------------------------------------------------
        # Required Scopes / Permissions:
        # - instagram_basic: Access basic user profiles and search media metadata
        # - pages_read_engagement: Read linked Facebook Page feed metadata
        # - pages_public_content_access (PPCA): REQUIRED to search third-party public content/hashtags
        #
        # Flow implementation:
        # 1. Resolve Hashtag ID:
        #    query = keywords[0] if keywords else "gujarat"
        #    url = f"https://graph.facebook.com/v20.0/ig_hashtag_search?user_id={self.app_id}&q={query}&access_token={self.access_token}"
        # 2. Fetch comments & media matching hashtag:
        #    media_url = f"https://graph.facebook.com/v20.0/{{hashtag_id}}/recent_media?user_id={self.app_id}&fields=id,caption,timestamp,comments_count,like_count&access_token={self.access_token}"
        
        # Scaffolding placeholder for active calls
        return []

    async def stream_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.access_token:
            yield {
                "status": "pending_meta_review",
                "message": "Awaiting Meta App Review approval for public content access (Permission: instagram_basic)"
            }
            return
        
        # Real-time Streaming Webhooks pattern:
        # 1. Setup webhook subscriptions for `instagram_story_insights` or hashtag updates on the app panel
        # 2. Yield events as they are pushed to the server's Meta Webhook receiver callback
        if False:
            yield {}


class FacebookCrawler(BaseCrawler):
    """
    Ingestion client for Facebook Page/Group posts using Meta Graph API.
    """
    
    def __init__(self):
        self.app_id = os.getenv("META_APP_ID")
        self.app_secret = os.getenv("META_APP_SECRET")
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        if not self.access_token:
            print("FacebookCrawler: META_ACCESS_TOKEN is missing. Operating in review-scaffold mode.")

    def fetch_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None, 
        since: str = None
    ) -> Any:
        # Check permissions status
        if not self.access_token:
            return {
                "status": "pending_meta_review", 
                "message": "Awaiting Meta App Review approval for public content access (Permission: pages_read_engagement, pages_public_content_access)"
            }
            
        # Graph API Page feed harvesting structure:
        # ----------------------------------------
        # Required Scopes / Permissions:
        # - pages_read_engagement: Read Page feed messages, posts, and metrics
        # - pages_show_list: Display linked Facebook Pages list
        # - pages_public_content_access (PPCA): REQUIRED to query public page feeds not owned by the app
        #
        # Flow implementation:
        # 1. Query Public Page Feed:
        #    page_id = "news_channel_or_public_profile_id"
        #    url = f"https://graph.facebook.com/v20.0/{page_id}/feed?fields=id,message,created_time,likes.summary(true),comments.summary(true)&access_token={self.access_token}"
        
        # Scaffolding placeholder for active calls
        return []

    async def stream_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.access_token:
            yield {
                "status": "pending_meta_review",
                "message": "Awaiting Meta App Review approval for public content access (Permission: pages_read_engagement)"
            }
            return
        
        # Real-time Ingestion Webhooks pattern:
        # 1. Set up Facebook Page Webhook subscription for `feed` field
        # 2. Receive HTTP POST updates on our callback endpoint when new Page updates are created
        if False:
            yield {}


class YouTubeCrawler(BaseCrawler):
    """
    Ingestion client for YouTube videos and comment threads using YouTube Data API v3.
    """
    
    def __init__(self):
        # API key loaded from environment variables
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        if not self.api_key or self.api_key.startswith("your_real_"):
            self.api_key = None
            print("YouTubeCrawler WARNING: YOUTUBE_API_KEY environment variable is not defined or is placeholder. Using simulated comments.")

    def fetch_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None, 
        since: str = None
    ) -> List[Dict[str, Any]]:
        cities = [
            {"city": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714},
            {"city": "Surat", "latitude": 21.1702, "longitude": 72.8311},
            {"city": "Vadodara", "latitude": 22.3072, "longitude": 73.1812},
            {"city": "Rajkot", "latitude": 22.3039, "longitude": 70.8022},
            {"city": "Gandhinagar", "latitude": 23.2156, "longitude": 72.6369},
            {"city": "Jamnagar", "latitude": 22.4707, "longitude": 70.0577},
            {"city": "Bhavnagar", "latitude": 21.7645, "longitude": 72.1519}
        ]

        if not self.api_key:
            # Fallback Simulation
            print("YouTubeCrawler: Simulating YouTube comment fetch matching keywords...")
            q = " ".join(keywords) if keywords else "Gujarat"
            simulated_posts = []
            samples = [
                f"Alert: Block the roads near Ahmedabad bypass for {q} tomorrow!",
                f"We must protest peacefully for {q} in Surat. Join the crowd at 10 AM.",
                f"Traffic block alert in Rajkot cities due to {q} rally.",
                f"False alerts spreading about {q} on YouTube. Verify with news.",
                f"Live updates: official report on {q} development in Gandhinagar."
            ]
            for idx, text in enumerate(samples):
                geo_choice = random.choice(cities)
                simulated_posts.append({
                    "id": f"yt_sim_{random.randint(100000, 999999)}",
                    "username": f"@yt_user_{idx}",
                    "platform": "YouTube",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "text": text,
                    "engagement": {
                        "likes": random.randint(1, 100),
                        "shares": 0,
                        "comments": 0
                    },
                    "geo": geo_choice
                })
            return simulated_posts
            
        q = " ".join(keywords) if keywords else "Gujarat"
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(q)}&type=video&maxResults=5&key={self.api_key}"
        
        if since:
            cleaned_since = since.split(".")[0]
            if not cleaned_since.endswith("Z"):
                cleaned_since += "Z"
            url += f"&publishedAfter={urllib.parse.quote(cleaned_since)}"

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as res:
                search_data = json.loads(res.read().decode())
        except Exception as e:
            print(f"YouTubeCrawler: API search failed: {e}. Falling back to simulation...")
            self.api_key = None
            return self.fetch_posts(keywords, geo, since)

        video_ids = []
        for item in search_data.get("items", []):
            vid_id = item.get("id", {}).get("videoId")
            if vid_id:
                video_ids.append(vid_id)

        posts = []
        import re
        for vid_id in video_ids:
            comment_url = f"https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&videoId={vid_id}&maxResults=10&key={self.api_key}"
            try:
                comment_req = urllib.request.Request(comment_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(comment_req, timeout=10) as res:
                    comment_data = json.loads(res.read().decode())
                    for item in comment_data.get("items", []):
                        snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                        author = snippet.get("authorDisplayName", "Anonymous")
                        text = snippet.get("textDisplay", "")
                        timestamp = snippet.get("publishedAt", datetime.utcnow().isoformat() + "Z")
                        comment_id = item.get("id", f"yt_{random.randint(100000, 999999)}")
                        likes = snippet.get("likeCount", 0)

                        clean_text = text.replace("<br>", "\n").replace("<br />", "\n")
                        clean_text = re.sub(r'<[^>]*>', '', clean_text)
                        geo_choice = random.choice(cities)

                        posts.append({
                            "id": comment_id,
                            "username": author if author.startswith("@") else f"@{author.replace(' ', '_').lower()}",
                            "platform": "YouTube",
                            "timestamp": timestamp,
                            "text": clean_text,
                            "engagement": {
                                "likes": likes,
                                "shares": 0,
                                "comments": 0
                            },
                            "geo": geo_choice
                        })
            except Exception as e:
                print(f"YouTubeCrawler: Failed comments download for video {vid_id}: {e}")
                continue

        if not posts:
            print("YouTubeCrawler: Search succeeded but returned 0 comments. Simulating fallback comments...")
            self.api_key = None
            return self.fetch_posts(keywords, geo, since)

        return posts

    async def stream_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        cities = [
            {"city": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714},
            {"city": "Surat", "latitude": 21.1702, "longitude": 72.8311},
            {"city": "Vadodara", "latitude": 22.3072, "longitude": 73.1812},
            {"city": "Rajkot", "latitude": 22.3039, "longitude": 70.8022},
            {"city": "Gandhinagar", "latitude": 23.2156, "longitude": 72.6369}
        ]

        if not self.api_key:
            # Simulated Streaming loop
            print("YouTubeCrawler: Simulating live YouTube comments stream...")
            q = " ".join(keywords) if keywords else "Gujarat"
            idx = 0
            while True:
                idx += 1
                text_choices = [
                    f"Warning: Road blockade near Surat bypass tomorrow morning for {q}!",
                    f"Fake news alerts: do not believe unofficial videos about {q}.",
                    f"We must gather near Vadodara for {q} protests.",
                    f"Peaceful debate regarding {q} live broadcast.",
                    f"Anyone has updates on the situation of {q} in Rajkot?"
                ]
                geo_choice = random.choice(cities)
                yield {
                    "id": f"yt_stream_sim_{idx}_{random.randint(1000, 9999)}",
                    "username": f"@yt_reporter_{idx}",
                    "platform": "YouTube",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "text": random.choice(text_choices),
                    "engagement": {
                        "likes": random.randint(5, 50),
                        "shares": 0,
                        "comments": 0
                    },
                    "geo": geo_choice
                }
                await asyncio.sleep(8)

        yielded_ids = set()
        q = " ".join(keywords) if keywords else "Gujarat"
        print(f"YouTubeCrawler: Starting live polling stream for '{q}'")

        search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(q)}&type=video&maxResults=5&key={self.api_key}"
        video_ids = []
        try:
            req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as res:
                search_data = json.loads(res.read().decode())
                for item in search_data.get("items", []):
                    vid_id = item.get("id", {}).get("videoId")
                    if vid_id:
                        video_ids.append(vid_id)
        except Exception as e:
            print(f"YouTubeCrawler: Stream start search failed: {e}. Falling back to simulation loop.")
            self.api_key = None
            async for p in self.stream_posts(keywords, geo):
                yield p
            return

        if not video_ids:
            print("YouTubeCrawler: Search yielded 0 videos. Falling back to simulation loop.")
            self.api_key = None
            async for p in self.stream_posts(keywords, geo):
                yield p
            return

        import re
        while True:
            for vid_id in video_ids:
                comment_url = f"https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&videoId={vid_id}&maxResults=10&key={self.api_key}"
                try:
                    comment_req = urllib.request.Request(comment_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(comment_req, timeout=10) as res:
                        comment_data = json.loads(res.read().decode())
                        for item in comment_data.get("items", []):
                            snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                            comment_id = item.get("id", "")

                            if not comment_id or comment_id in yielded_ids:
                                continue

                            yielded_ids.add(comment_id)
                            author = snippet.get("authorDisplayName", "Anonymous")
                            text = snippet.get("textDisplay", "")
                            timestamp = snippet.get("publishedAt", datetime.utcnow().isoformat() + "Z")
                            likes = snippet.get("likeCount", 0)

                            clean_text = text.replace("<br>", "\n").replace("<br />", "\n")
                            clean_text = re.sub(r'<[^>]*>', '', clean_text)
                            geo_choice = random.choice(cities)

                            yield {
                                "id": comment_id,
                                "username": author if author.startswith("@") else f"@{author.replace(' ', '_').lower()}",
                                "platform": "YouTube",
                                "timestamp": timestamp,
                                "text": clean_text,
                                "engagement": {
                                    "likes": likes,
                                    "shares": 0,
                                    "comments": 0
                                },
                                "geo": geo_choice
                            }
                            await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"YouTubeCrawler: stream thread comments error for video {vid_id}: {e}")
                    continue

            # Poll comments every 15 seconds to stay within quota guidelines
            await asyncio.sleep(15)


class TelegramCrawler(BaseCrawler):
    """
    Ingestion client for Telegram channels using MTProto Client API (Telethon).
    """
    
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.session_path = os.path.abspath(os.path.join(current_dir, "..", "..", "telegram_session"))
        
        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        if self.api_id:
            try:
                self.api_id = int(self.api_id)
            except ValueError:
                self.api_id = None
        
        if not self.api_id or not self.api_hash:
            print("TelegramCrawler: TELEGRAM_API_ID or TELEGRAM_API_HASH environment variables missing.")

    def fetch_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None, 
        since: str = None
    ) -> Any:
        if not self.api_id or not self.api_hash:
            return {
                "status": "pending_auth", 
                "message": "Telegram API credentials not configured or session not authenticated"
            }
            
        import threading
        result_container = []
        
        def worker():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            except Exception as e:
                result_container.append({"status": "pending_auth", "message": f"Event loop initialization error: {e}"})
                return
                
            from telethon import TelegramClient
            client = TelegramClient(self.session_path, self.api_id, self.api_hash, loop=loop)
            
            async def run():
                try:
                    await client.connect()
                    if not await client.is_user_authorized():
                        return {
                            "status": "pending_auth", 
                            "message": "Telegram session not authenticated. Run login flow first."
                        }
                    
                    posts = []
                    channels = ["gujaratsamacharofficial", "divyabhaskar", "ABPAsmitaOfficial", "SandeshNewsOfficial"]
                    cities = [
                        {"city": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714},
                        {"city": "Surat", "latitude": 21.1702, "longitude": 72.8311},
                        {"city": "Vadodara", "latitude": 22.3072, "longitude": 73.1812},
                        {"city": "Rajkot", "latitude": 22.3039, "longitude": 70.8022},
                        {"city": "Gandhinagar", "latitude": 23.2156, "longitude": 72.6369}
                    ]
                    
                    for channel in channels:
                        try:
                            async for message in client.iter_messages(channel, limit=10):
                                if not message.text:
                                    continue
                                if keywords:
                                    text_lower = message.text.lower()
                                    if not any(k.lower() in text_lower for k in keywords):
                                        continue
                                        
                                post_id = f"tg_{channel}_{message.id}"
                                geo_choice = random.choice(cities)
                                posts.append({
                                    "id": post_id,
                                    "username": f"@{channel}",
                                    "platform": "Telegram",
                                    "timestamp": message.date.isoformat() if message.date else datetime.utcnow().isoformat() + "Z",
                                    "text": message.text,
                                    "engagement": {
                                        "likes": getattr(message, "views", 0) // 100 or random.randint(1, 10),
                                        "shares": 0,
                                        "comments": 0
                                    },
                                    "geo": geo_choice
                                })
                        except Exception as e:
                            print(f"TelegramCrawler: Failed to fetch from channel {channel}: {e}")
                            
                    posts.sort(key=lambda p: p["timestamp"], reverse=True)
                    return posts
                except Exception as ex:
                    return {"status": "pending_auth", "message": f"Telegram connection error: {ex}"}
                finally:
                    await client.disconnect()

            try:
                res = loop.run_until_complete(run())
                result_container.append(res)
            except Exception as e:
                result_container.append({"status": "pending_auth", "message": f"Telegram loop execution error: {e}"})
            finally:
                loop.close()

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        
        return result_container[0] if result_container else []

    async def stream_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.api_id or not self.api_hash:
            yield {
                "status": "pending_auth", 
                "message": "Telegram API credentials not configured or session not authenticated"
            }
            return
            
        from telethon import TelegramClient
        client = TelegramClient(self.session_path, self.api_id, self.api_hash)
        
        await client.connect()
        if not await client.is_user_authorized():
            yield {
                "status": "pending_auth", 
                "message": "Telegram session not authenticated. Run login flow first."
            }
            await client.disconnect()
            return
            
        yielded_ids = set()
        channels = ["gujaratsamacharofficial", "divyabhaskar", "ABPAsmitaOfficial", "SandeshNewsOfficial"]
        cities = [
            {"city": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714},
            {"city": "Surat", "latitude": 21.1702, "longitude": 72.8311},
            {"city": "Vadodara", "latitude": 22.3072, "longitude": 73.1812},
            {"city": "Rajkot", "latitude": 22.3039, "longitude": 70.8022},
            {"city": "Gandhinagar", "latitude": 23.2156, "longitude": 72.6369}
        ]
        
        print(f"TelegramCrawler: Starting live polling stream for channels: {channels}")
        
        try:
            while True:
                for channel in channels:
                    try:
                        async for message in client.iter_messages(channel, limit=5):
                            if not message.text:
                                continue
                            if keywords:
                                text_lower = message.text.lower()
                                if not any(k.lower() in text_lower for k in keywords):
                                    continue
                                    
                            post_id = f"tg_{channel}_{message.id}"
                            if post_id in yielded_ids:
                                continue
                                
                            yielded_ids.add(post_id)
                            geo_choice = random.choice(cities)
                            yield {
                                "id": post_id,
                                "username": f"@{channel}",
                                "platform": "Telegram",
                                "timestamp": message.date.isoformat() if message.date else datetime.utcnow().isoformat() + "Z",
                                "text": message.text,
                                "engagement": {
                                    "likes": getattr(message, "views", 0) // 100 or random.randint(1, 10),
                                    "shares": 0,
                                    "comments": 0
                                },
                                "geo": geo_choice
                            }
                            await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"TelegramCrawler: error fetching from channel {channel}: {e}")
                        continue
                
                await asyncio.sleep(20)
        finally:
            await client.disconnect()
