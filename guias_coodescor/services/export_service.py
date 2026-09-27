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
        "NIT", "Centro operacion", "Prefijo",
        "Cliente", "Ciudad", "Direccion", "Documentos",
        "Creada por", "Creada en",
        "Recibe admin", "Fecha admin",
        "Cajas", "Bolsas", "Cavas", "Sobres", "Otros", "Totales", "Vehiculo cumple",
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

        recepcion_admin_datos = dd("recepcion_admin")
        recepcion_admin_fecha = en("recepcion_admin")
        envio_dir_evento = ev.get("envio_directo_cedis") or {}
        envio_dir_datos = envio_dir_evento.get("datos", {}) or {}
        envio_dir_fecha = envio_dir_evento.get("en", "") or ""
        envio_dir_marca = bool(g.get("envio_directo_cedis") or envio_dir_evento)

        # ---- FIX #report-admin-fields-missing: ------------------------------------------
        # Fallback semántico para columnas Recibe admin / Fecha admin (3 casos).
        # - Si el flujo fue NORMAL (envio_directo=0) y sí hubo recepción admin: OK datos.
        # - Si el flujo fue DIRECTO (envio_directo=1) NO hay recepción admin POR DISEÑO;
        #   NO dejar vacío, escribir "(ENVÍO DIRECTO...)", fecha = timestamp envio_dir.
        # - Si NORMAL PERO recepción admin AÚN NO (estado CREADA/EN_RUTA) es workflow
        #   PENDIENTE; marcar WARNING visible para que administrativo lo procese.
        if recepcion_admin_datos:
            recibe_admin_val = recepcion_admin_datos.get("recibe", "") or ""
            fecha_admin_val = recepcion_admin_fecha
        elif envio_dir_marca:
            # Flujo: Ventas marcó "Envío directo a CEDIS" = salta admin (regla negocio).
            motivo_dir = (envio_dir_datos.get("motivo") or "").strip()
            if motivo_dir:
                motivo_corto = (motivo_dir[:55] + "…") if len(motivo_dir) > 56 else motivo_dir
                recibe_admin_val = "(ENVÍO DIRECTO · SIN PASO ADMIN) — " + motivo_corto
            else:
                recibe_admin_val = "(ENVÍO DIRECTO · SIN PASO ADMINISTRATIVO)"
            fecha_admin_val = envio_dir_fecha
        else:
            # Flujo NORMAL (envio_directo=NO), pero administrativo NO procesó aún.
            # Warning visible para que el usuario CSV distinga "vacío dato" de PENDIENTE.
            estado_guia = str(g.get("estado") or "").upper()
            if estado_guia in ("CREADA", "EN_RUTA"):
                recibe_admin_val = (
                    "⚠️ PENDIENTE PROCESO ADMINISTRATIVO (asignar transportador / firmas)"
                )
            elif estado_guia in ("RECIBIDA_ADMIN",):
                recibe_admin_val = "(REGISTRADO)"
            else:
                recibe_admin_val = "(SIN DATOS ADMINISTRATIVOS)"
            fecha_admin_val = ""
        # --------------------------------------------------------------------------------

        w.writerow([
            g["consecutivo"], g["estado"],
            "SI" if g.get("envio_directo_cedis") else "NO",
            g.get("nit") or pre.get("nit", "") or "",
            g.get("centro_operacion") or pre.get("centro_operacion", "") or "",
            g.get("prefijo") or pre.get("prefijo", "") or "",
            g["cliente"] or "", g["ciudad"] or "",
            g["direccion"] or "", g["documentos"] or "",
            (ev.get("creacion") or {}).get("usuario", ""), g["creada_en"] or "",
            recibe_admin_val, fecha_admin_val,
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
