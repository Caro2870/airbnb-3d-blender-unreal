# Recorrido 3D de un Airbnb con IA (Blender + Unreal Engine 5.8)

Reconstrucción de un apartaestudio real (un apartaestudio de playa con balcón) a partir de **7 fotos del
anuncio y el plano**, sin escaneo 3D: Claude Code lee las fotos, **escribe código Python que modela la casa** en
Blender, compara cada render contra las fotos reales, corrige, y luego lleva el modelo a **Unreal Engine 5.8** para un
recorrido cinematográfico con **Path Tracer** en una RTX 5060 Ti (16 GB). Todo con herramientas gratuitas.

Inspirado en un post de ingenia.ai ("Claude reconstruyó un Airbnb en Blender y UE5 a partir de unas pocas fotos").

## Resultado

| Versión | Qué tiene | Render |
|---|---|---|
| Blender Cycles | primer borrador, cámaras calibradas a las 7 fotos | ~10 min |
| UE Lumen v3 | muebles detallados, cocina, baño, exterior | 3,4 min |
| UE Path Tracer (pt3) | sin grano (OIDN), exposición corregida, sofá y palmeras de Fab | 55 min |
| UE Path Tracer (pt4) | plano secuencia de 41 s, cielo HDRI con nubes, mar con oleaje, luz cálida | 83 min |

Auditoría independiente final (otro modelo, ver `auditoria_final.md`): **realismo 3,5/10, fidelidad 4,5/10, estilo
de la referencia 4/10**. Los interiores con sol directo llegan a "archviz decente" (5/10); el exterior y los textiles
son lo más débil.

## Arquitectura

```
fotos + plano ──► Claude Code (local) ──scp/ssh──► PC con RTX (Windows, OpenSSH)
                                                     │
   blender/apartaestudio/*.py  (paquete de casa      │  Blender 5.2 + OpenHouse 3D
   de OpenHouse 3D: plan, paredes, muebles,          ▼
   materiales, cámaras de las fotos)            render.ps1 ──► renders de comparación
                                                     │
                                       remoto/bake_export.py (hornea materiales → GLB)
                                                     ▼
                                       ue/Apartaestudio (UE 5.8, scripts Python headless)
                                         armar_apto.py   → importa el GLB (Interchange), luces
                                         fab_colocar.py  → sofá/palmeras/carros de Fab
                                         escena_apto.py  → sol, vidrio, focos, cámaras, secuencias, configs MRQ
                                         ambiente.py     → cielo HDRI, mar, sol suave, gradación
                                                     ▼
                                       remoto/ue_pipeline.ps1 → Movie Render Queue (Lumen o Path Tracer)
                                       remoto/video_pt.ps1    → tarea programada + ffmpeg → MP4
```

- **Base de modelado:** [OpenHouse 3D](https://github.com/yunfanye/openhouse-3d) (MIT). Este repo solo trae el
  paquete de casa `blender/apartaestudio/`; se copia a `openhouse-3d/houses/apartaestudio/`.
- Coordenadas: Blender en metros (x = ancho, y = hacia la ventana, z = arriba); Unreal = `(100x, −100y, 100z)` cm.

## Cómo correrlo

En la PC con la RTX (`ssh rtx`):

```powershell
# 1. Blender: construir y guardar el .blend (o renderizar cámaras de comparación)
powershell -ExecutionPolicy Bypass -File recorrido-3d\render.ps1 -Extra "--norender --save"
powershell -ExecutionPolicy Bypass -File recorrido-3d\render.ps1 -Cams all -Samples 32 -Scale 50   # LUZ=neutra para comparar con fotos

# 2. Hornear y exportar a GLB
blender -b <apartaestudio.blend> --python recorrido-3d\bake_export.py -- recorrido-3d\export\apartaestudio.glb

# 3. Unreal: armar nivel, modelos Fab, escena, ambiente y fotos de prueba
powershell -ExecutionPolicy Bypass -File recorrido-3d\ue_pipeline.ps1 -Steps armar+fab+escena+ambiente+prueba
#    pasos: armar, fab, escena, ambiente, prueba (Lumen JPG), pt (Path Tracer JPG), video (Lumen), video_pt

# 4. Video final con Path Tracer (como tarea programada, sobrevive al cierre de SSH)
schtasks /run /tn VideoPT        # ejecuta remoto\video_pt.ps1
```

Variables útiles: `LUZ_DENOISER=oidn|nne_gpu|nne_cpu`, `LUZ_PT_BIAS` (EV del Path Tracer), `LUZ_PT_SPP`,
`AMB_SKY` (brillo del cielo HDRI), `AMB_SKYLIGHT`, `FAB_SOFA_ROLL/YAW`.

## Lecciones aprendidas (lo que costó horas)

### Flujo de calidad
- **Comparar siempre contra la foto real** desde la misma cámara (cámaras resueltas por foto, luz neutra nublada para
  comparar; el atardecer solo para el video). Hoja foto-vs-render en cada iteración.
- **Usar otro modelo como juez** para no sesgarse, pero **verificar sus afirmaciones**: los jueces inventaron objetos
  "faltantes" que sí estaban. Pedirle que cite el cuadro/foto de cada crítica y que diga "no estoy seguro".
- Los jueces dan ±1 punto de ruido entre corridas; mirar tendencias, no un número.
- El dueño detecta cosas que el juez no: profundidad del balcón, una pared inventada, el color del piso exterior, la
  posición de la regadera, el tamaño del edificio vecino. Preguntarle temprano.
- **No inventar el entorno**: poner palmeras "porque se ven bonitas" bajó la fidelidad (la vista real es un parqueo).

### Blender / OpenHouse
- Telas con simulación de cloth se caían a través del sofá → manta analítica (`_hang_sheet`), doble capa con winding
  invertido, sin solidify (el solidify daba triángulos negros).
- Cuadros que se veían grises: reflejo rasante + imágenes oscuras → material mate + leve emisión + texturas aclaradas.
- Lavamanos "con madera adentro": la tapa del mueble cortaba la poza, y UE culea caras traseras → caras duplicadas
  invertidas.
- Hornear materiales procedurales a GLB (`bake_export.py`) es lo que hace posible llevarlo a Unreal.

### Unreal Engine 5.8 (headless con Python)
- Commandlet: `UnrealEditor-Cmd.exe proj -run=pythonscript -script=... -nullrhi`. **`unreal.log` no siempre llega al
  log del commandlet**: escribir los reportes a un archivo propio.
- GLTFImporter ya no existe en 5.8 → plugins `Interchange` + `InterchangeEditor`, `import_scene`.
- Los nombres de propiedades/enum cambian entre versiones → helpers `prop()` / `enum()` que prueban varios nombres.
- Exposición: la automática se ignoraba → **exposición física por cámara** (ISO 100, 1/60, f/x) + bias.
- **Path Tracer**: requiere `r.PathTracing=True` y formatos SM6 en `DefaultEngine.ini`.
  - El denoiser por defecto (NNE sobre DirectML) da **cuadros negros** en Blackwell → `NNEDenoiser 0` +
    `r.PathTracing.Denoiser.Name OIDN Denoiser Plugin` como *start console commands* del MRQ. Con OIDN, 32 spp
    ya salen limpios.
  - El PT ve ~2 EV distinto que Lumen: cámaras propias para el PT (bias 0.5–1.0 vs 2.5 en Lumen). Renderizar el PT
    con las cámaras de Lumen quemó todos los blancos.
  - 1 temporal sample (sin motion blur) divide el tiempo a la mitad: ~6 s/cuadro 1080p en una 5060 Ti.
- `spawn_actor_from_object` devuelve `None` en el commandlet para algunas mallas → `spawn_actor_from_class(StaticMeshActor)`
  + `set_static_mesh`.
- **Fab**: los FBX de Interchange salen con materiales "FBXLegacy" sin texturas a veces (las hojas .tga no se
  importaron) → importar la textura aparte y cablear `DiffuseColorMap` / `OpacityMaskMap` (canal alfa) + blend
  Masked + two-sided. Un OBJ llegó Y-up (sofá acostado) → roll 90°. Un GLB de 90 piezas pierde posiciones si se
  importa como assets: usar `import_scene`.
- **HDRI Backdrop** (plugin `HDRIBackdrop`, BP en `/HDRIBackdrop/Blueprints/HDRIBackdrop`): trae un piso proyectado
  que tapa el terreno → bajar el actor 60 m. El PT lo ve ~3× más oscuro que Lumen; su skylight se escala aparte.
- Mar: `BlendAngleCorrectedNormals` y `FlattenNormal` son *funciones*, no expresiones → Add + Normalize + Lerp hacia
  (0,0,1). Normal map de oleaje generado con FFT (espectro direccional).
- Plano secuencia: los giros junto a tabiques barren paredes en cuadro → girar solo en zonas abiertas, ~3 s por giro;
  previsualizar en Lumen (5 min) antes del PT (1,5 h).

### Windows remoto por SSH
- PowerShell 5.1: `;` en vez de `&&`, comillas escapadas `\"`, `-ExecutionPolicy Bypass`.
- **Los procesos lanzados desde SSH mueren al cerrar la sesión** (incluso con `Start-Process`) → `schtasks /create
  /it` + `schtasks /run` para renders largos.
- `Remove-Item` sobre una carpeta no vacía pide confirmación y **cuelga una tarea oculta** → filtrar con `-File`.

## Lo que falta para subir de nivel (según la auditoría final)
1. Exterior fiel a la foto (parqueo gris, calle, mar lejano) en vez de palmeras.
2. Sofá gris taupe (no caramelo), silla de oficina de malla negra.
3. Gradación más neutra: paredes blancas, no beige; cocina y baño menos oscuros.
4. Telas con pliegues (edredón acolchado, toalla), utilería en la cocina, gabinetes lacados con reflejo.

## Qué no está en este repo
Fotos del anuncio, plano, texturas derivadas de las fotos, renders, modelos de Fab (licencias de sus autores),
HDRIs (Poly Haven, CC0) y el `.venv`.
