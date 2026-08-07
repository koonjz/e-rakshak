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

def make_x_request(url: str, token: str) -> Dict[str, Any]:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "social-threat-analyzer/1.0",
                "Accept": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            status = response.status
            body = response.read().decode("utf-8")
            data = json.loads(body)
            return {
                "success": True,
                "status_code": status,
                "data": data
            }
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body = e.read().decode("utf-8")
            data = json.loads(body)
        except Exception:
            data = {"error": {"message": str(e), "code": status, "type": "HTTPError"}}
        return {
            "success": False,
            "status_code": status,
            "error_body": data
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": 500,
            "error_body": {
                "error": {
                    "message": str(e),
                    "code": 500,
                    "type": "InternalException"
                }
            }
        }


class TwitterCrawler(BaseCrawler):
    """
    Ingestion client for X (formerly Twitter) using the official Twitter API v2.
    """
    
    def __init__(self):
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        if not self.bearer_token:
            print("TwitterCrawler: TWITTER_BEARER_TOKEN is missing. Operating in standby mode.")

    def fetch_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None, 
        since: str = None
    ) -> Any:
        if not self.bearer_token:
            return {
                "status": "error",
                "message": "No credentials configured: TWITTER_BEARER_TOKEN is missing. Ingestion is blocked by X paid-API requirement."
            }
            
        query = keywords[0] if keywords else "gujarat"
        url = f"https://api.twitter.com/2/tweets/search/recent?query={urllib.parse.quote(query)}&tweet.fields=created_at,public_metrics&expansions=author_id"
        
        res = make_x_request(url, self.bearer_token)
        if res["success"]:
            posts = []
            tweets = res["data"].get("data", [])
            users = {u["id"]: u for u in res["data"].get("includes", {}).get("users", [])}
            for t in tweets:
                user = users.get(t.get("author_id"), {})
                metrics = t.get("public_metrics", {})
                posts.append({
                    "id": t.get("id"),
                    "username": user.get("username", f"user_{t.get('author_id')}"),
                    "platform": "twitter",
                    "timestamp": t.get("created_at"),
                    "text": t.get("text", ""),
                    "language": "English",
                    "threat_category": "Neutral",
                    "engagement": {
                        "likes": metrics.get("like_count", 0),
                        "shares": metrics.get("retweet_count", 0),
                        "comments": metrics.get("reply_count", 0)
                    },
                    "geo": {"city": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714}
                })
            return posts
        else:
            return {
                "status": "error",
                "status_code": res["status_code"],
                "error_body": res["error_body"]
            }

    async def stream_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.bearer_token:
            yield {
                "status": "error",
                "message": "No credentials configured: TWITTER_BEARER_TOKEN is missing. Ingestion is blocked by X paid-API requirement."
            }
            return
            
        posts = self.fetch_posts(keywords, geo)
        if isinstance(posts, dict) and posts.get("status") == "error":
            yield posts
        elif isinstance(posts, list):
            for post in posts:
                yield post


def make_meta_request(url: str) -> Dict[str, Any]:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "social-threat-analyzer/1.0", "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            status = response.status
            body = response.read().decode("utf-8")
            data = json.loads(body)
            return {
                "success": True,
                "status_code": status,
                "data": data
            }
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body = e.read().decode("utf-8")
            data = json.loads(body)
        except Exception:
            data = {"error": {"message": str(e), "code": status, "type": "HTTPError"}}
        return {
            "success": False,
            "status_code": status,
            "error_body": data
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": 500,
            "error_body": {
                "error": {
                    "message": str(e),
                    "code": 500,
                    "type": "InternalException"
                }
            }
        }

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
        if not self.access_token:
            return {
                "status": "error",
                "message": "No credentials configured: META_ACCESS_TOKEN is missing."
            }
            
        query = keywords[0] if keywords else "gujarat"
        user_id = self.app_id or "123456789"
        url = f"https://graph.facebook.com/v20.0/ig_hashtag_search?user_id={user_id}&q={query}&access_token={self.access_token}"
        
        res = make_meta_request(url)
        if res["success"]:
            hashtag_id = res["data"].get("data", [{}])[0].get("id")
            if hashtag_id:
                media_url = f"https://graph.facebook.com/v20.0/{hashtag_id}/recent_media?user_id={user_id}&fields=id,caption,timestamp,comments_count,like_count&access_token={self.access_token}"
                media_res = make_meta_request(media_url)
                if media_res["success"]:
                    posts = []
                    for item in media_res["data"].get("data", []):
                        posts.append({
                            "id": item.get("id"),
                            "username": f"ig_user_{item.get('id')[-4:]}",
                            "platform": "instagram",
                            "timestamp": item.get("timestamp"),
                            "text": item.get("caption", ""),
                            "language": "English",
                            "threat_category": "Neutral",
                            "engagement": {
                                "likes": item.get("like_count", 0),
                                "shares": 0,
                                "comments": item.get("comments_count", 0)
                            },
                            "geo": {"city": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714}
                        })
                    return posts
                else:
                    return {
                        "status": "error",
                        "status_code": media_res["status_code"],
                        "error_body": media_res["error_body"]
                    }
            return []
        else:
            return {
                "status": "error",
                "status_code": res["status_code"],
                "error_body": res["error_body"]
            }

    async def stream_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.access_token:
            yield {
                "status": "error",
                "message": "No credentials configured: META_ACCESS_TOKEN is missing."
            }
            return
        
        posts = self.fetch_posts(keywords, geo)
        if isinstance(posts, dict) and posts.get("status") == "error":
            yield posts
        elif isinstance(posts, list):
            for post in posts:
                yield post


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
        if not self.access_token:
            return {
                "status": "error",
                "message": "No credentials configured: META_ACCESS_TOKEN is missing."
            }
            
        page_id = "cocacola"
        url = f"https://graph.facebook.com/v20.0/{page_id}/feed?fields=id,message,created_time,shares,likes.summary(true),comments.summary(true)&access_token={self.access_token}"
        
        res = make_meta_request(url)
        if res["success"]:
            posts = []
            for item in res["data"].get("data", []):
                likes_summary = item.get("likes", {}).get("summary", {})
                comments_summary = item.get("comments", {}).get("summary", {})
                shares_count = item.get("shares", {}).get("count", 0)
                posts.append({
                    "id": item.get("id"),
                    "username": page_id,
                    "platform": "facebook",
                    "timestamp": item.get("created_time"),
                    "text": item.get("message", ""),
                    "language": "English",
                    "threat_category": "Neutral",
                    "engagement": {
                        "likes": likes_summary.get("total_count", 0),
                        "shares": shares_count,
                        "comments": comments_summary.get("total_count", 0)
                    },
                    "geo": {"city": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714}
                })
            return posts
        else:
            return {
                "status": "error",
                "status_code": res["status_code"],
                "error_body": res["error_body"]
            }

    async def stream_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.access_token:
            yield {
                "status": "error",
                "message": "No credentials configured: META_ACCESS_TOKEN is missing."
            }
            return
        
        posts = self.fetch_posts(keywords, geo)
        if isinstance(posts, dict) and posts.get("status") == "error":
            yield posts
        elif isinstance(posts, list):
            for post in posts:
                yield post


def make_youtube_request(url: str) -> Dict[str, Any]:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            body = response.read().decode("utf-8")
            data = json.loads(body)
            return {
                "success": True,
                "status_code": status,
                "data": data
            }
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body = e.read().decode("utf-8")
            data = json.loads(body)
        except Exception:
            data = {"error": {"message": str(e), "code": status, "type": "HTTPError"}}
        return {
            "success": False,
            "status_code": status,
            "error_body": data
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": 500,
            "error_body": {
                "error": {
                    "message": str(e),
                    "code": 500,
                    "type": "InternalException"
                }
            }
        }


class YouTubeCrawler(BaseCrawler):
    """
    Ingestion client for YouTube videos and comment threads using YouTube Data API v3.
    """
    
    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        if not self.api_key or self.api_key.startswith("your_real_"):
            self.api_key = None
            print("YouTubeCrawler WARNING: YOUTUBE_API_KEY environment variable is not defined or is placeholder.")

    def fetch_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None, 
        since: str = None
    ) -> Any:
        if not self.api_key:
            return {
                "status": "error",
                "message": "No credentials configured: YOUTUBE_API_KEY is missing."
            }
            
        q = " ".join(keywords) if keywords else "Gujarat"
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(q)}&type=video&maxResults=5&key={self.api_key}"
        if since:
            cleaned_since = since.split(".")[0]
            if not cleaned_since.endswith("Z"):
                cleaned_since += "Z"
            url += f"&publishedAfter={urllib.parse.quote(cleaned_since)}"
            
        res = make_youtube_request(url)
        if not res["success"]:
            return {
                "status": "error",
                "status_code": res["status_code"],
                "error_body": res["error_body"]
            }
            
        video_ids = []
        for item in res["data"].get("items", []):
            vid_id = item.get("id", {}).get("videoId")
            if vid_id:
                video_ids.append(vid_id)
                
        posts = []
        cities = [
            {"city": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714},
            {"city": "Surat", "latitude": 21.1702, "longitude": 72.8311},
            {"city": "Vadodara", "latitude": 22.3072, "longitude": 73.1812},
            {"city": "Rajkot", "latitude": 22.3039, "longitude": 70.8022},
            {"city": "Gandhinagar", "latitude": 23.2156, "longitude": 72.6369}
        ]
        import re
        for vid_id in video_ids:
            comment_url = f"https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&videoId={vid_id}&maxResults=10&key={self.api_key}"
            comment_res = make_youtube_request(comment_url)
            if not comment_res["success"]:
                print(f"YouTubeCrawler: Failed comments download for video {vid_id}: {comment_res['error_body']}")
                continue
                
            for item in comment_res["data"].get("items", []):
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
                
        return posts

    async def stream_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.api_key:
            yield {
                "status": "error",
                "message": "No credentials configured: YOUTUBE_API_KEY is missing."
            }
            return
            
        yielded_ids = set()
        q = " ".join(keywords) if keywords else "Gujarat"
        print(f"YouTubeCrawler: Starting live polling stream for '{q}'")
        
        search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(q)}&type=video&maxResults=5&key={self.api_key}"
        res = make_youtube_request(search_url)
        if not res["success"]:
            yield {
                "status": "error",
                "status_code": res["status_code"],
                "error_body": res["error_body"]
            }
            return
            
        video_ids = []
        for item in res["data"].get("items", []):
            vid_id = item.get("id", {}).get("videoId")
            if vid_id:
                video_ids.append(vid_id)
                
        cities = [
            {"city": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714},
            {"city": "Surat", "latitude": 21.1702, "longitude": 72.8311},
            {"city": "Vadodara", "latitude": 22.3072, "longitude": 73.1812},
            {"city": "Rajkot", "latitude": 22.3039, "longitude": 70.8022},
            {"city": "Gandhinagar", "latitude": 23.2156, "longitude": 72.6369}
        ]
        import re
        while True:
            for vid_id in video_ids:
                comment_url = f"https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&videoId={vid_id}&maxResults=10&key={self.api_key}"
                comment_res = make_youtube_request(comment_url)
                if not comment_res["success"]:
                    print(f"YouTubeCrawler: stream comments error for video {vid_id}: {comment_res['error_body']}")
                    continue
                    
                for item in comment_res["data"].get("items", []):
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
            await asyncio.sleep(20)


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
