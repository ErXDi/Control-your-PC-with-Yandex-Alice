# Stops the running agent (started with python or pythonw).
Get-CimInstance Win32_Process |
    Where-Object { $_.Name -match '^pythonw?\.exe$' -and $_.CommandLine -match 'agent[\\/]agent\.py' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Write-Host 'Agent stopped.'
