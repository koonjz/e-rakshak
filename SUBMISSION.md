# Project Submission Notes

This document provides a comprehensive summary of the Social Threat Analyzer implementation, platform coverage status, performance accuracy metrics, and inherent limitations.

---

## 1. Project Overview
The **Social Threat Analyzer** is a real-time, multilingual social media monitoring platform designed to ingest, analyze, and escalate potential public safety threats in Gujarat. It couples a high-performance **React + Vite (TypeScript)** frontend dashboard with a **FastAPI (Python)** backend that hosts modular social media crawlers, time-series trend analyzers, bot coordination campaign detection clusters, and a hybrid NLP/OCR text classifier.

---

## 2. Platform Ingestion Coverage Status

| Platform | Integration Pathway | Status | Details / Prerequisites |
| :--- | :--- | :--- | :--- |
| **📽️ YouTube** | REST API v3 Harvesting | **ACTIVE & OPERATIONAL** | Ingests live comment feeds based on query keywords. Requires a valid Google Cloud Developer `YOUTUBE_API_KEY` in `.env`. |
| **✈️ Telegram** | MTProto Client (Telethon) | **ACTIVE & OPERATIONAL** | Connects to decentralized networks to stream public channels. Requires `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` in `.env` and a one-time terminal authentication via `login_telegram.py`. |
| **📸 Instagram** | Meta Graph API | **PENDING APP REVIEW** | Implemented as a review-ready crawler scaffold (`InstagramCrawler`). Active production traffic is blocked pending Meta review for `instagram_basic` and public page read permissions. |
| **👥 Facebook** | Meta Graph API | **PENDING APP REVIEW** | Implemented as a review-ready crawler scaffold (`FacebookCrawler`). Feeds block pending Meta approval for public content access permissions. |
| **🐦 X (Twitter)** | V2 Streaming Client | **BLOCKED (Paid APIs)** | Protocol stubs (`TwitterCrawler`) are mapped and ready, but endpoints are commercialized. Read/search streaming requires a paid developer tier. |

---

## 3. Classifier & Coordination Performance Accuracy

*   **Multilingual Threat Classifier**:
    *   Trained on a balanced 500-post dataset ([sample_posts.json](file:///c:/Users/kunjp/OneDrive/Desktop/Experiments/social-threat-analyzer/data/sample_posts.json)) covering 5 languages (English, Hindi, Gujarati, Hinglish, Gujlish) and 4 threat categories.
    *   Integrates direct regex lookup override rules which yield **90% confidence matches** for verified threat phrases.
*   **Bot Coordination Detector**:
    *   Monitors Jaccard word set similarity, post synchronicity, and follower count ratios.
    *   Automated E2E integration test ([test_coordination.py](file:///c:/Users/kunjp/OneDrive/Desktop/Experiments/social-threat-analyzer/backend/test_coordination.py)) verified **100% Recall** (2 custom seeded botnets/campaigns were correctly identified, clustered, and served via `/api/coordination`).

---

## 4. Inherent Limitations

*   **OCR Image Parsing**: Indic-script OCR (Hindi/Gujarati) on visually complex or stylized memes with outline fonts and background noise is currently highly unreliable due to character segmentation failures, whereas Latin-script OCR is robust. To resolve this in production, a dedicated pre-processing layer (adaptive binarization and deep learning text-region cropping) is required.
*   **Classifier Vocabulary Bias**: The rule-based override layers (such as English direct threats and Gujarati roadblock keywords) function as targeted patches for specific failure cases, rather than systemic fixes to the underlying vocabulary training bias in the TF-IDF Naive Bayes model. Other untested phrases or vocabulary imbalances in the dataset will still exhibit high rates of category misclassification.
