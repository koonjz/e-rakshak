# Social Threat Analyzer - Platform API Integration Guide

This document outlines the connectivity pathways, current integration status, and instructions to activate each social media source for live, real-time ingestion.

---

## 📽️ YouTube Ingestion

### Status: **ACTIVE & OPERATIONAL**
The platform supports real-time keyword harvesting and comment indexing.

### How to Activate:
1. **Get a YouTube Data API v3 Key**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Create a project and enable the **YouTube Data API v3**.
   - Generate an **API Key** under Credentials.
2. **Configure Environment**:
   - Save the key in the root `.env` file of the project:
     ```env
     YOUTUBE_API_KEY=AIzaSy...
     ```
3. **Execution**:
   - Select **LIVE YOUTUBE MODE** in the analyst console.
   - Enter your keywords (e.g. `Gujarat, protest`) and hit **START STREAM**.

---

## 📸 Instagram & 👥 Facebook (Meta Graph API)

### Status: **PENDING META APP REVIEW**
Both crawlers are fully implemented as review-ready scaffolds (`InstagramCrawler` and `FacebookCrawler` in `backend/crawler/social_stubs.py`), containing the correct Graph API query nodes and permission bindings. Active production traffic is blocked pending Meta App Review.

### Access Permissions Required:
- `instagram_basic`: Required to read basic media info from Instagram Creator/Business profiles.
- `pages_read_engagement`: Required to read linked Facebook Page feeds.
- `pages_public_content_access` (PPCA): **App Review Required**. Required to query public posts/hashtags not owned by the developer.

### Flow & Endpoints Scaled:
1. **Instagram Hashtag Feed Query**:
   - Resolve Tag ID: `GET https://graph.facebook.com/v20.0/ig_hashtag_search?user_id={app_id}&q={keyword}&access_token={token}`
   - Retrieve Media Node: `GET https://graph.facebook.com/v20.0/{hashtag_id}/recent_media?user_id={app_id}&fields=id,caption,timestamp,comments_count,like_count&access_token={token}`
2. **Facebook Public Page Harvesting**:
   - Query Page Feed: `GET https://graph.facebook.com/v20.0/{page_id}/feed?fields=id,message,created_time,likes.summary(true),comments.summary(true)&access_token={token}`

### How to Activate:
1. Complete Meta App Review on the [Meta App Dashboard](https://developers.facebook.com/).
2. Load credentials into `.env`:
   ```env
   META_APP_ID=your_app_id
   META_APP_SECRET=your_app_secret
   META_ACCESS_TOKEN=your_production_system_user_token
   ```

---

## 🐦 X (Formerly Twitter)

### Status: **BLOCKED (Paid API Restrictions)**
Ingestion of public posts/tweets is currently blocked by commercial API changes.

### Limitations (As of 2026):
- **Free Tier**: Write-only access (posting tweets). Read/search endpoints are disabled.
- **Basic/Pro Tier ($100 to $5000/mo)**: Highly constrained request quotas that make real-time keyword monitoring cost-prohibitive for demo sandboxes.
- **Integration Scaffold**: Stubs inside `TwitterCrawler` outline the V2 AsyncStreamingClient WebSocket protocol (`https://api.twitter.com/2/tweets/search/stream`), ready to connect if a Pro developer token is supplied.

---

## ✈️ Telegram Ingestion (MTProto API)

### Status: **ACTIVE (User Session Authentication Required)**
The backend connects directly to Telegram's decentralized MTProto networks using the **Telethon** library. It reads and monitors public news channels.

### Setup & Credentials Required:
Unlike web scrapers or bot APIs, MTProto requires a registered application configuration:
1. Go to [my.telegram.org](https://my.telegram.org) and log in with your phone number.
2. Select **API development tools** and create a new application.
3. Retrieve your `api_id` and `api_hash`.

### How to Activate:
1. Add parameters to your `.env` file:
   ```env
   TELEGRAM_API_ID=your_api_id_integer
   TELEGRAM_API_HASH=your_api_hash_string
   ```
2. Run the interactive terminal log-in script in your console:
   ```bash
   .\venv\Scripts\python login_telegram.py
   ```
   *Note: Telethon will prompt you to enter your phone number and the verification code sent to your Telegram app. This generates the secure `telegram_session.session` file, which is saved locally and ignored by Git.*
3. Start the crawler via the analyst dashboard in **LIVE TELEGRAM MODE**.

