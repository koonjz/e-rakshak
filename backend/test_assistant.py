import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Import state from main.py to fetch pre-populated mock database
from main import state
from crawler.mock import MockCrawler
from assistant.query_router import answer_question

# Force prepopulate using 30 day lookback so we have sample data loaded
state.crawler = MockCrawler(lookback_days=30)
state.posts_db = []
state.prepopulate_db()

def test_questions():
    questions = [
        "how many incidents in Rajkot",
        "summarize the coordination clusters",
        "what's the current threat trend",
        "overall system status",
        "lookup cluster CLUSTER_01",
        "who won the world cup"  # Outside scope test
    ]
    
    print("====================================================")
    print("STARTING DATA-AWARE AI ASSISTANT SYSTEM TEST SUITE")
    print("====================================================\n")
    
    # Hide full API key in logs
    api_key = os.getenv("GEMINI_API_KEY", "")
    key_exists = bool(api_key and api_key != "your_gemini_api_key_here")
    key_len = len(api_key) if api_key else 0
    print(f"GEMINI_API_KEY configured: {key_exists} (Length: {key_len})")
    print("-" * 50 + "\n")
    
    for q in questions:
        print(f"User Question: '{q}'")
        res = answer_question(q, state.posts_db)
        print(f"Matched Intent: {res.get('matched_intent')}")
        print(f"Data Retrieved (Truncated): {str(res.get('data_used'))[:250]}")
        print(f"Gemini Answer Status: {res.get('status')}")
        print(f"Answer Output:\n{res.get('answer')}")
        print("-" * 50 + "\n")

if __name__ == "__main__":
    test_questions()
