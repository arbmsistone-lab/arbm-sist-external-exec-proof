param([Parameter(Mandatory=$true)][string]$SpecPath)
$wrapper=Join-Path $PSScriptRoot 'detached_watchdog.ps1'
$qSpec='"'+$SpecPath.Replace('"','\"')+'"'
$qWrap='"'+$wrapper.Replace('"','\"')+'"'
$argLine="-NoProfile -ExecutionPolicy Bypass -File $qWrap -SpecPath $qSpec"
$p=Start-Process powershell.exe -ArgumentList $argLine -PassThru -WindowStyle Hidden
Write-Host "DETACHED_WRAPPER_PID=$($p.Id)"
Write-Host "DETACHED_LAUNCH=PASS"
