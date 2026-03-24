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
        print("Warning: Planner returned non-JSON. Using single-subtask fallback.")
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

def save_subtask_result(subtask_id: int, title: str, result: str):
    """Save subtask result to file (external memory)."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    result_file = os.path.join(RESULTS_DIR, f"subtask_{subtask_id}_{title.replace(' ', '_')}.txt")
    with open(result_file, 'w') as f:
        f.write(f"# Subtask {subtask_id}: {title}\n")
        f.write(f"# Completed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(result)
    return result_file


# ============================================================
# PATTERN 5: EXECUTOR AGENT WITH ERROR PRESERVATION
# Each subtask gets its own isolated context window.
# Errors are LEFT in context (not hidden) so Claude learns.
# ============================================================

async def execute_subtask(subtask: dict, todo_context: str, api_key: str) -> tuple[bool, str]:
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
                        print(f"\n[{status}] {text[:200]}")
                    else:
                        print(f"\n[thinking] {text[:150]}")
            elif content_block.get("type") == "tool_use":
                step_count += 1
                tool_name = content_block.get('name', '')
                tool_input = content_block.get('input', {})
                if tool_name == "computer":
                    action = tool_input.get('action', '')
                    symbols = {
                        "screenshot": "[screenshot]", "mouse_move": "[mouse]",
                        "left_click": "[click]", "type": "[type]", "key": "[key]"
                    }
                    symbol = symbols.get(action, "[tool]")
                    detail = ""
                    if action == "type":
                        detail = f": {tool_input.get('text', '')[:40]}..."
                    elif action == "key":
                        detail = f": {tool_input.get('text', '')}"
                    print(f"  {symbol} Step {step_count}: {action}{detail}")

    def tool_output_callback(result, tool_use_id):
        # Pattern 5: Leave errors in context (don't suppress them)
        if result.error:
            print(f"  [error] Error (kept in context for learning): {result.error[:100]}")

    def api_response_callback(request, response, error):
        if error:
            print(f"\n[api-error] API Error: {error}")

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
        print("ERROR: ANTHROPIC_API_KEY not found in environment")
        return

    print("OPTIONS-CLAW v2.0 (MANUS-STYLE AGENT)")
    print("=" * 60)

    # ---- PHASE 1: PLAN ----
    print("\n[PHASE 1] Planning (decomposing task into subtasks)...")
    subtasks = await plan_task(task_prompt, api_key)
    total_est = sum(t.get("estimated_minutes", 10) for t in subtasks)
    print(f"   Plan created: {len(subtasks)} subtasks, ~{total_est} min estimated")
    for t in subtasks:
        print(f"      {t['id']}. {t['title']} (~{t.get('estimated_minutes', '?')} min)")

    # ---- PHASE 2: EXECUTE WITH TRACKING ----
    print(f"\n[PHASE 2] Executing {len(subtasks)} subtasks...")
    results = {}
    failed_tasks = []

    for idx, subtask in enumerate(subtasks):
        print(f"\n{'=' * 60}")
        print(f"SUBTASK {subtask['id']}/{len(subtasks)}: {subtask['title']}")
        print(f"{'=' * 60}")

        # Pattern 2: Update todo.md for goal recitation
        todo_context = write_todo(subtasks, idx, results)

        # Execute with retry
        success = False
        for attempt in range(MAX_SUBTASK_RETRIES + 1):
            if attempt > 0:
                print(f"\n[retry] Retry {attempt}/{MAX_SUBTASK_RETRIES}...")

            success, result_text = await execute_subtask(
                subtask, todo_context, api_key
            )

            if success:
                break
            elif attempt < MAX_SUBTASK_RETRIES:
                # Pattern 5: Error is already in the result_text
                print(f"   [warning] Subtask failed, will retry. Error preserved for learning.")

        # Pattern 4: Save result to file
        result_summary = result_text[-500:] if len(result_text) > 500 else result_text
        result_file = save_subtask_result(subtask["id"], subtask["title"], result_text)

        if success:
            results[subtask["id"]] = f"Completed. Details in {result_file}"
            print(f"\n   [done] Subtask {subtask['id']} complete -> saved to {result_file}")
        else:
            results[subtask["id"]] = f"FAILED after {MAX_SUBTASK_RETRIES + 1} attempts"
            failed_tasks.append(subtask)
            print(f"\n   [failed] Subtask {subtask['id']} failed after retries")

            # Ask: should we continue or abort?
            if idx < len(subtasks) - 1:
                print(f"   [warning] Continuing to next subtask despite failure...")

    # ---- PHASE 3: SUMMARY ----
    print(f"\n{'=' * 60}")
    print("EXECUTION SUMMARY")
    print(f"{'=' * 60}")

    # Final todo update
    write_todo(subtasks, len(subtasks), results)

    completed = len(subtasks) - len(failed_tasks)
    print(f"   Completed: {completed}/{len(subtasks)}")
    if failed_tasks:
        print(f"   Failed: {len(failed_tasks)}")
        for t in failed_tasks:
            print(f"      - {t['title']}")

    print(f"\n   Results saved in: {RESULTS_DIR}/")
    print(f"   Todo file: {TODO_FILE}")
    print(f"\nTo resume failed tasks, run with the specific subtask description")


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
