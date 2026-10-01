param([Parameter(Mandatory=$true)][string]$SpecPath)
$ErrorActionPreference='Stop'
$spec=Get-Content -Raw $SpecPath | ConvertFrom-Json
$RunDir=[string]$spec.run_dir
$MaxWallTimeSeconds=[int]$spec.max_wall_time_seconds
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
$stdout=Join-Path $RunDir 'stdout.log'; $stderr=Join-Path $RunDir 'stderr.log'
$started=Get-Date
$childArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',[string]$spec.child_script)
foreach($a in $spec.child_args){$childArgs += [string]$a}
$proc=Start-Process powershell.exe -ArgumentList $childArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
@{status='RUNNING';pid=$proc.Id;started_at=$started.ToString('o');max_wall_time_seconds=$MaxWallTimeSeconds}|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $RunDir 'detached_state.json')
$deadline=$started.AddSeconds($MaxWallTimeSeconds); $timedOut=$false
while(-not $proc.HasExited){
 @{pid=$proc.Id;observed_at=(Get-Date).ToString('o');elapsed_seconds=[math]::Round(((Get-Date)-$started).TotalSeconds,3)}|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $RunDir 'heartbeat.json')
 if((Get-Date)-ge $deadline){
  $timedOut=$true
  & taskkill.exe /PID $proc.Id /T /F | Out-Null
  break
 }
 Start-Sleep -Milliseconds 500
 try{$proc.Refresh()}catch{}
}
$ended=Get-Date; try{$proc.Refresh();$ec=$proc.ExitCode}catch{$ec=$null}
@{status=$(if($timedOut){'TIMEOUT'}else{'FINISHED'});pid=$proc.Id;started_at=$started.ToString('o');ended_at=$ended.ToString('o');elapsed_seconds=[math]::Round(($ended-$started).TotalSeconds,3);max_wall_time_seconds=$MaxWallTimeSeconds;watchdog_enforced=$true;timed_out=$timedOut;exit_code=$ec}|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $RunDir 'detached_final.json')
