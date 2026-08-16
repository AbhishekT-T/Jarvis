# Pane 2: Backend Specialist (opencode)
$Host.UI.RawUI.WindowTitle = "Swarm [2/4] - Backend Specialist (opencode)"
Clear-Host

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "       PANE 2: BACKEND SPECIALIST (opencode)              " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Worktree: $PWD" -ForegroundColor Gray
Write-Host "Branch:   $(git branch --show-current)" -ForegroundColor Gray
Write-Host ""
Write-Host "Usage:" -ForegroundColor Yellow
Write-Host "  1. Fetch & claim next backend task:" -ForegroundColor White
Write-Host "     python ../Jarvis/swarm/swarm_helper.py next --role backend --claim" -ForegroundColor Green
Write-Host ""
Write-Host "  2. Launch opencode agent:" -ForegroundColor White
Write-Host "     opencode" -ForegroundColor Green
Write-Host ""
Write-Host "  3. When done, commit & mark ready for review:" -ForegroundColor White
Write-Host "     git add . && git commit -m `"feat(backend): description`"" -ForegroundColor Green
Write-Host "     python ../Jarvis/swarm/swarm_helper.py set-status --id <ID> --status ready_for_review" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""
