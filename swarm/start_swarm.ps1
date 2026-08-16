<#
.SYNOPSIS
    Starts the 4-Agent Hybrid CLI Swarm in Windows Terminal for agy, opencode, cline, and kilo.
#>

$ErrorActionPreference = "Stop"

$RootPath = (Get-Item -Path $PSScriptRoot\..).FullName
Set-Location $RootPath

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Jarvis 4-Agent Swarm: agy | opencode | cline | kilo    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Ensure Git repo
if (-not (Test-Path ".git")) {
    Write-Error "Not a git repository root. Please run git init or run this inside the repository."
}

# 2. Setup branches and worktrees
$ParentDir = Split-Path $RootPath -Parent
$BackendDir = Join-Path $ParentDir "Jarvis-backend"
$FrontendDir = Join-Path $ParentDir "Jarvis-frontend"
$QADir = Join-Path $ParentDir "Jarvis-qa"

$Workers = @(
    @{ Role = "backend";  Tool = "opencode"; Dir = $BackendDir;  Branch = "agent/backend";  Color = "Green" },
    @{ Role = "frontend"; Tool = "cline";    Dir = $FrontendDir; Branch = "agent/frontend"; Color = "Yellow" },
    @{ Role = "qa";       Tool = "kilo";     Dir = $QADir;       Branch = "agent/qa";       Color = "Magenta" }
)

foreach ($w in $Workers) {
    $branchList = (git branch --list $w.Branch)
    if (-not $branchList) {
        Write-Host "[+] Creating branch $($w.Branch)..." -ForegroundColor Gray
        git branch $w.Branch
    }

    if (-not (Test-Path $w.Dir)) {
        Write-Host "[+] Creating worktree for $($w.Tool) ($($w.Role)) at $($w.Dir)..." -ForegroundColor $w.Color
        git worktree add $w.Dir $w.Branch
    } else {
        Write-Host "[OK] Worktree for $($w.Tool) ($($w.Role)) ready at $($w.Dir)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "[OK] All worktrees ready!" -ForegroundColor Green
Write-Host "[*] Spawning Windows Terminal 4-pane swarm..." -ForegroundColor Cyan

# 3. Check for wt.exe
$wtPath = (Get-Command wt.exe -ErrorAction SilentlyContinue)
if (-not $wtPath) {
    Write-Warning "Windows Terminal (wt.exe) not found on PATH."
    exit 0
}

# 4. Construct Windows Terminal 2x2 grid arguments using clean script paths
$P1 = Join-Path $RootPath "swarm\panes\pane1_lead.ps1"
$P2 = Join-Path $RootPath "swarm\panes\pane2_backend.ps1"
$P3 = Join-Path $RootPath "swarm\panes\pane3_frontend.ps1"
$P4 = Join-Path $RootPath "swarm\panes\pane4_qa.ps1"

$wtArgs = @(
    "-d", $RootPath, "powershell", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $P1,
    ";", "split-pane", "-V", "-d", $BackendDir, "powershell", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $P2,
    ";", "move-focus", "left",
    ";", "split-pane", "-H", "-d", $FrontendDir, "powershell", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $P3,
    ";", "move-focus", "right",
    ";", "split-pane", "-H", "-d", $QADir, "powershell", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $P4
)

Start-Process wt.exe -ArgumentList $wtArgs

Write-Host "[OK] 4-Agent Swarm terminal launched successfully in 4 split panes!" -ForegroundColor Green
