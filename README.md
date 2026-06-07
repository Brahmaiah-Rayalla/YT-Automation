# YouTube Engagement Automation

Full-stack web app that automates YouTube engagement (watch + like) across multiple accounts using Playwright, FastAPI, and a React dashboard.

## Features

- **Browser automation** — logs into YouTube, opens the latest feed video/Short, watches for a configurable duration, and likes it
- **Credential sources** — use test email/password from the dashboard, or load accounts from a Google Drive `.properties` file
- **Live progress** — real-time status feed per account while the workflow runs
- **Results table** — account email, video title, URL, like status, and errors
- **Sequential or parallel** execution (configurable)
- **Deployable** — Netlify (frontend) + Render/Railway/Docker (backend)

## Project Structure

```
Playwrite_ScriptAutomation/
├── backend/                 # FastAPI + Playwright API
│   ├── app/
│   ├── Dockerfile
│   ├── render.yaml
│   └── requirements.txt
├── frontend/                # React + Vite dashboard
│   ├── src/
│   └── netlify.toml
├── config/
│   └── settings.example.properties
└── README.md
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud project with Drive API enabled (for Drive-based credentials)
- A server with Chromium support for Playwright (Docker image included)

## Local Development

### 1. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
.\scripts\install_playwright_browsers.ps1

copy .env.example .env
# Edit .env with your settings
```

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

Health check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env
# VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

### 3. Run a test workflow from the UI

1. Enter a **test email** and **password** on the dashboard
2. Click **Run Workflow**
3. Watch the live progress feed and results table

If email/password are left empty, the backend loads accounts from Google Drive (requires env vars below).

## Google Drive Credentials Setup

### 1. Create a service account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable **Google Drive API**
4. Create a **Service Account** and download the JSON key

### 2. Upload credentials file to Drive

Create a file like `accounts.properties`:

```properties
user1@gmail.com=password1
user2@gmail.com=password2
```

Share the file with the service account email (`...@...iam.gserviceaccount.com`) as **Viewer**.

Copy the file ID from the URL:
`https://drive.google.com/file/d/<FILE_ID>/view`

### 3. Set backend environment variables

```env
GOOGLE_DRIVE_FILE_ID=your_file_id
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
```

`GOOGLE_SERVICE_ACCOUNT_JSON` can be the full JSON string or a path to the key file on the server.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | API port | `8000` |
| `CORS_ORIGINS` | Comma-separated frontend URLs | `http://localhost:5173` |
| `MIN_WATCH_SECONDS` | Minimum watch time before liking | `30` |
| `EXECUTION_MODE` | `sequential` or `parallel` | `sequential` |
| `HEADLESS` | Run browser headless | `true` |
| `BROWSER_CHANNEL` | `auto`, `chromium`, `chrome`, or `msedge` | `auto` |
| `GOOGLE_DRIVE_FILE_ID` | Drive file ID for credentials | — |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Service account JSON or file path | — |

### Frontend (`frontend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API URL | `""` (uses Vite proxy in dev) |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/workflow/run` | Start workflow |
| `GET` | `/api/workflow/status/{job_id}` | Poll progress and results |

### Start workflow request

```json
{
  "email": "test@gmail.com",
  "password": "optional-if-using-drive",
  "execution_mode": "sequential"
}
```

Leave `email` and `password` empty/null to load accounts from Google Drive.

## Deployment

### Backend — Render (Docker)

1. Push this repo to GitHub
2. Create a **Web Service** on Render using `backend/Dockerfile`
3. Set environment variables from `backend/.env.example`
4. Deploy and copy the service URL

`backend/render.yaml` is included for Blueprint-based deploys.

### Backend — Railway

1. Create a new project from GitHub
2. Set root directory to `backend`
3. Use the included `Dockerfile`
4. Add the same environment variables

### Frontend — Netlify

1. Connect the GitHub repo to Netlify
2. Base directory: `frontend`
3. Build command: `npm run build`
4. Publish directory: `frontend/dist`
5. Environment variable: `VITE_API_BASE_URL=https://your-backend-url`

`netlify.toml` is already configured.

### Connect frontend to backend

Set `VITE_API_BASE_URL` to your deployed backend URL and add that URL to backend `CORS_ORIGINS`.

## Important Notes

- **Google 2FA / CAPTCHA** — accounts with extra verification may fail automation; use app passwords where possible
- **YouTube ToS** — automated engagement may violate YouTube Terms of Service; use responsibly and only on accounts you own
- **Never commit secrets** — credentials stay in Google Drive or environment variables only
- **Parallel mode** — runs multiple browser instances; ensure your server has enough memory

## Troubleshooting

| Issue | Fix |
|-------|-----|
| API offline in dashboard | Check backend is running and `VITE_API_BASE_URL` / CORS is correct |
| Login fails | Verify credentials; check for 2FA/CAPTCHA |
| Drive credentials not loading | Confirm file ID, service account JSON, and file sharing |
| Like button not found | YouTube UI may have changed; check `youtube_automation.py` selectors |
| Playwright browser download times out | Run `.\scripts\install_playwright_browsers.ps1` or `python scripts/manual_download_playwright.py` |
| Playwright browser missing locally | Set `BROWSER_CHANNEL=chrome` to use installed Google Chrome |

## License

MIT — use at your own risk.
