import asyncio
import logging
from typing import Callable

from app.config import Settings
from app.drive_service import AccountCredentials, DriveService
from app.job_manager import JobManager
from app.models import AccountResult, JobStatus
from app.youtube_automation import YouTubeAutomation

logger = logging.getLogger(__name__)


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


class WorkflowRunner:
    def __init__(self, settings: Settings, job_manager: JobManager):
        self.settings = settings
        self.job_manager = job_manager
        self.automation = YouTubeAutomation(
            headless=settings.headless,
            min_watch_seconds=settings.min_watch_seconds,
            browser_channel=settings.browser_channel,
        )

    def resolve_accounts(
        self,
        email: str | None,
        password: str | None,
    ) -> list[AccountCredentials]:
        if not _is_blank(email) and not _is_blank(password):
            return [AccountCredentials(email=email.strip(), password=password.strip())]

        if not _is_blank(email) or not _is_blank(password):
            raise ValueError("Both email and password must be provided together, or leave both empty.")

        drive = DriveService(self.settings)
        return drive.fetch_credentials()

    async def run_job(
        self,
        job_id: str,
        youtube_handle: str,
        email: str | None,
        password: str | None,
        execution_mode: str | None = None,
    ) -> None:
        mode = execution_mode or self.settings.execution_mode
        progress = lambda message, level="info": self.job_manager.add_progress(job_id, message, level)

        try:
            accounts = self.resolve_accounts(email, password)
        except Exception as exc:
            self.job_manager.set_status(job_id, JobStatus.FAILED, str(exc))
            progress(f"Failed to load accounts: {exc}", "error")
            return

        self.job_manager.set_status(job_id, JobStatus.RUNNING)
        progress(
            f"Starting workflow for {len(accounts)} account(s) on {youtube_handle} in {mode} mode.",
            "info",
        )

        if mode == "parallel":
            await self._run_parallel(job_id, youtube_handle, accounts, progress)
        else:
            await self._run_sequential(job_id, youtube_handle, accounts, progress)

        self.job_manager.set_status(job_id, JobStatus.COMPLETED)
        progress("Workflow completed.", "success")

    async def _run_sequential(
        self,
        job_id: str,
        youtube_handle: str,
        accounts: list[AccountCredentials],
        progress: Callable[[str, str], None],
    ) -> None:
        for account in accounts:
            await self._process_account(job_id, youtube_handle, account, progress)

    async def _run_parallel(
        self,
        job_id: str,
        youtube_handle: str,
        accounts: list[AccountCredentials],
        progress: Callable[[str, str], None],
    ) -> None:
        await asyncio.gather(
            *(
                self._process_account(job_id, youtube_handle, account, progress)
                for account in accounts
            )
        )

    async def _process_account(
        self,
        job_id: str,
        youtube_handle: str,
        account: AccountCredentials,
        progress: Callable[[str, str], None],
    ) -> None:
        progress(f"Logging in as {account.email} for {youtube_handle}...", "info")
        try:
            result = await self.automation.run_account(
                account.email,
                account.password,
                youtube_handle,
            )
            account_result = AccountResult(
                email=account.email,
                video_title=result.video_title,
                video_url=result.video_url,
                liked=result.liked,
                status=result.status,
                error=result.error,
            )
            self.job_manager.add_result(job_id, account_result)

            if result.error:
                progress(f"{account.email}: failed - {result.error}", "error")
            elif result.liked:
                progress(f"Liked: {result.video_title or 'video'} ({account.email})", "success")
            else:
                progress(
                    f"Completed without like: {result.video_title or 'video'} ({account.email})",
                    "warning",
                )
        except Exception as exc:
            logger.exception("Unexpected error for %s", account.email)
            self.job_manager.add_result(
                job_id,
                AccountResult(
                    email=account.email,
                    status="failed",
                    error=str(exc),
                ),
            )
            progress(f"{account.email}: unexpected error - {exc}", "error")
