# Options-Claw Upgrade Guide

## v3.0: Three-Tier Hybrid Architecture (Beyond Manus)

v3 goes beyond Manus by exploiting domain-specific knowledge about Option Alpha to eliminate AI for 80%+ of operations. The core principle: **use the cheapest execution tier that can handle each step.**

### Three Tiers

| Tier | Technology | Cost | Speed | When Used |
|------|-----------|------|-------|-----------|
| 1 | OA Webhooks + Python | $0 | Instant | Recurring tasks (GEX monitoring, triggers) |
| 2 | Playwright browser automation | $0 | 30-60s | Bot creation, config, status checks |
| 3 | Claude Computer Use | $$$ | 5-60 min | Error recovery, novel tasks, first-time setup |

### 5 Beyond-Manus Innovations

1. **Cross-Session Learning DB** (`core/learning_db.py`) — SQLite database persists working selectors, task costs, UI patterns, and error solutions across runs. When Computer Use (Tier 3) discovers a new selector, it's recorded so Playwright (Tier 2) can use it next time. The system literally gets cheaper over time.

2. **Verification Agent** (`core/verifier.py`) — After critical actions, takes ONE screenshot and asks Claude Haiku a yes/no question (~$0.003/check). Catches the "confident but wrong" failure mode without burning Sonnet tokens.

3. **Speculative Execution** (`core/speculative_queue.py`) — Batches multiple Playwright actions before taking a verification screenshot. Instead of click->screenshot->click->screenshot (5 screenshots), it does click->click->click->click->click->screenshot (1 screenshot). 80% fewer screenshots.

4. **Cost-Aware Model Routing** (`core/model_router.py`) — Routes simple navigation to Haiku ($0.25/MTok), medium tasks to Sonnet ($3/MTok), and error recovery to Sonnet with extended thinking. Saves ~40% on AI costs.

5. **Parallel Subtasks** (`core/parallel_executor.py`) — Independent subtasks (e.g., building 5 automations) run simultaneously across multiple Playwright contexts. Subtasks marked with the same `parallel_group` execute concurrently.

### Tier Escalation

When Tier 2 (Playwright) fails — typically because OA changed their UI — it automatically escalates to Tier 3 (Computer Use) for that one step. Computer Use discovers the new selector, which gets recorded in the learning DB. Next time, Tier 2 handles it.

```
Playwright attempt -> SelectorNotFound -> Computer Use handles it
                                             |
                                     Records new selector in DB
                                             |
                                     Next time: Playwright succeeds
```

---

## v2.0: The 5 Manus AI Patterns

[Manus AI](https://manus.im) is the most popular autonomous agent platform. They published lessons from building agents that run complex, multi-step tasks. Options-Claw v2 applies their 5 key architecture patterns to solve specific problems with v1.

### Pattern 1: Planner/Executor Split

**Problem:** v1 dumps the entire task (up to 346 lines) into a single `sampling_loop()` call. By step 40 of 100, Claude forgets the original instructions due to the "lost-in-the-middle" attention problem.

**Solution:** Two agents instead of one:
- **Planner** (cheap, text-only, no Computer Use): Decomposes the task into 5-8 self-contained subtasks. Costs ~$0.01.
- **Executor** (Computer Use, one call per subtask): Each subtask runs in its own isolated context window. If subtask 4 fails, subtasks 1-3 are saved.

### Pattern 2: todo.md Goal Recitation

**Problem:** In long contexts, the model loses track of what it's supposed to do. The original goal drifts out of the attention window.

**Solution:** Before every subtask, rewrite a `todo.md` file and inject it at the END of the prompt. This pushes the global plan into the model's most recent attention window. The todo shows:
- Completed steps (with one-line summaries)
- Current step (with full instructions)
- Upcoming steps (titles only)

### Pattern 3: Context Compression (Screenshot Management)

**Problem:** Screenshots are ~1,500 tokens each. After 20 screenshots, that's 30K tokens of old images clogging the context window, making every API call slower and more expensive.

**Solution:** Only keep the 3 most recent screenshots. Old ones get replaced with `[Screenshot removed]`. This alone saves ~30K tokens on complex tasks.

Also: the system prompt is kept stable and identical across all calls to maximize KV-cache hit rate. Cached input tokens are 10x cheaper on Claude's API.

### Pattern 4: File-Based External Memory

**Problem:** v1 keeps everything in the context window — old results, old screenshots, old tool outputs. Context grows unboundedly.

**Solution:** Save subtask results to files on disk (`/tmp/options_claw_results/`). Only a one-line summary stays in the todo. If the executor needs old results, it can read the file.

### Pattern 5: Error Preservation

**Problem:** When Claude makes a mistake, conventional wisdom says to hide the error and retry cleanly. But this means Claude doesn't learn from the mistake and often repeats it.

**Solution:** Leave errors in context. When retrying a failed subtask, the previous error is appended to the prompt: "Previous attempt failed. The error was: {error}. Please try a different approach." Manus found this significantly improves recovery rates.

---

## Migration Steps

### 1. Fix the API Key (CRITICAL)

The v1 `run-task.ps1` had the Anthropic API key hardcoded in plaintext. This has been fixed.

```powershell
# Create your .env file from the template
cp .env.template .env

# Edit .env and add your API key
notepad .env
# Set: ANTHROPIC_API_KEY=your-api-key-here
```

The `.env` file is excluded from git via `.gitignore`. Both v1 and v2 scripts now read from `.env`.

### 2. Use v2 for Complex Tasks

```powershell
# v2 with the new Manus-style task file
.\Documents\AryanClawWorkspace\run-task-v2.ps1 -TaskFile Documents\AryanClawWorkspace\tasks\credit_scanner_v3_manus.txt

# Preview the plan without executing
.\Documents\AryanClawWorkspace\run-task-v2.ps1 -TaskFile Documents\AryanClawWorkspace\tasks\credit_scanner_v3_manus.txt -PlanOnly
```

### 3. Keep v1 for Simple Tasks

v1 still works and is simpler for quick tasks:

```powershell
.\Documents\AryanClawWorkspace\run-task.ps1 "Check my Option Alpha bots"
.\Documents\AryanClawWorkspace\run-task.ps1 -TaskFile Documents\AryanClawWorkspace\tasks\simple_test.txt
```

---

## v1 vs v2: Task File Writing Style

### v1 Style: Click-by-Click Instructions (346 lines)

```
STEP 1.1: Navigate to Bot Creation
1. From OA Dashboard, click "Bots" in the main navigation
2. Click the "+ New Bot" button (usually top-right)
3. SCREENSHOT: Take screenshot showing the bot creation dialog

STEP 1.2: Configure Basic Bot Settings
Field: Bot Name
Value: Credit Scanner V3 - GEX
...
```

v1 tasks tell Claude exactly WHAT to click. This works but creates huge prompts that blow up the context window.

### v2 Style: Goal-Oriented Instructions (~60 lines)

```
OBJECTIVE:
Build a Paper-mode bot named "Credit Scanner V3 - GEX" for SPY in Option Alpha.

BOT CONFIGURATION:
- Name: Credit Scanner V3 - GEX
- Symbol: SPY
- Mode: PAPER (CRITICAL - verify Paper mode is selected)

AUTOMATIONS TO BUILD (5 total):
1. GEX Regime Router
   - Trigger: Every 30 minutes during market hours
   - Logic: Check current GEX level...
```

v2 tasks describe WHAT to build, not HOW to click. The Planner agent figures out the UI navigation steps.

---

## Cost Comparison

| Metric | v1 (Single-Shot) | v2 (Manus-Style) |
|--------|-------------------|-------------------|
| Context per API call | Grows unboundedly | Fixed per subtask |
| Screenshots in context | 10+ (default) | 3 max |
| System prompt caching | No optimization | Stable prefix = 10x cheaper |
| Failed task recovery | Restart from scratch | Resume from last subtask |
| Estimated cost (complex task) | $3-5+ | $1-2 |

Estimated **60-70% cost savings** on complex tasks (30+ min).

---

## When to Use v1 vs v2

| Use Case | Recommendation |
|----------|---------------|
| Quick task (< 5 min) | v1 `run-task.ps1` |
| Simple task (< 10 steps) | v1 `run-task.ps1` |
| Complex multi-step task | v2 `run-task-v2.ps1` |
| Task that has failed before | v2 (better error recovery) |
| Expensive task you want to optimize | v2 (cost tracking) |
| Just want to see the plan | v2 with `-PlanOnly` |

---

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
Create a `.env` file in the `Documents/AryanClawWorkspace/` directory:
```
ANTHROPIC_API_KEY=your-key-here
```

### "manus_task_runner.py not found"
Make sure `manus_task_runner.py` is in the same directory as `run-task-v2.ps1`.

### Planner returns bad JSON
The planner has a fallback: if JSON parsing fails, it treats the entire task as a single subtask and runs it like v1. You'll see a warning in the output.

### Subtask keeps failing
Check the results files in the container:
```powershell
docker exec aryan-claw-local ls /tmp/options_claw_results/
docker exec aryan-claw-local cat /tmp/options_claw_results/subtask_3_*.txt
```

The error from each attempt is preserved in the result file.

### Container won't start
```powershell
# Remove old container and retry
docker rm -f aryan-claw-local
.\Documents\AryanClawWorkspace\run-task-v2.ps1 "your task"
```

### Want to see what Claude is doing
Open http://localhost:6080 in your browser to watch the virtual desktop in real time.

### Execution log
Full logs are saved inside the container:
```powershell
docker exec aryan-claw-local cat /tmp/options_claw_execution.log
```
