$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $PSScriptRoot
$Python="C:\Users\airto\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Log=Join-Path $Root "logs\stage7_preflight.txt"
Push-Location $PSScriptRoot
try {
 & $Python .\preflight.py *>&1 | Tee-Object -FilePath $Log
 exit $LASTEXITCODE
} finally {Pop-Location}
