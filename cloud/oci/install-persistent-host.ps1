param(
  [Parameter(Mandatory=$true)][string]$PublicIp,
  [Parameter(Mandatory=$true)][string]$SshKeyPath,
  [Parameter(Mandatory=$true)][string]$KnownHostsFile,
  [string]$RemoteUser='ubuntu',
  [string]$TokenFile="$env:LOCALAPPDATA\ARBM-Remote-Channels\state\oci-persistent-host.token"
)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$bootstrap=Join-Path $repo 'cloud\common\bootstrap-persistent-host.sh'
foreach($p in @($SshKeyPath,$KnownHostsFile,$TokenFile,$bootstrap)){
  if(-not (Test-Path -LiteralPath $p)){throw "required_file_missing:$p"}
}
foreach($cmd in @('ssh','scp','git')){
  if(-not (Get-Command $cmd -ErrorAction SilentlyContinue)){throw "required_command_missing:$cmd"}
}
$sha=(& git -C $repo rev-parse HEAD).Trim()
if($sha -notmatch '^[a-f0-9]{40}$'){throw 'invalid_control_sha'}
$token=[IO.File]::ReadAllText($TokenFile).Trim()
if($token.Length -lt 40){throw 'invalid_host_token'}
$target="${RemoteUser}@${PublicIp}"
$sshOpts=@('-i',$SshKeyPath,'-o',"UserKnownHostsFile=$KnownHostsFile",'-o','StrictHostKeyChecking=yes')
& scp @sshOpts -- $bootstrap "${target}:/tmp/arbm-bootstrap.sh"
if($LASTEXITCODE -ne 0){throw 'bootstrap_copy_failed'}

$token | & ssh @sshOpts $target "umask 077; tr -d '\r\n' > /tmp/arbm-host-token"
if($LASTEXITCODE -ne 0){throw 'token_transfer_failed'}
$token=$null

$remote="sudo env ARBM_HOST_ID=oci-always-free-persistent ARBM_CLOUD_VENDOR=oci ARBM_HOST_TOKEN_FILE=/tmp/arbm-host-token ARBM_CONTROL_SHA=$sha bash /tmp/arbm-bootstrap.sh; rc=`$?; sudo rm -f /tmp/arbm-host-token /tmp/arbm-bootstrap.sh; exit `$rc"
& ssh @sshOpts $target $remote
if($LASTEXITCODE -ne 0){throw 'remote_bootstrap_failed'}
Write-Output "ARBM_OCI_BOOTSTRAP_SENT sha=$sha host=$PublicIp"
