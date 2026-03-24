# Options-Claw: AI-Powered Algorithmic Trading System

**Project by Aryan Sharma**

---

## v2.0: Manus-Style Architecture (NEW)

Options-Claw v2 applies 5 patterns from [Manus AI](https://manus.im) to make autonomous trading bot building reliable, cheap, and recoverable.

### Architecture

```
                         +-----------------+
                         |   Task File     |
                         | (goal-oriented) |
                         +--------+--------+
                                  |
                                  v
                    +-------------+-------------+
                    |     PLANNER AGENT          |
                    |  (text-only, ~$0.01)       |
                    |  Decomposes into subtasks  |
                    +-------------+-------------+
                                  |
                         JSON subtask list
                                  |
              +-------------------+-------------------+
              |                   |                   |
              v                   v                   v
     +--------+------+  +--------+------+  +--------+------+
     | EXECUTOR #1   |  | EXECUTOR #2   |  | EXECUTOR #N   |
     | (Computer Use)|  | (Computer Use)|  | (Computer Use)|
     | Isolated ctx  |  | Isolated ctx  |  | Isolated ctx  |
     +--------+------+  +--------+------+  +--------+------+
              |                   |                   |
              v                   v                   v
     +--------+------+  +--------+------+  +--------+------+
     | Result file   |  | Result file   |  | Result file   |
     +---------------+  +---------------+  +---------------+
              |                   |                   |
              +-------------------+-------------------+
                                  |
                                  v
                         +--------+--------+
                         |   todo.md       |
                         | (goal recitation|
                         |  updated each   |
                         |  subtask)       |
                         +-----------------+
```

### Quick Start (v2)

```powershell
# 1. Clone and set up API key
git clone https://github.com/aaasharma870-art/Options-claw.git
cd Options-claw
cp .env.template .env
# Edit .env with your Anthropic API key

# 2. Run a task with Manus-style execution
cd Documents\AryanClawWorkspace
.\run-task-v2.ps1 -TaskFile tasks\credit_scanner_v3_manus.txt

# 3. Preview the plan without executing
.\run-task-v2.ps1 -TaskFile tasks\credit_scanner_v3_manus.txt -PlanOnly

# 4. Watch it work (optional)
# Open http://localhost:6080 in browser
```

### 5 Manus Patterns Applied

| Pattern | Problem Solved | Impact |
|---------|---------------|--------|
| Planner/Executor split | Goal drift on long tasks | Each subtask has fresh context |
| todo.md goal recitation | Forgetting instructions mid-task | Plan always in recent attention |
| Context compression | Screenshots bloat context | 3 max instead of unbounded |
| File-based memory | Results clog context window | Saved to disk, summaries in context |
| Error preservation | Repeating same mistakes | Errors kept so Claude learns |

### Security Note

**IMPORTANT:** Create a `.env` file from `.env.template` before running. Never commit API keys.

See [UPGRADE_GUIDE.md](UPGRADE_GUIDE.md) for full details on v2 architecture, migration, and cost savings.

---

## v1.0: Direct API Execution (Legacy)

The original system that bypasses Streamlit and calls the Computer Use API directly. Still works for simple tasks.

```powershell
cd Documents\AryanClawWorkspace
.\run-task.ps1 "Check my Option Alpha bots"
.\run-task.ps1 -TaskFile tasks\simple_test.txt
```

### What It Does

Options-Claw is an AI agent that:
- Autonomously builds complex trading bots in Option Alpha with 50+ configuration parameters
- Monitors real-time market data using Gamma Exposure (GEX) analysis for regime classification
- Executes sophisticated strategies including Iron Condors and directional credit spreads
- Manages risk automatically using position sizing, stop losses, and regime shift detection

### System Architecture (v1)

```
User -> PowerShell Script (run-task.ps1)
            |
            v
       Docker Container
       +-> Python Task Runner (direct_task_runner.py)
       +-> Anthropic SDK (sampling_loop)
       +-> Virtual Desktop (Firefox + Option Alpha)
            |
            v
       Claude API (Computer Use)
```

### Performance (v1)

| Metric | Before Optimization | After Optimization |
|--------|---------------------|-------------------|
| Task Success Rate | 20% | 95% |
| Max Task Duration | 5 minutes | Unlimited |
| Disconnection Rate | 60-90% | 0% |

---

## Real-World Application: Credit Scanner V3

### GEX-Based Regime Classification

- **Regime A (Positive GEX):** Market is sticky -> Trade Iron Condors
- **Regime B (Negative GEX):** Trends accelerate -> Trade directional spreads
- **Regime C (Transitional):** No clear structure -> No trades (risk management)

### 5 Automations

1. **GEX Regime Router** - Runs every 30 min, classifies market
2. **Positive GEX - Iron Condor** - Profits from range-bound behavior
3. **Positive GEX - Directional** - Mild directional bias trades
4. **Negative GEX - Directional** - Trend-following trades
5. **Regime Shift Monitor** - Exit protection, runs every 5 min

---

## Documentation

| Document | Purpose |
|----------|---------|
| [UPGRADE_GUIDE.md](UPGRADE_GUIDE.md) | v2 architecture, migration, cost savings |
| [START.md](Documents/AryanClawWorkspace/START.md) | Getting started guide |
| [WHATS_FIXED.md](Documents/AryanClawWorkspace/WHATS_FIXED.md) | Technical deep dive on all optimizations |
| [QUICK_REFERENCE.md](Documents/AryanClawWorkspace/QUICK_REFERENCE.md) | Command cheat sheet |

## Prerequisites

- Windows 10/11 with PowerShell
- Docker Desktop installed
- Anthropic API key (set in `.env` file)

---

## Contact

**Aryan Sharma**
- GitHub: [@aaasharma870-art](https://github.com/aaasharma870-art)

## License

This project is for educational and portfolio purposes. Not intended for production trading use without extensive additional testing and risk management.
