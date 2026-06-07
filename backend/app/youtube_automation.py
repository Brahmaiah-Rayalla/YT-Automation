import asyncio
import logging
import re
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

from playwright.sync_api import Page, sync_playwright

from app.browser_launcher import BrowserChannelSetting, launch_chromium_browser

logger = logging.getLogger(__name__)


@dataclass
class VideoEngagementResult:
    video_title: str
    video_url: str
    liked: bool
    status: str
    error: str | None = None


class YouTubeAutomation:
    _NAVIGATION_DESTROYED = "Execution context was destroyed"

    def __init__(
        self,
        headless: bool = True,
        min_watch_seconds: int = 30,
        browser_channel: BrowserChannelSetting = "auto",
    ):
        self.headless = headless
        self.min_watch_seconds = min_watch_seconds
        self.browser_channel = browser_channel

    def _wait_page_settled(self, page: Page, timeout_ms: int = 5000) -> None:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        except Exception:
            pass
        page.wait_for_timeout(300)

    def _safe_count(self, locator) -> int:
        try:
            return locator.count()
        except Exception as exc:
            if self._NAVIGATION_DESTROYED in str(exc):
                return 0
            raise

    def _has_matches(self, locator) -> bool:
        return self._safe_count(locator) > 0

    async def run_account(
        self,
        email: str,
        password: str,
        youtube_handle: str,
    ) -> VideoEngagementResult:
        # Sync Playwright in a worker thread avoids Windows asyncio subprocess errors
        # when running inside FastAPI/uvicorn background tasks.
        return await asyncio.to_thread(
            self._run_account_sync,
            email,
            password,
            youtube_handle,
        )

    def _normalize_youtube_handle(self, handle: str) -> tuple[str, str]:
        raw = handle.strip()
        if not raw:
            raise ValueError("YouTube handle is required")

        if "youtube.com" in raw:
            parsed = urlparse(raw if raw.startswith("http") else f"https://{raw}")
            path = parsed.path.strip("/")
            if path.startswith("@"):
                display_handle = f"@{path.split('/')[0].lstrip('@')}"
                return f"https://www.youtube.com/{display_handle}/shorts", display_handle
            if path.startswith("channel/"):
                channel_id = path.split("/")[1]
                return f"https://www.youtube.com/channel/{channel_id}/shorts", channel_id
            if path.startswith("c/"):
                channel_slug = path.split("/")[1]
                return f"https://www.youtube.com/c/{channel_slug}/shorts", channel_slug

        display_handle = raw if raw.startswith("@") else f"@{raw}"
        return f"https://www.youtube.com/{display_handle}/shorts", display_handle

    def _run_account_sync(
        self,
        email: str,
        password: str,
        youtube_handle: str,
    ) -> VideoEngagementResult:
        with sync_playwright() as playwright:
            browser = launch_chromium_browser(
                playwright,
                headless=self.headless,
                channel_setting=self.browser_channel,
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                locale="en-US",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            try:
                self._login(page, email, password)
                video_url, video_title = self._open_latest_short(page, youtube_handle)
                self._watch_video(page)
                liked = self._like_video(page)
                return VideoEngagementResult(
                    video_title=video_title,
                    video_url=video_url,
                    liked=liked,
                    status="success" if liked else "completed_without_like",
                )
            except Exception as exc:
                logger.exception("Automation failed for %s", email)
                return VideoEngagementResult(
                    video_title="",
                    video_url=page.url if page else "",
                    liked=False,
                    status="failed",
                    error=str(exc),
                )
            finally:
                context.close()
                browser.close()

    def _wait_for_email_input(self, page: Page):
        candidates = [
            page.locator('input[type="email"]').first,
            page.locator('input[name="identifier"]').first,
            page.get_by_label(re.compile(r"email|phone", re.I)),
        ]
        errors: list[str] = []
        for candidate in candidates:
            try:
                candidate.wait_for(state="visible", timeout=15000)
                return candidate
            except Exception as exc:
                errors.append(str(exc))
        raise RuntimeError(f"Email input not found on Google sign-in page. {' | '.join(errors)}")

    _SKIP_BUTTON_PATTERNS = [
        re.compile(r"not now", re.I),
        re.compile(r"skip", re.I),
        re.compile(r"maybe later", re.I),
        re.compile(r"no thanks", re.I),
        re.compile(r"continue without", re.I),
        re.compile(r"do this later", re.I),
        re.compile(r"remind me later", re.I),
        re.compile(r"cancel", re.I),
    ]

    def _try_click_skip_action(self, page: Page) -> bool:
        self._wait_page_settled(page)
        for pattern in self._SKIP_BUTTON_PATTERNS:
            for role in ("button", "link"):
                locator = page.get_by_role(role, name=pattern)
                if not self._has_matches(locator):
                    continue
                try:
                    locator.first.click(timeout=5000)
                    return True
                except Exception:
                    continue

        text_options = (
            "Not now",
            "Skip",
            "No thanks",
            "Maybe later",
            "Continue without passkey",
            "Do this later",
        )
        for text in text_options:
            locator = page.locator(
                f'button:has-text("{text}"), '
                f'div[role="button"]:has-text("{text}"), '
                f'a:has-text("{text}")'
            ).first
            if not self._has_matches(locator):
                continue
            try:
                if locator.is_visible():
                    locator.click(timeout=5000)
                    return True
            except Exception:
                continue
        return False

    def _follow_continue_url(self, page: Page) -> bool:
        query = parse_qs(urlparse(page.url).query)
        continue_values = query.get("continue", [])
        if not continue_values:
            return False

        target_url = unquote(continue_values[0])
        if not target_url.startswith("http"):
            return False

        logger.info("Following Google continue URL: %s", target_url)
        page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        return True

    def _finish_google_login(self, page: Page) -> None:
        deadline = time.time() + 90
        last_url = ""

        while time.time() < deadline:
            self._wait_page_settled(page)
            current_url = page.url

            if "youtube.com" in current_url and "accounts.google.com" not in current_url:
                return

            if current_url != last_url:
                logger.info("Google sign-in step: %s", current_url)
                last_url = current_url

            if "passkeyenrollment" in current_url or "passkey" in current_url.lower():
                if self._try_click_skip_action(page):
                    page.wait_for_timeout(2000)
                    continue
                if self._follow_continue_url(page):
                    page.wait_for_timeout(2000)
                    continue
                raise RuntimeError(
                    "Google showed passkey enrollment and no skip button was found. "
                    "Sign in once manually with HEADLESS=false, or dismiss passkey setup in Chrome."
                )

            if self._has_matches(page.locator("text=Stay signed in")):
                for pattern in (re.compile(r"^yes$", re.I), re.compile(r"continue", re.I)):
                    yes_button = page.get_by_role("button", name=pattern)
                    if self._has_matches(yes_button):
                        yes_button.first.click(timeout=5000)
                        page.wait_for_timeout(2000)
                        break

            if self._has_matches(page.locator("text=Verify")):
                raise RuntimeError(
                    "Google requested additional verification (2FA/CAPTCHA). "
                    "Complete verification manually or use an app password."
                )

            if self._has_matches(page.locator("text=Wrong password")):
                raise RuntimeError("Incorrect password.")

            if self._try_click_skip_action(page):
                page.wait_for_timeout(2000)
                continue

            page.wait_for_timeout(1500)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass

        if "accounts.google.com" in page.url:
            raise RuntimeError(f"Login did not complete. Current URL: {page.url}")

    def _click_next(self, page: Page) -> None:
        next_button = page.locator("#identifierNext, #passwordNext").first
        if self._has_matches(next_button):
            next_button.click(timeout=15000)
            self._wait_page_settled(page, timeout_ms=30000)
            return
        page.get_by_role("button", name=re.compile(r"^next$", re.I)).first.click(timeout=15000)
        self._wait_page_settled(page, timeout_ms=30000)

    def _wait_for_password_input(self, page: Page):
        selectors = [
            'input[name="Passwd"]',
            'input[type="password"]:not([aria-hidden="true"]):not([name="hiddenPassword"])',
        ]
        last_error: Exception | None = None
        for selector in selectors:
            locator = page.locator(selector).first
            try:
                locator.wait_for(state="visible", timeout=60000)
                return locator
            except Exception as exc:
                last_error = exc

        try:
            label_locator = page.get_by_label(re.compile(r"enter your password", re.I))
            label_locator.wait_for(state="visible", timeout=15000)
            return label_locator
        except Exception as exc:
            last_error = exc

        raise RuntimeError(
            "Password field did not become visible. Google may be blocking automated login "
            f"or showing an extra verification step. Last error: {last_error}"
        )

    def _login(self, page: Page, email: str, password: str) -> None:
        page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)

        sign_in = page.locator(
            'a[aria-label="Sign in"], tp-yt-paper-button:has-text("Sign in"), '
            'button:has-text("Sign in"), ytd-button-renderer a:has-text("Sign in")'
        ).first
        if not self._has_matches(sign_in):
            avatar = page.locator("#avatar-btn, button#avatar-btn")
            if self._has_matches(avatar):
                return
            raise RuntimeError("Sign in button not found on YouTube homepage")

        sign_in.click(timeout=15000)
        page.wait_for_url(re.compile(r"accounts\.google\.com"), timeout=30000)
        self._wait_page_settled(page, timeout_ms=30000)

        email_input = self._wait_for_email_input(page)
        email_input.fill(email)
        self._click_next(page)

        page.wait_for_load_state("domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)

        if self._has_matches(page.locator("text=Couldn't find your Google Account")):
            raise RuntimeError("Google account not found for the provided email.")

        password_input = self._wait_for_password_input(page)
        password_input.fill(password)
        self._click_next(page)
        page.wait_for_timeout(2000)
        self._finish_google_login(page)

    _CHANNEL_SHORT_SELECTOR = 'ytd-rich-item-renderer a[href*="/shorts/"]'

    def _get_latest_short_from_channel(self, page: Page) -> tuple[str, str]:
        short_data = page.evaluate(
            """() => {
                const anchors = document.querySelectorAll(
                    'ytd-rich-item-renderer a[href*="/shorts/"]'
                );
                for (const anchor of anchors) {
                    const href = anchor.href || anchor.getAttribute('href') || '';
                    const match = href.match(/\\/shorts\\/([A-Za-z0-9_-]{5,})/);
                    if (!match) continue;
                    const videoId = match[1];
                    const videoUrl = href.startsWith('http')
                        ? href.split('?')[0]
                        : `https://www.youtube.com/shorts/${videoId}`;
                    return { videoId, videoUrl };
                }
                return null;
            }"""
        )
        if not short_data:
            return "", ""
        return short_data["videoId"], short_data["videoUrl"]

    def _extract_shorts_title(self, page: Page) -> str:
        title = page.evaluate(
            """() => {
                const selectors = [
                    'yt-shorts-video-title-view-model h2',
                    'h2.ytShortsVideoTitleViewModelShortsVideoTitle',
                    'ytd-reel-player-header-renderer h2 yt-formatted-string',
                    'ytd-reel-player-header-renderer #title',
                ];
                for (const selector of selectors) {
                    const element = document.querySelector(selector);
                    const text = element?.textContent?.trim();
                    if (text) return text;
                }
                return '';
            }"""
        )
        return title or ""

    def _open_latest_short(self, page: Page, youtube_handle: str) -> tuple[str, str]:
        shorts_url, display_handle = self._normalize_youtube_handle(youtube_handle)

        logger.info("Opening latest Short for %s at %s", display_handle, shorts_url)
        page.goto(shorts_url, wait_until="domcontentloaded", timeout=60000)
        self._wait_page_settled(page, timeout_ms=10000)

        video_id = ""
        video_url = ""
        for attempt in range(4):
            try:
                page.wait_for_selector(self._CHANNEL_SHORT_SELECTOR, state="attached", timeout=10000)
            except Exception:
                page.mouse.wheel(0, 1400)
                self._wait_page_settled(page, timeout_ms=5000)
                continue

            video_id, video_url = self._get_latest_short_from_channel(page)
            if video_id:
                break

            page.mouse.wheel(0, 1400)
            self._wait_page_settled(page, timeout_ms=5000)

        if not video_id:
            raise RuntimeError(f"No Shorts found for channel {display_handle}")

        target_url = f"https://www.youtube.com/shorts/{video_id}"
        logger.info("Latest Short for %s: %s", display_handle, target_url)
        page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_url(re.compile(rf"/shorts/{re.escape(video_id)}"), timeout=30000)
        self._wait_for_shorts_player(page)

        title = self._extract_shorts_title(page) or "Unknown Short"
        return page.url or video_url or target_url, title.strip()

    def _wait_for_shorts_player(self, page: Page) -> None:
        self._wait_page_settled(page, timeout_ms=10000)
        try:
            page.wait_for_selector("video", state="visible", timeout=15000)
        except Exception:
            pass
        try:
            page.wait_for_selector(
                "like-button-view-model button, ytd-shorts h2",
                state="attached",
                timeout=15000,
            )
        except Exception:
            pass
        page.wait_for_timeout(1500)

    def _watch_video(self, page: Page) -> None:
        self._wait_page_settled(page, timeout_ms=10000)
        player = page.locator("video").first
        if self._has_matches(player):
            try:
                player.click(timeout=5000)
            except Exception:
                pass

        # Shorts auto-play; give the player time to register a real view.
        time.sleep(self.min_watch_seconds)

    def _is_liked(self, button) -> bool:
        aria_pressed = button.get_attribute("aria-pressed")
        if aria_pressed == "true":
            return True
        aria_label = (button.get_attribute("aria-label") or "").strip().lower()
        return aria_label.startswith("unlike")

    def _find_short_like_button(self, page: Page):
        candidates = [
            page.locator("like-button-view-model button").first,
            page.locator("ytd-reel-video-renderer like-button-view-model button").first,
            page.get_by_role("button", name=re.compile(r"^like this video", re.I)).first,
        ]
        for candidate in candidates:
            if not self._has_matches(candidate):
                continue
            aria_label = (candidate.get_attribute("aria-label") or "").lower()
            if aria_label.startswith("dislike"):
                continue
            return candidate
        return None

    def _click_like_button(self, page: Page, button) -> bool:
        if self._is_liked(button):
            logger.info("Short already liked")
            return True

        try:
            button.scroll_into_view_if_needed(timeout=5000)
        except Exception:
            pass

        try:
            button.click(timeout=5000)
        except Exception:
            try:
                button.evaluate("element => element.click()")
            except Exception:
                return False

        for _ in range(4):
            page.wait_for_timeout(750)
            if self._is_liked(button):
                logger.info("Short liked successfully")
                return True

        return self._is_liked(button)

    def _like_video(self, page: Page) -> bool:
        if "/shorts/" not in page.url:
            raise RuntimeError(f"Expected a Shorts page before liking, got: {page.url}")

        self._wait_for_shorts_player(page)

        try:
            page.locator("video").first.click(timeout=3000)
        except Exception:
            pass

        button = self._find_short_like_button(page)
        if button and self._click_like_button(page, button):
            return True

        try:
            page.locator("video").first.click(timeout=3000)
            page.keyboard.press("l")
            page.wait_for_timeout(1500)
            button = self._find_short_like_button(page)
            if button and self._is_liked(button):
                logger.info("Short liked via keyboard shortcut")
                return True
        except Exception:
            pass

        raise RuntimeError("Like button not found or not clickable on Shorts player")
