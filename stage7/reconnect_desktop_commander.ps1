Start-Sleep -Seconds 8
$log='C:\Users\airto\.desktop-commander-device\reconnect-test.log'
$arg='/c npx @wonderwhy-er/desktop-commander@latest remote >> "'+$log+'" 2>&1'
Start-Process cmd.exe -ArgumentList $arg -WindowStyle Hidden
