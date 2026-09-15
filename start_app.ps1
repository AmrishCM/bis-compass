# BIS Compass Application Starter
# Starts both the FastAPI Backend and Vite React Frontend servers

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "   BIS-Compass - AI Indian Standards & Compliance         " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Backend API:  http://127.0.0.1:8002" -ForegroundColor Cyan
Write-Host "API Docs:     http://127.0.0.1:8002/docs" -ForegroundColor Cyan
Write-Host "Frontend UI:  http://localhost:5174" -ForegroundColor Cyan
Write-Host "Press Ctrl+C or Enter to stop the application.`n" -ForegroundColor Yellow

# Start Backend Server
Write-Host "Starting Backend (FastAPI / Uvicorn on port 8002)..." -ForegroundColor DarkCyan
$backendJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location "$dir\backend"
    $env:PYTHONPATH = "$dir\backend"
    & python -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
} -ArgumentList $scriptDir

# Start Frontend Server
Write-Host "Starting Frontend (Vite / React on port 5174)..." -ForegroundColor DarkCyan
$frontendJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location "$dir\frontend"
    & npm run dev
} -ArgumentList $scriptDir

Start-Sleep -Seconds 3

Write-Host "`nServers are running!" -ForegroundColor Green
Write-Host "Open your browser at: http://localhost:5174`n" -ForegroundColor White

try {
    # Keep reading until keypress or interrupt
    [Console]::ReadLine() | Out-Null
} catch {
    # Handle interruption
}

Write-Host "`nStopping servers..." -ForegroundColor Yellow
if ($backendJob) {
    Stop-Job -Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $backendJob -ErrorAction SilentlyContinue
}
if ($frontendJob) {
    Stop-Job -Job $frontendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $frontendJob -ErrorAction SilentlyContinue
}

Write-Host "BIS-Compass stopped successfully." -ForegroundColor Green