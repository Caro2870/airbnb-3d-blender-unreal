# Tarea programada (GPU), tarea PruebaMejora: arma la escena (manta por simulación de tela, cono de focos FOCO_ANG),
# la guarda, rehace el mapa de objetos y renderiza cada grupo de luces por separado para las fotos 1 y 5.
# Luego en la PC local: ajustar_luz.py --fisico con los npz nuevos -> house.LUZ_FOTO -> render fino (prueba_fina.ps1).
param([string]$Ang = "50", [string]$Etiqueta = "v1")
$r = "$env:USERPROFILE\recorrido-3d"; $repo = "$r\openhouse-3d"; $log = "$r\prueba_mejora.log"; Set-Location $repo
"start $(Get-Date -Format HH:mm:ss) ang=$Ang" | Out-File $log
$env:ARCHVIZ_PYTHON = "$repo\.venv\Scripts\python.exe"
$env:ACABADOS = "original"; $env:LUZ = "neutra"; $env:HOUSE_HIDE = "Aire_Interior,Polvo"; $env:BIBLIO = "1"; $env:REALISMO = ""
$env:FOCO_ANG = $Ang
$b = "$env:USERPROFILE\tools\blender-5.2.3-windows-x64\blender.exe"
$bak = "$r\mvp\respaldo_$Etiqueta"; New-Item -ItemType Directory -Force $bak | Out-Null
Copy-Item "$r\mvp\luces_*.npz", "$r\mvp\mapa_*.npz" $bak -Force -EA SilentlyContinue
& $b -b --python-exit-code 1 --python run.py -- --house apartaestudio --device OPTIX --cam all --samples 1 --scale 10 --no-polish --norender --save 2>&1 | Select-String "geometry done|manta|Error|Traceback|line " | Out-File -Append $log
$blend = "$repo\houses\apartaestudio\output\apartaestudio.blend"
foreach ($c in "cuarto", "cabecero") {
  & $b -b $blend --python "$r\remoto\mapa_objetos.py" -- "$r\mvp\mapa_$c.npz" $c 47 2 "1080,1920" 2>&1 | Select-String "\[mapa\]|Error|Traceback" | Out-File -Append $log
  & $b -b $blend --python-exit-code 1 --python "$r\remoto\luces_separadas.py" -- "$r\mvp\luces_$c.npz" $c 47 64 2>&1 | Select-String "\[luces\]|Error|Traceback|line " | Out-File -Append $log
}
"done $(Get-Date -Format HH:mm:ss)" | Out-File -Append $log
schtasks /delete /tn PruebaMejora /f
