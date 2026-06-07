import threading
import uuid
from datetime import datetime, timezone

from app.models import AccountResult, JobState, JobStatus, ProgressEvent


class JobManager:
    def __init__(self):
        self._jobs: dict[str, JobState] = {}
        self._lock = threading.Lock()

    def create_job(self) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = JobState(job_id=job_id, status=JobStatus.PENDING)
        return job_id

    def get_job(self, job_id: str) -> JobState | None:
        with self._lock:
            return self._jobs.get(job_id)

    def set_status(self, job_id: str, status: JobStatus, error: str | None = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = status
            if error:
                job.error = error

    def add_progress(
        self,
        job_id: str,
        message: str,
        level: str = "info",
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.progress.append(
                ProgressEvent(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    message=message,
                    level=level,  # type: ignore[arg-type]
                )
            )

    def add_result(self, job_id: str, result: AccountResult) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.results.append(result)
