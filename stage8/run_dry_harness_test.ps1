$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $PSScriptRoot
$Python="C:\Users\airto\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Log=Join-Path $Root "logs\stage8_harness_prep.txt"
Push-Location $PSScriptRoot
try {
 & $Python .\test_dry_run_harness.py *>&1 | Tee-Object -FilePath $Log
 exit $LASTEXITCODE
} finally {Pop-Location}
