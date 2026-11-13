$p = "$env:USERPROFILE\recorrido-3d\prueba_colcha.ps1"
schtasks /create /f /tn PruebaColcha /sc once /st 23:59 /it /tr "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$p`"" | Out-Null
schtasks /run /tn PruebaColcha
