# Se ejecuta en la máquina RTX: crea el venv de OpenHouse 3D y hace un render de prueba en GPU.
$ErrorActionPreference = "Continue"
$root = "$env:USERPROFILE\recorrido-3d"
$repo = "$root\openhouse-3d"
$py = Get-ChildItem "$env:APPDATA\uv\python" -Directory |
    Where-Object Name -like "cpython-3.11.18*" |
    ForEach-Object { Join-Path $_.FullName "python.exe" }

Set-Location $repo
if (-not (Test-Path .venv)) { & $py -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -q --upgrade pip 2>&1 | Out-Null
& .\.venv\Scripts\python.exe -m pip install -q -e ".[dev]" 2>&1 | Select-Object -Last 3

$env:ARCHVIZ_PYTHON = "$repo\.venv\Scripts\python.exe"
$env:BLENDER = "$env:USERPROFILE\tools\blender-5.2.3-windows-x64\blender.exe"
& $env:BLENDER -b --python-exit-code 1 --python run.py -- --house _template --cam hero --scale 25 --samples 16 --device OPTIX --no-polish 2>&1 |
    Select-String -Pattern "Saved|Error|error|Traceback|device|Device" | Select-Object -Last 15
"EXIT $LASTEXITCODE"
Get-ChildItem -Recurse -Include *.png -Path $repo -ErrorAction SilentlyContinue |
    Where-Object LastWriteTime -gt (Get-Date).AddMinutes(-15) | Select-Object FullName
