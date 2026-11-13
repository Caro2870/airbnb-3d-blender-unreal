$p = "$env:USERPROFILE\recorrido-3d\remoto\prueba_luces.ps1"
schtasks /create /f /tn PruebaLuces /sc once /st 23:59 /it /tr "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$p`"" | Out-Null
schtasks /run /tn PruebaLuces
