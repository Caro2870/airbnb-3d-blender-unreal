$p = "$env:USERPROFILE\recorrido-3d\remoto\prueba_fina.ps1"
schtasks /create /f /tn PruebaFina /sc once /st 23:59 /it /tr "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$p`"" | Out-Null
schtasks /run /tn PruebaFina
