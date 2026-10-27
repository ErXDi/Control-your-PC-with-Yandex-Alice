# Removes the agent from Windows startup and stops it.
$startup = [Environment]::GetFolderPath('Startup')
Remove-Item (Join-Path $startup 'Alice PC Control.lnk') -ErrorAction SilentlyContinue
& (Join-Path $PSScriptRoot 'stop_agent.ps1')
Write-Host 'Autostart removed.' -ForegroundColor Green
