"""
Manual Playwright browser downloader with long timeouts and retries.
Use when `playwright install chromium` fails due to network timeouts.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

CDN_MIRRORS = [
    "https://playwright.azureedge.net",
    "https://playwright-akamai.azureedge.net",
    "https://playwright-verizon.azureedge.net",
]

# Playwright 1.49.1 browser revisions
ARTIFACTS = {
    "chromium-headless-shell": {
        "revision": "1148",
        "folder": "chromium_headless_shell-1148",
        "archive_name": "chromium-headless-shell-win64.zip",
        "executable": ("chrome-win", "headless_shell.exe"),
    },
    "chromium": {
        "revision": "1148",
        "folder": "chromium-1148",
        "archive_name": "chromium-win64.zip",
        "executable": ("chrome-win", "chrome.exe"),
    },
}


def browsers_dir() -> Path:
    custom = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if custom:
        return Path(custom)
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        return Path(local_app_data) / "ms-playwright"
    return Path.home() / ".cache" / "ms-playwright"


def is_installed(target_dir: Path, executable_parts: tuple[str, str]) -> bool:
    return (target_dir / executable_parts[0] / executable_parts[1]).exists()


def download_file(url: str, destination: Path, timeout_seconds: int) -> None:
    print(f"Downloading {url}")
    with urlopen(url, timeout=timeout_seconds) as response:
        total = int(response.headers.get("Content-Length", "0") or 0)
        downloaded = 0
        chunk_size = 1024 * 1024
        with destination.open("wb") as handle:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                if total:
                    percent = downloaded * 100 // total
                    print(f"  {percent}% ({downloaded // (1024 * 1024)} MiB)", end="\r")
    print()


def extract_zip(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "r") as archive:
        archive.extractall(destination)


def install_artifact(name: str, timeout_seconds: int, force: bool) -> bool:
    artifact = ARTIFACTS[name]
    root = browsers_dir()
    target_dir = root / artifact["folder"]

    if not force and is_installed(target_dir, artifact["executable"]):
        print(f"{name}: already installed at {target_dir}")
        return True

    if target_dir.exists():
        shutil.rmtree(target_dir)

    archive_name = artifact["archive_name"]
    revision = artifact["revision"]
    build_type = name if name != "chromium-headless-shell" else "chromium"
    relative_path = f"builds/{build_type}/{revision}/{archive_name}"

    last_error: Exception | None = None
    for mirror in CDN_MIRRORS:
        url = f"{mirror}/{relative_path}"
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = Path(temp_dir) / archive_name
                download_file(url, archive_path, timeout_seconds)
                extract_zip(archive_path, target_dir)
            if is_installed(target_dir, artifact["executable"]):
                print(f"{name}: installed to {target_dir}")
                return True
            raise RuntimeError(f"Download completed but executable missing in {target_dir}")
        except Exception as exc:
            last_error = exc
            print(f"{name}: failed from {mirror} ({exc})")

    print(f"{name}: all mirrors failed ({last_error})")
    return False


def remove_stale_lock() -> None:
    lock_path = browsers_dir() / "__dirlock"
    if lock_path.exists():
        shutil.rmtree(lock_path)
        print(f"Removed stale lock: {lock_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual Playwright browser downloader")
    parser.add_argument(
        "--artifact",
        choices=["chromium-headless-shell", "chromium", "all"],
        default="chromium-headless-shell",
    )
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    remove_stale_lock()
    browsers_dir().mkdir(parents=True, exist_ok=True)

    names = ["chromium-headless-shell", "chromium"] if args.artifact == "all" else [args.artifact]
    success = True
    for name in names:
        if not install_artifact(name, args.timeout_seconds, args.force):
            success = False

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
