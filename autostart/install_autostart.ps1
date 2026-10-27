# Adds the agent to Windows startup (no console window) and starts it right away.
$ErrorActionPreference = 'Stop'
$root  = Split-Path $PSScriptRoot -Parent
$agent = Join-Path $root 'agent\agent.py'

if (-not (Test-Path (Join-Path $root 'agent\config.json'))) {
    Write-Host 'agent\config.json not found. Copy agent\config.example.json to agent\config.json and fill it in (see README).' -ForegroundColor Red
    exit 1
}

$py  = & python -c "import sys; print(sys.executable)"
$pyw = Join-Path (Split-Path $py) 'pythonw.exe'
if (-not (Test-Path $pyw)) {
    Write-Host "pythonw.exe not found next to $py" -ForegroundColor Red
    exit 1
}

$startup = [Environment]::GetFolderPath('Startup')
$ws = New-Object -ComObject WScript.Shell

# remove shortcuts left over from older versions (start_alice.vbs)
Get-ChildItem $startup -Filter *.lnk | ForEach-Object {
    $s = $ws.CreateShortcut($_.FullName)
    if ("$($s.TargetPath) $($s.Arguments)" -match 'start_alice\.vbs') { Remove-Item $_.FullName }
}

$lnk = $ws.CreateShortcut((Join-Path $startup 'Alice PC Control.lnk'))
$lnk.TargetPath       = $pyw
$lnk.Arguments        = "`"$agent`""
$lnk.WorkingDirectory = $root
$lnk.Description      = 'Alice PC Control agent'
$lnk.Save()

Start-Process $pyw -ArgumentList "`"$agent`"" -WorkingDirectory $root
Write-Host 'Done: the agent is running in the background and will start with Windows.' -ForegroundColor Green
Write-Host "Log: $root\agent\agent.log"
