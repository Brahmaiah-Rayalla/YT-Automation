import logging
import os
from pathlib import Path
from typing import Literal

from playwright.sync_api import Browser, Playwright

logger = logging.getLogger(__name__)

BrowserChannelSetting = Literal["auto", "chromium", "chrome", "msedge"]


def _playwright_browsers_dir() -> Path:
    custom = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if custom:
        return Path(custom)
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        return Path(local_app_data) / "ms-playwright"
    return Path.home() / ".cache" / "ms-playwright"


def _has_bundled_headless_shell() -> bool:
    browsers_dir = _playwright_browsers_dir()
    if not browsers_dir.exists():
        return False
    return any(
        (path / "chrome-win" / "headless_shell.exe").exists()
        for path in browsers_dir.glob("chromium_headless_shell-*")
    )


def _has_bundled_chromium() -> bool:
    browsers_dir = _playwright_browsers_dir()
    if not browsers_dir.exists():
        return False
    return any(
        (path / "chrome-win" / "chrome.exe").exists()
        for path in browsers_dir.glob("chromium-*")
        if not path.name.startswith("chromium_headless_shell")
    )


def _build_launch_attempts(
    channel_setting: BrowserChannelSetting,
    headless: bool,
) -> list[tuple[str | None, bool, str]]:
    if channel_setting == "chromium":
        return [(None, headless, "bundled-chromium")]

    if channel_setting in {"chrome", "msedge"}:
        return [(channel_setting, headless, f"system-{channel_setting}")]

    attempts: list[tuple[str | None, bool, str]] = []
    if headless and _has_bundled_headless_shell():
        attempts.append((None, True, "bundled-headless-shell"))
    if _has_bundled_chromium():
        attempts.append((None, False, "bundled-chromium-headed"))
    if headless:
        attempts.extend(
            [
                ("chrome", True, "system-chrome-headless"),
                ("msedge", True, "system-edge-headless"),
            ]
        )
    attempts.extend(
        [
            ("chrome", False, "system-chrome-headed"),
            ("msedge", False, "system-edge-headed"),
        ]
    )
    return attempts


def launch_chromium_browser(
    playwright: Playwright,
    *,
    headless: bool = True,
    channel_setting: BrowserChannelSetting = "auto",
) -> Browser:
    errors: list[str] = []
    attempts = _build_launch_attempts(channel_setting, headless)

    stealth_args = ["--disable-blink-features=AutomationControlled"]

    for channel, use_headless, label in attempts:
        launch_kwargs: dict = {
            "headless": use_headless,
            "args": stealth_args,
        }
        if channel:
            launch_kwargs["channel"] = channel
        else:
            launch_kwargs["ignore_default_args"] = ["--enable-automation"]
        try:
            browser = playwright.chromium.launch(**launch_kwargs)
            logger.info("Launched browser via %s", label)
            return browser
        except Exception as exc:
            message = f"{label}: {exc}"
            logger.warning("Browser launch failed (%s)", message)
            errors.append(message)

    raise RuntimeError(
        "No usable browser found. Install Playwright browsers with "
        "`python -m playwright install chromium` or ensure Google Chrome / "
        "Microsoft Edge is installed. Details: " + " | ".join(errors)
    )
