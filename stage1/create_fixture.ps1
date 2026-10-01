param([string]$FixturePath="")
$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $PSScriptRoot
if(-not $FixturePath){$FixturePath=Join-Path $Root "fixtures\development\m1_reset_fixture.ods"}
$dir=Split-Path -Parent $FixturePath
New-Item -ItemType Directory -Force -Path $dir|Out-Null
$soffice="C:\Users\airto\LibreOfficeM1\program\soffice.exe"
if(-not(Test-Path $soffice)){throw "LibreOffice extraído não encontrado: $soffice"}
$env:PATH="C:\Users\airto\LibreOfficeM1\System64;C:\Users\airto\LibreOfficeM1\program;"+$env:PATH
$tmp=Join-Path $env:LOCALAPPDATA "Temp\m1_fixture.csv"
$data="Produto,Quantidade"+[Environment]::NewLine+"Teclado,10"
[IO.File]::WriteAllText($tmp,$data,(New-Object Text.UTF8Encoding($false)))
$profile="file:///C:/Users/airto/LibreOfficeM1HeadlessProfile"
& $soffice --headless "-env:UserInstallation=$profile" --convert-to ods --outdir $dir $tmp | Out-Host
Start-Sleep -Seconds 2
$generated=Join-Path $dir "m1_fixture.ods"
if(-not(Test-Path $generated)){throw "LibreOffice não gerou m1_fixture.ods"}
if(Test-Path $FixturePath){Remove-Item -Force $FixturePath}
Move-Item -Force $generated $FixturePath
Remove-Item -Force $tmp -ErrorAction SilentlyContinue
Write-Host "FIXTURE_CREATED_BY_LIBREOFFICE_HEADLESS=PASS"
Write-Host "GUI_FOREGROUND_BLOCKED=true"
Write-Host "FIXTURE=$FixturePath"
