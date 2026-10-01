param(
 [Parameter(Mandatory=$true)][string]$Task,
 [Parameter(Mandatory=$true)][string]$Fixture,
 [Parameter(Mandatory=$true)][string]$Output,
 [Parameter(Mandatory=$true)][string]$RunDir
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$config=Get-Content -Raw (Join-Path $PSScriptRoot 'baseline_config.json')|ConvertFrom-Json
$py='C:\Users\airto\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$child=Join-Path $PSScriptRoot 'run_baseline_child.ps1'
$spec=[ordered]@{
 run_dir=$RunDir
 max_wall_time_seconds=[int]$config.max_wall_time_seconds
 child_script=$child
 child_args=@('-Python',$py,'-Agent',(Join-Path $PSScriptRoot 'baseline_gui_agent.py'),'-Task',$Task,'-Fixture',$Fixture,'-Output',$Output,'-RunDir',$RunDir)
}
New-Item -ItemType Directory -Force -Path $RunDir|Out-Null
$specPath=Join-Path $RunDir 'job_spec.json'
$spec|ConvertTo-Json -Depth 6|Set-Content -Encoding UTF8 $specPath
& (Join-Path $PSScriptRoot 'launch_detached.ps1') -SpecPath $specPath
