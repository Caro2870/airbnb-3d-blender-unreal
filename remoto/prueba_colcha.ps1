$r = "$env:USERPROFILE\recorrido-3d"; $log = "$r\prueba_colcha.log"; $ren = "$r\openhouse-3d\houses\apartaestudio\output\renders"
"start $(Get-Date -Format HH:mm:ss)" | Out-File $log
$env:ACABADOS = "original"; $env:LUZ = "neutra"; $env:HOUSE_HIDE = "Aire_Interior,Polvo"; $env:BIBLIO = "1"; $env:REALISMO = ""
powershell -ExecutionPolicy Bypass -File "$r\render.ps1" -Cams "cuarto,cabecero" -Samples 32 -Scale 47 *>> $log
New-Item -ItemType Directory -Force "$r\mvp\colcha" | Out-Null
foreach ($c in "cuarto", "cabecero") { Copy-Item "$ren\$c.png" "$r\mvp\colcha\$c.png" -Force }
"done $(Get-Date -Format HH:mm:ss)" | Out-File -Append $log
schtasks /delete /tn PruebaColcha /f
