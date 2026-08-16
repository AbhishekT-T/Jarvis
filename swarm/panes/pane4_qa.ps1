# Pane 4: QA & Ponytail Reviewer (kilo)
$Host.UI.RawUI.WindowTitle = "Swarm [4/4] - QA & Ponytail Reviewer (kilo)"
Clear-Host

Write-Host "==========================================================" -ForegroundColor Magenta
Write-Host "     PANE 4: QA & PONYTAIL WORKER (Autonomous Mode)       " -ForegroundColor Magenta
Write-Host "==========================================================" -ForegroundColor Magenta
Write-Host "Worktree: $PWD" -ForegroundColor Gray
Write-Host "Branch:   $(git branch --show-current)" -ForegroundColor Gray
Write-Host ""
Write-Host "[*] Starting QA / Ponytail Reviewer daemon..." -ForegroundColor Magenta
Write-Host ""

python ..\Jarvis\swarm\worker.py --role qa --tool kilo --worktree $PWD
