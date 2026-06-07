from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowRequest(BaseModel):
    youtube_handle: str = Field(..., description="YouTube channel handle (e.g. @channelname)")
    email: str | None = Field(default=None, description="Optional test account email")
    password: str | None = Field(default=None, description="Optional test account password")
    execution_mode: Literal["sequential", "parallel"] | None = None


class AccountResult(BaseModel):
    email: str
    video_title: str = ""
    video_url: str = ""
    liked: bool = False
    status: str = "pending"
    error: str | None = None


class ProgressEvent(BaseModel):
    timestamp: str
    message: str
    level: Literal["info", "success", "warning", "error"] = "info"


class JobState(BaseModel):
    job_id: str
    status: JobStatus
    progress: list[ProgressEvent] = []
    results: list[AccountResult] = []
    error: str | None = None


class WorkflowStartResponse(BaseModel):
    job_id: str
    message: str
