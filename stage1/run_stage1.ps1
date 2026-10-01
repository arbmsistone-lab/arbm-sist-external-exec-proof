$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $PSScriptRoot
$Source=Join-Path $Root "fixtures\development\m1_reset_fixture.ods"
$Dest=Join-Path $Root "work\m1_working.ods"
$LogDir=Join-Path $Root "logs"
$Log=Join-Path $LogDir "stage1_full_output.txt"
$Python="C:\Users\airto\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
New-Item -ItemType Directory -Force -Path $LogDir,(Join-Path $Root "work")|Out-Null
Start-Transcript -Path $Log -Force|Out-Null
try {
 Write-Host "=== ARBM SIST M1 / ETAPA 1 / WINDOWS LOCAL ==="
 Write-Host "TIMESTAMP_START=$((Get-Date).ToString('o'))"
 $branch=(git -C $Root branch --show-current).Trim()
 Write-Host "GIT_BRANCH=$branch"
 if($branch -ne "m1-stage1"){throw "Branch incorreta: $branch"}
 if(-not(Test-Path $Python)){throw "Python não encontrado: $Python"}
 Write-Host "PYTHON=$(& $Python --version 2>&1)"
 Write-Host "[1/4] Fixture LibreOffice headless (background)..."
 & (Join-Path $PSScriptRoot "create_fixture.ps1") -FixturePath $Source
 Write-Host "[2/4] Mutação real + reset + negativos..."
 Push-Location $PSScriptRoot
 try {
  & $Python .\test_reset_10x.py --source $Source --dest $Dest --runs 10
  if($LASTEXITCODE -ne 0){throw "test_reset_10x falhou: $LASTEXITCODE"}
 } finally {Pop-Location}
 Write-Host "[3/4] Fingerprint..."
 & (Join-Path $PSScriptRoot "environment_fingerprint.ps1") -OutputPath (Join-Path $LogDir "environment_fingerprint.json")
 Write-Host "[4/4] Estabilidade fingerprint..."
 & (Join-Path $PSScriptRoot "test_fingerprint_stability.ps1")
 Write-Host "ETAPA_1_LOCAL_TEST_COMPLETE"
 Write-Host "TIMESTAMP_END=$((Get-Date).ToString('o'))"
 exit 0
} catch {
 Write-Host "ETAPA_1_LOCAL_TEST_FAILED"
 Write-Host "ERROR=$($_.Exception.Message)"
 exit 1
} finally {
 Stop-Transcript|Out-Null
}
