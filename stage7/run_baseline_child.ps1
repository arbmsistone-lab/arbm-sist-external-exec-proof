param(
 [Parameter(Mandatory=$true)][string]$Python,
 [Parameter(Mandatory=$true)][string]$Agent,
 [Parameter(Mandatory=$true)][string]$Task,
 [Parameter(Mandatory=$true)][string]$Fixture,
 [Parameter(Mandatory=$true)][string]$Output,
 [Parameter(Mandatory=$true)][string]$RunDir
)
& $Python $Agent --task $Task --fixture $Fixture --output $Output --run-dir $RunDir
exit $LASTEXITCODE
