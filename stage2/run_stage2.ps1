$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $PSScriptRoot
$Python="C:\Users\airto\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Log=Join-Path $Root "logs\stage2_verifiers.txt"
Push-Location $PSScriptRoot
try {
 & $Python .\build_fixtures.py *>&1 | Tee-Object -FilePath $Log
 & $Python .\test_verifiers.py *>&1 | Tee-Object -FilePath $Log -Append
 if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
} finally {Pop-Location}
