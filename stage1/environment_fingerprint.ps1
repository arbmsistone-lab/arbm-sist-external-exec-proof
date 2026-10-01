param([string]$OutputPath="")
$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $PSScriptRoot
$Logs=Join-Path $Root "logs"; New-Item -ItemType Directory -Force -Path $Logs|Out-Null
if(-not $OutputPath){$OutputPath=Join-Path $Logs "environment_fingerprint.json"}
Add-Type -AssemblyName System.Windows.Forms
$screen=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$os=Get-CimInstance Win32_OperatingSystem
$tz=Get-TimeZone; $culture=Get-Culture
$kbd=(Get-WinUserLanguageList|Select-Object -First 1).InputMethodTips -join ","
$lo="C:\Users\airto\LibreOfficeM1\program\soffice.exe"
$loVersion=if(Test-Path $lo){(Get-Item $lo).VersionInfo.ProductVersion}else{"NOT_FOUND"}
$py="C:\Users\airto\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$pyVersion=if(Test-Path $py){(& $py --version 2>&1 | Out-String).Trim()}else{"NOT_FOUND"}
$dpi=Get-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name LogPixels -ErrorAction SilentlyContinue
$scale=if($dpi.LogPixels){[math]::Round(($dpi.LogPixels/96.0)*100)}else{"SYSTEM_DEFAULT_OR_UNAVAILABLE"}
[ordered]@{
 captured_at=(Get-Date).ToString("o")
 computer_name=$env:COMPUTERNAME
 windows_caption=$os.Caption
 windows_version=$os.Version
 windows_build=$os.BuildNumber
 os_architecture=$os.OSArchitecture
 resolution_width=$screen.Width
 resolution_height=$screen.Height
 display_scale_percent=$scale
 culture=$culture.Name
 keyboard_layout=$kbd
 timezone=$tz.Id
 libreoffice_path=$lo
 libreoffice_version=$loVersion
 libreoffice_source="official MSI SHA256 4aa6c6e1895f4055104effcb556bd3362d20c6ad707c149543304f395ef9db95 extracted with pymsi"
 python_path=$py
 python_version=$pyVersion
 gui_foreground_blocked=$true
}|ConvertTo-Json -Depth 4|Set-Content -Encoding UTF8 $OutputPath
Write-Host "ENVIRONMENT_FINGERPRINT_OK"
Write-Host "Arquivo: $OutputPath"
