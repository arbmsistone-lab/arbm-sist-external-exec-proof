$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $PSScriptRoot; $Logs=Join-Path $Root "logs"; New-Item -ItemType Directory -Force -Path $Logs|Out-Null
$f1=Join-Path $Logs "environment_fingerprint_1.json"; $f2=Join-Path $Logs "environment_fingerprint_2.json"
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "environment_fingerprint.ps1") -OutputPath $f1
Start-Sleep -Milliseconds 300
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "environment_fingerprint.ps1") -OutputPath $f2
$o1=Get-Content $f1 -Raw|ConvertFrom-Json; $o2=Get-Content $f2 -Raw|ConvertFrom-Json
$o1.PSObject.Properties.Remove("captured_at"); $o2.PSObject.Properties.Remove("captured_at")
$j1=$o1|ConvertTo-Json -Depth 4 -Compress; $j2=$o2|ConvertTo-Json -Depth 4 -Compress
if($j1 -eq $j2){Write-Host "FINGERPRINT_STABLE=PASS"; exit 0}
Write-Host "FINGERPRINT_STABLE=FAIL"; Write-Host $j1; Write-Host $j2; exit 1