$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
$ShortcutPath = Join-Path $DesktopPath "JARVIS.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "M:\coding\Jarvis\JARVIS.exe"
$Shortcut.WorkingDirectory = "M:\coding\Jarvis"
$Shortcut.IconLocation = "M:\coding\Jarvis\jarvis.ico,0"
$Shortcut.Description = "JARVIS Cyberpunk Voice and HUD AI Assistant"
$Shortcut.Save()
Write-Host "Desktop shortcut created successfully at: $ShortcutPath"
