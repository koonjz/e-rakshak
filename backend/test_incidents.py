import urllib.request
import json
import time

def test_incidents_api():
    print("=== Testing incidents compilation logic ===")
    
    # Wait for backend to be fully initialized
    time.sleep(1)
    
    try:
        url = "http://127.0.0.1:8000/api/incidents"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode())
            print(f"Retrieved {len(data)} incidents from API.")
            
            # Print details of the first 2 incidents
            for idx, inc in enumerate(data[:2]):
                print(f"\nIncident #{idx+1}:")
                print(f"  Incident ID:  {inc.get('incident_id')}")
                print(f"  Summary:      {inc.get('summary')}")
                print(f"  Category:     {inc.get('threat_category')}")
                print(f"  Severity:     {inc.get('severity')}")
                print(f"  Affected Geo: {inc.get('affected_geo')}")
                print(f"  Timestamp:    {inc.get('timestamp')}")
                print(f"  Related Posts Count: {len(inc.get('related_posts', []))}")
                print(f"  Escalation Template Preview: {inc.get('suggested_escalation_template')[:80]}...")
            
            # Assertions
            assert len(data) > 0, "No incidents generated from startup database."
            assert any(i.get("threat_category") == "Incitement to Violence" for i in data), "Missing Incitement incidents."
            assert any(i.get("threat_category") == "Coordinated Amplification" for i in data), "Missing bot campaign incidents."
            
            print("\nIncident API test PASSED successfully.")
            
    except Exception as e:
        print(f"API Incident Test FAILED: {e}")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    test_incidents_api()
