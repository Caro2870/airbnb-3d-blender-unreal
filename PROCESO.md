# Proceso de mejora: medir contra las fotos

Bitácora de la etapa 2, después de la auditoría del video. Las comparaciones con imagen (solo renders) están en la
página del proyecto: https://caro2870.github.io/apartaestudio-3d/#medir. Las fotos del anuncio no se publican.

## Cómo se mide

- **Color por objeto**: `remoto/color_objetos.py` compara la mediana de cada objeto en CIELAB, foto contra render
  gemelo (misma cámara). Para saber qué píxel es qué objeto usa el mapa que hace `remoto/mapa_objetos.py`. dE: menos
  de 5 casi igual, 5–10 se nota, más de 10 es otro color.
- **Luz**: `remoto/luces_separadas.py` renderiza cada lámpara por separado (la imagen es lineal en las luces) y
  `remoto/ajustar_luz.py` resuelve la mezcla contra la foto en segundos, sin volver a renderizar.
- **Comparaciones**: `remoto/lado_a_lado.py` arma tiras foto | v0 | v1 con el mismo recorte.
- Regla: rehacer el mapa de objetos cada vez que algo cambia de forma o de lugar; con un mapa viejo los números
  mienten (la manta dio dE 17 con el mapa de una versión en la que estaba en el piso).

## Iteraciones

| Versión | Cambio | Resultado medido |
|---|---|---|
| v0 | Punto de partida: escala, cámaras, color y luz por foto ya medidos | dE medio 14,1 (cuarto) y 8,7 (cama) |
| prueba | Focos empotrados de 80° a 50° (`FOCO_ANG`) para explicar el piso naranja de la foto 1 | **Descartada**: paredes mejor (12,8 → 7,7), piso peor (11,2 → 14,9), total 15,9 → 16,8 |
| prueba | Curva de cámara del celular (gamma por canal, `ajustar_luz.py --curva`) | **Descartada**: el ajuste solo aclara todo; el piso no mejora |
| v1 | Manta del sofá por simulación de tela sobre cajas invisibles | Falló: la manta se resbaló entera al piso |
| v2 | Franja de atrás sujeta (como el roce real) y la manta parte apoyada | Manta dE 9,2 → **2,6**; cuarto 14,1 → **13,8** |
| v2 | Cojines: abolladuras x2 y pliegue diagonal por cara | Se lee más blando; todavía más sutil que la foto |

## Lo aprendido

- Una tela suelta sobre un borde se resbala si no tiene con qué agarrarse: sujetar (pin) la parte que en la vida
  real sostiene el roce.
- Si ninguna mezcla de luces, ningún cono y ninguna curva de cámara explican un color, y la otra foto del mismo
  material sí calza, el problema es de esa foto, no del modelo. Insistir solo empeora otra cosa.
- Las colisiones contra cajas simples funcionan mejor que contra la malla real del mueble, con sus cajas
  redondeadas que se superponen.

## Pendiente

- Toalla y almohadas blancas sin arrugado visible.
- Estampado de la banda del sofá distinto al de la foto.
- La manta todavía es algo más rígida que la real (ondas suaves, pocas).
