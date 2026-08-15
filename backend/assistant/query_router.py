import os
import re
import sys
from typing import Dict, Any, Optional
import google.generativeai as genai

# Setup target 't' to sys.path to import torch/transformers if needed
t_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "t"))
if t_dir not in sys.path:
    sys.path.insert(0, t_dir)

CANDIDATE_CITIES = ["rajkot", "surat", "ahmedabad", "vadodara", "gandhinagar"]
CANDIDATE_CATEGORIES = ["incitement to violence", "inflammatory", "neutral"]

def match_intent(question: str) -> Optional[Dict[str, Any]]:
    q = question.lower()
    
    # 1. System Status
    if any(k in q for k in ["system status", "status of the system", "overall status", "is the system online"]):
        return {"intent": "system_status"}
        
    # 2. Specific Cluster Lookup
    cluster_match = re.search(r"\bcluster_(\d+)\b", q)
    if cluster_match:
        return {"intent": "specific_cluster", "cluster_id": f"CLUSTER_{cluster_match.group(1)}"}
    m = re.search(r"\bcluster[-_]?[0-9a-zA-Z]+\b", q)
    if m:
        norm = m.group(0).upper().replace("-", "_")
        if "CLUSTER_" in norm:
            return {"intent": "specific_cluster", "cluster_id": norm}
        else:
            digits = re.search(r"\d+", norm)
            if digits:
                return {"intent": "specific_cluster", "cluster_id": f"CLUSTER_{digits.group(0)}"}
                
    # 3. Coordination Summary
    if any(k in q for k in ["coordination cluster", "coordination summary", "coordination clusters", "bot cluster", "bot-like", "coordinated behavior", "summarize coordination", "summarize the coordination"]):
        return {"intent": "coordination_summary"}
        
    # 4. Trends Summary
    if any(k in q for k in ["trend", "trends", "threat trend", "threat trends", "summarize trends"]):
        return {"intent": "trends_summary"}
        
    # 5. Incident Count / List
    if any(k in q for k in ["incident", "incidents", "how many incidents", "incident count", "list of incidents"]):
        city = None
        for c in CANDIDATE_CITIES:
            if c in q:
                city = c.capitalize()
                break
        category = None
        for cat in CANDIDATE_CATEGORIES:
            if cat in q:
                category = cat.capitalize()
                if category == "Incitement to violence":
                    category = "Incitement to Violence"
                break
        return {
            "intent": "incident_count",
            "city": city,
            "category": category
        }
        
    return None

def answer_question(question: str, posts_db: list) -> Dict[str, Any]:
    intent_info = match_intent(question)
    if not intent_info:
        return {
            "answer": "I'm sorry, but that question is outside the scope of my supported query types. I can help you with incident counts by city/category, coordinated clusters, threat trends, or system status.",
            "matched_intent": "outside_scope",
            "data_used": {}
        }
        
    intent = intent_info["intent"]
    data = {}
    
    # Retrieve real data based on intent
    try:
        if intent == "system_status":
            from analytics.graph_db import graph_manager
            from ml.image_analyzer import TESSERACT_AVAILABLE
            data = {
                "posts_count": len(posts_db),
                "neo4j_available": graph_manager.available,
                "tesseract_available": TESSERACT_AVAILABLE,
                "threat_classifier_initialized": True,
                "system_mode": "operational"
            }
        elif intent == "specific_cluster":
            from analytics.coordination import detect_coordinated_behavior
            cluster_id = intent_info.get("cluster_id")
            clusters = detect_coordinated_behavior(posts_db)
            matched_cluster = next((c for c in clusters if c["cluster_id"].upper() == cluster_id.upper()), None)
            if matched_cluster:
                data = {
                    "cluster_id": matched_cluster["cluster_id"],
                    "member_accounts": matched_cluster["member_accounts"],
                    "heuristics": matched_cluster["heuristics"],
                    "suspicion_score": matched_cluster["suspicion_score"],
                    "posts_count": len(matched_cluster.get("matched_posts", []))
                }
            else:
                data = {"error": f"Coordinated cluster {cluster_id} not found."}
        elif intent == "coordination_summary":
            from analytics.coordination import detect_coordinated_behavior
            clusters = detect_coordinated_behavior(posts_db)
            data = {
                "total_clusters": len(clusters),
                "clusters": [
                    {
                        "cluster_id": c["cluster_id"],
                        "members": len(c["member_accounts"]),
                        "suspicion_score": c["suspicion_score"],
                        "heuristics": c["heuristics"]
                    }
                    for c in clusters
                ]
            }
        elif intent == "trends_summary":
            from analytics.trends import compute_trends
            from collections import Counter
            trends_series = compute_trends(posts_db)
            all_keywords = Counter()
            for t in trends_series:
                all_keywords.update(t.get("top_keywords", {}))
            data = {
                "total_posts_analyzed": sum(t.get("post_count", 0) for t in trends_series),
                "trends_series_length": len(trends_series),
                "top_overall_keywords": dict(all_keywords.most_common(5)),
                "trends_series_summary": [
                    {
                        "timestamp": t.get("timestamp"),
                        "post_count": t.get("post_count", 0),
                        "is_spike": t.get("is_spike", False)
                    }
                    for t in trends_series
                ]
            }
        elif intent == "incident_count":
            from analytics.incidents import get_all_incidents
            incidents = get_all_incidents(posts_db)
            
            city_filter = intent_info.get("city")
            category_filter = intent_info.get("category")
            
            filtered = incidents
            if city_filter:
                filtered = [inc for inc in filtered if inc.get("city") == city_filter]
            if category_filter:
                filtered = [inc for inc in filtered if inc.get("threat_category") == category_filter]
                
            data = {
                "total_incidents_found": len(filtered),
                "city_filter": city_filter,
                "category_filter": category_filter,
                "incidents": [
                    {
                        "id": inc["id"],
                        "city": inc.get("city"),
                        "threat_category": inc.get("threat_category"),
                        "severity_score": inc.get("severity_score"),
                        "description": inc.get("description")
                    }
                    for inc in filtered
                ]
            }
    except Exception as e:
        data = {"error": f"Failed to retrieve data for intent {intent}: {str(e)}"}

    # Gemini Integration
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_api_key_here":
        return {
            "answer": f"Gemini API Key is not configured in .env. Here is the raw data backing your query: {data}",
            "matched_intent": intent,
            "data_used": data,
            "status": "api_key_missing"
        }
        
    try:
        genai.configure(api_key=api_key)
        system_instruction = (
            "You are a helpful data assistant for the Social Threat Analyzer application.\n"
            "Your task is to phrase a natural-language answer to the user's question using ONLY the provided real data.\n"
            "Strict Rules:\n"
            "1. Rely ONLY on the clear facts directly mentioned in the provided data.\n"
            "2. DO NOT make assumptions, extrapolate, or bring in any external knowledge.\n"
            "3. If the data does not contain the answer or is empty, state that directly.\n"
            "4. Keep the answer concise and direct."
        )
        
        gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        model = genai.GenerativeModel(gemini_model_name, system_instruction=system_instruction)
        
        prompt = f"User Question: {question}\n\nReal System Data:\n{data}"
        
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.0}
        )
        
        answer = response.text.strip()
        return {
            "answer": answer,
            "matched_intent": intent,
            "data_used": data,
            "status": "success"
        }
    except Exception as e:
        return {
            "answer": f"Failed to contact Gemini API due to an error: {str(e)}. Here is the raw data backing your query: {data}",
            "matched_intent": intent,
            "data_used": data,
            "status": "api_call_failed"
        }
