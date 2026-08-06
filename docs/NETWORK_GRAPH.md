# Coordinated Campaign Network Graph (Neo4j Integration)

This document provides a technical overview of the Neo4j graph database integration, the schema design, Cypher synchronization queries, and setup instructions.

---

## 1. Graph Schema Design

The network is modeled as a property graph with two node labels and two relationship types:

### Nodes
1.  **`Account` Nodes**: Represents social media handles.
    *   Label: `:Account`
    *   Properties:
        *   `username` (String, Unique Key): The account username (e.g. `@bot_agent_01`).
        *   `platform` (String): The source platform (e.g. `X`, `Telegram`, `YouTube`, `Instagram`, `Facebook`).
2.  **`Post` Nodes**: Represents individual ingested posts.
    *   Label: `:Post`
    *   Properties:
        *   `id` (String, Unique Key): The post ID.
        *   `text_snippet` (String): Snippet of the post text.
        *   `threat_category` (String): Threat classification label.
        *   `timestamp` (String): ISO timestamp of publication.

### Relationships
1.  **`POSTED`**: Directed relationship from an `Account` to a `Post`.
    *   Schema: `(:Account)-[:POSTED]->(:Post)`
2.  **`COORDINATES_WITH`**: Unidirected/Undirected relationship directly between two `Account` nodes that are members of the same detected coordination cluster.
    *   Schema: `(:Account)-[:COORDINATES_WITH {heuristic, suspicion_score}]->(:Account)`
    *   Properties:
        *   `heuristic` (String): Delineated list of triggered heuristics (e.g. `templated_text, suspicious_profiles`).
        *   `suspicion_score` (Integer): Campaign suspicion rating (0–100).

---

## 2. Cypher Queries Used

All synchronization queries use `MERGE` constraints to ensure idempotency and prevent node duplication on repeated ingestion cycles.

### Syncing Accounts, Posts, and Ingested Feeds
For every ingested post, the following query merges the author account, the post itself, and links them:
```cypher
MERGE (a:Account {username: $username})
ON CREATE SET a.platform = $platform
MERGE (p:Post {id: $post_id})
ON CREATE SET p.text_snippet = $snippet, p.threat_category = $threat, p.timestamp = $timestamp
MERGE (a)-[:POSTED]->(p)
```

### Syncing Coordinated Bot Campaigns
For each pair of accounts in a detected coordination cluster, we sort the usernames alphabetically (`u1 < u2`) and merge a unique undirected relationship:
```cypher
MATCH (a1:Account {username: $u1})
MATCH (a2:Account {username: $u2})
MERGE (a1)-[r:COORDINATES_WITH]->(a2)
SET r.heuristic = $heuristic, r.suspicion_score = $suspicion_score
```

### Querying the Visualization Data
To build the network graph on the dashboard, we retrieve accounts with their post volumes and max suspicion ratings, along with coordination links:
```cypher
// Fetch Nodes
MATCH (a:Account)
OPTIONAL MATCH (a)-[:POSTED]->(p:Post)
WITH a, count(p) AS post_count
OPTIONAL MATCH (a)-[r:COORDINATES_WITH]-()
WITH a, post_count, max(r.suspicion_score) AS max_suspicion
RETURN a.username AS username, a.platform AS platform, post_count AS post_count, coalesce(max_suspicion, 0) AS suspicion

// Fetch Edges
MATCH (a:Account)-[r:COORDINATES_WITH]->(b:Account)
RETURN a.username AS source, b.username AS target, r.heuristic AS heuristic, r.suspicion_score AS suspicion_score
```

---

## 3. Setup Instructions (Neo4j AuraDB)

AuraDB provides a fully managed cloud instance of Neo4j.

1.  **Create an AuraDB Instance**:
    *   Go to [Neo4j Console](https://console.neo4j.io/) and register a free instance.
    *   Download the generated credentials text file containing your `NEO4J_URI`, `NEO4J_USERNAME`, and `NEO4J_PASSWORD`.
2.  **Configure Environment**:
    *   Save these parameters inside your root `.env` file (which is gitignored):
        ```env
        NEO4J_URI=neo4j+s://xxxxxx.databases.neo4j.io
        NEO4J_USERNAME=neo4j
        NEO4J_PASSWORD=your-secret-aura-password
        ```
3.  **Graceful Fallback Mode**:
    *   If credentials are left blank or the server is offline, the backend API logs a `graph_db_unavailable` status and bypasses graph sync. The dashboard displays a setup instruction console, preventing any application crashes.

> [!IMPORTANT]
> **Credential Masking Constraint**: The platform strictly verifies database connection status as a boolean flag (`neo4j_available`). The Neo4j password or full URI containing credentials must never be output to console logs or HTTP responses.
