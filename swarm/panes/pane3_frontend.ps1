# Pane 3: Frontend Specialist (cline)
$Host.UI.RawUI.WindowTitle = "Swarm [3/4] - Frontend Specialist (cline)"
Clear-Host

Write-Host "==========================================================" -ForegroundColor Yellow
Write-Host "       PANE 3: FRONTEND WORKER (Autonomous Mode)          " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Yellow
Write-Host "Worktree: $PWD" -ForegroundColor Gray
Write-Host "Branch:   $(git branch --show-current)" -ForegroundColor Gray
Write-Host ""
Write-Host "[*] Starting Frontend autonomous worker daemon..." -ForegroundColor Yellow
Write-Host ""

python ..\Jarvis\swarm\worker.py --role frontend --tool cline --worktree $PWD
