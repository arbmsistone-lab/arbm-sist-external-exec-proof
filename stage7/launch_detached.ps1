param([Parameter(Mandatory=$true)][string]$SpecPath)
$ErrorActionPreference='Stop'
$wrapper=Join-Path $PSScriptRoot 'detached_watchdog.ps1'
$spec=Get-Content -Raw $SpecPath | ConvertFrom-Json
$runDir=[string]$spec.run_dir
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$wrapperOut=Join-Path $runDir 'wrapper_stdout.log'
$wrapperErr=Join-Path $runDir 'wrapper_stderr.log'
$qSpec='"'+$SpecPath.Replace('"','\"')+'"'
$qWrap='"'+$wrapper.Replace('"','\"')+'"'
$argLine="-NoProfile -ExecutionPolicy Bypass -File $qWrap -SpecPath $qSpec"
$p=Start-Process powershell.exe -ArgumentList $argLine -PassThru -WindowStyle Hidden -RedirectStandardOutput $wrapperOut -RedirectStandardError $wrapperErr
Write-Host "DETACHED_WRAPPER_PID=$($p.Id)"
Write-Host "DETACHED_LAUNCH=PASS"
Write-Host "WRAPPER_STDOUT=$wrapperOut"
Write-Host "WRAPPER_STDERR=$wrapperErr"
