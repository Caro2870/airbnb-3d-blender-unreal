# Se ejecuta en la máquina RTX: construye el apartaestudio y renderiza cámaras (o el video) con OpenHouse 3D.
#   render.ps1 -Cams all -Samples 32 -Scale 50
#   render.ps1 -Extra "--film all --film-draft"
param([string]$Cams = "all", [int]$Samples = 32, [int]$Scale = 50, [string]$Extra = "", [switch]$Polish)
$repo = "$env:USERPROFILE\recorrido-3d\openhouse-3d"
Set-Location $repo
$env:ARCHVIZ_PYTHON = "$repo\.venv\Scripts\python.exe"
$env:BLENDER = "$env:USERPROFILE\tools\blender-5.2.3-windows-x64\blender.exe"
$args_ = @("-b", "--python-exit-code", "1", "--python", "run.py", "--", "--house", "apartaestudio", "--device", "OPTIX")
if ($Extra) { $args_ += $Extra.Split(" ") } else { $args_ += @("--cam", $Cams, "--samples", "$Samples", "--scale", "$Scale"); if (-not $Polish) { $args_ += "--no-polish" } }
& $env:BLENDER @args_ 2>&1 | Select-String -Pattern "Saved|Error|error|Traceback|File |line |Exception|device|wrote|mp4" | Select-Object -Last 40
"EXIT $LASTEXITCODE"
