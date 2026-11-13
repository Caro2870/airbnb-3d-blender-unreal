# Tarea programada VideoAB: tomas del video A/B (shots.AB_SHOTS) con luz dorada de tarde, una vez por ficha.
#   -Prueba: solo el cuadro -Cuadro de cada toma (mide tiempo y encuadre)
#   A se renderiza hasta el fin de la cortina y B desde su inicio (cuadros -RangoA / -RangoB).
# OJO: render_shot salta los cuadros que ya existen; borrar mvp/video_ab antes de repetir una prueba.
# Salida: %USERPROFILE%\recorrido-3d\mvp\video_ab\<ficha>\<toma>\f_####.png
param([switch]$Prueba, [string]$RangoA = "1-63", [string]$RangoB = "33-96", [int]$Samples = 48, [string]$Res = "1280x720",
      [string]$Tomas = "ab_cuarto,ab_cocina", [string]$Fichas = "ficha_a,ficha_b", [string]$Sol = "-0.30,0.80,0.52", [string]$Cuadro = "48")
$r = "$env:USERPROFILE\recorrido-3d"; $repo = "$r\openhouse-3d"; $log = "$r\video_ab.log"; Set-Location $repo
$casa = "$repo\houses\apartaestudio"
"start $(Get-Date -Format HH:mm:ss)" | Out-File $log
$env:ARCHVIZ_PYTHON = "$repo\.venv\Scripts\python.exe"
$env:ACABADOS = "original"; Remove-Item Env:LUZ -EA SilentlyContinue; $env:HOUSE_HIDE = "Aire_Interior,Polvo"; $env:BIBLIO = "1"; $env:REALISMO = ""; $env:SOL = $Sol
$b = "$env:USERPROFILE\tools\blender-5.2.3-windows-x64\blender.exe"
$mapa = [ordered]@{ "ficha_a" = @("$casa\fichas\ficha_a_madera_blanco.json", $RangoA); "ficha_b" = @("$casa\fichas\ficha_b_concreto_negro.json", $RangoB) }
foreach ($n in $Fichas.Split(",")) {
    $env:ACABADOS_FICHA = $mapa[$n][0]
    $env:HOUSE_FILM_DIR = "$r\mvp\video_ab\$n"
    $rango = if ($Prueba) { "$Cuadro-$Cuadro" } else { $mapa[$n][1] }
    "$n cuadros $rango $(Get-Date -Format HH:mm:ss)" | Out-File -Append $log
    & $b -b --python-exit-code 1 --python run.py -- --house apartaestudio --device OPTIX --film $Tomas --film-frames $rango --samples $Samples --res $Res --scale 100 --no-mblur 2>&1 | Select-String "\[film\]|\[ficha\]|Error|Traceback|line " | Out-File -Append $log
}
Remove-Item Env:ACABADOS_FICHA, Env:HOUSE_FILM_DIR, Env:SOL -EA SilentlyContinue
"done $(Get-Date -Format HH:mm:ss)" | Out-File -Append $log
schtasks /delete /tn VideoAB /f
