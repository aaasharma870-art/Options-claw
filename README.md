# Options-Claw: AI-Powered Algorithmic Trading System

**Project by Aryan Sharma**

---

## v3.0: Three-Tier Hybrid Architecture (NEW)

Options-Claw v3 goes beyond Manus AI patterns by using the **cheapest execution tier** for each operation. 80%+ of tasks run at $0 cost.

### Architecture: Three Execution Tiers

```
                     +-------------------+
                     |   Orchestrator    |
                     | (tier routing,    |
                     |  learning DB,     |
                     |  verification)    |
                     +---------+---------+
                               |
              classify_tier()  |
              +----------------+----------------+
              |                |                |
              v                v                v
    +---------+------+ +------+--------+ +-----+---------+
    | TIER 1: Webhooks| | TIER 2: PW   | | TIER 3: CU    |
    | $0, instant     | | $0, fast     | | $$$, smart    |
    | Python + HTTP   | | Playwright   | | Computer Use  |
    | GEX monitoring, | | Bot creation,| | Error recovery|
    | signal triggers | | config, check| | novel tasks   |
    +-----------------+ +--------------+ +---------------+
              |                |                |
              +----------------+----------------+
                               |
                     +---------+---------+
                     |   Learning DB     |
                     | (selectors, costs |
                     |  patterns, fixes) |
                     +-------------------+
```

### Cost Comparison

| Task | v1 (Computer Use) | v2 (Manus) | v3 (Hybrid) |
|------|-------------------|------------|-------------|
| GEX monitoring (per day) | $20-40 | $8-15 | **$0** (webhooks) |
| Create bot | $8-12 | $2-4 | **$0** (Playwright) |
| Morning routine | $1-2 | $0.30-0.60 | **$0.01** (PW + Haiku) |
| Complex novel task | $8-12 | $2-4 | **$0.50-2** (PW + CU fallback) |
| **Monthly (20 tasks/day)** | **$400+** | **$100-200** | **$10-30** |

### 5 Beyond-Manus Innovations

1. **Cross-Session Learning DB** — Remembers working selectors, costs, patterns across runs
2. **Verification Agent** — Haiku ($0.003/check) verifies critical actions via screenshot
3. **Speculative Execution** — Batches 5 actions per screenshot instead of 1:1
4. **Cost-Aware Model Routing** — Haiku for simple nav, Sonnet for complex tasks
5. **Parallel Subtasks** — Independent automations build simultaneously

### Quick Start

```powershell
# 1. Clone and configure
git clone https://github.com/aaasharma870-art/Options-claw.git
cd Options-claw
cp .env.template .env
# Edit .env: set ANTHROPIC_API_KEY and optionally POLYGON_API_KEY

# 2. Run via orchestrator (routes to cheapest tier automatically)
python -c "import asyncio; from core.orchestrator import run_task; asyncio.run(run_task('Check my OA bots'))"

# 3. Or use individual tiers directly:

# Tier 1: GEX regime check (free, no AI)
python tier1_webhooks/gex_regime_engine.py --dry-run

# Tier 2: Discover OA selectors (free, interactive)
pip install playwright && playwright install chromium
python tier2_playwright/selector_discovery.py

# Tier 3: Computer Use fallback (via Docker)
cd tier3_computer_use
.\run-task-v2.ps1 -TaskFile ..\tasks\credit_scanner_v3_manus.txt
```

### Security

- **No API keys in code** — all secrets in `.env` (excluded by `.gitignore`)
- Session cookies saved to `data/session_cookies.json` (gitignored)
- Webhook URLs in `tier1_webhooks/webhook_config.json` (optionally gitignored)

---

## Project Structure

```
Options-claw/
+-- .gitignore, .env.template
+-- README.md, UPGRADE_GUIDE.md
|
+-- core/                         <-- v3 hybrid engine
|   +-- orchestrator.py           Main brain (tier routing)
|   +-- model_router.py           Cost-aware model selection
|   +-- verifier.py               Haiku screenshot verification
|   +-- learning_db.py            Cross-session SQLite memory
|   +-- speculative_queue.py      Batch actions, reduce screenshots
|   +-- parallel_executor.py      Run subtasks simultaneously
|   +-- config.py                 Central config
|
+-- tier1_webhooks/               <-- $0 webhook execution
|   +-- webhook_manager.py        Send/manage OA webhook calls
|   +-- gex_regime_engine.py      GEX calculation + regime classification
|   +-- webhook_config.json       Webhook URLs per automation
|   +-- cron_setup.md             How to schedule
|
+-- tier2_playwright/             <-- $0 browser automation
|   +-- playwright_runner.py      Base class (login, nav, forms)
|   +-- selector_discovery.py     Interactive selector finder
|   +-- ui_selectors.json         All known OA selectors
|   +-- actions/                  Playwright action modules
|
+-- tier3_computer_use/           <-- Smart fallback
|   +-- manus_task_runner.py      v2 Manus-style runner
|   +-- computer_use_fallback.py  Single-step fallback wrapper
|   +-- run-task-v2.ps1           PowerShell launcher
|
+-- tasks/                        <-- Task files
+-- data/                         <-- Runtime state (gitignored)
+-- legacy/                       <-- v1 system (reference)
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| [UPGRADE_GUIDE.md](UPGRADE_GUIDE.md) | v2 Manus patterns + v3 hybrid architecture |
| [tier1_webhooks/cron_setup.md](tier1_webhooks/cron_setup.md) | Deploy GEX engine to cron |
| [legacy/START.md](legacy/START.md) | Original v1 getting started guide |

## Real-World Application: Credit Scanner V3

GEX-based regime classification driving 5 interconnected automations:
- **Positive GEX** -> Iron Condors (range-bound) + Directional spreads
- **Negative GEX** -> Wide directional spreads (trend-following)
- **Transitional** -> No trades, reduce risk
- **Regime Shift Monitor** -> Exit protection every 5 minutes

## Contact

**Aryan Sharma** — [@aaasharma870-art](https://github.com/aaasharma870-art)

## License

Educational and portfolio purposes. Not intended for production trading without additional testing and risk management.
