# Arma la escena SIN render, corre el validador de realismo y exporta la geometría para el ajuste por siluetas.
# Resultado: %USERPROFILE%\recorrido-3d\realismo.json y siluetas_cuarto.npz (copiar a la PC local y correr remoto\siluetas.py)
$r = "$env:USERPROFILE\recorrido-3d"; $repo = "$r\openhouse-3d"; Set-Location $repo
$env:ARCHVIZ_PYTHON = "$repo\.venv\Scripts\python.exe"
$env:ACABADOS = "original"; $env:LUZ = "neutra"; $env:HOUSE_HIDE = "Aire_Interior,Polvo"; $env:BIBLIO = "1"
$b = "$env:USERPROFILE\tools\blender-5.2.3-windows-x64\blender.exe"
& $b -b --python-exit-code 1 --python run.py -- --house apartaestudio --device OPTIX --cam all --samples 1 --scale 10 --no-polish --norender --save 2>&1 | Select-String "geometry done|Error|Traceback" | Select-Object -Last 5
$blend = "$repo\houses\apartaestudio\output\apartaestudio.blend"
& $b -b $blend --python "$r\remoto\realismo.py" -- "$r\realismo.json" 2>&1 | Select-String "\[realismo\]|Error|Traceback" | Select-Object -First 60
& $b -b $blend --python "$r\remoto\exportar_siluetas.py" -- "$r\siluetas_cuarto.npz" cuarto 499 895 2>&1 | Select-String "\[siluetas\]|Error|Traceback"
