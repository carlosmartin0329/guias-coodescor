#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exportador periódico de SQLite local a Supabase.

Lee datos de la base SQLite principal (guias.db) y los replica a Supabase
mediante su API REST (PostgREST). Cada tabla se sincroniza con upsert
(clave primaria) para no duplicar registros.

Configuración requerida (variables de entorno o .env):
  SUPABASE_URL       -> https://TU_PROYECTO.supabase.co
  SUPABASE_KEY       -> clave anon o service_role de Supabase
  SUPABASE_BATCH     -> tamaño de lote por inserción (default 100)
  SQLITE_PATH        -> ruta a guias.db (default: C:\ProgramData\Coodescor\Guias\guias.db)

Ejecutar una vez:
  py exportar_a_supabase.py

Ejecutar cada 15 min (bucle interno):
  py exportar_a_supabase.py --loop --interval 900
"""
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("[ERROR] Falta instalar 'requests': pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SQLITE_PATH = os.environ.get(
    "SQLITE_PATH", r"C:\ProgramData\Coodescor\Guias\guias.db"
)
BATCH_SIZE = int(os.environ.get("SUPABASE_BATCH", "100"))

# Tablas a sincronizar y su clave primaria en SQLite
TABLAS = {
    "usuarios": "id",
    "clientes": "nit",
    "guias": "id",
    "eventos": "id",
    "config": "clave",
    "admin_auditoria": "id",
    "entrega_tokens": "id",
    "sesiones": "sid",
    "schema_migrations": "version",
}

LOG_PREFIX = "[supabase-export]"


def log(mensaje: str) -> None:
    print(f"{LOG_PREFIX} {datetime.now(timezone.utc).isoformat()} {mensaje}", flush=True)


def leer_sqlite_tabla(tabla: str, pk: str, desde_id: str = "") -> list:
    """
    Lee todas las filas de una tabla SQLite. Si desde_id se indica, lee solo
    filas con pk > desde_id (sincronización incremental).
    """
    if not os.path.isfile(SQLITE_PATH):
        raise FileNotFoundError(f"No existe la base SQLite: {SQLITE_PATH}")

    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if desde_id:
            filas = conn.execute(
                f'SELECT * FROM "{tabla}" WHERE "{pk}" > ? ORDER BY "{pk}"',
                (desde_id,),
            ).fetchall()
        else:
            filas = conn.execute(f'SELECT * FROM "{tabla}" ORDER BY "{pk}"').fetchall()
        return [dict(f) for f in filas]
    finally:
        conn.close()


def obtener_ultimo_pk_supabase(tabla: str, pk: str, headers: dict) -> str | None:
    """
    Obtiene el último valor de la clave primaria ya existente en Supabase
    para hacer sincronización incremental.
    """
    url = f"{SUPABASE_URL}/rest/v1/{tabla}"
    params = {"select": pk, "order": f"{pk}.desc", "limit": "1"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code != 200:
        log(f"  Advertencia: no se pudo leer último {pk} de {tabla}: {resp.text[:200]}")
        return None
    data = resp.json()
    if not data:
        return None
    return str(data[0][pk])


def enviar_a_supabase(tabla: str, filas: list, headers: dict) -> int:
    """
    Envía un lote de filas a Supabase usando upsert (on_conflict = pk).
    Devuelve la cantidad de filas procesadas.
    """
    if not filas:
        return 0

    url = f"{SUPABASE_URL}/rest/v1/{tabla}"
    # Supabase upsert requiere indicar la columna de conflicto en la cabecera
    upsert_headers = dict(headers)
    upsert_headers["Prefer"] = 'resolution=merge-duplicates,return=minimal'

    enviados = 0
    for i in range(0, len(filas), BATCH_SIZE):
        lote = filas[i : i + BATCH_SIZE]
        try:
            resp = requests.post(url, headers=upsert_headers, json=lote, timeout=60)
            if resp.status_code in (200, 201):
                enviados += len(lote)
            else:
                log(f"  Error enviando lote a {tabla}: HTTP {resp.status_code} {resp.text[:300]}")
        except Exception as ex:
            log(f"  Excepción enviando lote a {tabla}: {ex}")
    return enviados


def sincronizar_tabla(tabla: str, pk: str, headers: dict) -> dict:
    """
    Sincroniza una tabla completa desde SQLite a Supabase.
    Devuelve dict con estadísticas.
    """
    log(f"Sincronizando tabla '{tabla}' (pk={pk}) ...")

    # Obtener último PK ya en Supabase para sincronización incremental
    ultimo_pk = obtener_ultimo_pk_supabase(tabla, pk, headers)

    # Leer desde SQLite (solo nuevos si ya hay datos en Supabase)
    filas = leer_sqlite_tabla(tabla, pk, desde_id=ultimo_pk)

    if not filas:
        log(f"  No hay filas nuevas en '{tabla}'.")
        return {"tabla": tabla, "filas_leidas": 0, "filas_enviadas": 0}

    log(f"  Filas leídas de SQLite: {len(filas)}")
    enviados = enviar_a_supabase(tabla, filas, headers)
    log(f"  Filas enviadas a Supabase: {enviados}")
    return {"tabla": tabla, "filas_leidas": len(filas), "filas_enviadas": enviados}


def ejecutar_exportacion() -> dict:
    """Ejecuta una exportación completa de todas las tablas configuradas."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Faltan SUPABASE_URL o SUPABASE_KEY en el entorno.")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    log(f"Iniciando exportación a Supabase: {SUPABASE_URL}")
    log(f"Base SQLite: {SQLITE_PATH}")

    resultados = []
    total_enviadas = 0
    for tabla, pk in TABLAS.items():
        try:
            r = sincronizar_tabla(tabla, pk, headers)
            resultados.append(r)
            total_enviadas += r["filas_enviadas"]
        except Exception as ex:
            log(f"  ERROR en tabla '{tabla}': {ex}")
            resultados.append({"tabla": tabla, "error": str(ex)})

    log(f"Exportación completada. Total filas enviadas: {total_enviadas}")
    return {"total_enviadas": total_enviadas, "tablas": resultados}


def bucle_ejecucion(intervalo_segundos: int = 900) -> None:
    """Ejecuta la exportación en bucle cada intervalo_segundos (default 15 min)."""
    log(f"Modo bucle activado. Intervalo: {intervalo_segundos}s ({intervalo_segundos/60:.0f} min)")
    while True:
        try:
            ejecutar_exportacion()
        except Exception as ex:
            log(f"ERROR en ciclo de exportación: {ex}")
        log(f"Próxima ejecución en {intervalo_segundos}s ...")
        time.sleep(intervalo_segundos)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exporta datos de SQLite local a Supabase"
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Ejecutar en bucle continuo en lugar de una sola vez",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=900,
        help="Intervalo entre ejecuciones en segundos (default 900 = 15 min)",
    )
    args = parser.parse_args()

    if args.loop:
        bucle_ejecucion(args.interval)
    else:
        ejecutar_exportacion()


if __name__ == "__main__":
    main()
