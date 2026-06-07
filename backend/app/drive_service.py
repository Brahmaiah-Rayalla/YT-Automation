import io
import logging
from dataclasses import dataclass

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.config import Settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


@dataclass
class AccountCredentials:
    email: str
    password: str


def parse_credentials_file(content: str) -> list[AccountCredentials]:
    accounts: list[AccountCredentials] = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            logger.warning("Skipping invalid credentials line: %s", line)
            continue
        email, password = line.split("=", 1)
        email = email.strip()
        password = password.strip()
        if email and password:
            accounts.append(AccountCredentials(email=email, password=password))
    return accounts


class DriveService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service

        account_info = self.settings.get_service_account_info()
        if not account_info:
            raise ValueError(
                "GOOGLE_SERVICE_ACCOUNT_JSON is not configured. "
                "Set it when using Google Drive credentials."
            )

        credentials = service_account.Credentials.from_service_account_info(
            account_info, scopes=SCOPES
        )
        self._service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        return self._service

    def fetch_credentials(self) -> list[AccountCredentials]:
        file_id = self.settings.google_drive_file_id.strip()
        if not file_id:
            raise ValueError(
                "GOOGLE_DRIVE_FILE_ID is not configured. "
                "Set it when using Google Drive credentials."
            )

        service = self._get_service()
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        content = buffer.getvalue().decode("utf-8")
        accounts = parse_credentials_file(content)
        if not accounts:
            raise ValueError("No valid accounts found in the Google Drive credentials file.")
        return accounts
