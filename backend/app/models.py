from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AccountCredentialsInput(BaseModel):
    email: str
    password: str


class ShortPreview(BaseModel):
    video_id: str
    title: str
    url: str
    thumbnail_url: str | None = None


class ShortsListRequest(BaseModel):
    youtube_handle: str = Field(..., description="YouTube channel handle (e.g. @channelname)")
    limit: int = Field(default=10, ge=1, le=20)


class ShortsListResponse(BaseModel):
    handle: str
    shorts: list[ShortPreview]


class WorkflowRequest(BaseModel):
    youtube_handle: str = Field(..., description="YouTube channel handle (e.g. @channelname)")
    short_url: str = Field(..., description="Selected Short URL to view and like")
    account_mode: Literal["single", "multi"]
    email: str | None = Field(default=None, description="Single account email")
    password: str | None = Field(default=None, description="Single account password")
    accounts: list[AccountCredentialsInput] | None = Field(
        default=None,
        description="Multiple accounts for multi mode",
    )
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
