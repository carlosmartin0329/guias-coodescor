#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rutas API para gestión de transportadores externos.
Proporciona endpoints para autocompletado y CRUD de transportadores.
"""

import json

from guias_coodescor.services.transportadores_externos_service import (
    buscar_transportadores_externos,
    eliminar_transportador_externo,
    guardar_transportador_externo,
    listar_transportadores_externos,
    obtener_transportador_externo_por_id,
)
from guias_coodescor.services.auth_service import requerir_rol
from guias_coodescor.core.logging_config import get_logger

_log = get_logger(__name__)


def _cuerpo_dict(body) -> dict:
    """El router ya entrega un dict; se tolera también una cadena JSON."""
    if isinstance(body, dict):
        return body
    if isinstance(body, (str, bytes, bytearray)) and body:
        try:
            datos = json.loads(body)
        except (ValueError, TypeError):
            raise ValueError("Body JSON inválido")
        if not isinstance(datos, dict):
            raise ValueError("El cuerpo JSON debe ser un objeto")
        return datos
    return {}



def _handler_buscar_transportadores(qs, user, json_fn):
    """
    GET /api/transportadores_externos/buscar?q=<texto>&limite=<int>
    Requiere: cualquier sesión autenticada (401 si no).
    Retorna: {ok:True, resultados:[{id, nombre, cc, telefono, vehiculo, placa, flete}...]}
    """
    if not user:
        return json_fn({"ok": False, "error": "Sesión inválida o expirada"}, 401)
    
    q = (qs.get("q") or [""])[0].strip()
    
    try:
        limite = int((qs.get("limite") or ["10"])[0])
        limite = max(1, min(50, limite))
    except (ValueError, TypeError):
        limite = 10
    
    try:
        resultados = buscar_transportadores_externos(q, limite=limite)
        return json_fn({
            "ok": True,
            "resultados": resultados,
            "query": q,
            "total": len(resultados),
        })
    except Exception as e:
        _log.error("Error buscando transportadores: %s", e, exc_info=True)
        return json_fn({"ok": False, "error": str(e)}, 500)


def _handler_listar_transportadores(qs, user, json_fn):
    """
    GET /api/transportadores_externos/listar
    Retorna todos los transportadores externos activos.
    """
    if not user:
        return json_fn({"ok": False, "error": "Sesión inválida o expirada"}, 401)
    
    try:
        limite = int((qs.get("limite") or ["50"])[0])
        limite = max(1, min(100, limite))
    except (ValueError, TypeError):
        limite = 50
    
    try:
        transportadores = listar_transportadores_externos(limite=limite)
        return json_fn({
            "ok": True,
            "transportadores": transportadores,
            "total": len(transportadores),
        })
    except Exception as e:
        _log.error("Error listando transportadores: %s", e, exc_info=True)
        return json_fn({"ok": False, "error": str(e)}, 500)


def _handler_guardar_transportador(qs, user, json_fn, body):
    """
    POST /api/transportadores_externos/guardar
    Body: {nombre, cc, telefono, vehiculo?, placa?, flete?, observaciones?, id?}
    Crea o actualiza un transportador externo.
    """
    if not user:
        return json_fn({"ok": False, "error": "Sesión inválida o expirada"}, 401)
    # Solo Admin y Administrativo pueden modificar el maestro de transportadores
    # externos (config.PERMISO_REGISTRAR_TRANSPORTADOR_EXTERNO). Antes cualquier
    # rol autenticado (p. ej. Ventas) podía crear o desactivar estos registros.
    requerir_rol(user, "admin", "administrativo")

    try:
        datos = _cuerpo_dict(body)
    except ValueError as ex:
        return json_fn({"ok": False, "error": str(ex)}, 400)

    nombre = datos.get("nombre")
    if not nombre:
        return json_fn({"ok": False, "error": "nombre es obligatorio"}, 400)
    
    try:
        ok, msg, transportador_id = guardar_transportador_externo(datos, user)
        if ok:
            return json_fn({"ok": True, "mensaje": msg, "transportador_id": transportador_id})
        else:
            return json_fn({"ok": False, "error": msg}, 400)
    except Exception as e:
        _log.error("Error guardando transportador: %s", e, exc_info=True)
        return json_fn({"ok": False, "error": str(e)}, 500)


def _handler_eliminar_transportador(qs, user, json_fn, body):
    """
    POST /api/transportadores_externos/eliminar
    Body: {transportador_id}
    Elimina un transportador externo.
    """
    if not user:
        return json_fn({"ok": False, "error": "Sesión inválida o expirada"}, 401)
    requerir_rol(user, "admin", "administrativo")

    try:
        datos = _cuerpo_dict(body)
    except ValueError as ex:
        return json_fn({"ok": False, "error": str(ex)}, 400)

    transportador_id = datos.get("transportador_id")
    if not transportador_id:
        return json_fn({"ok": False, "error": "transportador_id es obligatorio"}, 400)
    
    try:
        ok, msg = eliminar_transportador_externo(int(transportador_id), user)
        if ok:
            return json_fn({"ok": True, "mensaje": msg})
        else:
            return json_fn({"ok": False, "error": msg}, 404)
    except Exception as e:
        _log.error("Error eliminando transportador: %s", e, exc_info=True)
        return json_fn({"ok": False, "error": str(e)}, 500)


RUTAS_TRANSPORTADORES_EXTERNOS_GET = [
    (r"^/api/transportadores_externos/buscar$", _handler_buscar_transportadores),
    (r"^/api/transportadores_externos/listar$", _handler_listar_transportadores),
]

RUTAS_TRANSPORTADORES_EXTERNOS_POST = [
    (r"^/api/transportadores_externos/guardar$", _handler_guardar_transportador),
    (r"^/api/transportadores_externos/eliminar$", _handler_eliminar_transportador),
]
