# Corre en la RTX por ssh directo (no usa GPU): arma la escena sin render, la guarda y saca el mapa de objetos de las
# cámaras gemelas de las fotos 1 y 5.  Luego, en la PC local:
#   scp rtx:recorrido-3d/mvp/mapa_*.npz .  ;  python remoto\color_objetos.py fotos\jpg\foto01.jpg <render> --mapa mapa_cuarto.npz
param([switch]$SinArmar)   # -SinArmar: reusar el .blend ya guardado (si solo cambió la cámara o nada)
$r = "$env:USERPROFILE\recorrido-3d"; $repo = "$r\openhouse-3d"; Set-Location $repo
$env:ARCHVIZ_PYTHON = "$repo\.venv\Scripts\python.exe"
$env:ACABADOS = "original"; $env:LUZ = "neutra"; $env:HOUSE_HIDE = "Aire_Interior,Polvo"; $env:BIBLIO = "1"
$b = "$env:USERPROFILE\tools\blender-5.2.3-windows-x64\blender.exe"
if (-not $SinArmar) {
  & $b -b --python-exit-code 1 --python run.py -- --house apartaestudio --device OPTIX --cam all --samples 1 --scale 10 --no-polish --norender --save 2>&1 | Select-String "\[build\]|Error|Traceback" | ForEach-Object Line
}
$blend = "$repo\houses\apartaestudio\output\apartaestudio.blend"
New-Item -ItemType Directory -Force "$r\mvp" | Out-Null
foreach ($c in "cuarto", "cabecero") {
  & $b -b $blend --python "$r\remoto\mapa_objetos.py" -- "$r\mvp\mapa_$c.npz" $c 47 2 "1080,1920" 2>&1 | Select-String "\[mapa\]|Error|Traceback" | ForEach-Object Line
}
