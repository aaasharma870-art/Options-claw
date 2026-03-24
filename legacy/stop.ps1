# ============================================================
# ARYAN-CLAW STOP SCRIPT
# ============================================================
# Stops the Computer Use container
# ============================================================

Write-Host ""
Write-Host "Stopping AryanClaw..." -ForegroundColor Yellow

docker rm -f aryan-claw-local 2>$null | Out-Null

if ($LASTEXITCODE -eq 0 -or $?) {
    Write-Host "✓ Container stopped" -ForegroundColor Green
} else {
    Write-Host "✓ Container was not running" -ForegroundColor Green
}

Write-Host ""
