$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $PSScriptRoot
$Python="C:\Users\airto\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Log=Join-Path $Root "logs\stage5_runner.txt"
Push-Location $PSScriptRoot
try {
 & $Python .\test_runner.py *>&1 | Tee-Object -FilePath $Log
 if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
 & $Python .\test_round_policy.py *>&1 | Tee-Object -FilePath $Log -Append
 if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
} finally {Pop-Location}
