"""Computer Use fallback — Tier 3 execution.

Used when Tier 1 (webhooks) and Tier 2 (Playwright) cannot handle a task.
Wraps the existing manus_task_runner.py (v2) for single-step execution.

When Tier 3 fires:
- Playwright selector failed (OA redesigned a page)
- Novel task with no Playwright action recorded
- Error recovery requiring visual understanding
- First-time setup of a new bot type
"""

import asyncio
import logging
import os
import sys
import time

from core.config import (
    EXECUTOR_MODEL, STABLE_SYSTEM_PREFIX, MAX_SCREENSHOTS_IN_CONTEXT,
    RESULTS_DIR,
)

log = logging.getLogger("options-claw.tier3")

# Reuse the stable system prefix from config for KV-cache optimization
STABLE_SYSTEM_PREFIX = """You are Options-Claw, an autonomous trading bot builder.
You are working inside Option Alpha's web interface to build and configure trading bots.

CORE RULES:
1. Take a screenshot BEFORE and AFTER every major configuration step
2. If any UI element is unclear or not found, describe what you see
3. Read all text on screen carefully - OA has many similar-looking buttons
4. Save frequently - OA can timeout on long sessions
5. After completing each step, report what was done

CURRENT TASK CONTEXT:
You are executing ONE specific subtask from a larger plan.
Focus ONLY on the current subtask. Do not try to do the entire plan.
When this subtask is complete, say "SUBTASK_COMPLETE" and summarize what was done.
If you encounter an error you cannot recover from, say "SUBTASK_FAILED" and explain why.
"""


async def execute_single_step(subtask: dict, api_key: str,
                              error_context: str = None,
                              screenshot_b64: str = None) -> tuple[bool, str]:
    """Execute a single subtask via Computer Use (Tier 3).

    This runs INSIDE the Docker container with the virtual desktop.

    Args:
        subtask: Subtask dict with title, description, checkpoint.
        api_key: Anthropic API key.
        error_context: If escalating from Tier 2, the error message.
        screenshot_b64: If available, screenshot of where Playwright got stuck.

    Returns:
        (success, result_text) tuple.
    """
    sys.path.insert(0, '/home/computeruse')

    try:
        from computer_use_demo.loop import sampling_loop, APIProvider
    except ImportError:
        log.error("computer_use_demo not available. Are you inside the Docker container?")
        return False, "SUBTASK_FAILED: Not running inside Computer Use container"

    # Build prompt
    prompt_parts = []

    if error_context:
        prompt_parts.append(
            f"## ESCALATED FROM PLAYWRIGHT (automated browser)\n"
            f"Playwright failed with this error: {error_context}\n"
            f"Please complete this step using visual interaction instead.\n"
        )

    prompt_parts.append(f"## YOUR CURRENT SUBTASK:\n**{subtask['title']}**\n")
    prompt_parts.append(subtask.get("description", ""))

    checkpoint = subtask.get("checkpoint", "Complete the step described above")
    prompt_parts.append(f"\n## COMPLETION CRITERIA:\n{checkpoint}")
    prompt_parts.append(
        "\nWhen done, say SUBTASK_COMPLETE and summarize what was accomplished.\n"
        "If stuck, say SUBTASK_FAILED and explain the blocker."
    )

    prompt = "\n".join(prompt_parts)

    # If we have a screenshot from Playwright, include it
    messages = []
    if screenshot_b64:
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_b64,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        })
    else:
        messages.append({"role": "user", "content": prompt})

    result_text = ""
    step_count = 0

    def output_callback(content_block):
        nonlocal step_count, result_text
        if isinstance(content_block, dict):
            if content_block.get("type") == "text":
                text = content_block.get("text", "")
                if text.strip():
                    result_text += text + "\n"
                    if "SUBTASK_COMPLETE" in text or "SUBTASK_FAILED" in text:
                        log.info(f"[Tier3] {text[:200]}")
                    else:
                        log.debug(f"[Tier3] {text[:150]}")
            elif content_block.get("type") == "tool_use":
                step_count += 1
                tool_name = content_block.get("name", "")
                tool_input = content_block.get("input", {})
                if tool_name == "computer":
                    action = tool_input.get("action", "")
                    log.info(f"  [Tier3] Step {step_count}: {action}")

    def tool_output_callback(result, tool_use_id):
        if result.error:
            log.warning(f"  [Tier3] Error (preserved): {result.error[:100]}")

    def api_response_callback(request, response, error):
        if error:
            log.error(f"[Tier3] API Error: {error}")

    try:
        await sampling_loop(
            model=EXECUTOR_MODEL,
            provider=APIProvider.ANTHROPIC,
            system_prompt_suffix=STABLE_SYSTEM_PREFIX,
            messages=messages,
            output_callback=output_callback,
            tool_output_callback=tool_output_callback,
            api_response_callback=api_response_callback,
            api_key=api_key,
            only_n_most_recent_images=MAX_SCREENSHOTS_IN_CONTEXT,
            max_tokens=4096,
            tool_version="computer_use_20250124",
            thinking_budget=None,
            token_efficient_tools_beta=False,
        )

        success = "SUBTASK_COMPLETE" in result_text
        return success, result_text

    except Exception as e:
        return False, f"SUBTASK_FAILED: Exception - {str(e)}"
