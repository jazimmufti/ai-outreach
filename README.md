# Arclent — Creator Discovery & Outreach Platform ⚡

A real, production-ready AI-powered **Creator Discovery and Outreach platform**. Enter any YouTube video URL to automatically identify the creator, discover their public social accounts (Instagram, X/Twitter, LinkedIn, TikTok, etc.), extract and classify public business contact emails via **LangGraph** and **Mistral AI**, and connect directly via social profiles or send emails through your connected **Gmail account** using Google OAuth 2.0.

---

## 🌟 Key Features

- **Real YouTube Discovery**: Parses standard video URLs, shortlinks (`youtu.be`), shorts, and embed links. Uses official **YouTube Data API v3** with an automatic resilient fallback to oEmbed + public HTML parsing if no API key is supplied.
- **Social Media Intelligence**: Detects public profiles across Instagram, X/Twitter, LinkedIn, TikTok, Facebook, GitHub, Linktree, and personal websites with confidence ratings.
- **Multi-Stage Email Discovery & Evidence Classification**:
  - Deterministic regex extraction from video descriptions, channel metadata, and creator contact web pages (`/contact`, `/about`, `mailto:` links).
  - Handles obfuscated email patterns (`name [at] domain [dot] com`).
  - Strict evidence tagging: distinguishes `publicly_published` vs `inferred` emails.
  - Never hallucinates emails. If no public email exists, prompts for manual email entry with real-time RFC 5322 validation.
- **AI Orchestration with LangGraph & Mistral AI**:
  - Multi-node pipeline (`validate_url` → `fetch_metadata` → `identify_creator` → `discover_socials` → `discover_emails` → `classify_and_finalize`).
  - Mistral AI reasoning to evaluate email authenticity, eliminate false positives, and classify contact confidence.
  - Server-Sent Events (SSE) streaming real-time progress to the UI.
- **Direct Gmail OAuth 2.0 Integration**:
  - Authenticates sender using secure OAuth 2.0 with minimal required scopes (`gmail.send`, `userinfo.email`).
  - Sends real MIME emails via the Gmail API (`users.messages.send`).
  - Secure token management in `token.json` (no passwords stored or transmitted).
- **Official Recipient Verification**:
  - When an outreach email is sent, the recipient receives secure confirmation links.
  - Real-time status updates when the creator officially approves the collaboration inquiry.
- **Retro-Editorial / Neo-Brutalist UI**:
  - Built with pure HTML5, CSS3, and Vanilla JavaScript (No npm or Node.js required).
  - Warm cream background, crisp black borders, vibrant green badges, and amber action buttons.

---

## 📁 Project Structure

```
ai-outreach/
├── app/
│   ├── __init__.py
│   ├── config.py                     # Pydantic Settings & environment loader
│   ├── main.py                       # FastAPI entrypoint, CORS, static routes
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── research.py               # POST /api/research & SSE /api/research/stream
│   │   ├── outreach.py               # Step-by-step outreach, email dispatch & verification
│   │   ├── gmail.py                  # Gmail OAuth (connect, callback, status, disconnect)
│   │   └── email.py                  # POST /api/email/send
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py                # Pydantic data models & request/response schemas
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── youtube_service.py        # YouTube Data API v3 + oEmbed/HTML fallback scraper
│   │   ├── social_discovery.py       # Social media profile regex & normalization
│   │   ├── email_discovery.py        # Multi-page email extraction & obfuscation parser
│   │   ├── mistral_service.py        # Mistral AI reasoning & evidence classifier
│   │   └── gmail_service.py          # Google OAuth 2.0 & Gmail API client
│   │
│   └── workflows/
│       ├── __init__.py
│       └── creator_research_graph.py # LangGraph state machine & streaming pipeline
│
├── frontend/
│   ├── index.html                    # Single-page UI with multi-step workflow
│   ├── styles.css                    # Design system (neo-brutalist / cream theme)
│   └── app.js                        # Client state, SSE progress, OAuth & form handlers
│
├── .env.example                      # Environment variables template
├── .env                              # Local environment configuration
├── .gitignore                        # Git ignore rules
├── requirements.txt                  # Python dependencies
└── README.md                         # Documentation
```

---

## ⚙️ Environment Variables

Create or update your `.env` file in the project root:

| Variable | Required | Description |
| :--- | :---: | :--- |
| `MISTRAL_API_KEY` | Optional | Mistral AI API key for evidence reasoning. Get at [Mistral AI Console](https://console.mistral.ai/api-keys/). |
| `YOUTUBE_API_KEY` | Optional | YouTube Data API v3 key. If omitted, the system falls back to oEmbed + public scraper. |
| `GOOGLE_CLIENT_ID` | Required for Gmail | Google OAuth 2.0 Web Client ID for sending email. |
| `GOOGLE_CLIENT_SECRET` | Required for Gmail | Google OAuth 2.0 Web Client Secret. |
| `GOOGLE_REDIRECT_URI` | Required for Gmail | OAuth Redirect URI (`http://localhost:8000/api/gmail/callback`). |
| `SESSION_SECRET_KEY` | Optional | Random string for signing OAuth session state. |

---

## 🚀 Quick Start Guide

### 1. Install Dependencies

Ensure Python 3.10+ is installed, then run:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your keys:

```bash
copy .env.example .env
```

### 3. Start the FastAPI Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser and navigate to:
👉 **`http://localhost:8000`**

---

## 🛠️ Step-by-Step Google Cloud & Gmail Setup

To enable real email sending via Gmail API:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g. `Creator-Outreach-App`).
3. **Enable APIs**:
   - Navigate to **APIs & Services > Library**.
   - Search and enable **Gmail API**.
   - Search and enable **YouTube Data API v3** (optional, recommended).
4. **Configure OAuth Consent Screen**:
   - Go to **APIs & Services > OAuth consent screen**.
   - Select User Type: **External** and click **Create**.
   - Fill in App name (`Arclent`), User support email, and Developer contact email.
   - Under **Scopes**, click **Add or Remove Scopes** and add:
     - `https://www.googleapis.com/auth/gmail.send`
     - `https://www.googleapis.com/auth/userinfo.email`
     - `openid`
   - Under **Test Users**, add your personal/testing Gmail address (e.g. `youremail@gmail.com`).
5. **Create OAuth 2.0 Credentials**:
   - Go to **APIs & Services > Credentials > Create Credentials > OAuth client ID**.
   - Application type: **Web application**.
   - Name: `Arclent Web Client`.
   - **Authorized redirect URIs**: Add `http://localhost:8000/api/gmail/callback`.
   - Click **Create**.
6. Copy the **Client ID** and **Client Secret** into your `.env` file:
   ```env
   GOOGLE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_client_secret_here
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/gmail/callback
   ```

---

## 🧠 Architecture Deep Dive

### 1. YouTube Discovery Engine
Extracts canonical video IDs from any YouTube format. If `YOUTUBE_API_KEY` is present, it uses `googleapiclient.discovery` to query `videos.list` and `channels.list`. If absent or rate-limited, it queries `https://www.youtube.com/oembed` and extracts JSON-LD metadata and initial data payloads to parse channel handles, subscriber counts, and avatars.

### 2. Social Discovery Service
Deterministic pattern matching identifies links to Instagram, X/Twitter, LinkedIn, TikTok, Facebook, GitHub, and personal domains. Handles are sanitized, removing system endpoints (`/share`, `/intent`, etc.), and assigned confidence levels.

### 3. Email Discovery & Evidence Classification
Executes contextual regex scanning across the video description, channel about text, and creator's official website contact pages (`/contact`, `/about`). Distinguishes between explicitly published contact addresses (`source_type: publicly_published`, `confidence: high`) and heuristic patterns. Sponsor and platform emails are filtered out.

### 4. LangGraph Workflow
Orchestrates the entire intelligence graph:
```
START
  ↓
[validate_url]
  ↓
[fetch_metadata]
  ↓
[identify_creator]
  ↓
[discover_socials]
  ↓
[discover_emails]
  ↓
[classify_and_finalize] (Mistral AI reasoning)
  ↓
END
```

The pipeline exposes both a synchronous JSON execution endpoint (`POST /api/research`) and an asynchronous Server-Sent Events generator (`GET /api/research/stream?youtube_url=...`) powering the live animated stepper in the UI.

---

## 🔒 Security & Privacy

- Client secrets and refresh tokens are stored exclusively on the backend (`token.json`).
- No passwords are ever collected or stored.
- Email sending requires active OAuth authorization and user confirmation before dispatching.
