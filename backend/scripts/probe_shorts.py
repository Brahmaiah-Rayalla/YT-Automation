"""Probe YouTube channel Shorts page structure (no login)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright

from app.browser_launcher import launch_chromium_browser

HANDLE = sys.argv[1] if len(sys.argv) > 1 else "@YouTube"


def main() -> None:
    url = f"https://www.youtube.com/{HANDLE}/shorts"
    with sync_playwright() as playwright:
        browser = launch_chromium_browser(
            playwright,
            headless=True,
            channel_setting="chrome",
        )
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        data = page.evaluate(
            """() => {
                const results = [];
                const seen = new Set();
                const anchors = document.querySelectorAll('a[href*="/shorts/"]');
                for (const a of anchors) {
                    const href = a.href || a.getAttribute('href') || '';
                    const match = href.match(/\\/shorts\\/([A-Za-z0-9_-]+)/);
                    if (!match || seen.has(match[1])) continue;
                    seen.add(match[1]);
                    const rect = a.getBoundingClientRect();
                    const parent = a.closest(
                        'ytd-rich-item-renderer, ytd-grid-shorts, ytd-reel-item-renderer, ytd-rich-grid-renderer'
                    );
                    results.push({
                        id: match[1],
                        href,
                        title: a.getAttribute('title')
                            || a.getAttribute('aria-label')
                            || (a.innerText || '').trim().slice(0, 80),
                        idAttr: a.id,
                        parent: parent ? parent.tagName.toLowerCase() : null,
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        visible: rect.width > 0 && rect.height > 0,
                    });
                }
                return results;
            }"""
        )

        print("PAGE URL:", page.url)
        generic_first = page.locator('a[href*="/shorts/"]').first.get_attribute("href")
        scoped_first = page.locator('ytd-rich-item-renderer a[href*="/shorts/"]').first.get_attribute("href")
        print("GENERIC FIRST LINK:", generic_first)
        print("SCOPED FIRST LINK:", scoped_first)
        print("SHORTS FOUND:", len(data))
        for index, item in enumerate(data[:10]):
            print(index, json.dumps(item))

        if not data:
            browser.close()
            return

        video_id = data[0]["id"]
        page.goto(f"https://www.youtube.com/shorts/{video_id}", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        likes = page.evaluate(
            """() => {
                const buttons = [...document.querySelectorAll('button')];
                return buttons
                    .filter((button) => (button.getAttribute('aria-label') || '')
                        .toLowerCase()
                        .includes('like'))
                    .map((button) => ({
                        label: button.getAttribute('aria-label'),
                        pressed: button.getAttribute('aria-pressed'),
                        visible: button.offsetParent !== null,
                        parent: button.closest(
                            'like-button-view-model, ytd-like-button-renderer, ytd-toggle-button-renderer'
                        )?.tagName,
                    }));
            }"""
        )
        print("LIKE BUTTONS:", json.dumps(likes, indent=2))

        like_btn = page.locator('button[aria-label*="like" i]').first
        print("GENERIC LIKE SELECTOR LABEL:", like_btn.get_attribute("aria-label"))

        like_btn2 = page.locator("like-button-view-model button").first
        print("LIKE-BUTTON-VIEW-MODEL LABEL:", like_btn2.get_attribute("aria-label"))

        titles = page.evaluate(
            """() => [...document.querySelectorAll('h2, ytd-reel-player-header-renderer yt-formatted-string')]
                .map((el) => ({
                    tag: el.tagName,
                    className: el.className,
                    parent: el.parentElement?.tagName,
                    text: (el.textContent || '').trim().slice(0, 100),
                }))
                .filter((item) => item.text)"""
        )
        print("TITLE CANDIDATES:", json.dumps(titles, indent=2))

        browser.close()


if __name__ == "__main__":
    main()
