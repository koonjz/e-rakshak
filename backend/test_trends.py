import sys
import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analytics.trends import compute_trends, extract_keywords

def test_trends_computation_isolation():
    print("=== Testing compute_trends in Isolation ===")
    
    # 1. Test keyword extraction
    sample_text = "Breaking: Fire in #Ahmedabad! Go to the municipal park #Safety"
    keywords = extract_keywords(sample_text)
    print(f"Text: '{sample_text}'")
    print(f"Extracted Keywords: {keywords}")
    # Expected: ['breaking', 'fire', '#ahmedabad', 'municipal', 'park', '#safety'] (filtered stopwords like 'in', 'go', 'to', 'the')
    assert "#ahmedabad" in keywords
    assert "#safety" in keywords
    assert "to" not in keywords
    print("Keyword extraction PASSED.")
    
    # 2. Test grouping & spike detection
    base_time = datetime.now()
    mock_posts = []
    
    # Generate mock posts over 4 days
    # Days 1-3 have normal volume (2 posts per day)
    # Day 4 has a spike (10 posts)
    for day_offset in range(3):
        post_time = base_time - timedelta(days=(3 - day_offset))
        for j in range(2):
            mock_posts.append({
                "text": "Normal day #Happy",
                "timestamp": post_time.isoformat(),
                "threat_category": "Neutral",
                "geo": {"city": "Ahmedabad"}
            })
            
    # Day 4 (Spike day)
    spike_time = base_time
    for j in range(10):
        mock_posts.append({
            "text": "ALERT: Severe situation in #Ahmedabad! #Panic",
            "timestamp": spike_time.isoformat(),
            "threat_category": "Incitement to Violence",
            "geo": {"city": "Ahmedabad"}
        })
        
    trends = compute_trends(mock_posts, interval="day")
    print(f"Trends Series Length: {len(trends)}")
    
    for pt in trends:
        print(f"Time: {pt['timestamp']} | Count: {pt['post_count']} | Spike: {pt['is_spike']} | Top Keywords: {pt['top_keywords']}")
        
    # Check that day 4 has flagged spike
    assert trends[-1]["is_spike"] is True
    # Check that day 1-3 does not flag spike
    assert trends[0]["is_spike"] is False
    
    # Test threat filtering
    filtered_trends = compute_trends(mock_posts, threat_category="Incitement to Violence", interval="day")
    print(f"Threat Filtered Series Length: {len(filtered_trends)}")
    assert len(filtered_trends) == 1  # Only day 4 has this category
    assert filtered_trends[0]["post_count"] == 10
    
    print("Trends computation isolation PASSED.\n")

def call_api(path: str) -> dict:
    import urllib.parse
    if "?" in path:
        base_path, query = path.split("?", 1)
        params = urllib.parse.parse_qsl(query)
        quoted_query = urllib.parse.urlencode(params)
        path = f"{base_path}?{quoted_query}"
        
    url = f"http://127.0.0.1:8000{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code} on {url}: {e.reason}")
        return {}
    except Exception as e:
        print(f"Connection Error on {url}: {e}")
        return {}

def test_api_trends_integration():
    print("=== Testing FastAPI Trends Endpoint Integration ===")
    
    # Query GET /api/trends without filters
    trends = call_api("/api/trends")
    if not trends:
        print("FAIL: Cannot contact trends API. Is uvicorn running?")
        sys.exit(1)
        
    print(f"Retrieved {len(trends)} time series datapoints from API.")
    print("First datapoint:")
    print(json.dumps(trends[0], indent=2))
    
    # Query with category filters
    filtered_trends = call_api("/api/trends?threat_category=Incitement to Violence")
    print(f"Retrieved {len(filtered_trends)} datapoints for Incitement to Violence.")
    if filtered_trends:
        print("Sample filtered datapoint:")
        print(json.dumps(filtered_trends[0], indent=2))
        
    print("API Integration test PASSED.\n")

if __name__ == "__main__":
    # Ensure UTF-8 console output
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
        
    test_trends_computation_isolation()
    test_api_trends_integration()
