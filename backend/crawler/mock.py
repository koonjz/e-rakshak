import os
import json
import asyncio
import random
from typing import List, Dict, Any, AsyncGenerator
from .base import BaseCrawler

class MockCrawler(BaseCrawler):
    """
    Mock social crawler that streams and fetches posts from a pre-generated JSON file
    to simulate real-time social media activity.
    """
    
    def __init__(self, data_path: str = None):
        if data_path is None:
            # Resolve path relative to backend/crawler/mock.py
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Expected: root/data/sample_posts.json, which is 2 directories up
            resolved_path = os.path.abspath(os.path.join(current_dir, "..", "..", "data", "sample_posts.json"))
            
            # Fallback checks
            if not os.path.exists(resolved_path):
                # Check root directory relative
                resolved_path = os.path.abspath(os.path.join("data", "sample_posts.json"))
                
            self.data_path = resolved_path
        else:
            self.data_path = data_path
            
        self.posts = self._load_posts()

    def _load_posts(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.data_path):
            print(f"MockCrawler Warning: File not found at {self.data_path}")
            return []
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"MockCrawler Error loading dataset: {e}")
            return []

    def _matches_criteria(self, post: Dict[str, Any], keywords: List[str] = None, geo: Dict[str, Any] = None) -> bool:
        # Keyword filtering (case insensitive search in text)
        if keywords:
            text = post.get("text", "").lower()
            if not any(kw.lower() in text for kw in keywords):
                return False
                
        # Geo filtering (by city name if specified in geo dict)
        if geo and "city" in geo:
            city_filter = geo["city"].lower()
            post_city = post.get("geo", {}).get("city", "").lower()
            if city_filter != post_city:
                return False
                
        return True

    def fetch_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None, 
        since: str = None
    ) -> List[Dict[str, Any]]:
        """
        Filters and returns posts immediately.
        """
        filtered = []
        for post in self.posts:
            if not self._matches_criteria(post, keywords, geo):
                continue
            
            # Simple timestamp filter
            if since and post.get("timestamp", "") < since:
                continue
                
            filtered.append(post)
        return filtered

    async def stream_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Simulates an infinite stream of incoming social media posts with random delays.
        """
        if not self.posts:
            print("MockCrawler Error: No posts loaded to stream.")
            return

        # Copy posts to shuffle and stream
        stream_pool = list(self.posts)
        random.shuffle(stream_pool)
        
        index = 0
        while True:
            post = stream_pool[index]
            
            if self._matches_criteria(post, keywords, geo):
                # Update timestamp to present to simulate active ingestion
                simulated_post = dict(post)
                # Set dynamic simulated timestamp (current time)
                from datetime import datetime
                simulated_post["timestamp"] = datetime.now().isoformat()
                
                yield simulated_post
                
                # Sleep between 0.5 to 2.5 seconds to simulate incoming stream delay
                delay = random.uniform(0.5, 2.5)
                await asyncio.sleep(delay)
            
            index += 1
            if index >= len(stream_pool):
                # Re-shuffle and loop indefinitely
                random.shuffle(stream_pool)
                index = 0
