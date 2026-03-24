# ============================================================
# ARYAN-CLAW SIMPLE TASK RUNNER
# ============================================================
# Run any task with Claude Computer Use - NO disconnects!
#
# Usage:
#   .\run-task.ps1 "Check my Option Alpha bots"
#   .\run-task.ps1 -TaskFile my_task.txt
#
# This script:
#   1. Ensures Computer Use container is running
#   2. Executes your task using the direct API (no Streamlit)
#   3. Shows real-time progress in terminal
#   4. Works for tasks of ANY length (no timeouts)
# ============================================================

param(
    [Parameter(Mandatory=$false, Position=0)]
    [string]$Task,

    [Parameter(Mandatory=$false)]
    [string]$TaskFile
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ARYAN-CLAW TASK RUNNER" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# STEP 1: Validate input
# ============================================================

if (-not $Task -and -not $TaskFile) {
    Write-Host "ERROR: You must provide either a task or a task file" -ForegroundColor Red
    Write-Host ""
    Write-Host "Usage examples:" -ForegroundColor Yellow
    Write-Host '  .\run-task.ps1 "Check my Option Alpha bots"' -ForegroundColor White
    Write-Host '  .\run-task.ps1 -TaskFile tasks\morning_routine.txt' -ForegroundColor White
    Write-Host ""
    exit 1
}

# Read task from file if provided
if ($TaskFile) {
    if (-not (Test-Path $TaskFile)) {
        Write-Host "ERROR: Task file not found: $TaskFile" -ForegroundColor Red
        exit 1
    }
    $Task = Get-Content $TaskFile -Raw
    Write-Host "[✓] Loaded task from: $TaskFile" -ForegroundColor Green
}

# Show task preview
$taskPreview = if ($Task.Length -gt 100) { $Task.Substring(0, 100) + "..." } else { $Task }
Write-Host ""
Write-Host "TASK: $taskPreview" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# STEP 2: Check Docker
# ============================================================

Write-Host "[1/4] Checking Docker..." -ForegroundColor Yellow

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "      ✗ Docker not found. Please install Docker Desktop." -ForegroundColor Red
    exit 1
}

$dockerInfo = docker info 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "      ✗ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host "      ✓ Docker is running" -ForegroundColor Green

# ============================================================
# STEP 3: Ensure Computer Use container is running
# ============================================================

Write-Host ""
Write-Host "[2/4] Checking Computer Use container..." -ForegroundColor Yellow

$containerRunning = docker ps --filter "name=aryan-claw-local" --format "{{.Names}}" 2>$null
if ($containerRunning -ne "aryan-claw-local") {
    Write-Host "      Computer Use container not running. Starting it now..." -ForegroundColor Yellow
    Write-Host ""

    # Stop old container if exists
    docker rm -f aryan-claw-local 2>$null | Out-Null

    # Read API key from environment or .env file (see .env.template)
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
        Write-Host "      Copy .env.template to .env and add your key" -ForegroundColor Yellow
        exit 1
    }

    $anthropicDir = Join-Path $env:USERPROFILE ".anthropic"
    $workspaceDir = Join-Path $env:USERPROFILE "Documents\AryanClawWorkspace"

    # Create directories if needed
    if (-not (Test-Path $anthropicDir)) {
        New-Item -ItemType Directory -Force -Path $anthropicDir | Out-Null
    }
    if (-not (Test-Path $workspaceDir)) {
        New-Item -ItemType Directory -Force -Path $workspaceDir | Out-Null
    }

    Write-Host "      Starting Computer Use container (this takes ~15 seconds)..." -ForegroundColor Yellow

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
        Write-Host "      ✗ Failed to start Computer Use container" -ForegroundColor Red
        exit 1
    }

    Write-Host "      Waiting for container to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15

    Write-Host "      ✓ Computer Use container started" -ForegroundColor Green
} else {
    Write-Host "      ✓ Computer Use container already running" -ForegroundColor Green
}

# ============================================================
# STEP 4: Prepare task file
# ============================================================

Write-Host ""
Write-Host "[3/4] Preparing task..." -ForegroundColor Yellow

# Create temp task file
$tempTaskFile = Join-Path $env:TEMP "aryan_claw_task_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
$Task | Out-File -FilePath $tempTaskFile -Encoding UTF8 -NoNewline

Write-Host "      ✓ Task prepared" -ForegroundColor Green

# ============================================================
# STEP 5: Execute task
# ============================================================

Write-Host ""
Write-Host "[4/4] Executing task..." -ForegroundColor Yellow
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  TASK EXECUTION LOG" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "TIP: To watch the AI work visually, open: http://localhost:6080" -ForegroundColor DarkGray
Write-Host ""
Write-Host "───────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

try {
    # Copy the direct task runner script into the container
    docker cp "direct_task_runner.py" aryan-claw-local:/tmp/direct_task_runner.py 2>$null

    # Copy the task file into the container
    docker cp $tempTaskFile aryan-claw-local:/tmp/task.txt 2>$null

    # Execute the task directly (bypasses Streamlit - no disconnects!)
    docker exec -i aryan-claw-local bash -c "cd /tmp && python3 direct_task_runner.py task.txt"

    $exitCode = $LASTEXITCODE

    Write-Host ""
    Write-Host "───────────────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host ""

    if ($exitCode -eq 0) {
        Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host "  TASK COMPLETED SUCCESSFULLY!" -ForegroundColor Green
        Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
    } else {
        Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Red
        Write-Host "  TASK FAILED (exit code: $exitCode)" -ForegroundColor Red
        Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Red
    }

    Write-Host ""

} finally {
    # Cleanup temp file
    if (Test-Path $tempTaskFile) {
        Remove-Item $tempTaskFile -Force
    }
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  - To run another task: .\run-task.ps1 `"your next task`"" -ForegroundColor White
Write-Host "  - To view the desktop: http://localhost:6080" -ForegroundColor White
Write-Host "  - To stop the container: docker rm -f aryan-claw-local" -ForegroundColor White
Write-Host ""
