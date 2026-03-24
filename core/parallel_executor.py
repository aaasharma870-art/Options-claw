"""Parallel subtask executor.

Runs independent subtasks simultaneously across multiple Playwright
browser contexts. Tasks in the same parallel_group run concurrently.

Example planner output:
    [
        {"id": 1, "title": "Create bot shell", "parallel_group": 1},
        {"id": 2, "title": "Build GEX Router", "parallel_group": 2, "depends_on": [1]},
        {"id": 3, "title": "Build Iron Condor", "parallel_group": 2, "depends_on": [1]},
        {"id": 4, "title": "Build Directional", "parallel_group": 2, "depends_on": [1]},
    ]
    # Group 1 runs first. Then all of group 2 in parallel.
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Callable, Awaitable

from core.config import PARALLEL_MAX_WORKERS

log = logging.getLogger("options-claw.parallel")


def group_subtasks(subtasks: list[dict]) -> list[list[dict]]:
    """Organize subtasks into sequential groups for parallel execution.

    Subtasks with the same parallel_group value run concurrently.
    Groups execute in order of their group number.

    Returns:
        List of groups, where each group is a list of subtasks
        that can run in parallel.
    """
    groups: dict[int, list[dict]] = defaultdict(list)

    for task in subtasks:
        group_id = task.get("parallel_group", task["id"])
        groups[group_id].append(task)

    # Sort by group key so dependencies are respected
    return [groups[k] for k in sorted(groups.keys())]


async def execute_parallel_group(
    group: list[dict],
    executor_fn: Callable[[dict], Awaitable[tuple[bool, str]]],
    max_workers: int = PARALLEL_MAX_WORKERS,
) -> dict[int, tuple[bool, str]]:
    """Run a group of independent subtasks in parallel.

    Args:
        group: List of subtasks to run simultaneously.
        executor_fn: Async function that executes a single subtask.
            Signature: async (subtask) -> (success, result_text)
        max_workers: Maximum concurrent executions.

    Returns:
        Dict mapping subtask id to (success, result_text).
    """
    semaphore = asyncio.Semaphore(max_workers)
    results = {}

    async def run_one(subtask: dict):
        async with semaphore:
            task_id = subtask["id"]
            log.info(f"[parallel] Starting subtask {task_id}: {subtask['title']}")
            start = time.time()

            try:
                success, result_text = await executor_fn(subtask)
            except Exception as e:
                success, result_text = False, f"SUBTASK_FAILED: {e}"

            dur = time.time() - start
            status = "done" if success else "FAILED"
            log.info(f"[parallel] Subtask {task_id} {status} in {dur:.0f}s")
            results[task_id] = (success, result_text)

    await asyncio.gather(*(run_one(task) for task in group))
    return results


async def execute_with_parallelism(
    subtasks: list[dict],
    executor_fn: Callable[[dict], Awaitable[tuple[bool, str]]],
) -> dict[int, tuple[bool, str]]:
    """Execute subtasks respecting parallel_group ordering.

    Groups run sequentially. Within each group, subtasks run in parallel.

    Returns:
        Dict mapping subtask id to (success, result_text).
    """
    groups = group_subtasks(subtasks)
    all_results = {}

    for i, group in enumerate(groups):
        if len(group) == 1:
            log.info(f"[group {i+1}/{len(groups)}] Running 1 subtask sequentially")
        else:
            log.info(f"[group {i+1}/{len(groups)}] Running {len(group)} subtasks in parallel")

        group_results = await execute_parallel_group(group, executor_fn)
        all_results.update(group_results)

        # Check if any task in this group failed
        failures = [tid for tid, (ok, _) in group_results.items() if not ok]
        if failures:
            log.warning(f"[group {i+1}] {len(failures)} subtask(s) failed: {failures}")
            # Continue to next group anyway — the orchestrator decides what to do

    return all_results
