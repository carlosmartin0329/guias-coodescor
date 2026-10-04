#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Importa clientes desde 'Base de datos cliente V2.xlsx' a la tabla `clientes`
de guias.db. NIT es la PK (normalizada a solo digitos).

Uso:
    python importar_clientes_excel.py
"""
import os
import re
import sqlite3
import openpyxl

# Rutas
EXCEL_PATH = r"D:\Users\57323\Downloads\Base de datos cliente V2.xlsx"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "guias_coodescor", "data", "guias.db")


def normalizar_nit(nit):
    """Normaliza NIT a solo digitos (sin puntos, guiones, espacios)."""
    if nit is None:
        return ""
    digitos = re.sub(r"[^0-9]", "", str(nit))
    return digitos.lstrip("0") if digitos else ""


def main():
    print(f"[1] Cargando Excel: {EXCEL_PATH}")
    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    ws = wb.active
    print(f"    Hoja: {ws.title} | Filas: {ws.max_row} | Cols: {ws.max_column}")

    # Buscar fila de headers (NIT debe estar ahi)
    headers = None
    header_row = None
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=5, values_only=True), 1):
        if row and str(row[0]).strip().upper() == "NIT":
            headers = [str(c).strip().upper() if c else "" for c in row]
            header_row = i
            break

    if not headers:
        print("[ERROR] No se encontro la fila de headers con 'NIT'")
        return

    print(f"    Headers en fila {header_row}: {headers}")

    # Mapear columnas
    col_map = {}
    for idx, h in enumerate(headers):
        if h == "NIT":
            col_map["nit"] = idx
        elif "RAZON" in h:
            col_map["razon_social"] = idx
        elif "CIUDAD" in h:
            col_map["ciudad"] = idx
        elif "DIRECCION" in h:
            col_map["direccion"] = idx
        elif "TELEFONO" == h or h.startswith("TELEFONO"):
            if "telefono" not in col_map:
                col_map["telefono"] = idx
        elif "CORREO" in h and "COMPRAS" in h:
            col_map["email"] = idx

    print(f"    Mapeo de columnas: {col_map}")

    # Leer datos
    clientes = []
    saltados = 0
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        if not row or not row[0]:
            saltados += 1
            continue

        nit = normalizar_nit(row[col_map["nit"]]) if "nit" in col_map else ""
        if not nit:
            saltados += 1
            continue

        razon = str(row[col_map["razon_social"]]).strip() if "razon_social" in col_map and row[col_map["razon_social"]] else ""
        ciudad = str(row[col_map["ciudad"]]).strip() if "ciudad" in col_map and row[col_map["ciudad"]] else ""
        direccion = str(row[col_map["direccion"]]).strip() if "direccion" in col_map and row[col_map["direccion"]] else ""
        telefono = str(row[col_map["telefono"]]).strip() if "telefono" in col_map and row[col_map["telefono"]] else ""
        email = str(row[col_map["email"]]).strip() if "email" in col_map and col_map["email"] < len(row) and row[col_map["email"]] else ""

        clientes.append({
            "nit": nit,
            "razon_social": razon,
            "ciudad": ciudad,
            "direccion": direccion,
            "telefono": telefono,
            "email": email,
            "cliente_descubierto": 0,
        })

    print(f"[2] Clientes leidos del Excel: {len(clientes)} (saltados: {saltados})")

    # Conectar a la BD
    print(f"[3] Conectando a BD: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    # Contar antes
    antes = conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    print(f"    Clientes en BD antes: {antes}")

    # Upsert (INSERT OR IGNORE para no sobrescribir manuales existentes)
    from datetime import datetime
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    insertados = 0
    actualizados = 0
    for c in clientes:
        c["creado_en"] = ahora
        c["actualizado_en"] = ahora
        cur = conn.execute(
            """INSERT INTO clientes (nit, razon_social, direccion, ciudad, telefono, email, cliente_descubierto, creado_en, actualizado_en)
               VALUES (:nit, :razon_social, :direccion, :ciudad, :telefono, :email, :cliente_descubierto, :creado_en, :actualizado_en)
               ON CONFLICT(nit) DO UPDATE SET
                 razon_social=excluded.razon_social,
                 direccion=COALESCE(NULLIF(excluded.direccion,''), clientes.direccion),
                 ciudad=COALESCE(NULLIF(excluded.ciudad,''), clientes.ciudad),
                 telefono=COALESCE(NULLIF(excluded.telefono,''), clientes.telefono),
                 email=COALESCE(NULLIF(excluded.email,''), clientes.email),
                 cliente_descubierto=0,
                 actualizado_en=excluded.actualizado_en
            """,
            c
        )
        if cur.rowcount == 1:
            insertados += 1
        else:
            actualizados += 1

    conn.commit()

    # Contar despues
    despues = conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    print(f"[4] Importacion completa:")
    print(f"    Nuevos insertados: {insertados}")
    print(f"    Actualizados: {actualizados}")
    print(f"    Total en BD ahora: {despues}")

    # Mostrar muestra
    print(f"[5] Muestra de primeros 5 clientes:")
    for row in conn.execute("SELECT nit, razon_social, ciudad FROM clientes ORDER BY nit LIMIT 5").fetchall():
        print(f"    NIT={row[0]} | {row[1]} | {row[2]}")

    conn.close()
    print("[OK] Importacion finalizada correctamente.")


if __name__ == "__main__":
    main()
