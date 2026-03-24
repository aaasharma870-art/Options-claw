# 🚀 ARYAN-CLAW - START HERE

**Your autonomous AI assistant for complex tasks - SIMPLIFIED & FIXED**

---

## ⚡ Quick Start (30 seconds)

```powershell
# Run any task - the system auto-starts if needed:
.\run-task.ps1 "Check my Option Alpha bots"
```

**That's it!** The script will:
- ✅ Start the Computer Use container automatically if needed
- ✅ Execute your task using Claude's Computer Use API
- ✅ Show real-time progress in the terminal
- ✅ **Works for tasks of ANY length** (no disconnections!)

---

## 📋 How It Works

### OLD SYSTEM ❌ (Had Problems)
- Complex orchestrator dashboard
- Streamlit web interface that disconnected on long tasks
- Multiple confusing startup scripts
- Tasks appeared to run but didn't actually execute

### NEW SYSTEM ✅ (Simple & Works)
- **One simple command:** `.\run-task.ps1 "your task"`
- **Direct API execution** - bypasses Streamlit entirely
- **No disconnections** - can run for hours
- **Real-time terminal output** - see exactly what's happening
- **Actually executes** - uses real Computer Use API

---

## 🎯 Usage Examples

### Simple Command
```powershell
.\run-task.ps1 "Check my Option Alpha bots"
```

### From a Task File
```powershell
.\run-task.ps1 -TaskFile tasks\morning_routine.txt
```

### Complex Multi-Step Task
```powershell
.\run-task.ps1 "Run my morning routine: check all bots, check Alpaca positions, analyze SPY and QQQ charts, give me a complete summary"
```

---

## 📁 Pre-Made Task Files

We've created common task files for you in the `tasks\` folder:

| File | What It Does |
|------|-------------|
| **[simple_test.txt](tasks/simple_test.txt)** | Quick test - opens Google to verify system works |
| **[check_bots.txt](tasks/check_bots.txt)** | Checks all Option Alpha bot statuses and P&L |
| **[morning_routine.txt](tasks/morning_routine.txt)** | Complete morning routine - bots, positions, charts |
| **[create_iron_condor_spy.txt](tasks/create_iron_condor_spy.txt)** | Creates an Iron Condor bot with specific settings |

**Usage:**
```powershell
.\run-task.ps1 -TaskFile tasks\simple_test.txt
.\run-task.ps1 -TaskFile tasks\morning_routine.txt
```

---

## 🖥️ Watch the AI Work Visually

While a task is running, you can **watch the AI control the desktop** in real-time:

**Open in browser:** http://localhost:6080

You'll see:
- The Firefox browser opening
- Mouse moving and clicking
- Forms being filled out
- Screenshots being taken

**Note:** The task keeps running even if you close the viewer!

---

## 💡 What You Can Do

### Option Alpha Tasks
```
- "Check my Option Alpha bots"
- "Create an Iron Condor bot for SPY with $500 max risk, 30-45 DTE"
- "Pause all my bots"
- "Change VIX filter on [Bot Name] to 15-22"
- "Show me all positions in my Option Alpha bots"
```

### Alpaca Tasks
```
- "Check my Alpaca positions"
- "What's my Alpaca account balance?"
- "Show me today's P&L on Alpaca"
```

### TradingView Analysis
```
- "Pull up SPY chart on TradingView with 20/50 EMA and RSI"
- "Analyze QQQ chart and tell me key support/resistance levels"
- "Compare SPY on 1H, 4H, and daily timeframes"
```

### Complex Multi-Step
```
- "Morning routine: check bots, check positions, analyze SPY/QQQ/VIX, summarize"
- "Create Iron Condor for QQQ, then verify it's active and screenshot it"
- "Check all my bots, if any are showing losses over 50%, pause them"
```

---

## 🛠️ Commands

### Run a Task
```powershell
# Inline task
.\run-task.ps1 "your task here"

# From file
.\run-task.ps1 -TaskFile path\to\task.txt
```

### Stop the Container
```powershell
.\stop.ps1
```

### Check Container Status
```powershell
docker ps | grep aryan-claw
```

### View Container Logs
```powershell
docker logs aryan-claw-local --tail 50
```

### View the Desktop
- **noVNC (browser):** http://localhost:6080
- **Streamlit interface:** http://localhost:8080 (optional, not needed for tasks)

---

## 🎬 What Happens When You Run a Task

```
1. Script checks if Docker is running ✓
2. Script checks if Computer Use container is running
   - If not running → starts it automatically
   - If already running → uses existing container
3. Your task is sent to the container
4. Claude AI executes the task step-by-step:
   - Opens browser
   - Navigates to websites
   - Clicks, types, reads
   - Takes screenshots
   - Thinks and adapts
5. Real-time progress shown in terminal with emojis:
   💭 Claude thinking
   🖱️  Mouse movement
   👆 Clicking
   ⌨️  Typing
   📸 Screenshot
   ✓ Success
6. Task completes - you get a summary!
```

---

## ⚙️ Settings & Configuration

The system is configured for **maximum performance**:

- **8GB shared memory** - handles complex web pages
- **8 CPU cores** - fast execution
- **16GB RAM** - no memory issues
- **2560x1440 resolution** - see everything clearly
- **No timeout limits** - tasks can run for hours
- **32K max response** - handles complex outputs

You don't need to change anything - it just works!

---

## 🐛 Troubleshooting

### "Docker not found"
**Fix:** Install Docker Desktop for Windows
- Download: https://www.docker.com/products/docker-desktop/

### "Docker is not running"
**Fix:** Start Docker Desktop application

### "Container failed to start"
**Fix:** Check Docker Desktop has enough resources allocated
- Right-click Docker Desktop → Settings → Resources
- Ensure: 8GB RAM, 4+ CPUs allocated

### Task seems stuck
- Open http://localhost:6080 to see what's happening
- Check logs: `docker logs aryan-claw-local --tail 50`
- The AI might be waiting for a page to load

### Need to login to a website
Some tasks require you to be logged in (Option Alpha, Alpaca, etc.)

**One-time setup:**
1. Open http://localhost:6080 (or http://localhost:8080)
2. Login to the website manually
3. The session stays active - future tasks will work automatically

**Security:** The AI cannot see or type passwords - you must login manually

---

## 📊 Cost Estimate

Tasks use Claude's Computer Use API - costs vary by complexity:

| Task Type | Approx Cost | Example |
|-----------|-------------|---------|
| Simple check | $0.10 - $0.30 | "Check my bots" |
| Medium task | $0.50 - $1.50 | "Create a bot" |
| Complex multi-step | $1.00 - $5.00 | "Morning routine" |

**Monthly estimate (20 tasks/day):** ~$200-400

**Tips to reduce costs:**
- Batch related tasks together
- Use task files for repeated workflows
- Be specific in your prompts (reduces back-and-forth)

---

## 🔗 Important Links

- **View AI Desktop:** http://localhost:6080
- **Streamlit Interface:** http://localhost:8080 (optional, not recommended for long tasks)
- **Docker Desktop:** https://www.docker.com/products/docker-desktop/

---

## 📚 Where's Everything Else?

### Old Scripts (Archived)
All the old confusing scripts have been moved to `archive/old_scripts/`

If you need the orchestrator dashboard or other advanced features, they're still there, but this new simple system is **recommended** for reliability.

### Documentation (Still Useful)
- [README.md](README.md) - Original overview
- [QUICK_START.md](QUICK_START.md) - Orchestrator dashboard guide (old system)
- [HOW_TO_RUN_LONG_TASKS.md](HOW_TO_RUN_LONG_TASKS.md) - Background on the direct runner approach

---

## 🎯 Next Steps

### First Time Setup (5 minutes)
1. Make sure Docker Desktop is installed and running
2. Test the system:
   ```powershell
   .\run-task.ps1 -TaskFile tasks\simple_test.txt
   ```
3. Watch it work at http://localhost:6080
4. Once the test completes, you're ready!

### Daily Usage
```powershell
# Morning routine
.\run-task.ps1 -TaskFile tasks\morning_routine.txt

# Quick checks
.\run-task.ps1 "Check my bots"

# Custom tasks
.\run-task.ps1 "Your custom task here"
```

---

## 💪 Why This System Is Better

| Feature | Old System | New System |
|---------|-----------|------------|
| **Disconnections** | Frequent on long tasks ❌ | Never ✅ |
| **Complexity** | 20+ scripts, confusing ❌ | 1 simple script ✅ |
| **Actually Works** | Simulated execution ❌ | Real API calls ✅ |
| **Task Length** | Limited by timeouts ❌ | Unlimited ✅ |
| **Setup** | Multiple steps ❌ | Auto-starts ✅ |
| **Progress Tracking** | Web dashboard only ❌ | Real-time terminal ✅ |
| **Reliability** | Crashes, freezes ❌ | Rock solid ✅ |

---

## ✅ You're Ready!

**One command is all you need:**

```powershell
.\run-task.ps1 "Check my Option Alpha bots"
```

The system handles everything else automatically.

**Happy automating! 🚀**

---

## ❓ Questions?

- Check container is running: `docker ps`
- View logs: `docker logs aryan-claw-local`
- Watch visually: http://localhost:6080
- Stop everything: `.\stop.ps1`

Everything is designed to be simple and just work. If you hit any issues, the error messages will guide you to the solution.
