#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Servicio de reportes de resultados Load Test (solo admin).

Formatos:
  - HTML imprimible (vista A4 compatible) — exportar a PDF via browser print.
  - CSV UTF-8 BOM con separador ";" (abrir directamente en Excel Windows).
No se usa reportlab/openpyxl (prohibido externos). Todo stdlib.
"""
import csv
import io
import json
import os
from datetime import datetime as _dt
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from guias_coodescor.config import DATA_DIR
from guias_coodescor.web.views.base import card_accion, escape, page


LAST_FILENAME = "loadtest_LAST.txt"


def _last_path() -> Path:
    return Path(DATA_DIR) / LAST_FILENAME


def leer_ultimo_resumen() -> Optional[Dict[str, Any]]:
    """Devuelve el diccionario completo de resumen.json asociado a loadtest_LAST.txt.
    None si no hubo ejecución o los archivos están corruptos."""
    lp = _last_path()
    if not lp.exists():
        return None
    try:
        contenido = lp.read_text(encoding="utf-8").splitlines()
        resumen_path = None
        tag = None
        for ln in contenido:
            if ln.startswith("Resumen_json="):
                resumen_path = ln.split("=", 1)[1].strip()
            if ln.startswith("Tag="):
                tag = ln.split("=", 1)[1].strip()
        if not resumen_path and tag:
            resumen_path = str(Path(DATA_DIR) / f"loadtest_{tag}_resumen.json")
        if not resumen_path:
            return None
        rp = Path(resumen_path)
        if not rp.is_absolute():
            rp = Path(DATA_DIR) / rp
        if not rp.exists():
            return None
        return json.loads(rp.read_text(encoding="utf-8"))
    except Exception:
        return None


def leer_ultimo_jsonl(resumen: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not resumen:
        return rows
    jpath = resumen.get("jsonl_path") or ""
    if not jpath:
        return rows
    jp = Path(jpath)
    if not jp.is_absolute():
        jp = Path(DATA_DIR) / jp
    if not jp.exists():
        return rows
    with open(jp, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                rows.append(json.loads(ln))
            except Exception:
                continue
    return rows


def rows_para_csv(resumen: Dict[str, Any]) -> List[List[Any]]:
    """Rows CSV: filas detalle (eventos). Cabeceras incluidas en pos 0."""
    header = [
        "ts_iso",
        "operacion",
        "ok",
        "guia_id",
        "usuario",
        "rol_usuario",
        "duracion_ms",
        "error",
        "ciudad",
        "docs_mini",
        "mensaje_extra",
        "tag_lote",
    ]
    out: List[List[Any]] = [header]
    tag = resumen.get("tag", "") if resumen else ""
    for ev in leer_ultimo_jsonl(resumen):
        try:
            ts = ev.get("ts")
            ts_iso = _dt.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] if ts else ""
        except Exception:
            ts_iso = ""
        dx = ev.get("datos_extra") if isinstance(ev.get("datos_extra"), dict) else {}
        ciudad = ""
        if isinstance(dx, dict):
            ciudad = dx.get("ciudad") or ""
            docs = dx.get("docs") or []
            if isinstance(docs, list):
                docs_str = " | ".join(f"{d.get('prefijo','')} {d.get('numero','')}".strip() for d in docs[:3] if isinstance(d, dict))
            else:
                docs_str = ""
            msg_e = str(dx.get("mensaje") or dx.get("tipo") or "")[:180]
        else:
            docs_str = ""
            msg_e = ""
        out.append([
            ts_iso,
            str(ev.get("operacion") or ""),
            "1" if ev.get("ok") else "0",
            str(ev.get("guia_id") or ""),
            str(ev.get("usuario") or ""),
            str(ev.get("rol_usuario") or ""),
            f"{float(ev.get('dur_ms') or 0):.3f}".replace(".", ","),
            (str(ev.get("error") or "")[:500]),
            str(ciudad),
            docs_str,
            msg_e,
            tag,
        ])
    return out


def generar_csv_bytes(resumen: Dict[str, Any]) -> Tuple[bytes, str]:
    """Devuelve (bytes_csv_utf8_bom, nombre_archivo)."""
    if not resumen:
        rows = [["sin ejecución"]]
        nombre = "loadtest_sin_ejecucion.csv"
    else:
        rows = rows_para_csv(resumen)
        tag = resumen.get("tag") or "ultimo"
        nombre = f"loadtest_{tag}_resultados.csv"
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    for r in rows:
        writer.writerow(list(r))
    text = buf.getvalue()
    return ("\ufeff" + text).encode("utf-8"), nombre


def vista_reporte_admin(user: Dict[str, Any]) -> Tuple[int, str, Optional[Dict[str, Any]]]:
    """Devuelve (status, html, resumen_dict). Status 200 o 404 empty-state.
    NOTA: ya se llamó requerir_rol antes."""
    resumen = leer_ultimo_resumen()
    body = _cuerpo_reporte_html(resumen)
    title = "Reporte Load Test · Última Ejecución" if resumen else "Reporte Load Test · Sin ejecución"
    return 200, page(title, body, user=user), resumen


def _kpi(titulo: str, valor: str, subtitulo: str = "", estilo: str = "") -> str:
    return f"""
    <div class="cardaccion kpi" style="background:var(--surface-elevada);color:var(--texto);border:1px solid var(--borde);{estilo}">
      <b style="font-size:15px;color:var(--texto-secundario);letter-spacing:.3px">{escape(titulo)}</b>
      <span style="font-size:28px;font-weight:900;color:var(--azul);margin-top:6px;display:block">{escape(str(valor))}</span>
      <span style="display:block;font-size:12px;color:var(--texto-secundario);margin-top:2px">{escape(str(subtitulo))}</span>
    </div>"""


def _tabla_por_rol(por_rol: Dict[str, Dict[str, int]]) -> str:
    if not por_rol:
        return "<p>Sin datos por rol.</p>"
    filas = []
    tot_ok = tot_err = tot_total = 0
    for rol, m in sorted(por_rol.items()):
        ok = int(m.get("ok", 0))
        total = int(m.get("total", 0))
        er = int(m.get("errores", 0))
        tasa = (100.0 * ok / total) if total > 0 else 0.0
        filas.append(f"<tr><td>{escape(rol)}</td><td>{total}</td><td style='color:var(--ok,#15803d);font-weight:700'>{ok}</td><td style='color:var(--err,#b91c1c);font-weight:700'>{er}</td><td>{tasa:.2f}%</td></tr>")
        tot_ok += ok; tot_total += total; tot_err += er
    tasa_tot = (100.0 * tot_ok / tot_total) if tot_total > 0 else 0.0
    filas.append(f"<tr style='background:var(--surface)'><td><b>TOTAL</b></td><td><b>{tot_total}</b></td><td><b>{tot_ok}</b></td><td><b>{tot_err}</b></td><td><b>{tasa_tot:.2f}%</b></td></tr>")
    return f"""
    <h3 style="margin-top:18px">Resultados por tipo de usuario (rol)</h3>
    <div class="tbl-wrap" style="overflow:auto;border:1px solid var(--borde);border-radius:12px;background:var(--surface)">
      <table class="tbl" style="width:100%;border-collapse:collapse">
        <thead><tr style="background:var(--surface-elevada)">
          <th style="padding:10px 12px;text-align:left;border-bottom:1px solid var(--borde)">Rol</th>
          <th style="padding:10px 12px;text-align:right;border-bottom:1px solid var(--borde)">Total eventos</th>
          <th style="padding:10px 12px;text-align:right;border-bottom:1px solid var(--borde)">OK</th>
          <th style="padding:10px 12px;text-align:right;border-bottom:1px solid var(--borde)">Errores</th>
          <th style="padding:10px 12px;text-align:right;border-bottom:1px solid var(--borde)">Tasa éxito</th>
        </tr></thead>
        <tbody>{''.join(filas)}</tbody>
      </table>
    </div>"""


def _tabla_por_operacion(ops: Dict[str, Dict[str, Any]]) -> str:
    if not ops:
        return "<p>Sin métricas de operaciones.</p>"
    filas = []
    for op, m in sorted(ops.items()):
        filas.append(
            f"<tr><td><b>{escape(op)}</b></td>"
            f"<td>{int(m.get('count',0))}</td>"
            f"<td>{m.get('min_ms',0):.1f}</td>"
            f"<td>{m.get('p50_ms',0):.1f}</td>"
            f"<td style='color:var(--azul);font-weight:700'>{m.get('p95_ms',0):.1f}</td>"
            f"<td style='color:var(--err,#b91c1c);font-weight:800'>{m.get('p99_ms',0):.1f}</td>"
            f"<td>{m.get('max_ms',0):.1f}</td>"
            f"<td>{m.get('avg_ms',0):.1f}</td></tr>"
        )
    return f"""
    <h3 style="margin-top:22px">Métricas de procesamiento por operación (ms)</h3>
    <div class="tbl-wrap" style="overflow:auto;border:1px solid var(--borde);border-radius:12px;background:var(--surface)">
      <table class="tbl" style="width:100%;border-collapse:collapse;font-size:14px">
        <thead><tr style="background:var(--surface-elevada)">
          <th style="padding:10px 12px;text-align:left;border-bottom:1px solid var(--borde)">Operación</th>
          <th style="padding:10px 12px;text-align:right;border-bottom:1px solid var(--borde)">N</th>
          <th style="padding:10px 12px;text-align:right;border-bottom:1px solid var(--borde)">min</th>
          <th style="padding:10px 12px;text-align:right;border-bottom:1px solid var(--borde)">p50</th>
          <th style="padding:10px 12px;text-align:right;border-bottom:1px solid var(--borde)">p95</th>
          <th style="padding:10px 12px;text-align:right;border-bottom:1px solid var(--borde)">p99</th>
          <th style="padding:10px 12px;text-align:right;border-bottom:1px solid var(--borde)">max</th>
          <th style="padding:10px 12px;text-align:right;border-bottom:1px solid var(--borde)">avg</th>
        </tr></thead>
        <tbody>{''.join(filas)}</tbody>
      </table>
    </div>"""


def _tabla_top_errores(top: List[Dict[str, Any]]) -> str:
    if not top:
        return "<p style='color:var(--ok,#15803d);font-weight:700'>✅ Sin incidencias registradas.</p>"
    filas = []
    for r in top:
        filas.append(f"<tr><td style='color:var(--err,#b91c1c);font-weight:700'>{int(r.get('count',0))}</td><td>{escape(str(r.get('mensaje',''))[:300])}</td></tr>")
    return f"""
    <h3 style="margin-top:22px">Incidencias · Top errores más frecuentes</h3>
    <div class="tbl-wrap" style="overflow:auto;border:1px solid var(--borde);border-radius:12px;background:var(--surface)">
      <table class="tbl" style="width:100%;border-collapse:collapse">
        <thead><tr style="background:var(--surface-elevada)">
          <th style="padding:10px 12px;text-align:right;width:90px;border-bottom:1px solid var(--borde)">Cantidad</th>
          <th style="padding:10px 12px;text-align:left;border-bottom:1px solid var(--borde)">Mensaje</th>
        </tr></thead>
        <tbody>{''.join(filas)}</tbody>
      </table>
    </div>"""


def _cuerpo_reporte_html(resumen: Optional[Dict[str, Any]]) -> str:
    if not resumen:
        return """
        <section class="container" style="max-width:900px;margin:0 auto">
          <h1>📊 Reporte de Load Test</h1>
          <div class="cardaccion" style="background:#fff7ed;color:#9a3412;border:1px solid #fdba74">
            <b>No hay ejecución de load test aún.</b>
            <span>Ejecuta <code>python loadtest_500_ventas_cedis.py --guias 500 --workers 50</code> para generar el primer reporte.</span>
          </div>
        </section>"""

    tag = resumen.get("tag") or ""
    tasa = resumen.get("tasa_exito_pct", 0.0)
    estilo_ok = "" if tasa >= 95 else "background:#fef2f2;border:1px solid #fecaca;color:#7f1d1d"
    if tasa >= 99:
        estilo_ok = "background:#ecfdf5;border:1px solid #a7f3d0;color:#065f46"
    elif tasa >= 95:
        estilo_ok = "background:#eff6ff;border:1px solid #bfdbfe;color:#1e3a8a"
    kpis = f"""
    <div class="kpis-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:14px 0 16px">
      {_kpi("Tag lote", str(tag or "-"), "Fecha y hora de la ejecución")}
      {_kpi("Guías parametrizadas", resumen.get("guias_parametro", "?"), "Objetivo de la prueba")}
      {_kpi("Guías creadas OK", f"{resumen.get('guias_creadas_ok','?')}", "Fase A VENTAS")}
      {_kpi("Workers concurrencia", f"{resumen.get('workers','?')}", "Threads paralelos")}
      {_kpi("Duración total", f"{float(resumen.get('duracion_total_seg',0)):.1f} s", "FASE A + FASE B")}
      {_kpi("Throughput", f"{float(resumen.get('throughput_guias_por_seg',0)):.2f} /s", "Guías x segundo")}
      {_kpi("Tasa éxito total", f"{tasa:.2f}%", f"{resumen.get('total_ok','?')} OK de {resumen.get('total_eventos','?')} eventos", estilo_ok)}
      {_kpi("Eventos erróneos", f"{resumen.get('n_errores_totales',0)}", "Incidencias registradas", "#888" not in estilo_ok and estilo_ok or "")}
    </div>"""

    # Barra de botones acciones (no se imprime)
    acciones = f"""
    <div class="acciones-reporte no-print" style="display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 22px">
      <a class="btn primario" href="/api/loadtest/ultimo.csv" download>⬇️ Descargar Excel (CSV)</a>
      <button class="btn" onclick="window.print()">🖨️ Exportar PDF (Imprimir)</button>
      <a class="btn" href="/admin">← Volver Admin</a>
    </div>"""

    # Encabezado print-only
    enc_print = f"""
    <div class="only-print" style="display:none">
      <h2 style="margin:0 0 4px">Guías Coodescor · Reporte Load Test</h2>
      <p style="margin:0 0 14px;color:#475569">Tag {escape(str(tag or ''))} · Fecha impresión {_dt.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>"""

    return f"""
    <section class="container" style="max-width:1200px;margin:0 auto">
      {enc_print}
      <h1 style="margin-bottom:6px">📊 Reporte de Resultados · Load Test</h1>
      <p class="sub" style="color:var(--texto-secundario);margin:0 0 4px">Simulación concurrencia 500 guías — usuarios Ventas vs CEDIS trabajando simultáneamente.</p>
      {acciones}
      {kpis}
      {_tabla_por_rol(resumen.get("por_rol") or {})}
      {_tabla_por_operacion(resumen.get("por_operacion_ms") or {})}
      {_tabla_top_errores(resumen.get("top_errores") or [])}
      <div class="notas" style="margin-top:26px;padding:14px;border:1px dashed var(--borde);border-radius:12px;background:var(--surface)">
        <h4 style="margin:0 0 6px">Notas</h4>
        <ul style="margin:0 0 0 18px;padding:0;color:var(--texto-secundario);font-size:13px;line-height:1.7">
          <li>Tiempos p50 / p95 / p99 expresados en milisegundos por operación.</li>
          <li>CSV UTF-8 BOM + separador <b>;</b> compatible con Excel (doble click directamente).</li>
          <li>PDF vía <b>Imprimir → Guardar como PDF</b> en navegador. Hoja A4 optimizada en CSS.</li>
          <li>0 registros "database is locked" = base de datos SQLite no saturó bajo concurrencia.</li>
        </ul>
      </div>
    </section>"""
