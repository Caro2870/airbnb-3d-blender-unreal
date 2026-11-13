# Tarea programada (GPU): render a resolución completa (1080x1920) de las cámaras de las fotos 1 y 5, para medir textura.
$r = "$env:USERPROFILE\recorrido-3d"; $log = "$r\prueba_fina.log"; $ren = "$r\openhouse-3d\houses\apartaestudio\output\renders"
"start $(Get-Date -Format HH:mm:ss)" | Out-File $log
$env:ACABADOS = "original"; $env:LUZ = "neutra"; $env:HOUSE_HIDE = "Aire_Interior,Polvo"; $env:BIBLIO = "1"; $env:REALISMO = ""
powershell -ExecutionPolicy Bypass -File "$r\render.ps1" -Cams "cuarto,cabecero" -Samples 128 -Scale 100 *>> $log
New-Item -ItemType Directory -Force "$r\mvp\fina" | Out-Null
foreach ($c in "cuarto", "cabecero") { Copy-Item "$ren\$c.png" "$r\mvp\fina\$c.png" -Force }
"done $(Get-Date -Format HH:mm:ss)" | Out-File -Append $log
schtasks /delete /tn PruebaFina /f
