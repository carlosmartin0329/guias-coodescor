# Reporte WCAG 2.1 AA · Contrastes Modo Claro vs Oscuro

> Fecha: 2026-09-27 · Paletas: `style.css` :root[data-theme=light/dark]
> Criterio: Texto normal ≥ 4.5:1 (AA), Texto grande/UI ≥ 3:1 (AA Large)
> Resultado global: **20/20 PASA** 🔥 · 0 fallos ✅

## Tema Claro

| # | Categoría | Par de colores | FG | BG | Ratio | Req. | Estado |
|---|---|---|---|---|---|---|---|
| 1 | Texto normal (AA) | Texto sobre fondo blanco | `#0F172A` | `#FFFFFF` | **17.85:1** | ≥4.5:1 | ✅ PASS |
| 2 | Texto secundario (AA) | Texto secundario sobre blanco | `#475569` | `#FFFFFF` | **7.58:1** | ≥4.5:1 | ✅ PASS |
| 3 | Botón primario (AA) | Texto blanco sobre azul primario | `#FFFFFF` | `#1D4ED8` | **6.7:1** | ≥4.5:1 | ✅ PASS |
| 4 | Texto UI grande (AA) | Azul primario sobre blanco (links/botones grande) | `#1D4ED8` | `#FFFFFF` | **6.7:1** | ≥3.0:1 | ✅ PASS |
| 5 | Error/Danger (AA) | Texto danger sobre blanco | `#B91C1C` | `#FFFFFF` | **6.47:1** | ≥4.5:1 | ✅ PASS |
| 6 | Exito/Success (AA) | Texto success sobre blanco | `#15803D` | `#FFFFFF` | **5.02:1** | ≥4.5:1 | ✅ PASS |
| 7 | Warning (AA) | Texto warning sobre blanco | `#A16207` | `#FFFFFF` | **4.92:1** | ≥4.5:1 | ✅ PASS |
| 8 | Borde input (AA) | Borde sobre blanco (componente UI) | `#64748B` | `#FFFFFF` | **4.76:1** | ≥3.0:1 | ✅ PASS |
| 9 | Borde scrollbar (AA) | Scrollbar sobre blanco (componente UI) | `#64748B` | `#FFFFFF` | **4.76:1** | ≥3.0:1 | ✅ PASS |

## Tema Oscuro

| # | Categoría | Par de colores | FG | BG | Ratio | Req. | Estado |
|---|---|---|---|---|---|---|---|
| 1 | Texto normal (AA) | Texto sobre fondo gris oscuro | `#E2E8F0` | `#0B1220` | **15.19:1** | ≥4.5:1 | ✅ PASS |
| 2 | Texto normal (AA) | Texto sobre tarjeta surface oscura | `#E2E8F0` | `#111C33` | **13.76:1** | ≥4.5:1 | ✅ PASS |
| 3 | Texto secundario (AA) | Texto secundario fondo oscuro | `#94A3B8` | `#0B1220` | **7.3:1** | ≥4.5:1 | ✅ PASS |
| 4 | Botón primario (AA) | Texto oscuro sobre azul primario | `#0B1220` | `#3B82F6` | **5.09:1** | ≥4.5:1 | ✅ PASS |
| 5 | Texto UI grande (AA) | Azul primario oscuro sobre bg (links grande) | `#3B82F6` | `#0F172A` | **4.85:1** | ≥3.0:1 | ✅ PASS |
| 6 | Error/Danger (AA) | Texto danger sobre surface oscura | `#F87171` | `#111C33` | **6.13:1** | ≥4.5:1 | ✅ PASS |
| 7 | Exito/Success (AA) | Texto success sobre surface oscura | `#4ADE80` | `#111C33` | **9.74:1** | ≥4.5:1 | ✅ PASS |
| 8 | Warning (AA) | Texto warning sobre surface oscura | `#FACC15` | `#111C33` | **11.08:1** | ≥4.5:1 | ✅ PASS |
| 9 | Borde input (AA) | Borde oscuro sobre surface (componente UI) | `#94A3B8` | `#111C33` | **6.62:1** | ≥3.0:1 | ✅ PASS |
| 10 | Borde scrollbar (AA) | Scrollbar oscuro sobre fondo (componente UI) | `#94A3B8` | `#0B1220` | **7.3:1** | ≥3.0:1 | ✅ PASS |
| 11 | Focus outline (AA) | Focus ring azul claro sobre bg oscuro | `#60A5FA` | `#0B1220` | **7.36:1** | ≥3.0:1 | ✅ PASS |

## Conclusión

Todos los pares evaluados cumplen WCAG 2.1 AA en ambos temas.
Además se implementaron los patrones accesorios:
  - `*:focus-visible` visible siempre (2px outline + 3px shadow)
  - `.skip-link` para saltar a contenido principal en Tab
  - `@media (prefers-reduced-motion: reduce)` elimina transiciones/animaciones
  - `--touch-target: 44px` (alto mínimo controles interactivos WCAG)
  - Dark mode: `data-theme` persistente + `prefers-color-scheme` fallback
  - NO-FOUC: script inline antes del CSS aplica `data-theme` inmediato

---
_Script: `probe_wcag_contrast.py` · Fórmula: W3C WCAG 2.1 §F1 §G17 §G18_