# ⚡ AryanClaw Quick Reference

## 🎯 Main Command

```powershell
.\run-task.ps1 "your task here"
```

## 📁 Use Pre-Made Tasks

```powershell
.\run-task.ps1 -TaskFile tasks\simple_test.txt
.\run-task.ps1 -TaskFile tasks\check_bots.txt
.\run-task.ps1 -TaskFile tasks\morning_routine.txt
.\run-task.ps1 -TaskFile tasks\create_iron_condor_spy.txt
```

## 🛠️ Common Commands

| Command | What It Does |
|---------|-------------|
| `.\run-task.ps1 "task"` | Run a task |
| `.\stop.ps1` | Stop the container |
| `docker ps` | Check if container is running |
| `docker logs aryan-claw-local --tail 50` | View recent logs |

## 🌐 URLs

| URL | Purpose |
|-----|---------|
| http://localhost:6080 | Watch AI work visually |
| http://localhost:8080 | Streamlit interface (optional) |

## 📝 Example Tasks

### Option Alpha
```powershell
.\run-task.ps1 "Check my Option Alpha bots"
.\run-task.ps1 "Create Iron Condor for SPY with $500 max risk, 30-45 DTE"
.\run-task.ps1 "Pause all my bots"
```

### Alpaca
```powershell
.\run-task.ps1 "Check my Alpaca positions"
.\run-task.ps1 "What's my account balance?"
```

### TradingView
```powershell
.\run-task.ps1 "Show me SPY chart with 20/50 EMA and RSI"
.\run-task.ps1 "Analyze QQQ support and resistance levels"
```

### Multi-Step
```powershell
.\run-task.ps1 "Morning routine: check bots, positions, and SPY/QQQ charts"
```

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Docker not found" | Install Docker Desktop |
| "Docker not running" | Start Docker Desktop |
| Task seems stuck | Check http://localhost:6080 |
| Need to login | Open http://localhost:6080, login manually |

## 📊 Progress Indicators

While task runs, you'll see:
- 💭 Claude thinking
- 🖱️ Mouse movement
- 👆 Clicking
- ⌨️ Typing
- 📸 Screenshot
- ✓ Success
- ⚡ API call

## 💰 Rough Costs

- Simple: $0.10-$0.30
- Medium: $0.50-$1.50
- Complex: $1.00-$5.00

## 📚 Full Docs

- **[START.md](START.md)** - Complete guide
- **[WHATS_FIXED.md](WHATS_FIXED.md)** - What changed
