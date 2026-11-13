# Tarea programada PruebaFicha: demo A/B por código de catálogo. Mismo departamento y mismas cámaras de venta con
# (1) los acabados de las fotos, (2) ficha A y (3) ficha B. Salida: %USERPROFILE%\recorrido-3d\mvp\ficha\<nombre>\<cam>.png
param([string]$Cams = "v_cuarto,v_cocina", [int]$Samples = 128, [int]$Scale = 50)
$r = "$env:USERPROFILE\recorrido-3d"; $log = "$r\prueba_ficha.log"
$casa = "$r\openhouse-3d\houses\apartaestudio"
"start $(Get-Date -Format HH:mm:ss)" | Out-File $log
$env:ACABADOS = "original"; $env:LUZ = "neutra"; $env:HOUSE_HIDE = "Aire_Interior,Polvo"; $env:BIBLIO = "1"; $env:REALISMO = ""
$fichas = [ordered]@{ "original" = ""; "ficha_a" = "$casa\fichas\ficha_a_madera_blanco.json"; "ficha_b" = "$casa\fichas\ficha_b_concreto_negro.json" }
foreach ($n in $fichas.Keys) {
    if ($fichas[$n]) { $env:ACABADOS_FICHA = $fichas[$n] } else { Remove-Item Env:ACABADOS_FICHA -EA SilentlyContinue }
    "$n $(Get-Date -Format HH:mm:ss)" | Out-File -Append $log
    powershell -ExecutionPolicy Bypass -File "$r\render.ps1" -Cams $Cams -Samples $Samples -Scale $Scale 2>&1 | Select-String "\[ficha\]|Saved|Error|Traceback" | Out-File -Append $log
    $dst = "$r\mvp\ficha\$n"; New-Item -ItemType Directory -Force $dst | Out-Null
    foreach ($c in $Cams.Split(",")) { Copy-Item "$casa\output\renders\$c.png" "$dst\$c.png" -Force -EA SilentlyContinue }
}
Remove-Item Env:ACABADOS_FICHA -EA SilentlyContinue
"done $(Get-Date -Format HH:mm:ss)" | Out-File -Append $log
schtasks /delete /tn PruebaFicha /f
