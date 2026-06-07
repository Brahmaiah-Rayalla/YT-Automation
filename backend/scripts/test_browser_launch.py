import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright

from app.browser_launcher import launch_chromium_browser


def main() -> None:
    with sync_playwright() as playwright:
        browser = launch_chromium_browser(playwright, headless=True, channel_setting="auto")
        page = browser.new_page()
        page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
        print(f"sync-launch: OK (page title: {page.title()})")
        browser.close()


if __name__ == "__main__":
    main()
