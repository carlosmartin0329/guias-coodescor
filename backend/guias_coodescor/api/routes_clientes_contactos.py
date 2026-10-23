#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rutas API para gestión de contactos de clientes (tabla clientes_contactos).
Proporciona endpoints para autocompletado y CRUD de contactos.
"""

import json

from guias_coodescor.services.clientes_contactos_service import (
    buscar_contactos,
    eliminar_contacto,
    guardar_contacto,
    listar_contactos_por_cliente,
    obtener_contacto_por_id,
)
from guias_coodescor.core.logging_config import get_logger

_log = get_logger(__name__)


def _handler_buscar_contactos(qs, user, json_fn):
    """
    GET /api/clientes_contactos/buscar?q=<texto>&nit_cliente=<nit>&limite=<int>
    Requiere: cualquier sesión autenticada (401 si no).
    Retorna: {ok:True, resultados:[{id, nit_cliente, nombre, telefono, cedula}...]}
    """
    if not user:
        return json_fn({"ok": False, "error": "Sesión inválida o expirada"}, 401)
    
    q = (qs.get("q") or [""])[0].strip()
    nit_cliente = (qs.get("nit_cliente") or [""])[0].strip() or None
    
    try:
        limite = int((qs.get("limite") or ["10"])[0])
        limite = max(1, min(50, limite))
    except (ValueError, TypeError):
        limite = 10
    
    try:
        resultados = buscar_contactos(q, nit_cliente, limite=limite)
        return json_fn({
            "ok": True,
            "resultados": resultados,
            "query": q,
            "nit_cliente": nit_cliente,
            "total": len(resultados),
        })
    except Exception as e:
        _log.error("Error buscando contactos: %s", e, exc_info=True)
        return json_fn({"ok": False, "error": str(e)}, 500)


def _handler_listar_por_cliente(qs, user, json_fn):
    """
    GET /api/clientes_contactos/por_cliente?nit_cliente=<nit>&limite=<int>
    Retorna todos los contactos de un cliente específico.
    """
    if not user:
        return json_fn({"ok": False, "error": "Sesión inválida o expirada"}, 401)
    
    nit_cliente = (qs.get("nit_cliente") or [""])[0].strip()
    if not nit_cliente:
        return json_fn({"ok": False, "error": "nit_cliente es obligatorio"}, 400)
    
    try:
        limite = int((qs.get("limite") or ["50"])[0])
        limite = max(1, min(100, limite))
    except (ValueError, TypeError):
        limite = 50
    
    try:
        contactos = listar_contactos_por_cliente(nit_cliente, limite=limite)
        return json_fn({
            "ok": True,
            "contactos": contactos,
            "nit_cliente": nit_cliente,
            "total": len(contactos),
        })
    except Exception as e:
        _log.error("Error listando contactos por cliente: %s", e, exc_info=True)
        return json_fn({"ok": False, "error": str(e)}, 500)


def _handler_guardar_contacto(qs, user, json_fn, body):
    """
    POST /api/clientes_contactos/guardar
    Body: {nit_cliente, nombre, telefono, cedula, id?}
    Crea o actualiza un contacto.
    """
    if not user:
        return json_fn({"ok": False, "error": "Sesión inválida o expirada"}, 401)
    
    try:
        datos = json.loads(body) if body else {}
    except (ValueError, TypeError):
        return json_fn({"ok": False, "error": "Body JSON inválido"}, 400)
    
    nit_cliente = datos.get("nit_cliente")
    if not nit_cliente:
        return json_fn({"ok": False, "error": "nit_cliente es obligatorio"}, 400)
    
    nombre = datos.get("nombre")
    if not nombre:
        return json_fn({"ok": False, "error": "nombre es obligatorio"}, 400)
    
    try:
        ok, msg, contacto_id = guardar_contacto(datos, nit_cliente)
        if ok:
            return json_fn({"ok": True, "mensaje": msg, "contacto_id": contacto_id})
        else:
            return json_fn({"ok": False, "error": msg}, 400)
    except Exception as e:
        _log.error("Error guardando contacto: %s", e, exc_info=True)
        return json_fn({"ok": False, "error": str(e)}, 500)


def _handler_eliminar_contacto(qs, user, json_fn, body):
    """
    POST /api/clientes_contactos/eliminar
    Body: {contacto_id}
    Elimina un contacto.
    """
    if not user:
        return json_fn({"ok": False, "error": "Sesión inválida o expirada"}, 401)
    
    try:
        datos = json.loads(body) if body else {}
    except (ValueError, TypeError):
        return json_fn({"ok": False, "error": "Body JSON inválido"}, 400)
    
    contacto_id = datos.get("contacto_id")
    if not contacto_id:
        return json_fn({"ok": False, "error": "contacto_id es obligatorio"}, 400)
    
    try:
        ok, msg = eliminar_contacto(int(contacto_id))
        if ok:
            return json_fn({"ok": True, "mensaje": msg})
        else:
            return json_fn({"ok": False, "error": msg}, 404)
    except Exception as e:
        _log.error("Error eliminando contacto: %s", e, exc_info=True)
        return json_fn({"ok": False, "error": str(e)}, 500)


RUTAS_CLIENTES_CONTACTOS_GET = [
    (r"^/api/clientes_contactos/buscar$", _handler_buscar_contactos),
    (r"^/api/clientes_contactos/por_cliente$", _handler_listar_por_cliente),
]

RUTAS_CLIENTES_CONTACTOS_POST = [
    (r"^/api/clientes_contactos/guardar$", _handler_guardar_contacto),
    (r"^/api/clientes_contactos/eliminar$", _handler_eliminar_contacto),
]
