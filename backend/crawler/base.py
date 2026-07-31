from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator

class BaseCrawler(ABC):
    """
    Abstract Base Class for pluggable social media crawlers.
    Each platform (Mock, Twitter, Instagram, etc.) must implement this class.
    """
    
    @abstractmethod
    def fetch_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None, 
        since: str = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical posts matching the given criteria.
        
        Args:
            keywords: List of search keywords/hashtags.
            geo: Dict specifying location coordinates and radius.
            since: ISO timestamp to fetch posts after.
            
        Returns:
            List of dictionaries representing post entities.
        """
        pass

    @abstractmethod
    async def stream_posts(
        self, 
        keywords: List[str] = None, 
        geo: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream live posts in near real-time.
        
        Args:
            keywords: List of search keywords/hashtags.
            geo: Dict specifying location coordinates and radius.
            
        Yields:
            Post entities as dictionaries as they arrive.
        """
        pass
