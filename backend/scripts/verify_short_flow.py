"""Verify latest-short discovery without login."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright

from app.browser_launcher import launch_chromium_browser
from app.youtube_automation import YouTubeAutomation

HANDLE = sys.argv[1] if len(sys.argv) > 1 else "@YouTube"


def main() -> None:
    automation = YouTubeAutomation(browser_channel="chrome")
    with sync_playwright() as playwright:
        browser = launch_chromium_browser(playwright, headless=True, channel_setting="chrome")
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        url, title = automation._open_latest_short(page, HANDLE)
        button = automation._find_short_like_button(page)
        label = button.get_attribute("aria-label") if button else None
        print("OPENED:", url)
        print("TITLE:", title)
        print("LIKE BUTTON:", label)
        browser.close()


if __name__ == "__main__":
    main()
