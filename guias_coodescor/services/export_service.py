#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio de exportación: generación de CSV y reportes.
"""
import csv
import io
from typing import Tuple

from guias_coodescor.services.eventos_service import listar_eventos
from guias_coodescor.services.guias_service import (
    buscar_guias,
    generar_codigo_verificacion,
    obtener_prellenado_ventas,
)


def exportar_guias_csv() -> Tuple[bytes, str]:
    """
    Genera un CSV con todas las guías. Devuelve (bytes_en_utf8_sig, nombre_archivo).
    """
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow([
        "Consecutivo", "Estado", "Envio directo CEDIS",
        "Cliente", "Ciudad", "Direccion", "Documentos",
        "Creada por", "Creada en",
        "Recibe admin", "Fecha admin",
        "Cajas", "Bolsas", "Cayvas", "Sobres", "Otros", "Totales", "Vehiculo cumple",
        "Transportador (prellenado)", "CC transportador (prellenado)",
        "Tel transportador (prellenado)", "Vehiculo (prellenado)",
        "Placa (prellenado)", "Flete (prellenado)",
        "Recibe cliente (prellenado)",
        "Transportador", "Placa", "Flete", "Fecha transporte",
        "Recibe cliente", "Fecha cliente", "Codigo",
    ])

    for g in buscar_guias(limite=100000):
        ev = {x["tipo"]: x for x in listar_eventos(g["id"])}
        pre = obtener_prellenado_ventas(g["id"])
        dd = lambda t: (ev.get(t) or {}).get("datos", {}) or {}
        en = lambda t: (ev.get(t) or {}).get("en", "") or ""
        w.writerow([
            g["consecutivo"], g["estado"],
            "SI" if g.get("envio_directo_cedis") else "NO",
            g["cliente"] or "", g["ciudad"] or "",
            g["direccion"] or "", g["documentos"] or "",
            (ev.get("creacion") or {}).get("usuario", ""), g["creada_en"] or "",
            dd("recepcion_admin").get("recibe", ""), en("recepcion_admin"),
            dd("control_cedis").get("cajas", ""), dd("control_cedis").get("bolsas", ""),
            dd("control_cedis").get("cayvas", ""), dd("control_cedis").get("sobres", ""),
            dd("control_cedis").get("otros", ""), dd("control_cedis").get("totales", ""),
            dd("control_cedis").get("vehiculo_cumple", ""),
            pre.get("transportador_nombre", ""), pre.get("transportador_cc", ""),
            pre.get("transportador_tel", ""), pre.get("transportador_vehiculo", ""),
            pre.get("transportador_placa", ""), pre.get("transportador_flete", ""),
            pre.get("cliente_recibe_nombre", ""),
            dd("entrega_transporte").get("nombre", ""), dd("entrega_transporte").get("placa", ""),
            dd("entrega_transporte").get("flete", ""), en("entrega_transporte"),
            dd("entrega_cliente").get("recibe", ""), en("entrega_cliente"),
            generar_codigo_verificacion(g),
        ])
    data = buf.getvalue().encode("utf-8-sig")
    return data, "guias_coodescor.csv"
