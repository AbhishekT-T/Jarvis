# Pane 3: Frontend Specialist (cline)
$Host.UI.RawUI.WindowTitle = "Swarm [3/4] - Frontend Specialist (cline)"
Clear-Host

Write-Host "==========================================================" -ForegroundColor Yellow
Write-Host "       PANE 3: FRONTEND SPECIALIST (cline)                " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Yellow
Write-Host "Worktree: $PWD" -ForegroundColor Gray
Write-Host "Branch:   $(git branch --show-current)" -ForegroundColor Gray
Write-Host ""
Write-Host "Usage:" -ForegroundColor Yellow
Write-Host "  1. Fetch & claim next frontend task:" -ForegroundColor White
Write-Host "     python ../Jarvis/swarm/swarm_helper.py next --role frontend --claim" -ForegroundColor Green
Write-Host ""
Write-Host "  2. Launch cline agent:" -ForegroundColor White
Write-Host "     cline" -ForegroundColor Green
Write-Host ""
Write-Host "  3. When done, commit & mark ready for review:" -ForegroundColor White
Write-Host "     git add . && git commit -m `"feat(frontend): description`"" -ForegroundColor Green
Write-Host "     python ../Jarvis/swarm/swarm_helper.py set-status --id <ID> --status ready_for_review" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Yellow
Write-Host ""
