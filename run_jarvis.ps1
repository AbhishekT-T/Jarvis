<#
.SYNOPSIS
    1-Click Launcher for Jarvis Voice & Text Assistant.
#>

param (
    [switch]$Text
)

$RootPath = (Get-Item -Path $PSScriptRoot).FullName
$JarvisDir = Join-Path $RootPath "jarvis_project"
$VenvPython = Join-Path $JarvisDir ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment not found at $VenvPython. Please check your setup."
    exit 1
}

Set-Location $JarvisDir

if ($Text) {
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "             Starting JARVIS in Text Mode                 " -ForegroundColor Cyan
    Write-Host "==========================================================" -ForegroundColor Cyan
    & $VenvPython main.py --text
} else {
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "             Starting JARVIS in Voice Mode                " -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "Say 'Hey Jarvis' to wake him up!" -ForegroundColor Yellow
    & $VenvPython main.py
}
