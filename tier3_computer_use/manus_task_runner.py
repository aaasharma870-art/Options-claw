"""
Manus-Style Task Runner for Options-Claw
=========================================
Applies 5 key Manus AI patterns to fix:
  - Slow execution (context bloat -> compress old observations)
  - Losing track of long tasks (no goal recitation -> todo.md pattern)
  - High cost (no caching -> append-only context + stable prefix)
  - Fragile on complex tasks (single-shot -> planner/executor split)

Architecture:
  1. PLANNER agent decomposes task -> subtasks (cheap, text-only call)
  2. EXECUTOR agent runs each subtask with Computer Use (isolated context)
  3. todo.md is updated after each subtask (goal recitation)
  4. Results saved to files, not kept in context (external memory)
  5. Errors left in context so Claude learns (error preservation)
"""

import asyncio
import sys
import os
import json
import time
import logging
from pathlib import Path
from typing import Optional

# ============================================================
# CONFIG
# ============================================================

PLANNER_MODEL = "claude-sonnet-4-5-20250929"  # Cheap model for planning
EXECUTOR_MODEL = "claude-sonnet-4-5-20250929"  # Same model for execution
MAX_SCREENSHOTS_IN_CONTEXT = 3  # Manus pattern: only keep N most recent
MAX_SUBTASK_RETRIES = 2
RESULTS_DIR = "/tmp/options_claw_results"
TODO_FILE = "/tmp/options_claw_todo.md"
LOG_FILE = "/tmp/options_claw_execution.log"

# ============================================================
# LOGGING SETUP
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("options-claw")

# Stable system prefix (never changes -> maximizes KV-cache hits)
# This is the #1 cost optimization from Manus
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


# ============================================================
# COST TRACKER
# ============================================================

class CostTracker:
    """Track API calls and estimate costs per subtask."""

    # Approximate pricing (per 1M tokens)
    INPUT_COST_PER_M = 3.00   # Claude Sonnet input
    OUTPUT_COST_PER_M = 15.00  # Claude Sonnet output
    CACHED_INPUT_COST_PER_M = 0.30  # Cached input (10x cheaper)

    def __init__(self):
        self.subtask_stats = {}
        self.total_api_calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def start_subtask(self, subtask_id: int):
        self.subtask_stats[subtask_id] = {
            "api_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "start_time": time.time()
        }

    def record_api_call(self, subtask_id: int, response=None):
        self.total_api_calls += 1
        stats = self.subtask_stats.get(subtask_id, {})
        stats["api_calls"] = stats.get("api_calls", 0) + 1

        if response and hasattr(response, 'usage'):
            input_tok = getattr(response.usage, 'input_tokens', 0)
            output_tok = getattr(response.usage, 'output_tokens', 0)
            stats["input_tokens"] = stats.get("input_tokens", 0) + input_tok
            stats["output_tokens"] = stats.get("output_tokens", 0) + output_tok
            self.total_input_tokens += input_tok
            self.total_output_tokens += output_tok

    def end_subtask(self, subtask_id: int):
        stats = self.subtask_stats.get(subtask_id, {})
        stats["end_time"] = time.time()
        stats["duration_s"] = stats["end_time"] - stats.get("start_time", stats["end_time"])

    def summary(self) -> str:
        est_input_cost = (self.total_input_tokens / 1_000_000) * self.INPUT_COST_PER_M
        est_output_cost = (self.total_output_tokens / 1_000_000) * self.OUTPUT_COST_PER_M
        est_total = est_input_cost + est_output_cost

        lines = [
            "\nCOST SUMMARY",
            "-" * 40,
            f"  Total API calls:    {self.total_api_calls}",
            f"  Input tokens:       ~{self.total_input_tokens:,}",
            f"  Output tokens:      ~{self.total_output_tokens:,}",
            f"  Estimated cost:     ~${est_total:.2f}",
            f"    (input: ${est_input_cost:.2f}, output: ${est_output_cost:.2f})",
            "",
            "  Per subtask:"
        ]
        for sid, stats in self.subtask_stats.items():
            dur = stats.get("duration_s", 0)
            calls = stats.get("api_calls", 0)
            lines.append(f"    Subtask {sid}: {calls} calls, {dur:.0f}s")
        lines.append("-" * 40)
        return "\n".join(lines)


cost_tracker = CostTracker()


# ============================================================
# PATTERN 1: PLANNER AGENT
# Decomposes big tasks into subtasks (text-only, no Computer Use)
# This is cheap (~$0.01) and prevents the executor from drifting
# ============================================================

async def plan_task(task_prompt: str, api_key: str) -> list[dict]:
    """Use Claude to decompose a complex task into ordered subtasks."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    planning_prompt = f"""You are a task planner for an AI agent that builds trading bots in Option Alpha.

Break this task into sequential subtasks that can each be completed independently in 5-15 minutes.

RULES:
- Each subtask must be self-contained (the executor has NO memory of previous subtasks)
- Each subtask must start with "Navigate to..." or "On the current screen..."
- Include verification steps (e.g., "Take a screenshot to confirm X was saved")
- If a subtask depends on a previous one, include the context needed
- Max 8 subtasks (if more needed, group related steps)

Respond with a JSON array of objects, each with:
- "id": sequential number (1, 2, 3...)
- "title": short name (e.g., "Create bot shell")
- "description": detailed instructions for this specific subtask
- "depends_on": list of subtask IDs this depends on (empty for first)
- "estimated_minutes": how long this should take
- "checkpoint": what to verify before marking complete

TASK TO DECOMPOSE:
{task_prompt}

Respond ONLY with the JSON array, no other text."""

    response = client.messages.create(
        model=PLANNER_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": planning_prompt}]
    )

    # Track planner cost
    if hasattr(response, 'usage'):
        cost_tracker.total_input_tokens += getattr(response.usage, 'input_tokens', 0)
        cost_tracker.total_output_tokens += getattr(response.usage, 'output_tokens', 0)
        cost_tracker.total_api_calls += 1

    # Parse the plan
    plan_text = response.content[0].text.strip()

    # Strip markdown code fences if present
    if plan_text.startswith("```"):
        plan_text = plan_text.split("\n", 1)[1]
    if plan_text.endswith("```"):
        plan_text = plan_text.rsplit("```", 1)[0]

    try:
        subtasks = json.loads(plan_text)
    except json.JSONDecodeError:
        # Fallback: treat entire task as one subtask
        log.warning("Planner returned non-JSON. Using single-subtask fallback.")
        subtasks = [{
            "id": 1,
            "title": "Execute full task",
            "description": task_prompt,
            "depends_on": [],
            "estimated_minutes": 60,
            "checkpoint": "All steps completed"
        }]

    return subtasks


# ============================================================
# PATTERN 2: TODO.MD GOAL RECITATION
# Manus's key insight: constantly rewrite the todo list so the
# global plan stays in the model's recent attention window.
# This prevents "lost-in-the-middle" goal drift.
# ============================================================

def write_todo(subtasks: list[dict], current_idx: int, results: dict):
    """Write/update the todo.md file with current progress."""
    lines = ["# Options-Claw Task Progress\n"]
    lines.append(f"**Current step**: {current_idx + 1} of {len(subtasks)}\n")
    lines.append(f"**Last updated**: {time.strftime('%H:%M:%S')}\n\n")

    for i, task in enumerate(subtasks):
        if i < current_idx:
            # Completed
            result = results.get(task["id"], "No result recorded")
            # Truncate long results (keep context lean)
            if len(result) > 200:
                result = result[:200] + "..."
            lines.append(f"- [x] **{task['title']}** -> {result}\n")
        elif i == current_idx:
            # Current
            lines.append(f"- [ ] **{task['title']}** <-- IN PROGRESS\n")
            lines.append(f"  - {task['description'][:300]}\n")
        else:
            # Upcoming
            lines.append(f"- [ ] {task['title']}\n")

    Path(TODO_FILE).write_text("".join(lines))
    return "".join(lines)


# ============================================================
# PATTERN 3: CONTEXT COMPRESSION
# Manus keeps context lean by:
# - Only keeping N most recent screenshots
# - Saving full results to files, keeping summaries in context
# - Dropping old tool outputs but preserving URLs/file paths
# ============================================================

def compress_messages(messages: list, max_screenshots: int = MAX_SCREENSHOTS_IN_CONTEXT) -> list:
    """Compress message history to prevent context bloat.

    Key insight from Manus: you don't need every screenshot in context.
    Keep only the N most recent ones. Old screenshots are the #1 context hog.
    """
    # Count screenshots from the end
    screenshot_count = 0
    compressed = []

    for msg in reversed(messages):
        if isinstance(msg.get("content"), list):
            new_content = []
            for block in msg["content"]:
                if block.get("type") == "image":
                    screenshot_count += 1
                    if screenshot_count <= max_screenshots:
                        new_content.append(block)
                    else:
                        # Replace old screenshot with text marker
                        new_content.append({
                            "type": "text",
                            "text": "[Screenshot removed - older than recent context]"
                        })
                else:
                    new_content.append(block)
            compressed.append({**msg, "content": new_content})
        else:
            compressed.append(msg)

    compressed.reverse()
    return compressed


# ============================================================
# PATTERN 4: FILE-BASED EXTERNAL MEMORY
# Save intermediate results to files instead of keeping them
# in the context window. The executor can read files when needed.
# ============================================================

def save_subtask_result(subtask_id: int, title: str, result: str,
                        start_time: float, end_time: float):
    """Save subtask result to file (external memory) with timestamps."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    result_file = os.path.join(RESULTS_DIR, f"subtask_{subtask_id}_{title.replace(' ', '_')}.txt")
    duration = end_time - start_time
    with open(result_file, 'w') as f:
        f.write(f"# Subtask {subtask_id}: {title}\n")
        f.write(f"# Started:   {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}\n")
        f.write(f"# Completed: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}\n")
        f.write(f"# Duration:  {duration:.0f}s ({duration/60:.1f} min)\n\n")
        f.write(result)
    return result_file


# ============================================================
# PATTERN 5: EXECUTOR AGENT WITH ERROR PRESERVATION
# Each subtask gets its own isolated context window.
# Errors are LEFT in context (not hidden) so Claude learns.
# ============================================================

async def execute_subtask(subtask: dict, todo_context: str, api_key: str,
                          previous_error: str = None) -> tuple[bool, str]:
    """Execute a single subtask with Computer Use, isolated context."""
    sys.path.insert(0, '/home/computeruse')
    from computer_use_demo.loop import sampling_loop, APIProvider

    # Build the prompt with goal recitation (Pattern 2)
    prompt = f"""## YOUR CURRENT TODO LIST (do NOT skip ahead):
{todo_context}

## YOUR CURRENT SUBTASK:
**{subtask['title']}**

{subtask['description']}

## COMPLETION CRITERIA:
{subtask.get('checkpoint', 'Complete all steps described above')}

When done, say SUBTASK_COMPLETE and summarize what was accomplished.
If stuck, say SUBTASK_FAILED and explain the blocker."""

    # Pattern 5: If retrying, append the previous error so Claude learns
    if previous_error:
        prompt += f"""

## PREVIOUS ATTEMPT FAILED
The error was: {previous_error}
Please try a different approach."""

    messages = [{"role": "user", "content": prompt}]
    step_count = 0
    result_text = ""

    def output_callback(content_block):
        nonlocal step_count, result_text
        if isinstance(content_block, dict):
            if content_block.get("type") == "text":
                text = content_block.get('text', '')
                if text.strip():
                    result_text += text + "\n"
                    # Check for completion signals
                    if "SUBTASK_COMPLETE" in text or "SUBTASK_FAILED" in text:
                        status = "COMPLETE" if "COMPLETE" in text else "FAILED"
                        log.info(f"[{status}] {text[:200]}")
                    else:
                        log.info(f"[thinking] {text[:150]}")
            elif content_block.get("type") == "tool_use":
                step_count += 1
                tool_name = content_block.get('name', '')
                tool_input = content_block.get('input', {})
                if tool_name == "computer":
                    action = tool_input.get('action', '')
                    detail = ""
                    if action == "type":
                        detail = f": {tool_input.get('text', '')[:40]}..."
                    elif action == "key":
                        detail = f": {tool_input.get('text', '')}"
                    log.info(f"  Step {step_count}: {action}{detail}")

    def tool_output_callback(result, tool_use_id):
        # Pattern 5: Leave errors in context (don't suppress them)
        if result.error:
            log.warning(f"  Error (kept in context for learning): {result.error[:100]}")

    def api_response_callback(request, response, error):
        if error:
            log.error(f"API Error: {error}")
        else:
            cost_tracker.record_api_call(subtask["id"], response)

    try:
        final_messages = await sampling_loop(
            model=EXECUTOR_MODEL,
            provider=APIProvider.ANTHROPIC,
            system_prompt_suffix=STABLE_SYSTEM_PREFIX,  # Stable prefix for caching
            messages=messages,
            output_callback=output_callback,
            tool_output_callback=tool_output_callback,
            api_response_callback=api_response_callback,
            api_key=api_key,
            only_n_most_recent_images=MAX_SCREENSHOTS_IN_CONTEXT,  # Pattern 3
            max_tokens=4096,
            tool_version="computer_use_20250124",
            thinking_budget=None,
            token_efficient_tools_beta=False
        )

        success = "SUBTASK_COMPLETE" in result_text
        return success, result_text

    except Exception as e:
        return False, f"SUBTASK_FAILED: Exception - {str(e)}"


# ============================================================
# MAIN ORCHESTRATOR
# Ties all 5 Manus patterns together
# ============================================================

async def run_task(task_prompt: str):
    """Main entry point: plan -> execute -> track -> compress -> save."""

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY not found in environment")
        return

    task_start = time.time()
    log.info("OPTIONS-CLAW v2.0 (MANUS-STYLE AGENT)")
    log.info("=" * 60)

    # ---- PHASE 1: PLAN ----
    log.info("[PHASE 1] Planning (decomposing task into subtasks)...")
    subtasks = await plan_task(task_prompt, api_key)
    total_est = sum(t.get("estimated_minutes", 10) for t in subtasks)
    log.info(f"   Plan created: {len(subtasks)} subtasks, ~{total_est} min estimated")
    for t in subtasks:
        log.info(f"      {t['id']}. {t['title']} (~{t.get('estimated_minutes', '?')} min)")

    # ---- PHASE 2: EXECUTE WITH TRACKING ----
    log.info(f"[PHASE 2] Executing {len(subtasks)} subtasks...")
    results = {}
    failed_tasks = []

    for idx, subtask in enumerate(subtasks):
        log.info(f"\n{'=' * 60}")
        log.info(f"SUBTASK {subtask['id']}/{len(subtasks)}: {subtask['title']}")
        log.info(f"{'=' * 60}")

        # Pattern 2: Update todo.md for goal recitation
        todo_context = write_todo(subtasks, idx, results)

        # Start cost tracking for this subtask
        cost_tracker.start_subtask(subtask["id"])
        subtask_start = time.time()

        # Execute with retry
        success = False
        previous_error = None
        for attempt in range(MAX_SUBTASK_RETRIES + 1):
            if attempt > 0:
                log.info(f"[retry] Retry {attempt}/{MAX_SUBTASK_RETRIES}...")

            success, result_text = await execute_subtask(
                subtask, todo_context, api_key, previous_error=previous_error
            )

            if success:
                break
            elif attempt < MAX_SUBTASK_RETRIES:
                # Pattern 5: Preserve error for next attempt
                previous_error = result_text[-500:] if len(result_text) > 500 else result_text
                log.warning("Subtask failed, will retry. Error preserved for learning.")

        subtask_end = time.time()
        cost_tracker.end_subtask(subtask["id"])

        # Pattern 4: Save result to file with timestamps
        result_file = save_subtask_result(
            subtask["id"], subtask["title"], result_text,
            subtask_start, subtask_end
        )

        if success:
            results[subtask["id"]] = f"Completed. Details in {result_file}"
            log.info(f"[done] Subtask {subtask['id']} complete -> saved to {result_file}")
        else:
            results[subtask["id"]] = f"FAILED after {MAX_SUBTASK_RETRIES + 1} attempts"
            failed_tasks.append(subtask)
            log.error(f"Subtask {subtask['id']} failed after retries")

            if idx < len(subtasks) - 1:
                log.warning("Continuing to next subtask despite failure...")

    # ---- PHASE 3: SUMMARY ----
    task_end = time.time()
    task_duration = task_end - task_start

    log.info(f"\n{'=' * 60}")
    log.info("EXECUTION SUMMARY")
    log.info(f"{'=' * 60}")

    # Final todo update
    write_todo(subtasks, len(subtasks), results)

    completed = len(subtasks) - len(failed_tasks)
    log.info(f"   Completed: {completed}/{len(subtasks)}")
    if failed_tasks:
        log.info(f"   Failed: {len(failed_tasks)}")
        for t in failed_tasks:
            log.info(f"      - {t['title']}")

    log.info(f"   Total duration: {task_duration:.0f}s ({task_duration/60:.1f} min)")
    log.info(f"   Results saved in: {RESULTS_DIR}/")
    log.info(f"   Todo file: {TODO_FILE}")
    log.info(f"   Execution log: {LOG_FILE}")

    # Cost summary
    log.info(cost_tracker.summary())

    log.info("To resume failed tasks, run with the specific subtask description")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 manus_task_runner.py <task_file>")
        print("   Or: python3 manus_task_runner.py - (read from stdin)")
        sys.exit(1)

    if sys.argv[1] == "-":
        task = sys.stdin.read()
    else:
        with open(sys.argv[1], 'r') as f:
            task = f.read()

    asyncio.run(run_task(task))
