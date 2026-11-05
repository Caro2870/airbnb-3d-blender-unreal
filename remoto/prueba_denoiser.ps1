# Runs on the RTX: path-traced test stills for each denoiser / exposure combination, each kept in renders\test_<den>_<bias>
$r = "$env:USERPROFILE\recorrido-3d"
$log = "$r\ue\prueba_denoiser.log"
"start $(Get-Date -Format HH:mm)" | Out-File $log
foreach ($c in @(@("oidn", "0.5"), @("oidn", "-0.5"), @("nne_gpu", "0.5"))) {
    $env:LUZ_DENOISER = $c[0]; $env:LUZ_PT_BIAS = $c[1]; $env:LUZ_PT_SPP = "32"
    "### $($c[0]) bias $($c[1])" | Out-File -Append $log
    powershell -ExecutionPolicy Bypass -File "$r\ue_pipeline.ps1" -Steps escena+pt *>> $log
    $dst = "$r\ue\renders\test_$($c[0])_$($c[1])"
    New-Item -ItemType Directory -Force $dst | Out-Null
    Get-ChildItem "$r\ue\renders" -Filter "PT_*" -File | Copy-Item -Destination $dst
}
"done $(Get-Date -Format HH:mm)" | Out-File -Append $log
