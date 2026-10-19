#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reporte verificación WCAG 2.1 AA contrast ratios modo claro/oscuro.
Cálculo de luminancia relativa + ratio de contraste (WCAG 2.1 §1.4.3)
Fórmula: L = 0.2126*R + 0.7152*G + 0.0722*B, con sRGB → lineal
Ratio = (L1+0.05) / (L2+0.05), L1 > L2
Criterios AA:  texto normal ≥ 4.5:1, texto grande ≥ 3:1, UI componente ≥ 3:1
"""
from __future__ import annotations

def _srgb_to_lin(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

def hex_to_rgb(hx: str) -> tuple[int, int, int]:
    hx = hx.lstrip("#")
    if len(hx) == 3:
        hx = "".join(ch*2 for ch in hx)
    return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))

def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (_srgb_to_lin(c) for c in rgb)
    return 0.2126*r + 0.7152*g + 0.0722*b

def ratio(hex1: str, hex2: str) -> float:
    L1, L2 = luminance(hex_to_rgb(hex1)), luminance(hex_to_rgb(hex2))
    if L1 < L2: L1, L2 = L2, L1
    return (L1 + 0.05) / (L2 + 0.05)

def check(cat: str, name: str, fg: str, bg: str, min_r: float, theme: str) -> str:
    r = ratio(fg, bg)
    passed = r >= min_r
    return {
        "tema": theme, "cat": cat, "par": name,
        "fg": fg.upper(), "bg": bg.upper(),
        "ratio": round(r, 2), "min": min_r,
        "ok": passed,
    }

rows = [
    # ===== TEMA CLARO =====
    check("Texto normal (AA)",      "Texto sobre fondo blanco",
          "#0f172a", "#ffffff", 4.5, "Claro"),
    check("Texto secundario (AA)",  "Texto secundario sobre blanco",
          "#475569", "#ffffff", 4.5, "Claro"),
    check("Botón primario (AA)",    "Texto blanco sobre azul primario",
          "#ffffff", "#1d4ed8", 4.5, "Claro"),
    check("Texto UI grande (AA)",   "Azul primario sobre blanco (links/botones grande)",
          "#1d4ed8", "#ffffff", 3.0, "Claro"),
    check("Error/Danger (AA)",      "Texto danger sobre blanco",
          "#b91c1c", "#ffffff", 4.5, "Claro"),
    check("Exito/Success (AA)",     "Texto success sobre blanco",
          "#15803d", "#ffffff", 4.5, "Claro"),
    check("Warning (AA)",           "Texto warning sobre blanco",
          "#a16207", "#ffffff", 4.5, "Claro"),
    check("Borde input (AA)",       "Borde sobre blanco (componente UI)",
          "#64748b", "#ffffff", 3.0, "Claro"),
    check("Borde scrollbar (AA)",   "Scrollbar sobre blanco (componente UI)",
          "#64748b", "#ffffff", 3.0, "Claro"),

    # ===== TEMA OSCURO =====
    check("Texto normal (AA)",      "Texto sobre fondo gris oscuro",
          "#e2e8f0", "#0b1220", 4.5, "Oscuro"),
    check("Texto normal (AA)",      "Texto sobre tarjeta surface oscura",
          "#e2e8f0", "#111c33", 4.5, "Oscuro"),
    check("Texto secundario (AA)",  "Texto secundario fondo oscuro",
          "#94a3b8", "#0b1220", 4.5, "Oscuro"),
    check("Botón primario (AA)",    "Texto oscuro sobre azul primario",
          "#0b1220", "#3b82f6", 4.5, "Oscuro"),
    check("Texto UI grande (AA)",   "Azul primario oscuro sobre bg (links grande)",
          "#3b82f6", "#0f172a", 3.0, "Oscuro"),
    check("Error/Danger (AA)",      "Texto danger sobre surface oscura",
          "#f87171", "#111c33", 4.5, "Oscuro"),
    check("Exito/Success (AA)",     "Texto success sobre surface oscura",
          "#4ade80", "#111c33", 4.5, "Oscuro"),
    check("Warning (AA)",           "Texto warning sobre surface oscura",
          "#facc15", "#111c33", 4.5, "Oscuro"),
    check("Borde input (AA)",       "Borde oscuro sobre surface (componente UI)",
          "#94a3b8", "#111c33", 3.0, "Oscuro"),
    check("Borde scrollbar (AA)",   "Scrollbar oscuro sobre fondo (componente UI)",
          "#94a3b8", "#0b1220", 3.0, "Oscuro"),
    check("Focus outline (AA)",     "Focus ring azul claro sobre bg oscuro",
          "#60a5fa", "#0b1220", 3.0, "Oscuro"),
]

failures = [r for r in rows if not r["ok"]]
ok_total = sum(1 for r in rows if r["ok"])

# === Render en markdown ====
md = []
md.append("# Reporte WCAG 2.1 AA · Contrastes Modo Claro vs Oscuro\n")
md.append(f"> Fecha: 2026-09-27 · Paletas: `style.css` :root[data-theme=light/dark]")
md.append(f"> Criterio: Texto normal ≥ 4.5:1 (AA), Texto grande/UI ≥ 3:1 (AA Large)")
md.append(f"> Resultado global: **{ok_total}/{len(rows)} PASA** 🔥" + (" · 0 fallos ✅" if not failures else f" · {len(failures)} fallos ❌"))
md.append("")

for theme in ("Claro", "Oscuro"):
    md.append(f"## Tema {theme}\n")
    md.append("| # | Categoría | Par de colores | FG | BG | Ratio | Req. | Estado |")
    md.append("|---|---|---|---|---|---|---|---|")
    i = 0
    for r in rows:
        if r["tema"] != theme: continue
        i += 1
        st = "✅ PASS" if r["ok"] else "❌ FAIL"
        md.append(f"| {i} | {r['cat']} | {r['par']} | `{r['fg']}` | `{r['bg']}` | **{r['ratio']}:1** | ≥{r['min']}:1 | {st} |")
    md.append("")

if failures:
    md.append("## Fallos detectados\n")
    for f in failures:
        md.append(f"- ❌ **{f['tema']}/{f['par']}**: ratio {f['ratio']}:1 < {f['min']}:1 (FG=`{f['fg']}` BG=`{f['bg']}`). Requiere ajustar paleta.")
    md.append("")
else:
    md.append("## Conclusión\n")
    md.append("Todos los pares evaluados cumplen WCAG 2.1 AA en ambos temas.")
    md.append("Además se implementaron los patrones accesorios:")
    md.append("  - `*:focus-visible` visible siempre (2px outline + 3px shadow)")
    md.append("  - `.skip-link` para saltar a contenido principal en Tab")
    md.append("  - `@media (prefers-reduced-motion: reduce)` elimina transiciones/animaciones")
    md.append("  - `--touch-target: 44px` (alto mínimo controles interactivos WCAG)")
    md.append("  - Dark mode: `data-theme` persistente + `prefers-color-scheme` fallback")
    md.append("  - NO-FOUC: script inline antes del CSS aplica `data-theme` inmediato")

md.append("")
md.append("---")
md.append("_Script: `probe_wcag_contrast.py` · Fórmula: W3C WCAG 2.1 §F1 §G17 §G18_")
content = "\n".join(md)

with open("reporte_contraste_WCAG_AA.md", "w", encoding="utf-8") as f:
    f.write(content)

print(content)
print(f"\n=== Reporte escrito: reporte_contraste_WCAG_AA.md ({len(rows)} pares, {len(failures)} fallos) ===")
