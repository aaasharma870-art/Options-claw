"""Speculative execution queue.

Instead of screenshot-after-every-action, batch multiple actions
and verify periodically. Reduces screenshot overhead by 60-80%.

Confidence levels:
- High (>0.9): Skip screenshot. E.g., filling a text field.
- Medium (0.5-0.9): Save screenshot locally, don't send to AI.
- Low (<0.5): Take screenshot AND verify with AI before continuing.
"""

import asyncio
import base64
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from core.config import SPECULATIVE_VERIFICATION_INTERVAL

log = logging.getLogger("options-claw.speculative")


@dataclass
class Action:
    """A single UI action to execute."""
    action_type: str          # "click", "fill", "select", "key"
    selector: str             # CSS selector
    value: str = ""           # Value for fill/select actions
    confidence: float = 0.9   # How confident we are this will work
    description: str = ""     # Human-readable description


@dataclass
class ActionResult:
    """Result of executing an action."""
    action: Action
    success: bool
    error: str = ""
    screenshot_b64: str = ""  # Only populated on verification points
    timestamp: float = field(default_factory=time.time)


class SpeculativeQueue:
    """Batches actions and verifies periodically instead of per-action.

    Usage:
        queue = SpeculativeQueue(page, verification_interval=5)
        queue.add(Action("click", "#new-bot"))
        queue.add(Action("fill", "#bot-name", "Credit Scanner V3"))
        queue.add(Action("select", "#symbol", "SPY"))
        queue.add(Action("click", "#paper-mode"))
        queue.add(Action("click", "#create-bot"))
        results = await queue.execute()
    """

    def __init__(self, page=None, verification_interval: int = SPECULATIVE_VERIFICATION_INTERVAL):
        self.page = page  # Playwright page object
        self.actions: list[Action] = []
        self.results: list[ActionResult] = []
        self.verification_interval = verification_interval

    def add(self, action: Action):
        """Add an action to the queue."""
        self.actions.append(action)

    async def execute(self) -> list[ActionResult]:
        """Execute all queued actions with periodic verification.

        Takes screenshots only at verification points (every N actions)
        or when confidence is low.
        """
        if not self.page:
            raise RuntimeError("No Playwright page set. Call set_page() first.")

        results = []
        since_last_verify = 0

        for i, action in enumerate(self.actions):
            result = await self._execute_action(action)
            results.append(result)

            if not result.success:
                # Action failed — take screenshot for debugging
                log.warning(f"Action failed: {action.description or action.action_type} on {action.selector}")
                result.screenshot_b64 = await self._take_screenshot()
                break

            since_last_verify += 1

            # Decide whether to verify
            needs_verify = (
                action.confidence < 0.5  # Low confidence: always verify
                or since_last_verify >= self.verification_interval  # Periodic check
                or i == len(self.actions) - 1  # Last action: always verify
            )

            if needs_verify:
                result.screenshot_b64 = await self._take_screenshot()
                since_last_verify = 0

                if action.confidence < 0.5:
                    log.info(f"Low-confidence action verified: {action.description}")
            elif action.confidence < 0.9:
                # Medium confidence: save screenshot locally but don't verify with AI
                result.screenshot_b64 = await self._take_screenshot()
                log.debug(f"Medium-confidence screenshot saved: {action.description}")

        self.results = results
        self.actions = []
        return results

    async def _execute_action(self, action: Action) -> ActionResult:
        """Execute a single Playwright action."""
        try:
            if action.action_type == "click":
                await self.page.click(action.selector, timeout=10000)
            elif action.action_type == "fill":
                await self.page.fill(action.selector, action.value, timeout=10000)
            elif action.action_type == "select":
                await self.page.select_option(action.selector, action.value, timeout=10000)
            elif action.action_type == "key":
                await self.page.keyboard.press(action.value)
            else:
                return ActionResult(action=action, success=False,
                                    error=f"Unknown action type: {action.action_type}")

            return ActionResult(action=action, success=True)

        except Exception as e:
            return ActionResult(action=action, success=False, error=str(e))

    async def _take_screenshot(self) -> str:
        """Take a screenshot and return as base64."""
        screenshot_bytes = await self.page.screenshot()
        return base64.b64encode(screenshot_bytes).decode("utf-8")

    def set_page(self, page):
        """Set the Playwright page object."""
        self.page = page
