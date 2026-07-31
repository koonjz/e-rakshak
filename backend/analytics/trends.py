import re
from datetime import datetime
from collections import Counter, defaultdict
from typing import List, Dict, Any

# Stopword list covering English, Hindi, Gujarati, and Hinglish/Gujlish grammatical particles
STOPWORDS = {
    # English
    "the", "and", "are", "for", "you", "this", "that", "with", "from", "have", "about", "when", 
    "your", "last", "will", "some", "been", "here", "just", "very", "would", "they", "their", "them",
    "what", "than", "then", "there", "were", "was", "not", "out", "our", "but", "only", "about", "more",
    
    # Hindi / Hinglish particles
    "के", "में", "है", "हैं", "को", "का", "की", "से", "और", "पर", "इस", "भी", "कर", "यह", "हो", "तो",
    "लोग", "लोगों", "लिए", "नहीं", "कुछ", "एक", "था", "थी", "थे", "अब", "है", "हैं", "था", "थी", "थे",
    "hai", "hain", "aur", "bhi", "jo", "par", "chal", "karo", "hum", "sath", "saath", "liye", "hota",
    "hote", "gaya", "gayi", "gaye", "kya", "yeh", "woh", "isko", "unko", "inhe", "unhe", "raha", "rahe",
    "rhi", "rha", "tha", "thi", "the", "kar", "ke", "ki", "ko", "se", "ka", "pe", "se",
    
    # Gujarati / Gujlish particles
    "ને", "છે", "આ", "ની", "ના", "થી", "અને", "પણ", "નું", "આજે", "હતું", "હતા", "ખૂબ", "માટે", "હું",
    "તને", "અહીં", "તો", "કે", "એક", "તે", "હતા", "હતી", "હતું", "છો", "હું", "અમે", "તમે", "તેઓ",
    "chhe", "ne", "aa", "loko", "badha", "joya", "maza", "karyu", "nu", "ni", "no", "aemni", "tane",
    "mari", "thi", "ane", "pan", "potana", "aena", "aeni", "tari", "taro", "tara", "tame", "ame", "te",
    "su", "shu", "tyare", "aaje", "kale", "pela", "peli", "pelu"
}

def parse_timestamp(ts: str) -> datetime:
    """
    Parses ISO timestamp safely, dropping timezone offsets for standard bucket calculations.
    """
    try:
        # Handle Z suffix
        if ts.endswith("Z"):
            ts = ts[:-1]
        # Split timezone offsets like +05:30
        if "+" in ts:
            ts = ts.split("+")[0]
        return datetime.fromisoformat(ts)
    except Exception:
        return datetime.now()

def extract_keywords(text: str) -> List[str]:
    """
    Tokenizes text, keeping hashtags (starting with #) and words while filtering out stopwords.
    """
    text_lower = text.lower()
    # Find hashtags or standard words (alphanumeric words, allowing # at the start)
    tokens = re.findall(r'#?\w+', text_lower)
    
    filtered_tokens = []
    for token in tokens:
        # Keep hashtags of any length, but filter out pure numbers and standard stopwords
        if token.startswith("#"):
            if len(token) > 1 and not token[1:].isdigit():
                filtered_tokens.append(token)
        else:
            if len(token) >= 3 and not token.isdigit() and token not in STOPWORDS:
                filtered_tokens.append(token)
                
    return filtered_tokens

def compute_trends(posts: List[Dict[str, Any]], threat_category: str = None, interval: str = "day") -> List[Dict[str, Any]]:
    """
    Groups posts into time-series buckets and computes analytics metrics.
    
    Args:
        posts: List of ingested post dictionaries.
        threat_category: Optional string (Neutral, Inflammatory, Incitement to Violence, Fake News) to filter by.
        interval: Time bucket width ("day", "hour", "minute").
        
    Returns:
        List of chronological datapoints with trends analytics.
    """
    # 1. Filter posts by threat category if provided
    filtered_posts = []
    for post in posts:
        post_cat = post.get("threat_category", "")
        # Case insensitive match
        if threat_category:
            if not post_cat or post_cat.lower() != threat_category.lower():
                continue
        filtered_posts.append(post)
        
    # 2. Bucket posts chronologically
    buckets = defaultdict(list)
    for post in filtered_posts:
        dt = parse_timestamp(post.get("timestamp", ""))
        
        # Build bucket keys based on interval
        if interval == "minute":
            key = dt.strftime("%Y-%m-%dT%H:%M:00")
        elif interval == "hour":
            key = dt.strftime("%Y-%m-%dT%H:00:00")
        else:  # day
            key = dt.strftime("%Y-%m-%d")
            
        buckets[key].append(post)
        
    # 3. Sort bucket keys chronologically
    sorted_keys = sorted(buckets.keys())
    
    trends_series = []
    
    # 4. Compute metrics per bucket
    for i, key in enumerate(sorted_keys):
        bucket_posts = buckets[key]
        post_count = len(bucket_posts)
        
        # Extract keywords & hashtags
        keywords_counter = Counter()
        for post in bucket_posts:
            keywords_counter.update(extract_keywords(post.get("text", "")))
        top_keywords = dict(keywords_counter.most_common(5))
        
        # Extract geo distributions
        geo_counter = Counter()
        for post in bucket_posts:
            geo_city = post.get("geo", {}).get("city")
            if geo_city:
                geo_counter[geo_city] += 1
        geo_distribution = dict(geo_counter)
        
        # Extract language distributions (additional useful metric)
        lang_counter = Counter()
        for post in bucket_posts:
            lang = post.get("language")
            if lang:
                lang_counter[lang] += 1
        lang_distribution = dict(lang_counter)
        
        # 5. Spike detection: Compare current volume against rolling average of previous 3 windows
        previous_counts = []
        for j in range(max(0, i - 3), i):
            prev_key = sorted_keys[j]
            previous_counts.append(len(buckets[prev_key]))
            
        baseline = sum(previous_counts) / len(previous_counts) if previous_counts else 0.0
        
        # Flag a spike if volume is at least 1.5x the rolling average and >= 5 posts
        is_spike = False
        if baseline > 0:
            is_spike = (post_count > (baseline * 1.5)) and (post_count >= 5)
            
        trends_series.append({
            "timestamp": key,
            "post_count": post_count,
            "top_keywords": top_keywords,
            "geo_distribution": geo_distribution,
            "lang_distribution": lang_distribution,
            "rolling_baseline": round(baseline, 2),
            "is_spike": is_spike
        })
        
    return trends_series
