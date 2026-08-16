# Pane 4: QA & Ponytail Reviewer (kilo)
$Host.UI.RawUI.WindowTitle = "Swarm [4/4] - QA & Ponytail Reviewer (kilo)"
Clear-Host

Write-Host "==========================================================" -ForegroundColor Magenta
Write-Host "     PANE 4: QA & PONYTAIL REVIEWER (kilo)                " -ForegroundColor Magenta
Write-Host "==========================================================" -ForegroundColor Magenta
Write-Host "Worktree: $PWD" -ForegroundColor Gray
Write-Host "Branch:   $(git branch --show-current)" -ForegroundColor Gray
Write-Host ""
Write-Host "Usage:" -ForegroundColor Yellow
Write-Host "  1. Check tasks waiting for QA review:" -ForegroundColor White
Write-Host "     python ../Jarvis/swarm/swarm_helper.py list --status ready_for_review" -ForegroundColor Green
Write-Host ""
Write-Host "  2. Review diffs with Ponytail to delete bloat:" -ForegroundColor White
Write-Host "     kilo `"ponytail-review git diff agent/backend against main`"" -ForegroundColor Green
Write-Host ""
Write-Host "  3. Merge approved branch to main:" -ForegroundColor White
Write-Host "     git checkout main && git merge agent/backend --no-ff" -ForegroundColor Green
Write-Host "     python ../Jarvis/swarm/swarm_helper.py set-status --id <ID> --status completed" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Magenta
Write-Host ""
