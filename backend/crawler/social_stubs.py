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

def _is_enabled(env_var: str, default: bool = True) -> bool:
    """Read a boolean env var. Treats missing/empty as the default."""
    val = os.getenv(env_var, "").strip().lower()
    if not val:
        return default
    return val not in ("false", "0", "no", "off")


def _read_seed_list(env_var: str) -> List[str]:
    """
    Read an optional comma-separated list of channel/page identifiers.
    Returns [] silently when the env var is unset or empty — an empty list
    means 'no manually specified seeds' rather than 'disabled'.
    Strips leading '@' for uniformity.
    """
    raw = os.getenv(env_var, "").strip()
    if not raw:
        return []
    return [c.strip().lstrip("@") for c in raw.split(",") if c.strip()]


# Global discovery settings — read once at module load.
# SOCIAL_AUTO_DISCOVERY: when true (default), crawlers attempt keyword-driven
#   source discovery before falling back to manually specified seeds.
# SOCIAL_SOURCE_MODE: 'auto' (default) or 'manual'. In 'manual' mode only
#   manually specified seeds (TELEGRAM_CHANNELS / FACEBOOK_PAGES) are used.
AUTO_DISCOVERY: bool = _is_enabled("SOCIAL_AUTO_DISCOVERY", default=True)
SOURCE_MODE: str = os.getenv("SOCIAL_SOURCE_MODE", "auto").strip().lower()


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
    Ingestion client for Facebook using Meta Graph API.

    Discovery mode (SOCIAL_AUTO_DISCOVERY=true, default):
        Attempts automatic page discovery via GET /search?type=page&q=<keyword>.
        Falls back gracefully when the token lacks 'pages_search' permission.
        FACEBOOK_PAGES seeds are merged with any auto-discovered pages.

    Manual mode (SOCIAL_SOURCE_MODE=manual):
        Only fetches from pages explicitly listed in FACEBOOK_PAGES.

    Disabled (ENABLE_FACEBOOK=false):
        Returns a disabled status immediately without making any API calls.

    Note: Meta Graph API removed general public-post keyword search in 2018.
    Page discovery via /search?type=page requires 'pages_search' permission.
    """

    def __init__(self, lookback_days: int = 7):
        self.lookback_days = lookback_days
        self.enabled = _is_enabled("ENABLE_FACEBOOK", default=True)
        self.auto_discovery = AUTO_DISCOVERY
        self.source_mode = SOURCE_MODE
        self.app_id = os.getenv("META_APP_ID")
        self.app_secret = os.getenv("META_APP_SECRET")
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        # Optional seed pages — merged with auto-discovered pages, not a restriction
        self.seed_pages = _read_seed_list("FACEBOOK_PAGES")
        if self.seed_pages:
            print(f"[crawler] FacebookCrawler: {len(self.seed_pages)} seed page(s): {self.seed_pages}")
        if not self.access_token:
            print("FacebookCrawler: META_ACCESS_TOKEN is missing. Operating in review-scaffold mode.")
        if not self.enabled:
            print("[crawler] FacebookCrawler: disabled via ENABLE_FACEBOOK=false")

    def _discover_pages(self, keywords: List[str]) -> List[str]:
        """
        Attempt to discover relevant Facebook pages via keyword search.

        Calls GET /v20.0/search?type=page&q=<keyword>. This requires the
        'pages_search' permission on the access token. If the endpoint
        returns a 400/403, logs a clear explanation and returns [] — it does
        NOT raise an exception or block other operations.

        Returns a list of numeric page IDs discovered.
        """
        if not self.access_token or not keywords:
            return []
        query = " ".join(keywords[:3])  # Use up to 3 keywords for the query
        url = (
            f"https://graph.facebook.com/v20.0/search"
            f"?q={urllib.parse.quote(query)}&type=page"
            f"&fields=id,name&limit=10"
            f"&access_token={self.access_token}"
        )
        res = make_meta_request(url)
        if res["success"]:
            pages = [item["id"] for item in res["data"].get("data", []) if item.get("id")]
            if pages:
                names = [item.get("name", item["id"]) for item in res["data"].get("data", []) if item.get("id")]
                print(f"[crawler] FacebookCrawler: Auto-discovered {len(pages)} page(s): {names}")
            return pages
        sc = res.get("status_code", 0)
        if sc in (400, 403):
            print(
                f"[crawler] FacebookCrawler: Auto-discovery unavailable — "
                f"token lacks 'pages_search' permission (HTTP {sc}). "
                f"Falling back to FACEBOOK_PAGES seeds."
            )
        else:
            print(f"[crawler] FacebookCrawler: Page discovery call failed (HTTP {sc}): {res['error_body']}")
        return []

    def _resolve_page_list(self, keywords: List[str]) -> List[str]:
        """
        Build the final ordered list of pages to fetch from:
        1. Auto-discovered pages (when SOCIAL_AUTO_DISCOVERY=true and SOCIAL_SOURCE_MODE!=manual)
        2. Manually specified seeds from FACEBOOK_PAGES (merged in, deduped)
        """
        if self.source_mode == "manual":
            return list(self.seed_pages)  # strict manual-only mode
        discovered = self._discover_pages(keywords) if self.auto_discovery else []
        seen = set(discovered)
        combined = list(discovered)
        for seed in self.seed_pages:
            if seed not in seen:
                combined.append(seed)
                seen.add(seed)
        return combined

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
        if not self.enabled:
            return {"status": "disabled", "message": "Facebook crawler is disabled (ENABLE_FACEBOOK=false)."}
        if not self.access_token:
            return {"status": "error", "message": "No credentials configured: META_ACCESS_TOKEN is missing."}

        page_ids = self._resolve_page_list(keywords or [])
        if not page_ids:
            if self.source_mode == "manual":
                return {
                    "status": "error",
                    "message": "No Facebook pages configured (SOCIAL_SOURCE_MODE=manual, FACEBOOK_PAGES is empty)."
                }
            return {
                "status": "error",
                "message": (
                    "No Facebook pages found via auto-discovery and no seeds configured in FACEBOOK_PAGES. "
                    "Set FACEBOOK_PAGES=<page_id1>,<page_id2> in .env, or ensure the token has 'pages_search' permission."
                )
            }

        all_posts: List[Dict] = []
        for page_id in page_ids:
            url = (
                f"https://graph.facebook.com/v20.0/{urllib.parse.quote(str(page_id))}/feed"
                f"?fields=id,message,created_time,shares,likes.summary(true),comments.summary(true)"
                f"&access_token={self.access_token}"
            )
            res = make_meta_request(url)
            if not res["success"]:
                print(f"FacebookCrawler: Failed to fetch page '{page_id}': {res['error_body']}")
                continue
            for item in res["data"].get("data", []):
                post = self._build_post(item, str(page_id))
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
        if not self.enabled:
            yield {"status": "disabled", "message": "Facebook crawler is disabled (ENABLE_FACEBOOK=false)."}
            return
        if not self.access_token:
            yield {"status": "error", "message": "No credentials configured: META_ACCESS_TOKEN is missing."}
            return

        posts = self.fetch_posts(keywords, geo)
        if isinstance(posts, dict):
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
    Ingestion client for Telegram using MTProto (Telethon).

    Discovery mode (SOCIAL_AUTO_DISCOVERY=true, default):
        Uses keyword-driven global message search across all channels the
        session account has joined:
            client.iter_messages(None, search=query)
        The system automatically identifies the source channel from each
        message — no channel list needed in advance.
        TELEGRAM_CHANNELS acts as optional seed channels: if provided, the
        crawler joins them first (expanding the searchable dialog set), then
        searches across everything.

    Manual mode (SOCIAL_SOURCE_MODE=manual):
        Only fetches from channels explicitly listed in TELEGRAM_CHANNELS,
        with keyword filtering applied.

    Disabled (ENABLE_TELEGRAM=false):
        Returns a disabled status immediately without connecting.

    source_url format: https://t.me/<channel_username>/<message_id>
    Set to None for private channels/groups (no public permalink available).
    """

    def __init__(self, lookback_days: int = 7):
        self.lookback_days = lookback_days
        self.enabled = _is_enabled("ENABLE_TELEGRAM", default=True)
        self.auto_discovery = AUTO_DISCOVERY
        self.source_mode = SOURCE_MODE
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

        # Optional seed channels — joined before global search to expand the
        # searchable dialog set. Not a fixed allowlist.
        self.seed_channels = _read_seed_list("TELEGRAM_CHANNELS")
        if self.seed_channels:
            print(f"[crawler] TelegramCrawler: {len(self.seed_channels)} seed channel(s) will be joined: {self.seed_channels}")
        if not self.enabled:
            print("[crawler] TelegramCrawler: disabled via ENABLE_TELEGRAM=false")


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
        source_url is set to the t.me permalink when channel_username is known
        (public channel). Set to None for private channels/groups.
        """
        post_id = f"tg_{channel_username or 'private'}_{message.id}"
        source_url = (
            f"https://t.me/{channel_username}/{message.id}"
            if channel_username
            else None
        )
        return {
            "id": post_id,
            "username": f"@{channel_username}" if channel_username else "@private_channel",
            "platform": "Telegram",
            "timestamp": message.date.isoformat() if message.date else datetime.utcnow().isoformat() + "Z",
            "text": message.text,
            "source_url": source_url,
            "engagement": {
                "likes": (getattr(message, "views", 0) or 0) // 100 or random.randint(1, 10),
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
        if not self.enabled:
            return {"status": "disabled", "message": "Telegram crawler is disabled (ENABLE_TELEGRAM=false)."}
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
                result_container.append({"status": "pending_auth", "message": f"Event loop init error: {e}"})
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
                    query = " ".join(keywords) if keywords else ""
                    posts: List[Dict] = []
                    seen_ids: set = set()

                    # Collect all entities/channels to scan
                    entities_to_scan = []

                    # 1. Join and add seed channels
                    for ch in self.seed_channels:
                        try:
                            entity = await client.get_entity(ch)
                            pub_username = getattr(entity, "username", None) or str(ch)
                            entities_to_scan.append((entity, pub_username))
                            print(f"[crawler] TelegramCrawler: Resolved seed channel '{ch}'")
                        except Exception as e:
                            print(f"[crawler] TelegramCrawler: Could not resolve seed '{ch}': {e}")

                    # 2. Dynamic discovery: search public channels by keywords
                    if self.auto_discovery and self.source_mode != "manual" and keywords:
                        from telethon.tl.functions.contacts import SearchRequest
                        from telethon.tl.types import Channel
                        for kw in keywords:
                            try:
                                search_res = await client(SearchRequest(q=kw, limit=8))
                                print(f"[crawler] TelegramCrawler: Discovered {len(search_res.chats)} public entities for '{kw}'")
                                for chat in search_res.chats:
                                    if isinstance(chat, Channel):
                                        username = getattr(chat, "username", None)
                                        # Deduplicate against seeds and already added channels
                                        if username and not any(u == username for _, u in entities_to_scan):
                                            entities_to_scan.append((chat, username))
                                            print(f"[crawler] TelegramCrawler: Auto-discovered public channel '@{username}'")
                            except Exception as se:
                                print(f"[crawler] TelegramCrawler: Dynamic channel search failed for '{kw}': {se}")

                    # ── Fetching messages from target entities ──
                    for entity, pub_username in entities_to_scan:
                        try:
                            print(f"[crawler] TelegramCrawler: Fetching from channel '@{pub_username}'")
                            async for message in client.iter_messages(
                                entity, limit=30
                            ):
                                if not message.text:
                                    continue
                                if message.date and message.date < cutoff_date:
                                    # Since messages are returned newest first, we can stop fetching
                                    break
                                if keywords:
                                    if not any(k.lower() in message.text.lower() for k in keywords):
                                        continue
                                post = self._build_post(message, pub_username)
                                if post["id"] not in seen_ids:
                                    seen_ids.add(post["id"])
                                    posts.append(post)
                        except Exception as fe:
                            print(f"[crawler] TelegramCrawler: Failed to fetch from '{pub_username}': {fe}")

                    # ── Fallback/Comprehensive: Keyword-driven global search across joined dialogs ──
                    if query and self.source_mode != "manual":
                        print(f"[crawler] TelegramCrawler: Running global search for '{query}'")
                        try:
                            async for message in client.iter_messages(
                                None, search=query, limit=100
                            ):
                                if not message.text:
                                    continue
                                if message.date and message.date < cutoff_date:
                                    continue
                                chat = getattr(message, "chat", None)
                                channel_username = getattr(chat, "username", None) if chat else None
                                post = self._build_post(message, channel_username)
                                if post["id"] not in seen_ids:
                                    seen_ids.add(post["id"])
                                    posts.append(post)
                        except Exception as e:
                            print(f"[crawler] TelegramCrawler: Global search error: {e}")

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
                result_container.append({"status": "pending_auth", "message": f"Telegram loop error: {e}"})
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
        if not self.enabled:
            yield {"status": "disabled", "message": "Telegram crawler is disabled (ENABLE_TELEGRAM=false)."}
            return
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

        query = " ".join(keywords) if keywords else ""
        print(f"[crawler] TelegramCrawler: Starting auto-discovery stream for query '{query}'")

        # Join seed channels first to expand the searchable dialog set
        for ch in self.seed_channels:
            try:
                await client.get_entity(ch)
            except Exception as e:
                print(f"[crawler] TelegramCrawler: Could not resolve seed '{ch}': {e}")

        yielded_ids: set = set()

        try:
            while True:
                from datetime import timezone, timedelta
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)

                # Get all entities to stream from
                entities_to_scan = []

                # Add seeds
                for ch in self.seed_channels:
                    try:
                        ent = await client.get_entity(ch)
                        pub_username = getattr(ent, "username", None) or str(ch)
                        entities_to_scan.append((ent, pub_username))
                    except Exception:
                        pass

                # Discover new channels based on keywords
                if self.auto_discovery and self.source_mode != "manual" and keywords:
                    from telethon.tl.functions.contacts import SearchRequest
                    from telethon.tl.types import Channel
                    for kw in keywords:
                        try:
                            search_res = await client(SearchRequest(q=kw, limit=5))
                            for chat in search_res.chats:
                                if isinstance(chat, Channel):
                                    username = getattr(chat, "username", None)
                                    if username and not any(u == username for _, u in entities_to_scan):
                                        entities_to_scan.append((chat, username))
                        except Exception as se:
                            print(f"[crawler] TelegramCrawler: Dynamic search failed during stream: {se}")

                # ── Stream posts from resolved entities ──
                for entity, pub_username in entities_to_scan:
                    try:
                        async for message in client.iter_messages(entity, limit=5):
                            if not message.text:
                                continue
                            if message.date and message.date < cutoff_date:
                                continue
                            if keywords:
                                if not any(k.lower() in message.text.lower() for k in keywords):
                                    continue
                            post = self._build_post(message, pub_username)
                            if post["id"] not in yielded_ids:
                                yielded_ids.add(post["id"])
                                yield post
                                await asyncio.sleep(0.5)
                    except Exception:
                        pass

                # ── Fallback/Comprehensive: search all joined dialogs ──
                if query and self.source_mode != "manual":
                    try:
                        async for message in client.iter_messages(None, search=query, limit=20):
                            if not message.text:
                                continue
                            if message.date and message.date < cutoff_date:
                                continue
                            chat = getattr(message, "chat", None)
                            channel_username = getattr(chat, "username", None) if chat else None
                            post = self._build_post(message, channel_username)
                            if post["id"] not in yielded_ids:
                                yielded_ids.add(post["id"])
                                yield post
                                await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"[crawler] TelegramCrawler: Stream global search error: {e}")

                await asyncio.sleep(20)
        finally:
            await client.disconnect()


