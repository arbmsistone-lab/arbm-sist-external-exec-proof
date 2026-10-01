param([string]$FixturePath="")
$ErrorActionPreference="Stop"
$env:TEMP="$env:LOCALAPPDATA\Temp"
$env:TMP=$env:TEMP
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class M1Win {
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int c);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, IntPtr p);
 [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
 [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a,uint b,bool f);
 [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
 [DllImport("user32.dll")] public static extern IntPtr SetFocus(IntPtr h);
 [DllImport("user32.dll")] public static extern bool EnableWindow(IntPtr h,bool enable);
}
"@
function Force-Foreground([IntPtr]$target){
 $fg=[M1Win]::GetForegroundWindow()
 $fgTid=[M1Win]::GetWindowThreadProcessId($fg,[IntPtr]::Zero)
 $curTid=[M1Win]::GetCurrentThreadId()
 [M1Win]::AttachThreadInput($curTid,$fgTid,$true)|Out-Null
 [M1Win]::ShowWindow($target,3)|Out-Null
 [M1Win]::BringWindowToTop($target)|Out-Null
 [M1Win]::SetForegroundWindow($target)|Out-Null
 [M1Win]::SetFocus($target)|Out-Null
 [M1Win]::AttachThreadInput($curTid,$fgTid,$false)|Out-Null
}
$Root=Split-Path -Parent $PSScriptRoot
if(-not $FixturePath){$FixturePath=Join-Path $Root "fixtures\development\m1_reset_fixture.ods"}
$logDir=Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $FixturePath),$logDir|Out-Null
Remove-Item $FixturePath -Force -ErrorAction SilentlyContinue
Get-Process soffice,soffice.bin -ErrorAction SilentlyContinue|Stop-Process -Force -ErrorAction SilentlyContinue
$blockedWindows=@()
try {
 Get-Process chrome,claude -ErrorAction SilentlyContinue|Where-Object {$_.MainWindowHandle -ne 0}|ForEach-Object {
   $blockedWindows += $_.MainWindowHandle
   [M1Win]::EnableWindow($_.MainWindowHandle,$false)|Out-Null
   [M1Win]::ShowWindow($_.MainWindowHandle,6)|Out-Null
 }
 $soffice="C:\Users\airto\LibreOfficeM1\program\soffice.exe"
 if(-not(Test-Path $soffice)){throw "LibreOffice nao encontrado: $soffice"}
 $profileDir=Join-Path $env:LOCALAPPDATA "Temp\ARBM_M1_LibreOffice_Profile"
 Remove-Item $profileDir -Recurse -Force -ErrorAction SilentlyContinue
 New-Item -ItemType Directory -Force -Path $profileDir|Out-Null
 $profileUri="file:///"+(($profileDir -replace "\\","/") -replace " ","%20")
 Start-Process -FilePath $soffice -ArgumentList @("-env:UserInstallation=$profileUri","--calc")
 $p=$null
 for($wait=1;$wait -le 30;$wait++){
   Start-Sleep -Milliseconds 500
   $p=Get-Process soffice.bin -ErrorAction SilentlyContinue|Where-Object {$_.MainWindowHandle -ne 0}|Sort-Object StartTime -Descending|Select-Object -First 1
   if($p){break}
 }
 if(-not $p){throw "Janela do Calc nao encontrada apos 15s"}
 $h=$p.MainWindowHandle
 Force-Foreground $h
 Start-Sleep -Milliseconds 500
 if([M1Win]::GetForegroundWindow() -ne $h){throw "CALC_NOT_FOREGROUND"}
 $data="Produto"+[char]9+"Quantidade"+[Environment]::NewLine+"Teclado"+[char]9+"10"
 [System.Windows.Forms.Clipboard]::SetText($data)
 [System.Windows.Forms.SendKeys]::SendWait("^{HOME}")
 [System.Windows.Forms.SendKeys]::SendWait("^v")
 Start-Sleep -Milliseconds 800
 # Screenshot antes do salvamento: prova visual do fixture na interface.
 $b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds
 $bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height
 $g=[System.Drawing.Graphics]::FromImage($bmp)
 $g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size)
 $shot=Join-Path $logDir "fixture_before_save.png"
 $bmp.Save($shot,[System.Drawing.Imaging.ImageFormat]::Png)
 $g.Dispose(); $bmp.Dispose()
 Force-Foreground $h
 Start-Sleep -Milliseconds 300
 [System.Windows.Forms.SendKeys]::SendWait("^s")
 Start-Sleep -Milliseconds 900
 $dlg=[M1Win]::GetForegroundWindow()
 if($dlg -eq $h){throw "SAVE_DIALOG_NOT_OPEN"}
 [System.Windows.Forms.SendKeys]::SendWait("^a")
 [System.Windows.Forms.SendKeys]::SendWait($FixturePath)
 [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
 Start-Sleep -Seconds 3
 if(-not(Test-Path $FixturePath)){
   [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
   Start-Sleep -Seconds 2
 }
 if(-not(Test-Path $FixturePath)){throw "SAVE_FAILED"}
 Write-Host "FIXTURE_CREATED_BY_CALC_GUI=PASS"
 Write-Host "FIXTURE_SCREENSHOT=$shot"
 Write-Host "FIXTURE=$FixturePath"
} finally {
 Get-Process soffice,soffice.bin -ErrorAction SilentlyContinue|Stop-Process -Force -ErrorAction SilentlyContinue
 foreach($hwnd in $blockedWindows){[M1Win]::EnableWindow($hwnd,$true)|Out-Null}
}
