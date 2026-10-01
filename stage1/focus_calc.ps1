param([int]$TargetPid=29400)
$env:TEMP="$env:LOCALAPPDATA\Temp"
$env:TMP=$env:TEMP
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class M1Win32 {
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
}
"@
$p=Get-Process -Id $TargetPid -ErrorAction Stop
$h=$p.MainWindowHandle
$show=[M1Win32]::ShowWindow($h,9)
$focus=[M1Win32]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 800
$fg=[M1Win32]::GetForegroundWindow()
Write-Host "CALC_HANDLE=$h SHOW=$show SET_FOREGROUND=$focus FOREGROUND_HANDLE=$fg TITLE=$($p.MainWindowTitle)"
if($fg -ne $h){exit 2}
