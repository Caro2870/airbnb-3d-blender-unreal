# Tarea programada PruebaVentaHoy: las cámaras de venta niveladas (v_*) con el modelo actual, mismos ajustes que
# prueba_venta.ps1 (6-nov), para comparar en la misma cámara. Salida: %USERPROFILE%\recorrido-3d\mvp\venta_hoy\
$r = "$env:USERPROFILE\recorrido-3d"; $log = "$r\prueba_venta_hoy.log"
"start $(Get-Date -Format HH:mm:ss)" | Out-File $log
$env:ACABADOS = "original"; $env:LUZ = "neutra"; $env:HOUSE_HIDE = "Aire_Interior,Polvo"; $env:BIBLIO = "1"; $env:REALISMO = ""
$cams = "v_cuarto,v_cama,v_detalle"
powershell -ExecutionPolicy Bypass -File "$r\render.ps1" -Cams $cams -Samples 128 -Scale 50 *>> $log
$dst = "$r\mvp\venta_hoy"; New-Item -ItemType Directory -Force $dst | Out-Null
foreach ($c in $cams.Split(",")) {
    Copy-Item "$r\openhouse-3d\houses\apartaestudio\output\renders\$c.png" "$dst\$c.png" -Force -ErrorAction SilentlyContinue
}
"done $(Get-Date -Format HH:mm:ss)" | Out-File -Append $log
schtasks /delete /tn PruebaVentaHoy /f
