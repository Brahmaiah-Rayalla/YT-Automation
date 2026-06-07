import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.job_manager import JobManager
from app.models import (
    JobState,
    ShortPreview,
    ShortsListRequest,
    ShortsListResponse,
    WorkflowRequest,
    WorkflowStartResponse,
)
from app.workflow import WorkflowRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
job_manager = JobManager()
workflow_runner = WorkflowRunner(settings, job_manager)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("YouTube automation API started")
    if settings.serve_frontend and STATIC_DIR.exists():
        logger.info("Serving frontend from %s", STATIC_DIR)
    yield
    logger.info("YouTube automation API stopped")


app = FastAPI(
    title="YouTube Engagement Automation API",
    version="1.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/shorts/list", response_model=ShortsListResponse)
async def list_channel_shorts(request: ShortsListRequest):
    youtube_handle = request.youtube_handle.strip()
    if not youtube_handle:
        raise HTTPException(status_code=400, detail="YouTube handle is required.")

    try:
        handle, shorts = await workflow_runner.automation.list_channel_shorts(
            youtube_handle,
            limit=request.limit,
        )
    except Exception as exc:
        logger.exception("Failed to list Shorts for %s", youtube_handle)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ShortsListResponse(
        handle=handle,
        shorts=[
            ShortPreview(
                video_id=item.video_id,
                title=item.title,
                url=item.url,
                thumbnail_url=item.thumbnail_url,
            )
            for item in shorts
        ],
    )


@app.post("/api/workflow/run", response_model=WorkflowStartResponse)
async def start_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks):
    youtube_handle = request.youtube_handle.strip()
    short_url = request.short_url.strip()

    if not youtube_handle:
        raise HTTPException(status_code=400, detail="YouTube handle is required.")
    if not short_url:
        raise HTTPException(status_code=400, detail="A Short must be selected before running the workflow.")

    job_id = job_manager.create_job()

    async def run_workflow():
        await workflow_runner.run_job(
            job_id=job_id,
            youtube_handle=youtube_handle,
            short_url=short_url,
            account_mode=request.account_mode,
            email=request.email,
            password=request.password,
            accounts=request.accounts,
            execution_mode=request.execution_mode,
        )

    background_tasks.add_task(run_workflow)
    account_label = (
        "1 account"
        if request.account_mode == "single"
        else f"{len(request.accounts or [])} accounts"
    )
    return WorkflowStartResponse(
        job_id=job_id,
        message=f"Workflow started for {youtube_handle} with {account_label}.",
    )


@app.get("/api/workflow/status/{job_id}", response_model=JobState)
async def get_workflow_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


if settings.serve_frontend and STATIC_DIR.exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        candidate = STATIC_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)

        return FileResponse(STATIC_DIR / "index.html")
