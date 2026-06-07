# Deployment Guide

## Single application (recommended)

The backend can serve the built React dashboard and API from **one URL**.

### Local single-app run

```powershell
cd backend
.\scripts\build_app.ps1
.\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

### Docker

```bash
docker build -t youtube-automation .
docker run -p 8000:8000 -e MIN_WATCH_SECONDS=15 youtube-automation
```

## Cloud deployment

### Render (recommended)

This app needs a **long-running server with Playwright/Chromium**. Render works well:

1. Push this repo to GitHub
2. Create a **Web Service** on [Render](https://render.com)
3. Connect the repo and use the included `render.yaml` or Dockerfile
4. Set environment variables from `backend/.env.example`
5. Deploy

### Netlify (not supported for full app)

**Netlify cannot run this project as a single app** because:

- Netlify hosts static sites and short-lived serverless functions
- Playwright browser automation needs a persistent server (30s+ per workflow)
- Python FastAPI + Chromium will exceed Netlify function limits

If you use Netlify, you could only host the **frontend static files** there, but the backend must still run elsewhere (Render, Railway, Fly.io, VPS).

For a unified experience, deploy the Docker image to Render instead.

## Environment variables

| Variable | Description |
|----------|-------------|
| `PORT` | Server port (Render sets this automatically) |
| `SERVE_FRONTEND` | `true` to serve dashboard from `/` |
| `MIN_WATCH_SECONDS` | Watch duration before like (default `15`) |
| `HEADLESS` | `true` for cloud |
| `BROWSER_CHANNEL` | Use `chromium` in Docker/cloud |
| `CORS_ORIGINS` | `*` when frontend is served by same host |

## Development vs production

| Mode | Frontend | Backend |
|------|----------|---------|
| Dev | `npm run dev` on :5173 | `uvicorn` on :8000 |
| Single app | Built into `backend/static` | Serves UI + API on :8000 |

Leave `VITE_API_BASE_URL` empty when building for single-app deployment so API calls use the same origin.
