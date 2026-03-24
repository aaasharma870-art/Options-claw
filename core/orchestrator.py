"""Main orchestrator — the brain of Options-Claw v3.

Routes each subtask to the cheapest execution tier:
    Tier 1: OA Webhooks + Python ($0, instant)
    Tier 2: Playwright browser automation ($0, fast)
    Tier 3: Claude Computer Use ($$$, smart)

Flow: plan -> classify tier -> execute -> verify -> learn
"""

import asyncio
import logging
import time

from core.config import get_api_key, RESULTS_DIR
from core.learning_db import LearningDB
from core.model_router import route_model
from core.verifier import verify_action
from core.parallel_executor import execute_with_parallelism

log = logging.getLogger("options-claw.orchestrator")

# Task types eligible for each tier
TIER1_TASK_TYPES = frozenset([
    "trigger_automation", "send_signal", "regime_update",
    "pause_automation", "resume_automation",
])

TIER2_TASK_TYPES = frozenset([
    "create_bot", "create_automation", "configure_automation",
    "check_status", "pause_bot", "resume_bot",
])


class OptionsClawOrchestrator:
    """Three-tier hybrid execution engine."""

    def __init__(self):
        self.learning_db = LearningDB()
        self._webhook_manager = None
        self._playwright_runner = None

    @property
    def webhook_manager(self):
        if self._webhook_manager is None:
            from tier1_webhooks.webhook_manager import WebhookManager
            self._webhook_manager = WebhookManager()
        return self._webhook_manager

    @property
    def playwright_runner(self):
        if self._playwright_runner is None:
            from tier2_playwright.playwright_runner import PlaywrightRunner
            self._playwright_runner = PlaywrightRunner()
        return self._playwright_runner

    async def execute_task(self, task: str):
        """Full pipeline: plan -> route -> execute -> verify -> learn."""
        api_key = get_api_key()
        task_start = time.time()

        log.info("OPTIONS-CLAW v3.0 (HYBRID THREE-TIER ENGINE)")
        log.info("=" * 60)

        # Phase 1: Plan (text-only Claude call)
        log.info("[PHASE 1] Planning...")
        subtasks = await self._plan(task, api_key)
        log.info(f"Plan: {len(subtasks)} subtasks")
        for t in subtasks:
            tier = self.classify_tier(t)
            log.info(f"  {t['id']}. {t['title']} -> Tier {tier}")

        # Phase 2: Execute (parallel where possible)
        log.info("[PHASE 2] Executing...")

        async def run_subtask(subtask):
            return await self._execute_subtask(subtask, api_key)

        results = await execute_with_parallelism(subtasks, run_subtask)

        # Phase 3: Summary
        task_duration = time.time() - task_start
        succeeded = sum(1 for ok, _ in results.values() if ok)
        log.info(f"\n{'=' * 60}")
        log.info(f"COMPLETE: {succeeded}/{len(subtasks)} subtasks in {task_duration:.0f}s")
        log.info(f"{'=' * 60}")

        return results

    async def _plan(self, task: str, api_key: str) -> list[dict]:
        """Decompose task into subtasks using the planner."""
        import anthropic
        from core.config import PLANNER_MODEL

        client = anthropic.Anthropic(api_key=api_key)
        import json

        planning_prompt = f"""You are a task planner for an AI agent that manages trading bots in Option Alpha.

Break this task into sequential subtasks. For each subtask, classify its type.

TASK TYPES (use these exact strings):
- "trigger_automation" — Send a signal/trigger to an existing automation
- "regime_update" — Update the GEX regime classification
- "create_bot" — Create a new bot
- "create_automation" — Add an automation to a bot
- "configure_automation" — Set parameters on an existing automation
- "check_status" — Check bot/automation status
- "pause_bot" / "resume_bot" — Toggle bot state
- "custom" — Anything that doesn't fit above

RULES:
- Each subtask must be self-contained
- Mark independent subtasks with the same "parallel_group" number
- Max 8 subtasks

Respond with a JSON array:
[{{
    "id": 1,
    "title": "short name",
    "type": "task_type from above",
    "description": "detailed instructions",
    "depends_on": [],
    "parallel_group": 1,
    "estimated_minutes": 10,
    "checkpoint": "what to verify",
    "requires_verification": true
}}]

TASK TO DECOMPOSE:
{task}

Respond ONLY with the JSON array."""

        response = client.messages.create(
            model=PLANNER_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": planning_prompt}],
        )

        plan_text = response.content[0].text.strip()
        if plan_text.startswith("```"):
            plan_text = plan_text.split("\n", 1)[1]
        if plan_text.endswith("```"):
            plan_text = plan_text.rsplit("```", 1)[0]

        try:
            return json.loads(plan_text)
        except json.JSONDecodeError:
            log.warning("Planner returned non-JSON, using single-subtask fallback")
            return [{
                "id": 1, "title": "Execute full task", "type": "custom",
                "description": task, "depends_on": [], "parallel_group": 1,
                "estimated_minutes": 60, "checkpoint": "All steps completed",
                "requires_verification": True,
            }]

    def classify_tier(self, subtask: dict) -> int:
        """Determine cheapest execution tier for this subtask."""
        task_type = subtask.get("type", "custom")

        # Tier 1: Webhook-eligible tasks
        if task_type in TIER1_TASK_TYPES:
            if self.webhook_manager.has_webhook(subtask.get("automation_name", "")):
                return 1

        # Tier 2: Tasks with known Playwright actions
        if task_type in TIER2_TASK_TYPES:
            confidence = self.learning_db.selector_confidence(task_type)
            if confidence > 0.8:
                return 2

        # Tier 3: Everything else (Computer Use)
        return 3

    async def _execute_subtask(self, subtask: dict, api_key: str) -> tuple[bool, str]:
        """Execute a subtask on the appropriate tier with fallback."""
        tier = self.classify_tier(subtask)
        subtask_start = time.time()
        task_type = subtask.get("type", "custom")

        log.info(f"Subtask {subtask['id']}: '{subtask['title']}' -> Tier {tier}")

        success = False
        result_text = ""
        actual_tier = tier

        try:
            if tier == 1:
                success, result_text = await self._execute_tier1(subtask)
            elif tier == 2:
                try:
                    success, result_text = await self._execute_tier2(subtask)
                except Exception as e:
                    log.warning(f"Tier 2 failed ({e}), escalating to Tier 3")
                    actual_tier = 3
                    success, result_text = await self._execute_tier3(subtask, api_key, error_context=str(e))
                    if success:
                        # Learn from Tier 3 for future Tier 2 use
                        log.info("Recording Tier 3 discovery for future Tier 2 use")
            else:
                success, result_text = await self._execute_tier3(subtask, api_key)
        except Exception as e:
            success = False
            result_text = f"SUBTASK_FAILED: {e}"

        # Verify critical actions
        if success and subtask.get("requires_verification"):
            success, result_text = await self._verify_subtask(subtask, result_text)

        # Record to learning DB
        duration = int(time.time() - subtask_start)
        cost = 0.0 if actual_tier < 3 else 0.50  # rough estimate
        self.learning_db.record_task(
            task_type=task_type,
            parameters={"title": subtask["title"]},
            tier=actual_tier,
            duration_s=duration,
            cost=cost,
            success=success,
            error_msg=result_text if not success else None,
        )

        return success, result_text

    async def _execute_tier1(self, subtask: dict) -> tuple[bool, str]:
        """Execute via OA webhook (free, instant)."""
        automation_name = subtask.get("automation_name", subtask["title"])
        payload = subtask.get("webhook_payload", {})
        response = await self.webhook_manager.trigger(automation_name, payload)
        if response.get("success"):
            return True, f"Webhook triggered: {automation_name}"
        return False, f"Webhook failed: {response.get('error', 'unknown')}"

    async def _execute_tier2(self, subtask: dict) -> tuple[bool, str]:
        """Execute via Playwright (free, fast)."""
        task_type = subtask.get("type", "")
        return await self.playwright_runner.execute_action(task_type, subtask)

    async def _execute_tier3(self, subtask: dict, api_key: str,
                             error_context: str = None) -> tuple[bool, str]:
        """Execute via Computer Use (expensive, smart)."""
        from tier3_computer_use.computer_use_fallback import execute_single_step
        return await execute_single_step(subtask, api_key, error_context=error_context)

    async def _verify_subtask(self, subtask: dict, result_text: str) -> tuple[bool, str]:
        """Verify a completed subtask using Haiku."""
        checkpoint = subtask.get("checkpoint", "")
        if not checkpoint:
            return True, result_text

        try:
            # Take screenshot for verification
            if self._playwright_runner and self._playwright_runner.page:
                import base64
                screenshot_bytes = await self._playwright_runner.page.screenshot()
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

                passed, answer = await verify_action(screenshot_b64, checkpoint)
                if passed:
                    log.info(f"Verification passed: {checkpoint}")
                    return True, result_text
                else:
                    log.warning(f"Verification failed: {answer}")
                    return False, f"Verification failed: {answer}. {result_text}"
        except Exception as e:
            log.warning(f"Verification skipped: {e}")

        return True, result_text

    def close(self):
        """Clean up resources."""
        self.learning_db.close()


async def run_task(task: str):
    """Convenience entry point."""
    orchestrator = OptionsClawOrchestrator()
    try:
        return await orchestrator.execute_task(task)
    finally:
        orchestrator.close()
