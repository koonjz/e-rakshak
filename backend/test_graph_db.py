import os
import sys

# Ensure parent directory and backend are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Force UTF-8 console encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from analytics.graph_db import Neo4jGraphManager

def test_graph_fallback():
    print("=== Testing Neo4j Fallback Graceful Failure ===")
    
    # Temporarily remove env variables to force fallback
    old_uri = os.environ.get("NEO4J_URI")
    old_user = os.environ.get("NEO4J_USERNAME")
    old_pass = os.environ.get("NEO4J_PASSWORD")
    
    try:
        os.environ["NEO4J_URI"] = ""
        os.environ["NEO4J_USERNAME"] = ""
        os.environ["NEO4J_PASSWORD"] = ""
        
        fallback_manager = Neo4jGraphManager()
        
        # Verify availability is boolean False
        assert isinstance(fallback_manager.available, bool)
        assert fallback_manager.available is False
        assert fallback_manager.error_message == "Credentials missing"
        
        # Test synchronizer and fetcher returns safely on fallback mode
        sync_result = fallback_manager.sync_posts_and_coordination([], [])
        assert sync_result is False
        
        fetch_result = fallback_manager.get_network_graph()
        assert fetch_result["status"] == "graph_db_unavailable"
        assert fetch_result["nodes"] == []
        assert fetch_result["edges"] == []
        
        print("Neo4j fallback graceful handling verified successfully.")
        
    finally:
        # Restore environment
        if old_uri is not None:
            os.environ["NEO4J_URI"] = old_uri
        if old_user is not None:
            os.environ["NEO4J_USERNAME"] = old_user
        if old_pass is not None:
            os.environ["NEO4J_PASSWORD"] = old_pass

if __name__ == "__main__":
    test_graph_fallback()
