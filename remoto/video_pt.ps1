# Runs on the RTX (as a scheduled task, so it survives SSH): path-traced film with the OIDN denoiser, then the MP4
$r = "$env:USERPROFILE\recorrido-3d"
$log = "$r\ue\video_pt.log"
$env:LUZ_DENOISER = "oidn"; $env:LUZ_PT_BIAS = "1.0"; $env:LUZ_PT_SPP = "32"; $env:AMB_SKY = "360"
"start $(Get-Date -Format HH:mm)" | Out-File $log
powershell -ExecutionPolicy Bypass -File "$r\ue_pipeline.ps1" -Steps fab+escena+ambiente+video_pt *>> $log
$ff = "$r\openhouse-3d\.venv\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
& $ff -y -loglevel error -framerate 24 -i "$r\ue\renders\PT\f.%04d.png" `
    -vf "fade=t=in:st=0:d=0.6,fade=t=out:st=40.8:d=0.7,format=yuv420p" `
    -c:v libx264 -crf 17 -preset slow -movflags +faststart "$r\ue\recorrido_ue_pt4.mp4" *>> $log
"done $(Get-Date -Format HH:mm)" | Out-File -Append $log
