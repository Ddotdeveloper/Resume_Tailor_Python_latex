# Deploy Resume Tailor — Free Tier

## Option A: All on Render (recommended)

Single Web Service serves both the API and the demo page at the same URL.

### 1. Push to GitHub

```bash
git add -A && git commit -m "add deployment files"
git push
```

### 2. Deploy on Render

1. Go to [render.com](https://render.com) → Sign up with GitHub
2. **New Web Service** → connect your repo
3. Settings:
   - **Name**: `resume-tailor`
   - **Runtime**: Docker
   - **Branch**: `main`
   - **Health Check Path**: `/health`
   - **Plan**: Free
4. Add environment variables:
   | Key | Value |
   |---|---|
   | `GROQ_API_KEY` | your key from [console.groq.com](https://console.groq.com) |
   | `ALLOWED_ORIGINS` | `*` |
   | `PORT` | `10000` |
5. **Create Web Service** — first deploy takes ~3 min
6. Copy the URL (e.g. `https://resume-tailor.onrender.com`)

### 3. Verify

Open the Render URL in a browser → you'll see the demo page. Health check and generate API are at the same URL:

```bash
# Health check
curl https://resume-tailor.onrender.com/health

# Test generate
curl -X POST https://resume-tailor.onrender.com/generate \
  -H "Content-Type: application/json" \
  -d '{"company_name":"TestCo","job_description":"Looking for a Python engineer"}'
```

### 4. Share with recruiters

Send them the Render URL — the demo page loads automatically at the root path.

**Note:** Free tier sleeps after 15 min idle. First request after sleep takes ~30s.

---

## Option B: Local demo (no hosting)

```bash
cd resume_tailor_project/python_backend
export PORT=5001
source venv/bin/activate
python server.py
```

Then open `http://localhost:5001` in your browser — the demo page is served by Flask.

---

## Chrome Extension

### Point extension at your deployed backend

The extension hardcodes `http://127.0.0.1:5001` in `resume_tailor_project/browser_extension/popup.js`:
- Line 56: health check URL
- Line 148: generate POST URL

Change both to your Render URL (e.g. `https://resume-tailor.onrender.com`).

### Load extension in Chrome (free)

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** → select `resume_tailor_project/browser_extension/`

### Usage flow

1. Go to a job posting page and **highlight** the job description text
2. Click the extension icon (top-right toolbar)
3. Enter company name → click **Generate**
4. Extension downloads the tailored PDF and/or `.tex` file

### Auth token (optional)

If you set `AUTH_TOKEN` on the server, users click the gear icon in the extension, paste the token, and save.

### Publish to Chrome Web Store ($5 one-time)

To avoid the "Load unpacked" step, publish properly:
1. Zip `resume_tailor_project/browser_extension/`
2. Go to [chrome.google.com/webstore/devconsole](https://chrome.google.com/webstore/devconsole)
3. Pay the $5 registration fee (one-time) → upload the zip
4. After review (~1 day), users can install from the store like any extension

| File | Purpose |
|---|---|
| `Dockerfile` | Render container with Python + tectonic |
| `demo/index.html` | Demo page for recruiters to try live |
| `AGENTS.md` | Dev instructions for this repo |

## Troubleshooting

- **LaTeX/PDF fails on Render**: the server still returns `.tex` content. PDF is optional — demo gracefully shows download buttons for what's available.
- **Cold start is slow**: Render free tier unloads idle containers. Tell recruiters "first load takes ~30s."
- **CORS errors**: ensure `ALLOWED_ORIGINS=*` in Render env vars.
- **Rate limited**: default 10 req/min. Set `RATE_LIMIT` env to increase.
