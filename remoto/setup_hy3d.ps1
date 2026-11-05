# Se ejecuta en la máquina RTX: entorno para Hunyuan3D-2.1 (solo generación de forma) con PyTorch cu128 (Blackwell sm_120).
$ErrorActionPreference = "Continue"
$root = "$env:USERPROFILE\recorrido-3d"
$py = Get-ChildItem "$env:APPDATA\uv\python" -Directory | Where-Object Name -like "cpython-3.11.18*" | ForEach-Object { Join-Path $_.FullName "python.exe" }
Set-Location $root
if (-not (Test-Path hy3d)) { git clone -q --depth 1 https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1.git hy3d 2>&1 | Out-Null }
if (-not (Test-Path hy3d\.venv)) { & $py -m venv hy3d\.venv }
$vp = "$root\hy3d\.venv\Scripts\python.exe"
& $vp -m pip install -q --upgrade pip 2>&1 | Out-Null
& $vp -m pip install -q torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128 2>&1 | Select-Object -Last 2
& $vp -m pip install -q "diffusers==0.30.0" "transformers==4.46.0" "accelerate==1.1.1" "huggingface-hub==0.30.2" einops opencv-python "numpy<2" omegaconf tqdm trimesh pymeshlab pytorch-lightning==1.9.5 torchdiffeq timm scikit-image rembg onnxruntime 2>&1 | Select-Object -Last 3
& $vp -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0), torch.cuda.get_arch_list()[-2:])"
