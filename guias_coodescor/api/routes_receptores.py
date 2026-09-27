#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rutas API para gestión de receptores / reclamantes (DB temporal cifrada).
Permisos:
  - POST /api/receptores                 : admin | administrativo | cedis (403 otros)
  - GET  /api/receptores?nit=<NIT>       : admin | administrativo | cedis | transportador (transportador ve sólo sus guías asignadas)
  - GET  /api/receptores?guia=<id>       : mismo esquema permisos que nit
  - DELETE /api/receptores/<id_temp>     : SÓLO admin (403 resto)
"""
import re as _re
from guias_coodescor.services.auth_service import ForbiddenError, requerir_rol
from guias_coodescor.services.receptores_service import (
    eliminar_receptor,
    listar_por_nit,
    obtener_por_guia,
    registrar_receptor,
)


def _handler_receptores_post(user, body, ip, json_fn):
    """
    POST /api/receptores  — crear receptor.
    Body JSON:
      nit_cliente (oblig): str NIT (FK validada a clientes.nit)
      guia_relacionada_id (opc): int id de guía (FK validada a guias.id)
      tipo_doc (oblig): enum CC|CE|TI|PAS|NIT|RC|Otro
      nombres_apellidos (oblig): str
      numero_doc (oblig): str
      telefono (opc): str
      email (opc): str
      parentesco_reclamante (opc): str
    """
    requerir_rol(user, "admin", "administrativo", "cedis")
    ok, codigo, msg, data = registrar_receptor(user, body, ip=ip)
    status = codigo if isinstance(codigo, int) else (201 if ok else 400)
    if ok:
        return json_fn({"ok": True, "msg": msg or "Receptor registrado", **(data or {})}, status)
    return json_fn({"ok": False, "error": msg or "No se pudo registrar el receptor", **(data or {})}, status)


def _handler_receptores_get(qs, user, json_fn):
    """
    GET /api/receptores?nit=<NIT>  o  ?guia=<gid>

    Permisos: admin | administrativo | cedis | transportador
              (ventas y público quedan 403 Forbidden)
    """
    requerir_rol(user, "admin", "administrativo", "cedis", "transportador")
    nit = (qs.get("nit") or [""])[0].strip()
    guia = (qs.get("guia") or [""])[0].strip()
    if nit:
        data = listar_por_nit(user, nit)
        return json_fn({"ok": True, "nit": nit, "total": len(data), "data": data})
    if guia:
        try:
            gid = int(guia)
        except (ValueError, TypeError):
            return json_fn({"ok": False, "error": "guia inválido (debe ser numérico)"}, 400)
        ok, code, msg, data = obtener_por_guia(user, gid)
        if not ok:
            return json_fn({"ok": False, "error": msg}, code if isinstance(code, int) else 403)
        return json_fn({"ok": True, "msg": msg, "data": data}, code if isinstance(code, int) else 200)
    return json_fn({
        "ok": False,
        "error": "Parámetro requerido faltante. Use ?nit=<NIT> o ?guia=<guia_id>",
        "uso": [
            "GET /api/receptores?nit=900123456-7  -> lista receptores por NIT",
            "GET /api/receptores?guia=42          -> datos del receptor de una guía",
        ],
    }, 400)


def _handler_receptores_delete(match, user, json_fn):
    """
    DELETE /api/receptores/<id_temp>  (solo admin)
    """
    requerir_rol(user, "admin")
    try:
        id_temp = int(match.group(1))
    except (ValueError, TypeError):
        return json_fn({"ok": False, "error": "id_temp inválido"}, 400)
    ok, msg = eliminar_receptor(user, id_temp)
    status = 200 if ok else 400
    return json_fn({"ok": bool(ok), "msg": msg}, status)


RUTAS_RECEPTORES_GET = [
    (r"^/api/receptores$", _handler_receptores_get),
]

RUTAS_RECEPTORES_POST = [
    (r"^/api/receptores$", _handler_receptores_post),
]

RUTAS_RECEPTORES_DELETE_REGEX = (r"^/api/receptores/(\d+)$", _handler_receptores_delete)
