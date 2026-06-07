import asyncio
import logging
from typing import Callable

from app.config import Settings
from app.drive_service import AccountCredentials
from app.job_manager import JobManager
from app.models import AccountCredentialsInput, AccountResult, JobStatus
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
        account_mode: str,
        email: str | None,
        password: str | None,
        accounts: list[AccountCredentialsInput] | None,
    ) -> list[AccountCredentials]:
        if account_mode == "single":
            if _is_blank(email) or _is_blank(password):
                raise ValueError("Email and password are required for single account mode.")
            return [AccountCredentials(email=email.strip(), password=password.strip())]

        if account_mode == "multi":
            if not accounts:
                raise ValueError("At least one account is required for multi account mode.")
            resolved: list[AccountCredentials] = []
            for index, account in enumerate(accounts, start=1):
                if _is_blank(account.email) or _is_blank(account.password):
                    raise ValueError(f"Account #{index} is missing email or password.")
                resolved.append(
                    AccountCredentials(
                        email=account.email.strip(),
                        password=account.password.strip(),
                    )
                )
            return resolved

        raise ValueError(f"Unsupported account mode: {account_mode}")

    async def run_job(
        self,
        job_id: str,
        youtube_handle: str,
        short_url: str,
        account_mode: str,
        email: str | None,
        password: str | None,
        accounts: list[AccountCredentialsInput] | None,
        execution_mode: str | None = None,
    ) -> None:
        mode = execution_mode or self.settings.execution_mode
        progress = lambda message, level="info": self.job_manager.add_progress(job_id, message, level)

        try:
            resolved_accounts = self.resolve_accounts(account_mode, email, password, accounts)
        except Exception as exc:
            self.job_manager.set_status(job_id, JobStatus.FAILED, str(exc))
            progress(f"Failed to load accounts: {exc}", "error")
            return

        self.job_manager.set_status(job_id, JobStatus.RUNNING)
        progress(
            f"Starting workflow for {len(resolved_accounts)} account(s) on {youtube_handle} "
            f"({short_url}) in {mode} mode.",
            "info",
        )

        if mode == "parallel":
            await self._run_parallel(job_id, short_url, resolved_accounts, progress)
        else:
            await self._run_sequential(job_id, short_url, resolved_accounts, progress)

        self.job_manager.set_status(job_id, JobStatus.COMPLETED)
        progress("Workflow completed.", "success")

    async def _run_sequential(
        self,
        job_id: str,
        short_url: str,
        accounts: list[AccountCredentials],
        progress: Callable[[str, str], None],
    ) -> None:
        if len(accounts) == 1:
            await self._process_account(job_id, short_url, accounts[0], progress)
            return

        for account in accounts:
            progress(f"Logging in as {account.email}...", "info")

        account_pairs = [(account.email, account.password) for account in accounts]
        results = await self.automation.run_accounts_sequential(account_pairs, short_url)
        for email, result in results:
            self._record_account_result(job_id, email, result, progress)

    async def _run_parallel(
        self,
        job_id: str,
        short_url: str,
        accounts: list[AccountCredentials],
        progress: Callable[[str, str], None],
    ) -> None:
        await asyncio.gather(
            *(self._process_account(job_id, short_url, account, progress) for account in accounts)
        )

    def _record_account_result(
        self,
        job_id: str,
        email: str,
        result,
        progress: Callable[[str, str], None],
    ) -> None:
        account_result = AccountResult(
            email=email,
            video_title=result.video_title,
            video_url=result.video_url,
            liked=result.liked,
            status=result.status,
            error=result.error,
        )
        self.job_manager.add_result(job_id, account_result)

        if result.error:
            progress(f"{email}: failed - {result.error}", "error")
        elif result.liked:
            progress(f"Liked: {result.video_title or 'Short'} ({email})", "success")
        else:
            progress(
                f"Completed without like: {result.video_title or 'Short'} ({email})",
                "warning",
            )

    async def _process_account(
        self,
        job_id: str,
        short_url: str,
        account: AccountCredentials,
        progress: Callable[[str, str], None],
    ) -> None:
        progress(f"Logging in as {account.email}...", "info")
        try:
            result = await self.automation.run_account(
                account.email,
                account.password,
                short_url,
            )
            self._record_account_result(job_id, account.email, result, progress)
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
