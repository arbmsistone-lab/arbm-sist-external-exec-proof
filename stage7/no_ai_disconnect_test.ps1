param([string]$RunDir,[int]$Seconds=20)
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
$start=Get-Date
for($i=0;$i -lt $Seconds;$i++){
 @{tick=$i;time=(Get-Date).ToString('o')}|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $RunDir 'child_heartbeat.json')
 Start-Sleep -Seconds 1
}
@{status='PASS';started_at=$start.ToString('o');ended_at=(Get-Date).ToString('o');ai_calls=0}|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $RunDir 'child_result.json')
Write-Host 'NO_AI_CHILD=PASS'
