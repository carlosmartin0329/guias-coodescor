#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vistas HTML de autenticación (login) y tablero principal (dashboard).
"""
from guias_coodescor.config import ESTADOS
from guias_coodescor.services.guias_service import (
    contar_por_estado,
    listar_guias_por_estado,
)
from guias_coodescor.web.views.base import (
    card_accion,
    escape,
    lista_guias,
    page,
)


def vista_login() -> str:
    return page("Ingreso", """
    <div class="loginbox"><h1>📦 Guías Coodescor</h1>
    <p class="sub">Acta de entrega de transporte de mercancías · sistema local</p>
    <form data-api="/api/login" data-redirect="/tablero">
      <label>Usuario<input name="usuario" autocomplete="username" required autofocus></label>
      <label>Contraseña<input name="clave" type="password" autocomplete="current-password" required></label>
      <button class="btn primario">Ingresar</button>
    </form>
    <p class="demo">
      Usuarios iniciales:
      <code>admin/admin123</code> ·
      <code>administrativo/adminbod123</code> ·
      <code>ventas/ventas123</code> ·
      <code>ventas2/ventas123</code> ·
      <code>cedis/cedis123</code><br>
      CAMBIE LAS CLAVES POR DEFECTO desde el panel Admin.
    </p></div>""")


def vista_tablero(user: dict) -> str:
    rol = user.get("rol", "")
    bloques = []
    if rol == "ventas":
        pend_creadas = listar_guias_por_estado("CREADA", 10)
        pend_cedis = listar_guias_por_estado("EN_CEDIS", 10)
        bloques.append(card_accion("➕ Crear guía nueva",
            "Registra cliente, dirección, transportador y opción de envío directo.", "/guia/nueva"))
        bloques.append(lista_guias(pend_creadas, "Esperando recepción de Bodega / Administrativo"))
        bloques.append(lista_guias(pend_cedis, "Envío directo a CEDIS (listas para control"))
    if rol in ("admin", "administrativo"):
        pend = listar_guias_por_estado("CREADA", 10)
        if rol == "admin":
            bloques.append(card_accion("🛡️ Panel administrativo",
                "Usuarios, consecutivo, exportar y anular.", "/admin"))
        bloques.append(lista_guias(pend, "Guías por recibir en bodega (firmar recepción)"))
    if rol == "cedis":
        ctrl = listar_guias_por_estado("RECIBIDA_ADMIN", 10)
        ced  = listar_guias_por_estado("EN_CEDIS", 10)
        ruta = listar_guias_por_estado("EN_RUTA", 10)
        bloques.append(lista_guias(ctrl, "1 · Por controlar (bultos y vehículo"))
        bloques.append(lista_guias(ced,  "2 · Por entregar al transportador"))
        bloques.append(lista_guias(ruta, "3 · En ruta · por entregar al cliente"))
    if rol == "transportador":
        en_ruta = listar_guias_por_estado("EN_RUTA", 15)
        en_cedis = listar_guias_por_estado("EN_CEDIS", 10)
        bloques.append(card_accion("🚚 Mis guías en ruta",
            "Guías asignadas para entrega al cliente final.", "/guias?estado=EN_RUTA"))
        bloques.append(lista_guias(en_ruta, "📦 En ruta · por entregar"))
        bloques.append(lista_guias(en_cedis, "📋 Disponibles en CEDIS (por recoger)"))

    tot = contar_por_estado()
    resumen = "".join(
        f'<div class="kpi" style="border-color:{ESTADOS[r["estado"]][1]}">'
        f'<b>{r["n"]}</b><span>{escape(ESTADOS[r["estado"]][0])}</span></div>'
        for r in tot if r["estado"] in ESTADOS
    )
    busc = """<form class="busc" action="/guias" method="get">
      <input name="q" placeholder="Buscar por consecutivo o cliente…">
      <button class="btn">Buscar</button></form>"""
    cuerpo = (
        f"<h2>Hola, {escape(user.get('nombre'))} 👋</h2>"
        f"<div class='kpis'>{resumen}</div>{busc}"
        + "".join(bloques)
    )
    return page("Tablero", cuerpo, user)
