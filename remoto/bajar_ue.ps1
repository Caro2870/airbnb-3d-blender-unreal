# Download the second frame of every still from the RTX Movie Render Queue output and tile them into hoja.jpg
param([string]$Name = "ue_prueba")
$d = "$env:USERPROFILE\Desktop\recorrido-3d\renders\$Name"
New-Item -ItemType Directory -Force $d | Out-Null
$files = C:\Windows\System32\OpenSSH\ssh.exe -o BatchMode=yes rtx 'Get-ChildItem $env:USERPROFILE\recorrido-3d\ue\renders -Filter *.jpeg | % Name'
$keep = $files | Group-Object { $_ -replace '\.\d{4}\.jpeg$', '' } | ForEach-Object { $_.Group | Sort-Object | Select-Object -Last 1 }
foreach ($f in $keep) { C:\Windows\System32\OpenSSH\scp.exe -q "rtx:recorrido-3d/ue/renders/$f" "$d\" }
& $env:USERPROFILE\Desktop\recorrido-3d\.venv\Scripts\python.exe -c @"
from PIL import Image, ImageDraw
import glob, os
fs = sorted(glob.glob(r'$d\_Foto_*.jpeg'), key=os.path.getmtime)
fs.sort(key=lambda f: int(f.split('.')[-2]))
ims = []
for f in fs:
    im = Image.open(f).resize((960, 540)); ImageDraw.Draw(im).text((12, 10), os.path.basename(f)[6:-10], fill='red')
    ims.append(im)
rows = (len(ims) + 1) // 2
s = Image.new('RGB', (1920, 540 * rows), 'black')
for i, im in enumerate(ims):
    s.paste(im, ((i % 2) * 960, (i // 2) * 540))
s.save(r'$d\hoja.jpg', quality=88)
print(len(ims), 'stills')
"@
