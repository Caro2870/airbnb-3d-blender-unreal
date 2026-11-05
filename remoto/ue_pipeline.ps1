# Runs on the RTX machine: rebuild the Unreal level from export\apartaestudio.glb and render with Movie Render Queue.
#   ue_pipeline.ps1 -Steps armar+fab+escena+ambiente+prueba+pt    (any subset, in that order)
#   ue_pipeline.ps1 -Steps video  |  -Steps video_pt
param([string]$Steps = "armar+escena+prueba")
$list = $Steps -split "[+, ]+"        # one string from the command line ($Steps is typed [string], so split into a new var)
$UE = "D:\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
$P = "$env:USERPROFILE\recorrido-3d\ue\Apartaestudio\Apartaestudio.uproject"
$PY = "$env:USERPROFILE\recorrido-3d\ue\Apartaestudio\Content\Python"
$LOG = "$env:USERPROFILE\recorrido-3d\ue"
$OUT = "$env:USERPROFILE\recorrido-3d\ue\renders"

function Script($name) {
    & $UE $P -run=pythonscript -script="$PY\$name.py" -unattended -nosplash -nullrhi -stdout -FullStdOutLogOutput 2>&1 |
        Out-File -Encoding utf8 "$LOG\$name.log"
    Select-String -Path "$LOG\$name.log" -Pattern "\[(armar|escena)_apto\] (saved|actors|glass|sequences|denoiser)|LogPython: Error" |
        ForEach-Object { $_.Line -replace "^.*LogPython: ", "" }
}

function Render($seq, $cfg) {
    $t = Get-Date
    & $UE $P /Game/Apto/Mapa_Apto -game -dx12 -sm6 -LevelSequence="/Game/Apto/$seq" -MoviePipelineConfig="/Game/Apto/$cfg" `
        -windowed -resx=1280 -resy=720 -RenderOffscreen -unattended -NoLoadingScreen -nosplash -stdout 2>&1 |
        Out-File -Encoding utf8 "$LOG\render_$seq.log"
    "$seq/$cfg done in {0:N1} min" -f ((Get-Date) - $t).TotalMinutes
    Select-String -Path "$LOG\render_$seq.log" -Pattern "LogMovieRenderPipeline: Error|LogOpenImageDenoise|LogNNEDenoiser|LogPathTracingDenoising" | ForEach-Object { $_.Line }
}

foreach ($s in $list) {
    "== $s"
    switch ($s) {
        "armar"    { Script "armar_apto" }
        "fab"      { Script "fab_colocar"; Get-Content "$LOG\fab_colocar.txt" }
        "escena"   { Script "escena_apto" }
        "ambiente" { Script "ambiente"; Get-Content "$LOG\ambiente.txt" }
        "prueba"   { Get-ChildItem $OUT -File -Filter "_Foto_*" -ErrorAction SilentlyContinue | Remove-Item; Render "Prueba" "MRQ_Prueba" }
        "pt"       { Get-ChildItem $OUT -File -Filter "PT_*" -ErrorAction SilentlyContinue | Remove-Item; Render "Prueba_PT" "MRQ_PT_Prueba" }
        "video"    { Remove-Item "$OUT\f.*.png" -ErrorAction SilentlyContinue; Render "Recorrido" "MRQ_Recorrido" }
        "video_pt" { Remove-Item "$OUT\PT\*" -ErrorAction SilentlyContinue; Render "Recorrido_PT" "MRQ_PT_Recorrido" }
    }
}
Get-ChildItem $OUT -File | Measure-Object | ForEach-Object { "files in renders: " + $_.Count }
