import asyncio
import logging
import sys
from contextlib import asynccontextmanager

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.job_manager import JobManager
from app.models import JobState, WorkflowRequest, WorkflowStartResponse
from app.workflow import WorkflowRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
job_manager = JobManager()
workflow_runner = WorkflowRunner(settings, job_manager)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("YouTube automation API started")
    yield
    logger.info("YouTube automation API stopped")


app = FastAPI(
    title="YouTube Engagement Automation API",
    version="1.0.0",
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


@app.post("/api/workflow/run", response_model=WorkflowStartResponse)
async def start_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks):
    youtube_handle = request.youtube_handle.strip()
    if not youtube_handle:
        raise HTTPException(status_code=400, detail="YouTube handle is required.")

    job_id = job_manager.create_job()

    async def run_workflow():
        await workflow_runner.run_job(
            job_id=job_id,
            youtube_handle=youtube_handle,
            email=request.email,
            password=request.password,
            execution_mode=request.execution_mode,
        )

    background_tasks.add_task(run_workflow)
    source = "frontend credentials" if request.email and request.password else "Google Drive file"
    return WorkflowStartResponse(
        job_id=job_id,
        message=f"Workflow started for {youtube_handle} using {source}.",
    )


@app.get("/api/workflow/status/{job_id}", response_model=JobState)
async def get_workflow_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
