---
name: recorrido-3d-ia
description: Reconstruir un espacio real (Airbnb, apartamento, casa, local) en 3D a partir de pocas fotos y un plano, modelándolo con código en Blender (OpenHouse 3D) y renderizando un recorrido fotorrealista en Unreal Engine 5 (Lumen o Path Tracer) en una GPU NVIDIA, con auditorías foto-vs-render. Usar cuando pidan "recorrido 3D", "video tipo walkthrough de mi apartamento/Airbnb", "pasar fotos a 3D", "render en Unreal/Blender de un espacio real", "hacerlo como el video de referencia", o retomar/mejorar el proyecto recorrido-3d-airbnb, aunque no nombren la skill.
---

# Recorrido 3D con IA: fotos + plano → Blender → Unreal Engine 5

Repo de referencia con todo el código y las lecciones: **github.com/Caro2870/airbnb-3d-blender-unreal** (público). Léelo antes
de empezar: el README tiene la arquitectura, los comandos y la lista de trampas ya resueltas. Reutiliza sus scripts en
vez de reescribirlos.

## Qué se puede prometer (y qué no)
- Con 5–10 fotos + plano se logra "archviz decente" (auditoría ~4–5/10 de realismo en interiores con sol). Para 7–8/10
  hacen falta modelos escaneados (Fab/Megascans de pago), telas con pliegues y mucha utilería.
- Las zonas que no salen en ninguna foto son supuestos: documentarlos (`REFERENCES.md`) y **no inventar** entorno
  "bonito" (palmeras, playa) que no corresponde; engaña al huésped y baja la fidelidad.
- Tiempos en una RTX 5060 Ti: Lumen 1080p ~3–5 min por video; Path Tracer 32 spp + OIDN ~6 s/cuadro (~1,5 h para 40 s).

## Flujo
1. **Insumos.** Fotos (HEIC→JPG), plano con medidas, video/post de referencia de estilo. Pregunta al dueño lo que no
   se ve (color del piso exterior, qué hay al final del balcón, dónde está la regadera…): detecta errores que ningún
   juez ve.
2. **Modelo en Blender (OpenHouse 3D).** Paquete de casa: `plan.py` (cotas del plano), `shell.py`, `interior.py`,
   `muebles.py`, `detalles.py`, `surroundings.py`, `house.py` (materiales, cámaras por foto). Cámaras resueltas para
   que cada foto tenga su render gemelo.
3. **Bucle de calidad.** Render de las cámaras con luz neutra (`LUZ=neutra`) → hoja foto-vs-render → corregir.
   Juez independiente (subagente de otro modelo) con prompt estricto: cada crítica cita foto/cuadro, "no estoy
   seguro" si duda. **Verifica sus afirmaciones** antes de actuar (han inventado faltantes).
4. **A Unreal.** `bake_export.py` hornea materiales a GLB → `ue_pipeline.ps1 -Steps armar+fab+escena+ambiente+prueba`.
5. **Look.** Cielo HDRI con nubes (plugin HDRIBackdrop), mar con normal map de oleaje, sol con `light_source_angle`
   ~2.5, lámparas encendidas, gradación cálida suave. Modelos de Fab gratis para lo que el código no logra
   (sofá, plantas, carros), revisando licencia.
6. **Cámara.** Plano secuencia a 1,55 m con lente 18 mm (estilo "huésped caminando"). Girar solo en zonas abiertas,
   ~3 s por giro. Previsualizar en Lumen antes del Path Tracer.
7. **Render final.** Path Tracer + OIDN, como **tarea programada** (`schtasks /it`), ffmpeg a MP4 (versión <30 MB para
   el celular). Auditoría final con otro modelo.

## Trampas conocidas (resueltas en el repo)
- UE 5.8: GLTFImporter no existe → Interchange `import_scene`. Nombres de propiedades cambian → helpers `prop()`/`enum()`.
- `unreal.log` no aparece en el log del commandlet → escribir reportes a archivo.
- Exposición automática ignorada → exposición física por cámara. Path Tracer necesita sus propias cámaras (~2 EV
  menos que Lumen) o quema los blancos.
- Denoiser NNE/DirectML = cuadros negros en Blackwell → `NNEDenoiser 0` + `r.PathTracing.Denoiser.Name OIDN Denoiser
  Plugin` en `start_console_commands` del MRQ.
- `spawn_actor_from_object` → `None` en commandlet: usar `spawn_actor_from_class(StaticMeshActor)` + `set_static_mesh`.
- FBX de Fab: texturas que no entran (.tga) → importar aparte y cablear al MI (Masked, two-sided para hojas). OBJ Y-up
  → roll 90°. GLB de muchas piezas → `import_scene`, no assets sueltos.
- HDRI Backdrop trae piso proyectado → bajar el actor 60 m; el PT lo ve ~3× más oscuro que Lumen.
- `BlendAngleCorrectedNormals`/`FlattenNormal` son funciones de material, no expresiones.
- SSH a Windows: procesos lanzados mueren al cerrar la sesión → tareas programadas. `Remove-Item` de carpeta no vacía
  cuelga un proceso oculto pidiendo confirmación → `-File`. PowerShell 5.1: `;`, `\"`, `-ExecutionPolicy Bypass`.
- Cloth sim atraviesa muebles → telas analíticas. Solidify en telas finas → triángulos negros.

## Seguridad
- Las cuentas (Epic, Fab, GitHub) las inicia el usuario; nunca escribir contraseñas.
- Aceptar licencias de Fab y descargar archivos solo con su visto bueno explícito.
- No subir fotos del anuncio, plano ni modelos de terceros a repos públicos.
