# ============================================================
# OPTIONS-CLAW v2.0 - MANUS-STYLE TASK RUNNER
# ============================================================
# Applies 5 Manus AI patterns for reliable, cheap execution:
#   1. Planner/executor split (no more single-shot dumps)
#   2. todo.md goal recitation (no more losing track)
#   3. File-based memory (results in files, not context)
#   4. Context compression (old screenshots dropped)
#   5. Error preservation (Claude learns from mistakes)
#
# Usage:
#   .\run-task-v2.ps1 "Build a credit scanner bot"
#   .\run-task-v2.ps1 -TaskFile tasks\credit_scanner_v3_optimized.txt
#   .\run-task-v2.ps1 -TaskFile tasks\morning_routine.txt -PlanOnly
# ============================================================

param(
    [Parameter(Mandatory=$false, Position=0)]
    [string]$Task,

    [Parameter(Mandatory=$false)]
    [string]$TaskFile,

    [Parameter(Mandatory=$false)]
    [switch]$PlanOnly  # Just show the plan, don't execute
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  OPTIONS-CLAW v2.0 (MANUS-STYLE AGENT)" -ForegroundColor Cyan
Write-Host "  5 patterns: plan -> track -> compress -> save -> learn" -ForegroundColor DarkCyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# STEP 1: Validate input
# ============================================================

if (-not $Task -and -not $TaskFile) {
    Write-Host "ERROR: Provide a task or task file" -ForegroundColor Red
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host '  .\run-task-v2.ps1 "Check my Option Alpha bots"' -ForegroundColor White
    Write-Host '  .\run-task-v2.ps1 -TaskFile tasks\credit_scanner_v3_optimized.txt' -ForegroundColor White
    Write-Host '  .\run-task-v2.ps1 -TaskFile tasks\morning_routine.txt -PlanOnly' -ForegroundColor White
    Write-Host ""
    exit 1
}

if ($TaskFile) {
    if (-not (Test-Path $TaskFile)) {
        Write-Host "ERROR: Task file not found: $TaskFile" -ForegroundColor Red
        exit 1
    }
    $Task = Get-Content $TaskFile -Raw
    Write-Host "[OK] Loaded task from: $TaskFile" -ForegroundColor Green
}

$taskLines = ($Task.Trim() -split "`n").Count
Write-Host "[OK] Task loaded: $taskLines lines" -ForegroundColor Green

# ============================================================
# STEP 2: Check Docker
# ============================================================

Write-Host ""
Write-Host "[1/4] Checking Docker..." -ForegroundColor Yellow

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "      Docker not found. Please install Docker Desktop." -ForegroundColor Red
    exit 1
}

$dockerInfo = docker info 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "      Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "      Docker is running" -ForegroundColor Green

# ============================================================
# STEP 3: Ensure Computer Use container is running
# ============================================================

Write-Host ""
Write-Host "[2/4] Checking Computer Use container..." -ForegroundColor Yellow

$containerRunning = docker ps --filter "name=aryan-claw-local" --format "{{.Names}}" 2>$null
if ($containerRunning -ne "aryan-claw-local") {
    Write-Host "      Starting Computer Use container (~15 seconds)..." -ForegroundColor Yellow

    docker rm -f aryan-claw-local 2>$null | Out-Null

    # Read API key from env or .env file
    $apiKey = $env:ANTHROPIC_API_KEY
    if (-not $apiKey) {
        $envFile = Join-Path $PSScriptRoot ".env"
        if (Test-Path $envFile) {
            Get-Content $envFile | ForEach-Object {
                if ($_ -match "^ANTHROPIC_API_KEY=(.+)$") {
                    $apiKey = $matches[1].Trim()
                }
            }
        }
    }
    if (-not $apiKey) {
        Write-Host "      ERROR: Set ANTHROPIC_API_KEY in environment or .env file" -ForegroundColor Red
        exit 1
    }

    $anthropicDir = Join-Path $env:USERPROFILE ".anthropic"
    $workspaceDir = Join-Path $env:USERPROFILE "Documents\AryanClawWorkspace"

    if (-not (Test-Path $anthropicDir)) { New-Item -ItemType Directory -Force -Path $anthropicDir | Out-Null }
    if (-not (Test-Path $workspaceDir)) { New-Item -ItemType Directory -Force -Path $workspaceDir | Out-Null }

    docker run `
        --name aryan-claw-local `
        --shm-size=8g `
        --cpus=8 `
        --memory=16g `
        --restart=unless-stopped `
        -e "ANTHROPIC_API_KEY=$apiKey" `
        -e "API_RESPONSE_CALLBACK_TIMEOUT_SECONDS=0" `
        -e "MAX_RESPONSE_LEN=32000" `
        -v "${anthropicDir}:/home/computeruse/.anthropic" `
        -v "${workspaceDir}:/home/computeruse/Desktop" `
        -p 5900:5900 `
        -p 8501:8501 `
        -p 6080:6080 `
        -p 8080:8080 `
        -e WIDTH=2560 `
        -e HEIGHT=1440 `
        -d `
        ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest | Out-Null

    if ($LASTEXITCODE -ne 0) {
        Write-Host "      Failed to start container" -ForegroundColor Red
        exit 1
    }

    Start-Sleep -Seconds 15
    Write-Host "      Container started" -ForegroundColor Green
} else {
    Write-Host "      Container already running" -ForegroundColor Green
}

# ============================================================
# STEP 4: Copy runner + task into container, execute
# ============================================================

Write-Host ""
Write-Host "[3/4] Preparing Manus-style runner..." -ForegroundColor Yellow

# Copy the new runner into the container
$runnerPath = Join-Path $PSScriptRoot "manus_task_runner.py"
if (-not (Test-Path $runnerPath)) {
    Write-Host "      ERROR: manus_task_runner.py not found in $PSScriptRoot" -ForegroundColor Red
    Write-Host "      Make sure manus_task_runner.py is in the same directory as this script" -ForegroundColor Yellow
    exit 1
}

docker cp $runnerPath aryan-claw-local:/tmp/manus_task_runner.py 2>$null

# Write task to temp file and copy
$tempTaskFile = Join-Path $env:TEMP "aryan_claw_task_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
$Task | Out-File -FilePath $tempTaskFile -Encoding UTF8 -NoNewline
docker cp $tempTaskFile aryan-claw-local:/tmp/task.txt 2>$null

Write-Host "      Runner and task loaded" -ForegroundColor Green

# ============================================================
# STEP 5: Execute
# ============================================================

Write-Host ""
Write-Host "[4/4] Executing with Manus patterns..." -ForegroundColor Yellow
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Green
Write-Host "  EXECUTION LOG" -ForegroundColor Green
Write-Host "  Desktop viewer: http://localhost:6080" -ForegroundColor DarkGray
Write-Host "=======================================================" -ForegroundColor Green
Write-Host ""

$startTime = Get-Date

try {
    if ($PlanOnly) {
        # Just show the plan
        docker exec -i aryan-claw-local bash -c "cd /tmp && python3 -c `"
import asyncio, os, json
os.environ.setdefault('ANTHROPIC_API_KEY', os.popen('echo \`$ANTHROPIC_API_KEY').read().strip())
from manus_task_runner import plan_task
subtasks = asyncio.run(plan_task(open('task.txt').read(), os.environ['ANTHROPIC_API_KEY']))
print(json.dumps(subtasks, indent=2))
`""
    } else {
        docker exec -i aryan-claw-local bash -c "cd /tmp && python3 manus_task_runner.py task.txt"
    }

    $exitCode = $LASTEXITCODE
    $duration = (Get-Date) - $startTime

    Write-Host ""
    Write-Host "-------------------------------------------------------" -ForegroundColor DarkGray

    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "=======================================================" -ForegroundColor Green
        Write-Host "  TASK COMPLETED in $([math]::Round($duration.TotalMinutes, 1)) minutes" -ForegroundColor Green
        Write-Host "=======================================================" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "=======================================================" -ForegroundColor Red
        Write-Host "  TASK FAILED (exit code: $exitCode)" -ForegroundColor Red
        Write-Host "=======================================================" -ForegroundColor Red
    }

} finally {
    if (Test-Path $tempTaskFile) {
        Remove-Item $tempTaskFile -Force
    }
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  View results: docker exec aryan-claw-local cat /tmp/options_claw_todo.md" -ForegroundColor White
Write-Host "  View details: docker exec aryan-claw-local ls /tmp/options_claw_results/" -ForegroundColor White
Write-Host "  Desktop view: http://localhost:6080" -ForegroundColor White
Write-Host "  Run another:  .\run-task-v2.ps1 `"your next task`"" -ForegroundColor White
Write-Host ""
