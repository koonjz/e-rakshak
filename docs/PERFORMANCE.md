# System Ingestion & Query Performance

This document summarizes the real-world throughput, classification latency, and scalability measurements of the Social Threat Analyzer backend processing engine.

## 1. Classification & Ingestion Throughput

We evaluated the system under high load by injecting a sudden burst of **500 synthetic posts** through the full classifier and ingestion pipeline (Classification -> In-memory indexing).

*   **Total Processing Time**: `2.5753 seconds`
*   **Sustained Throughput Rate**: `194.15 posts/second`
*   **Average Classification Latency Per Post**: `5.15 ms`

---

## 2. API Endpoint Scalability (Data Volume vs. Query Latency)

We separately evaluated the latency of the analytical query functions (representing `GET /api/trends`, `GET /api/coordination`, and `GET /api/incidents`) under database volumes of **500**, **1000**, and **2000** posts.

| In-Memory DB Volume | Trends Query Latency | Bot Coordination Query Latency | Incidents Query Latency |
| :--- | :--- | :--- | :--- |
| **500 posts** | `9.04 ms` | `192.50 ms` | `184.78 ms` |
| **1000 posts** | `14.60 ms` | `568.65 ms` | `550.66 ms` |
| **2000 posts** | `55.28 ms` | `1151.35 ms` | `1267.53 ms` |

---

## 3. Honest Volume Assessment & Performance Scaling

*   **Trends Query Performance**: Scales linearly with volume. Because trends calculation requires datetime binning, geo-aggregations, and keyword token counting, processing larger array sizes has a clear performance impact. However, even at 2000 posts, queries complete in under `55.3 ms`, representing sub-second near-real-time performance.
*   **Bot Coordination Detector**: The detector performs Jaccard similarity comparison across post text content (`O(N^2)` comparison complexity inside the temporal window). As a result, query latency increases quadratically with database volume if all posts are clustered, representing the largest scaling bottleneck.
*   **Memory Footprint**: The system utilizes an in-memory database (`state.posts_db`). Storing 2000 posts consumes negligible memory (~2–5 MB heap space delta). For database scale above 10,000+ posts, swapping the list-based state for an indexed document store (e.g. SQLite, PostgreSQL) is recommended.
