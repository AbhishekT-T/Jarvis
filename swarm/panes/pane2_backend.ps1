# Pane 2: Backend Specialist (opencode)
$Host.UI.RawUI.WindowTitle = "Swarm [2/4] - Backend Specialist (opencode)"
Clear-Host

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "       PANE 2: BACKEND WORKER (Autonomous Mode)           " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Worktree: $PWD" -ForegroundColor Gray
Write-Host "Branch:   $(git branch --show-current)" -ForegroundColor Gray
Write-Host ""
Write-Host "[*] Starting Backend autonomous worker daemon..." -ForegroundColor Green
Write-Host ""

python ..\Jarvis\swarm\worker.py --role backend --tool opencode --worktree $PWD
