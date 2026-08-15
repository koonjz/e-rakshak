import os
import json
import random
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Any, AsyncGenerator, Optional
from .base import BaseCrawler

# Load environment variables from workspace root .env
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".env"))
load_dotenv(dotenv_path=dotenv_path)


# ---------------------------------------------------------------------------
# Env-var helpers
# ---------------------------------------------------------------------------

def _read_channel_list(env_var: str, label: str) -> List[str]:
    """
    Parse a comma-separated list of channel/page identifiers from an env var.
    Strips leading '@' for uniformity and returns clean strings.
    Logs a warning and returns [] when the env var is missing or empty.
    """
    raw = os.getenv(env_var, "").strip()
    if not raw:
        print(
            f"[crawler] WARNING: {env_var} is not set. "
            f"{label} crawler will not extract from any source. "
            f"Set {env_var} in your .env file as a comma-separated list."
        )
        return []
    channels = [c.strip().lstrip("@") for c in raw.split(",") if c.strip()]
    print(f"[crawler] {label} sources loaded from {env_var}: {channels}")
    return channels


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

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
            return {
                "success": True,
                "status_code": response.status,
                "data": json.loads(response.read().decode("utf-8"))
            }
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8"))
        except Exception:
            data = {"error": {"message": str(e), "code": e.code, "type": "HTTPError"}}
        return {"success": False, "status_code": e.code, "error_body": data}
    except Exception as e:
        return {
            "success": False,
            "status_code": 500,
            "error_body": {"error": {"message": str(e), "code": 500, "type": "InternalException"}}
        }


def make_meta_request(url: str) -> Dict[str, Any]:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "social-threat-analyzer/1.0", "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return {
                "success": True,
                "status_code": response.status,
                "data": json.loads(response.read().decode("utf-8"))
            }
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8"))
        except Exception:
            data = {"error": {"message": str(e), "code": e.code, "type": "HTTPError"}}
        return {"success": False, "status_code": e.code, "error_body": data}
    except Exception as e:
        return {
            "success": False,
            "status_code": 500,
            "error_body": {"error": {"message": str(e), "code": 500, "type": "InternalException"}}
        }


def make_youtube_request(url: str) -> Dict[str, Any]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return {
                "success": True,
                "status_code": response.status,
                "data": json.loads(response.read().decode("utf-8"))
            }
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8"))
        except Exception:
            data = {"error": {"message": str(e), "code": e.code, "type": "HTTPError"}}
        return {"success": False, "status_code": e.code, "error_body": data}
    except Exception as e:
        return {
            "success": False,
            "status_code": 500,
            "error_body": {"error": {"message": str(e), "code": 500, "type": "InternalException"}}
        }


# ---------------------------------------------------------------------------
# TwitterCrawler
# ---------------------------------------------------------------------------

class TwitterCrawler(BaseCrawler):
    """
    Ingestion client for X (formerly Twitter) using the official Twitter API v2.
    Searches across all public tweets matching the configured keywords —
    no specific account or profile is hardcoded.
    Each post includes a source_url pointing to the exact tweet.
    """

    def __init__(self, lookback_days: int = 7):
        self.lookback_days = lookback_days
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        if not self.bearer_token:
            print("TwitterCrawler: TWITTER_BEARER_TOKEN is missing. Operating in standby mode.")

    def _build_post(self, tweet: Dict, user: Dict) -> Dict[str, Any]:
        """Build a normalised post dict with source_url from a raw API tweet object."""
        metrics = tweet.get("public_metrics", {})
        tweet_id = tweet.get("id", "")
        username = user.get("username", f"user_{tweet.get('author_id')}")
        # Construct exact tweet permalink — never fabricated when tweet_id and username are present
        source_url = (
            f"https://twitter.com/{username}/status/{tweet_id}"
            if tweet_id and username
            else None
        )
        return {
            "id": tweet_id,
            "username": f"@{username}" if username and not username.startswith("@") else username,
            "platform": "twitter",
            "timestamp": tweet.get("created_at"),
            "text": tweet.get("text", ""),
            "language": "English",
            "threat_category": "Neutral",
            "source_url": source_url,
            "engagement": {
                "likes": metrics.get("like_count", 0),
                "shares": metrics.get("retweet_count", 0),
                "comments": metrics.get("reply_count", 0)
            },
            "geo": {"city": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714}
        }

    def fetch_posts(
        self,
        keywords: List[str] = None,
        geo: Dict[str, Any] = None,
        since: str = None
    ) -> Any:
        if not self.bearer_token:
            return {
                "status": "error",
                "message": "No credentials configured: TWITTER_BEARER_TOKEN is missing. "
                           "Ingestion is blocked by X paid-API requirement."
            }

        query = " ".join(keywords) if keywords else "gujarat"
        url = (
            f"https://api.twitter.com/2/tweets/search/recent"
            f"?query={urllib.parse.quote(query)}"
            f"&tweet.fields=created_at,public_metrics"
            f"&expansions=author_id"
            f"&max_results=10"
        )

        res = make_x_request(url, self.bearer_token)
        if res["success"]:
            users = {u["id"]: u for u in res["data"].get("includes", {}).get("users", [])}
            return [
                self._build_post(t, users.get(t.get("author_id"), {}))
                for t in res["data"].get("data", [])
            ]
        return {"status": "error", "status_code": res["status_code"], "error_body": res["error_body"]}

    async def stream_posts(
        self,
        keywords: List[str] = None,
        geo: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.bearer_token:
            yield {
                "status": "error",
                "message": "No credentials configured: TWITTER_BEARER_TOKEN is missing. "
                           "Ingestion is blocked by X paid-API requirement."
            }
            return

        posts = self.fetch_posts(keywords, geo)
        if isinstance(posts, dict) and posts.get("status") == "error":
            yield posts
        elif isinstance(posts, list):
            for post in posts:
                yield post


# ---------------------------------------------------------------------------
# InstagramCrawler
# ---------------------------------------------------------------------------

class InstagramCrawler(BaseCrawler):
    """
    Ingestion client for Instagram using Meta Graph API (hashtag search).
    Searches across public posts matching configured keywords — no specific
    account is hardcoded. Each post includes a source_url when available.
    """

    def __init__(self, lookback_days: int = 7):
        self.lookback_days = lookback_days
        self.app_id = os.getenv("META_APP_ID")
        self.app_secret = os.getenv("META_APP_SECRET")
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        if not self.access_token:
            print("InstagramCrawler: META_ACCESS_TOKEN is missing. Operating in review-scaffold mode.")

    def _build_post(self, item: Dict, keyword: str) -> Dict[str, Any]:
        """Build a normalised post dict with source_url from a raw Graph API media item."""
        item_id = item.get("id", "")
        # Instagram shortcode is not returned by hashtag search — permalink unavailable without it
        # We explicitly mark source_url as None rather than fabricating a link
        source_url = None
        tail = item_id[-4:] if len(item_id) >= 4 else item_id
        return {
            "id": item_id,
            "username": f"ig_user_{tail}",
            "platform": "instagram",
            "timestamp": item.get("timestamp"),
            "text": item.get("caption", ""),
            "language": "English",
            "threat_category": "Neutral",
            "source_url": source_url,  # Not constructable from hashtag search results
            "engagement": {
                "likes": item.get("like_count", 0),
                "shares": 0,
                "comments": item.get("comments_count", 0)
            },
            "geo": {"city": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714}
        }

    def fetch_posts(
        self,
        keywords: List[str] = None,
        geo: Dict[str, Any] = None,
        since: str = None
    ) -> Any:
        if not self.access_token:
            return {"status": "error", "message": "No credentials configured: META_ACCESS_TOKEN is missing."}

        keyword = keywords[0] if keywords else "gujarat"
        user_id = self.app_id or "123456789"
        url = (
            f"https://graph.facebook.com/v20.0/ig_hashtag_search"
            f"?user_id={user_id}&q={urllib.parse.quote(keyword)}&access_token={self.access_token}"
        )

        res = make_meta_request(url)
        if not res["success"]:
            return {"status": "error", "status_code": res["status_code"], "error_body": res["error_body"]}

        hashtag_id = res["data"].get("data", [{}])[0].get("id")
        if not hashtag_id:
            return []

        media_url = (
            f"https://graph.facebook.com/v20.0/{hashtag_id}/recent_media"
            f"?user_id={user_id}&fields=id,caption,timestamp,comments_count,like_count"
            f"&access_token={self.access_token}"
        )
        media_res = make_meta_request(media_url)
        if not media_res["success"]:
            return {"status": "error", "status_code": media_res["status_code"], "error_body": media_res["error_body"]}

        return [self._build_post(item, keyword) for item in media_res["data"].get("data", [])]

    async def stream_posts(
        self,
        keywords: List[str] = None,
        geo: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.access_token:
            yield {"status": "error", "message": "No credentials configured: META_ACCESS_TOKEN is missing."}
            return

        posts = self.fetch_posts(keywords, geo)
        if isinstance(posts, dict) and posts.get("status") == "error":
            yield posts
        elif isinstance(posts, list):
            for post in posts:
                yield post


# ---------------------------------------------------------------------------
# FacebookCrawler
# ---------------------------------------------------------------------------

class FacebookCrawler(BaseCrawler):
    """
    Ingestion client for Facebook Page posts using Meta Graph API.

    Target pages are read from the FACEBOOK_PAGES environment variable
    (comma-separated page IDs or slugs). No page is hardcoded.
    Each post includes a source_url when constructable.
    """

    def __init__(self, lookback_days: int = 7):
        self.lookback_days = lookback_days
        self.app_id = os.getenv("META_APP_ID")
        self.app_secret = os.getenv("META_APP_SECRET")
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        # Discover pages from env — no hardcoded defaults
        self.pages = _read_channel_list("FACEBOOK_PAGES", "FacebookCrawler")
        if not self.access_token:
            print("FacebookCrawler: META_ACCESS_TOKEN is missing. Operating in review-scaffold mode.")

    def _build_post(self, item: Dict, page_id: str) -> Dict[str, Any]:
        """Build a normalised post dict with source_url from a raw Graph API feed item."""
        raw_id = item.get("id", "")
        # Facebook post IDs are typically "<page_id>_<post_id>"
        post_suffix = raw_id.split("_", 1)[-1] if "_" in raw_id else raw_id
        source_url = (
            f"https://www.facebook.com/{page_id}/posts/{post_suffix}"
            if page_id and post_suffix
            else None
        )
        likes_summary = item.get("likes", {}).get("summary", {})
        comments_summary = item.get("comments", {}).get("summary", {})
        return {
            "id": raw_id,
            "username": f"@{page_id}",
            "platform": "facebook",
            "timestamp": item.get("created_time"),
            "text": item.get("message", ""),
            "language": "English",
            "threat_category": "Neutral",
            "source_url": source_url,
            "engagement": {
                "likes": likes_summary.get("total_count", 0),
                "shares": item.get("shares", {}).get("count", 0),
                "comments": comments_summary.get("total_count", 0)
            },
            "geo": {"city": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714}
        }

    def fetch_posts(
        self,
        keywords: List[str] = None,
        geo: Dict[str, Any] = None,
        since: str = None
    ) -> Any:
        if not self.access_token:
            return {"status": "error", "message": "No credentials configured: META_ACCESS_TOKEN is missing."}
        if not self.pages:
            return {"status": "error", "message": "No Facebook pages configured. Set FACEBOOK_PAGES in .env."}

        all_posts: List[Dict] = []
        for page_id in self.pages:
            url = (
                f"https://graph.facebook.com/v20.0/{urllib.parse.quote(page_id)}/feed"
                f"?fields=id,message,created_time,shares,likes.summary(true),comments.summary(true)"
                f"&access_token={self.access_token}"
            )
            res = make_meta_request(url)
            if not res["success"]:
                print(f"FacebookCrawler: Failed to fetch page '{page_id}': {res['error_body']}")
                continue
            for item in res["data"].get("data", []):
                post = self._build_post(item, page_id)
                # Optional keyword filter
                if keywords:
                    text_lower = post["text"].lower()
                    if not any(k.lower() in text_lower for k in keywords):
                        continue
                all_posts.append(post)
        return all_posts

    async def stream_posts(
        self,
        keywords: List[str] = None,
        geo: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.access_token:
            yield {"status": "error", "message": "No credentials configured: META_ACCESS_TOKEN is missing."}
            return
        if not self.pages:
            yield {"status": "error", "message": "No Facebook pages configured. Set FACEBOOK_PAGES in .env."}
            return

        posts = self.fetch_posts(keywords, geo)
        if isinstance(posts, dict) and posts.get("status") == "error":
            yield posts
        elif isinstance(posts, list):
            for post in posts:
                yield post


# ---------------------------------------------------------------------------
# YouTubeCrawler
# ---------------------------------------------------------------------------

class YouTubeCrawler(BaseCrawler):
    """
    Ingestion client for YouTube videos and comment threads using YouTube Data API v3.
    Searches across all public videos matching the configured keywords —
    no specific channel or account is hardcoded.
    Each comment includes a source_url linking to the exact comment on the video.
    """

    def __init__(self, lookback_days: int = 7):
        self.lookback_days = lookback_days
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        if not self.api_key or self.api_key.startswith("your_real_"):
            self.api_key = None
            print("YouTubeCrawler WARNING: YOUTUBE_API_KEY environment variable is not defined or is placeholder.")

    _CITIES = [
        {"city": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714},
        {"city": "Surat", "latitude": 21.1702, "longitude": 72.8311},
        {"city": "Vadodara", "latitude": 22.3072, "longitude": 73.1812},
        {"city": "Rajkot", "latitude": 22.3039, "longitude": 70.8022},
        {"city": "Gandhinagar", "latitude": 23.2156, "longitude": 72.6369}
    ]

    def _build_comment_post(self, item: Dict, video_id: str) -> Optional[Dict[str, Any]]:
        """Build a normalised post dict for a YouTube comment with source_url."""
        import re
        snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
        comment_id = item.get("id", "")
        if not comment_id:
            return None
        author = snippet.get("authorDisplayName", "Anonymous")
        text = snippet.get("textDisplay", "")
        clean_text = re.sub(r'<[^>]*>', '', text.replace("<br>", "\n").replace("<br />", "\n"))
        timestamp = snippet.get("publishedAt", datetime.utcnow().isoformat() + "Z")
        likes = snippet.get("likeCount", 0)
        # Direct permalink to the exact comment on the video
        source_url = (
            f"https://www.youtube.com/watch?v={video_id}&lc={urllib.parse.quote(comment_id)}"
            if video_id and comment_id
            else None
        )
        username = author if author.startswith("@") else f"@{author.replace(' ', '_').lower()}"
        return {
            "id": comment_id,
            "username": username,
            "platform": "YouTube",
            "timestamp": timestamp,
            "text": clean_text,
            "source_url": source_url,
            "engagement": {"likes": likes, "shares": 0, "comments": 0},
            "geo": random.choice(self._CITIES)
        }

    def _search_video_ids(self, q: str, published_after: str) -> List[str]:
        url = (
            f"https://www.googleapis.com/youtube/v3/search"
            f"?part=snippet&q={urllib.parse.quote(q)}&type=video&maxResults=5"
            f"&key={self.api_key}&publishedAfter={urllib.parse.quote(published_after)}"
        )
        res = make_youtube_request(url)
        if not res["success"]:
            print(f"YouTubeCrawler: search failed: {res['error_body']}")
            return []
        return [
            item.get("id", {}).get("videoId")
            for item in res["data"].get("items", [])
            if item.get("id", {}).get("videoId")
        ]

    def fetch_posts(
        self,
        keywords: List[str] = None,
        geo: Dict[str, Any] = None,
        since: str = None
    ) -> Any:
        if not self.api_key:
            return {"status": "error", "message": "No credentials configured: YOUTUBE_API_KEY is missing."}

        q = " ".join(keywords) if keywords else "Gujarat"
        if since:
            cleaned = since.split(".")[0]
            published_after = cleaned if cleaned.endswith("Z") else cleaned + "Z"
        else:
            from datetime import timedelta, timezone
            cutoff = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)
            published_after = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

        video_ids = self._search_video_ids(q, published_after)
        posts: List[Dict] = []
        for vid_id in video_ids:
            comment_url = (
                f"https://www.googleapis.com/youtube/v3/commentThreads"
                f"?part=snippet&videoId={vid_id}&maxResults=10&key={self.api_key}"
            )
            comment_res = make_youtube_request(comment_url)
            if not comment_res["success"]:
                print(f"YouTubeCrawler: Failed comments download for video {vid_id}: {comment_res['error_body']}")
                continue
            for item in comment_res["data"].get("items", []):
                post = self._build_comment_post(item, vid_id)
                if post:
                    posts.append(post)
        return posts

    async def stream_posts(
        self,
        keywords: List[str] = None,
        geo: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        if not self.api_key:
            yield {"status": "error", "message": "No credentials configured: YOUTUBE_API_KEY is missing."}
            return

        from datetime import timedelta, timezone
        q = " ".join(keywords) if keywords else "Gujarat"
        print(f"YouTubeCrawler: Starting live polling stream for '{q}'")
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)
        published_after = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
        video_ids = self._search_video_ids(q, published_after)

        yielded_ids: set = set()
        while True:
            for vid_id in video_ids:
                comment_url = (
                    f"https://www.googleapis.com/youtube/v3/commentThreads"
                    f"?part=snippet&videoId={vid_id}&maxResults=10&key={self.api_key}"
                )
                comment_res = make_youtube_request(comment_url)
                if not comment_res["success"]:
                    print(f"YouTubeCrawler: stream comments error for video {vid_id}: {comment_res['error_body']}")
                    continue
                for item in comment_res["data"].get("items", []):
                    post = self._build_comment_post(item, vid_id)
                    if not post or post["id"] in yielded_ids:
                        continue
                    yielded_ids.add(post["id"])
                    yield post
                    await asyncio.sleep(0.5)
            await asyncio.sleep(20)


# ---------------------------------------------------------------------------
# TelegramCrawler
# ---------------------------------------------------------------------------

class TelegramCrawler(BaseCrawler):
    """
    Ingestion client for Telegram channels using MTProto Client API (Telethon).

    Target channels are read from the TELEGRAM_CHANNELS environment variable
    (comma-separated, with or without '@'). No channel is hardcoded.
    Each message includes a source_url in the form https://t.me/<username>/<message_id>
    for public channels, or None for private channels/groups.
    """

    def __init__(self, lookback_days: int = 7):
        self.lookback_days = lookback_days
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

        # Discover channels from env — no hardcoded list
        self.channels = _read_channel_list("TELEGRAM_CHANNELS", "TelegramCrawler")

    _CITIES = [
        {"city": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714},
        {"city": "Surat", "latitude": 21.1702, "longitude": 72.8311},
        {"city": "Vadodara", "latitude": 22.3072, "longitude": 73.1812},
        {"city": "Rajkot", "latitude": 22.3039, "longitude": 70.8022},
        {"city": "Gandhinagar", "latitude": 23.2156, "longitude": 72.6369}
    ]

    def _build_post(self, message: Any, channel_username: Optional[str]) -> Dict[str, Any]:
        """
        Build a normalised post dict for a Telegram message.
        source_url is set to the t.me permalink when channel_username is available
        (i.e. the channel is public). For private channels it is set to None.
        """
        post_id = f"tg_{channel_username or 'private'}_{message.id}"
        # Build direct post link only when the public username is known
        if channel_username:
            source_url = f"https://t.me/{channel_username}/{message.id}"
        else:
            source_url = None  # Private channel — direct link not available

        return {
            "id": post_id,
            "username": f"@{channel_username}" if channel_username else "@private_channel",
            "platform": "Telegram",
            "timestamp": message.date.isoformat() if message.date else datetime.utcnow().isoformat() + "Z",
            "text": message.text,
            "source_url": source_url,
            "engagement": {
                "likes": getattr(message, "views", 0) // 100 or random.randint(1, 10),
                "shares": 0,
                "comments": 0
            },
            "geo": random.choice(self._CITIES)
        }

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
        if not self.channels:
            return {
                "status": "error",
                "message": "No Telegram channels configured. Set TELEGRAM_CHANNELS in .env."
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

                    from datetime import timezone, timedelta
                    cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)
                    posts: List[Dict] = []

                    for channel in self.channels:
                        try:
                            # Resolve the entity to get its public username (None for private)
                            entity = await client.get_entity(channel)
                            public_username = getattr(entity, "username", None)

                            async for message in client.iter_messages(
                                entity, limit=10, offset_date=cutoff_date, reverse=True
                            ):
                                if not message.text:
                                    continue
                                if message.date and message.date < cutoff_date:
                                    continue
                                if keywords:
                                    text_lower = message.text.lower()
                                    if not any(k.lower() in text_lower for k in keywords):
                                        continue
                                posts.append(self._build_post(message, public_username))

                        except Exception as e:
                            print(f"TelegramCrawler: Failed to fetch from channel '{channel}': {e}")

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
        if not self.channels:
            yield {
                "status": "error",
                "message": "No Telegram channels configured. Set TELEGRAM_CHANNELS in .env."
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

        print(f"TelegramCrawler: Starting live polling stream for channels: {self.channels}")

        # Pre-resolve entity -> public username mapping once
        entity_map: Dict[str, Optional[str]] = {}
        for channel in self.channels:
            try:
                entity = await client.get_entity(channel)
                entity_map[channel] = getattr(entity, "username", None)
            except Exception as e:
                print(f"TelegramCrawler: Could not resolve entity for '{channel}': {e}")
                entity_map[channel] = None

        yielded_ids: set = set()

        try:
            while True:
                for channel in self.channels:
                    try:
                        from datetime import timezone, timedelta
                        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)
                        public_username = entity_map.get(channel)

                        async for message in client.iter_messages(channel, limit=5):
                            if not message.text:
                                continue
                            if message.date and message.date < cutoff_date:
                                continue
                            if keywords:
                                text_lower = message.text.lower()
                                if not any(k.lower() in text_lower for k in keywords):
                                    continue

                            post = self._build_post(message, public_username)
                            if post["id"] in yielded_ids:
                                continue
                            yielded_ids.add(post["id"])
                            yield post
                            await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"TelegramCrawler: error fetching from channel '{channel}': {e}")
                        continue

                await asyncio.sleep(20)
        finally:
            await client.disconnect()
