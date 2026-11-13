# Tarea programada (GPU): arma la escena, la guarda y renderiza cada grupo de luces por separado para la cámara de la foto 1.
$r = "$env:USERPROFILE\recorrido-3d"; $repo = "$r\openhouse-3d"; $log = "$r\prueba_luces.log"; Set-Location $repo
"start $(Get-Date -Format HH:mm:ss)" | Out-File $log
$env:ARCHVIZ_PYTHON = "$repo\.venv\Scripts\python.exe"
$env:ACABADOS = "original"; $env:LUZ = "neutra"; $env:HOUSE_HIDE = "Aire_Interior,Polvo"; $env:BIBLIO = "1"
$b = "$env:USERPROFILE\tools\blender-5.2.3-windows-x64\blender.exe"
& $b -b --python-exit-code 1 --python run.py -- --house apartaestudio --device OPTIX --cam all --samples 1 --scale 10 --no-polish --norender --save 2>&1 | Select-String "geometry done|Error|Traceback" | Out-File -Append $log
$blend = "$repo\houses\apartaestudio\output\apartaestudio.blend"
foreach ($c in "cuarto") {
  & $b -b $blend --python-exit-code 1 --python "$r\remoto\luces_separadas.py" -- "$r\mvp\luces_$c.npz" $c 47 64 2>&1 | Select-String "\[luces\]|Error|Traceback|line " | Out-File -Append $log
}
"done $(Get-Date -Format HH:mm:ss)" | Out-File -Append $log
schtasks /delete /tn PruebaLuces /f
