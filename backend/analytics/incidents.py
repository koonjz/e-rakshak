import time
from typing import List, Dict, Any

def get_all_incidents(posts_db: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Scans state.posts_db for Incitement to Violence and Coordinated Amplification (suspicion >= 75)
    to compile persistent incident records.
    """
    incidents = []
    
    # 1. Scan for posts classified as Incitement to Violence
    for post in posts_db:
        if post.get("threat_category") == "Incitement to Violence":
            post_id = post.get("id", "unknown")
            username = post.get("username", "unknown")
            platform = post.get("platform", "X")
            city = post.get("geo", {}).get("city", "Gujarat")
            timestamp = post.get("timestamp", "")
            text = post.get("text", "")
            
            # Generate suggested escalation template
            template = (
                f"CRITICAL MONITORING ALERT\n"
                f"=========================\n"
                f"Incident ID: INC-POST-{post_id}\n"
                f"Detection Time: {timestamp}\n"
                f"Severity: HIGH\n"
                f"Category: Incitement to Violence\n"
                f"Source User: {username} ({platform})\n"
                f"Location: {city}\n\n"
                f"Content:\n\"{text}\"\n\n"
                f"Duty Officer Action Required: Please forward this alert to local police dispatch in {city} for physical monitoring."
            )
            
            incidents.append({
                "incident_id": f"INC-POST-{post_id}",
                "summary": f"Violent Incitement by {username} on {platform}",
                "threat_category": "Incitement to Violence",
                "severity": "HIGH",
                "affected_geo": city,
                "timestamp": timestamp,
                "related_posts": [post],
                "suggested_escalation_template": template
            })
    
    # 2. Scan for coordination clusters with suspicion score >= 75
    try:
        from analytics.coordination import detect_coordinated_behavior
        clusters = detect_coordinated_behavior(posts_db)
        for cluster in clusters:
            if cluster.get("suspicion_score", 0) >= 75:
                cluster_id = cluster.get("cluster_id", "unknown")
                heuristics = cluster.get("heuristics", [])
                suspicion = cluster.get("suspicion_score", 0)
                matched_posts = cluster.get("matched_posts", [])
                
                # Extract affected locations
                cities = set()
                for p in matched_posts:
                    city = p.get("geo", {}).get("city")
                    if city:
                        cities.add(city)
                    else:
                        # Fallback match by ID
                        p_id = p.get("id")
                        db_post = next((x for x in posts_db if x.get("id") == p_id), None)
                        if db_post and db_post.get("geo", {}).get("city"):
                            cities.add(db_post["geo"]["city"])
                
                city_str = ", ".join(cities) if cities else "Gujarat region"
                member_accounts = cluster.get("member_accounts", [])
                first_text = matched_posts[0].get("text", "") if matched_posts else ""
                
                trigger_list = ", ".join(heuristics)
                accounts_str = ", ".join(member_accounts)
                
                template = (
                    f"CRITICAL MONITORING ALERT - COORDINATED BOTNET CAMPAIGN\n"
                    f"=======================================================\n"
                    f"Incident ID: INC-CLUST-{cluster_id}\n"
                    f"Severity: CRITICAL\n"
                    f"Category: Coordinated Amplification\n"
                    f"Suspicion Score: {suspicion}%\n"
                    f"Triggered Heuristics: {trigger_list}\n"
                    f"Location(s): {city_str}\n\n"
                    f"Bot Accounts involved:\n{accounts_str}\n\n"
                    f"Sample Message matched:\n\"{first_text}\"\n\n"
                    f"Duty Officer Action Required: Restrict bot accounts and report coordinate influence campaign to security operations center."
                )
                
                # We want to use a timestamp for the cluster, let's use the most recent post timestamp in cluster
                timestamps = [p.get("timestamp", "") for p in matched_posts if p.get("timestamp")]
                cluster_time = max(timestamps) if timestamps else time.strftime("%Y-%m-%dT%H:%M:%S")
                
                incidents.append({
                    "incident_id": f"INC-CLUST-{cluster_id}",
                    "summary": f"Botnet Campaign {cluster_id.upper()} ({suspicion}% suspicion)",
                    "threat_category": "Coordinated Amplification",
                    "severity": "CRITICAL",
                    "affected_geo": city_str,
                    "timestamp": cluster_time,
                    "related_posts": matched_posts,
                    "suggested_escalation_template": template
                })
    except Exception as e:
        # Fallback print, log failure
        print(f"Error extracting coordination incidents: {e}")
        
    # Sort incidents by timestamp descending
    incidents.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return incidents
