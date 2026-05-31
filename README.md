# Web Page to Markdown API

Convert any web page to clean, readable Markdown with one HTTP request. Extracts article content using Mozilla's Readability algorithm, strips navigation, ads, and sidebars.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?templateUrl=https://github.com/INAPP-Mobile/webpage-to-markdown-api)

## Features

- **Readability extraction** — Leverages Mozilla's Readability algorithm for clean article extraction
- **Markdown output** — Clean, well-formatted Markdown via markdownify
- **URL validation** — Validates and normalises URLs automatically
- **Timeouts** — 10-second request timeout to prevent hanging
- **Size limits** — 1MB response size cap to prevent abuse
- **CORS enabled** — Ready for cross-origin requests from any frontend
- **Error handling** — Graceful error messages for invalid URLs, timeouts, oversized responses
- **Railpack auto-detect** — No Dockerfile needed

## API Reference

| Method | Endpoint | Description | Status Codes |
|--------|----------|-------------|-------------|
| `GET` | `/` | API info and version | 200 |
| `GET` | `/health` | Health check | 200 |
| `GET` | `/convert?url=<url>` | Convert web page to Markdown | 200 / 400 / 413 / 502 / 504 |

### `/convert` — Convert a URL to Markdown

**Request:**
```
GET /convert?url=https://example.com/article
```

**Success Response (200):**
```json
{
  "title": "Example Article Title",
  "markdown": "# Example Article Title\n\nThis is the article content...",
  "source_url": "https://example.com/article",
  "length": 1234
}
```

**Error Responses:**

| Status | Meaning |
|--------|---------|
| `400` | Invalid URL (missing scheme, no hostname, etc.) |
| `413` | Response exceeds 1MB size limit |
| `502` | Failed to fetch the URL (DNS error, non-200 status) |
| `504` | Request timed out (after 10 seconds) |
| `422` | Could not extract readable content |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload

# Test
curl "http://localhost:8000/convert?url=https://example.com"

# Run tests
pytest tests/ -v -m "not integration"
```

## Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?templateUrl=https://github.com/INAPP-Mobile/webpage-to-markdown-api)

Click the button above to deploy instantly on Railway — no configuration needed.

### Manual Deploy

1. Fork this repo to your GitHub account
2. Go to [Railway Dashboard](https://railway.app/new)
3. Select **"Deploy from GitHub repo"**
4. Choose your fork
5. Railway auto-detects Python via Railpack — no Dockerfile needed
6. Click **Deploy**

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| (none required) | All defaults work out of the box | — |

No additional configuration needed. Railway auto-detects Python and sets `$PORT` automatically.

## Template

Published on the Railway marketplace. Kickback monetization: 25% revenue share from every deployment.
