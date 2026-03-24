"""Playwright-based browser automation for Option Alpha.

Handles bot creation, configuration, and status checks at $0 cost
and 10x speed compared to Computer Use.

Features:
- Session cookie management (login once, reuse)
- Centralized selector registry (ui_selectors.json)
- Automatic fallback to Tier 3 on selector failure
- Single verification screenshot after completion
"""

import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import Optional

from core.config import (
    OA_BASE_URL, OA_BOTS_URL, OA_LOGIN_URL,
    SESSION_COOKIES_PATH, SELECTOR_FILE,
)

log = logging.getLogger("options-claw.playwright")


class SelectorNotFound(Exception):
    """Raised when a Playwright selector can't find the target element."""
    pass


class PlaywrightRunner:
    """Base class for Playwright automation in Option Alpha."""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self._selectors: dict = {}
        self._load_selectors()

    def _load_selectors(self):
        """Load UI selectors from registry file."""
        if SELECTOR_FILE.exists():
            self._selectors = json.loads(SELECTOR_FILE.read_text())
            log.info(f"Loaded selectors for {len(self._selectors)} pages")
        else:
            log.warning(f"Selector file not found: {SELECTOR_FILE}")

    def get_selector(self, page: str, element: str) -> str:
        """Get a CSS selector for a page element."""
        page_selectors = self._selectors.get(page, {})
        selector = page_selectors.get(element)
        if not selector:
            raise SelectorNotFound(
                f"No selector for '{page}.{element}'. "
                f"Run selector_discovery.py to find it."
            )
        return selector

    async def launch(self, headless: bool = True):
        """Launch browser and restore session."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

        pw = await async_playwright().start()
        self.browser = await pw.chromium.launch(headless=headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
        )

        # Restore cookies if available
        if SESSION_COOKIES_PATH.exists():
            cookies = json.loads(SESSION_COOKIES_PATH.read_text())
            await self.context.add_cookies(cookies)
            log.info("Session cookies restored")

        self.page = await self.context.new_page()

    async def ensure_logged_in(self):
        """Navigate to OA and verify login state. Prompt if needed."""
        if not self.page:
            await self.launch(headless=False)

        await self.page.goto(OA_BOTS_URL)
        await self.page.wait_for_load_state("networkidle")

        if "login" in self.page.url.lower():
            log.info("Session expired. Please log in manually in the browser window...")
            await self.page.pause()  # Opens interactive inspector
            # After user logs in, save new cookies
            await self._save_cookies()
            log.info("New session cookies saved")

    async def _save_cookies(self):
        """Save browser cookies for future sessions."""
        cookies = await self.context.cookies()
        SESSION_COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
        SESSION_COOKIES_PATH.write_text(json.dumps(cookies, indent=2))

    async def navigate_to(self, path: str):
        """Navigate to a path within OA."""
        url = f"{OA_BASE_URL}{path}" if path.startswith("/") else path
        await self.page.goto(url)
        await self.page.wait_for_load_state("networkidle")

    async def click(self, page_name: str, element: str, timeout: int = 10000):
        """Click an element using the selector registry."""
        selector = self.get_selector(page_name, element)
        try:
            await self.page.click(selector, timeout=timeout)
        except Exception as e:
            raise SelectorNotFound(
                f"Failed to click '{page_name}.{element}' ({selector}): {e}"
            )

    async def fill(self, page_name: str, element: str, value: str, timeout: int = 10000):
        """Fill a text input using the selector registry."""
        selector = self.get_selector(page_name, element)
        try:
            await self.page.fill(selector, value, timeout=timeout)
        except Exception as e:
            raise SelectorNotFound(
                f"Failed to fill '{page_name}.{element}' ({selector}): {e}"
            )

    async def select(self, page_name: str, element: str, value: str, timeout: int = 10000):
        """Select a dropdown option using the selector registry."""
        selector = self.get_selector(page_name, element)
        try:
            await self.page.select_option(selector, value, timeout=timeout)
        except Exception as e:
            raise SelectorNotFound(
                f"Failed to select '{page_name}.{element}' ({selector}): {e}"
            )

    async def screenshot_base64(self) -> str:
        """Take a screenshot and return as base64 string."""
        screenshot_bytes = await self.page.screenshot()
        return base64.b64encode(screenshot_bytes).decode("utf-8")

    async def execute_action(self, action_type: str, subtask: dict) -> tuple[bool, str]:
        """Execute a named action. Dispatches to action modules."""
        await self.ensure_logged_in()

        if action_type == "create_bot":
            from tier2_playwright.actions.create_bot import create_bot
            return await create_bot(self, subtask)
        elif action_type == "create_automation":
            from tier2_playwright.actions.create_automation import create_automation
            return await create_automation(self, subtask)
        elif action_type == "configure_automation":
            from tier2_playwright.actions.configure_automation import configure_automation
            return await configure_automation(self, subtask)
        elif action_type == "check_status":
            from tier2_playwright.actions.check_bot_status import check_bot_status
            return await check_bot_status(self, subtask)
        elif action_type in ("pause_bot", "resume_bot"):
            from tier2_playwright.actions.pause_resume_bot import toggle_bot
            return await toggle_bot(self, subtask)
        else:
            raise SelectorNotFound(f"No Playwright action for type '{action_type}'")

    async def close(self):
        """Clean up browser resources."""
        if self.context:
            await self._save_cookies()
        if self.browser:
            await self.browser.close()
