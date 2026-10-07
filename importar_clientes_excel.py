#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Importar clientes desde Excel a la tabla clientes (SQLite).
Uso: python importar_clientes_excel.py
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import openpyxl
from guias_coodescor.database.connection import db_connection
from guias_coodescor.config import DATA_DIR
from guias_coodescor.core.utils import ahora_txt

EXCEL_PATH = r"D:\Users\57323\Downloads\Base de datos cliente V2.xlsx"

AHORA = ahora_txt()


def importar():
    if not os.path.exists(EXCEL_PATH):
        print(f"[ERROR] No existe: {EXCEL_PATH}")
        return 1

    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True)
    ws = wb.active

    # Headers en fila 2 (fila 1 es título)
    headers = [cell.value for cell in next(ws.iter_rows(min_row=2, max_row=2))]
    print(f"Headers: {headers}")

    # Mapeo de columnas
    # NIT, RAZON SOCIAL, CIUDAD, DIRECCION, TELEFONO, TIPO DE CLIENTE, ENCARGADO DE COMPRAS, CORREO ELECTRONICO COMPRAS, TELEFONO COMPRAS
    col_nit = 0
    col_razon = 1
    col_ciudad = 2
    col_direccion = 3
    col_telefono = 4
    col_tipo = 5
    col_encargado = 6
    col_email = 7
    col_tel_compras = 8

    insertados = 0
    actualizados = 0
    errores = 0

    with db_connection(commit=True) as conn:
        for i, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
            nit = row[col_nit]
            razon = row[col_razon]
            ciudad = row[col_ciudad]
            direccion = row[col_direccion]
            telefono = row[col_telefono]
            tipo = row[col_tipo]
            encargado = row[col_encargado]
            email = row[col_email]
            tel_compras = row[col_tel_compras]

            if not nit or not razon:
                continue

            nit_str = str(nit).strip()
            razon_str = str(razon).strip() if razon else ""
            ciudad_str = str(ciudad).strip() if ciudad else ""
            direccion_str = str(direccion).strip() if direccion else ""
            telefono_str = str(telefono).strip() if telefono else ""
            email_str = str(email).strip() if email else ""

            # Verificar si existe
            existe = conn.execute(
                "SELECT 1 FROM clientes WHERE nit = ?", (nit_str,)
            ).fetchone()

            if existe:
                conn.execute(
                    """UPDATE clientes SET
                        razon_social = ?, ciudad = ?, direccion = ?,
                        telefono = ?, email = ?, actualizado_en = ?
                       WHERE nit = ?""",
                    (razon_str, ciudad_str, direccion_str, telefono_str, email_str, AHORA, nit_str)
                )
                actualizados += 1
            else:
                conn.execute(
                    """INSERT INTO clientes (nit, razon_social, ciudad, direccion, telefono, email, creado_en, actualizado_en)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (nit_str, razon_str, ciudad_str, direccion_str, telefono_str, email_str, AHORA, AHORA)
                )
                insertados += 1

    print(f"[OK] Insertados: {insertados}, Actualizados: {actualizados}, Errores: {errores}")
    return 0


if __name__ == "__main__":
    sys.exit(importar())