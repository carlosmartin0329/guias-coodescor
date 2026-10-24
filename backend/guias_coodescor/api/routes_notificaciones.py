#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rutas API para notificaciones en tiempo real.
Proporciona endpoints para:
- Polling de nuevas guías
- Obtener el conteo actual de guías por estado
"""

import time

from guias_coodescor.services.guias_service import buscar_guias, contar_por_estado
from guias_coodescor.core.logging_config import get_logger

_log = get_logger(__name__)

_ESTADOS_PENDIENTES_POR_ROL = {
    "ventas": ("CREADA", "RECIBIDA_ADMIN", "EN_CEDIS", "EN_RUTA"),
    "administrativo": ("CREADA",),
    "cedis": ("RECIBIDA_ADMIN", "EN_CEDIS"),
    "transportador": ("EN_CEDIS", "EN_RUTA"),
    "admin": ("CREADA", "RECIBIDA_ADMIN", "EN_CEDIS", "EN_RUTA"),
}


def _handler_pendientes_perfil(qs, user, json_fn):
    """GET /api/notificaciones/pendientes · tareas abiertas para el perfil."""
    if not user:
        return json_fn({"ok": False, "error": "Sesión inválida o expirada"}, 401)

    rol = user.get("rol") or ""
    estados = _ESTADOS_PENDIENTES_POR_ROL.get(rol)
    if estados is None:
        return json_fn({"ok": False, "error": "Perfil no habilitado para notificaciones"}, 403)

    try:
        transportador_id = None
        if rol == "transportador":
            transportador_id = int(user.get("id") or 0)
            if transportador_id <= 0:
                return json_fn({"ok": False, "error": "Sesión de transportador inválida"}, 403)

        notificaciones = []
        transportador_filtro = (
            transportador_id if transportador_id is not None else None
        )
        conteo_estados = {
            item["estado"]: item["n"]
            for item in contar_por_estado(
                transportador_asignado_id=transportador_filtro
            )
        }
        for estado in estados:
            guias = buscar_guias(
                estado=estado,
                limite=50,
                transportador_asignado_id=transportador_id,
            )
            for guia in guias:
                guia_id = guia.get("id")
                if guia_id is None:
                    continue
                notificaciones.append({
                    "id": f"{guia_id}:{estado}",
                    "guia_id": guia_id,
                    "consecutivo": guia.get("consecutivo"),
                    "cliente": guia.get("cliente") or "",
                    "ciudad": guia.get("ciudad") or "",
                    "estado": estado,
                    "creada_en": guia.get("creada_en") or "",
                    "mensaje": f"Guía pendiente: {estado}",
                })

        notificaciones.sort(
            key=lambda item: (str(item.get("creada_en") or ""), int(item["guia_id"])),
            reverse=True,
        )
        return json_fn({
            "ok": True,
            "notificaciones": notificaciones[:100],
            "count": len(notificaciones),
            "estados": conteo_estados,
            "timestamp": time.time(),
        })
    except Exception as e:
        _log.error("Error consultando pendientes del perfil: %s", e, exc_info=True)
        return json_fn({"ok": False, "error": "No se pudieron consultar las notificaciones"}, 500)


def _handler_polling_nuevas_guias(qs, user, json_fn):
    """
    GET /api/notificaciones/nuevas_guias?ultima_consulta=<timestamp>
    
    Retorna las guías creadas desde la última consulta.
    Usado para polling desde el frontend.
    
    Parámetros:
    - ultima_consulta: Timestamp de la última consulta (ISO format o epoch)
    
    Retorna:
    {
      "ok": true,
      "nuevas": [lista de guías nuevas],
      "timestamp": timestamp actual,
      "has_new": bool
    }
    """
    if not user:
        return json_fn({"ok": False, "error": "Sesión inválida o expirada"}, 401)

    try:
        ultima_consulta_str = (qs.get("ultima_consulta") or [""])[0].strip()
        if ultima_consulta_str:
            try:
                ultima_consulta = float(ultima_consulta_str)
            except ValueError:
                import datetime
                try:
                    dt = datetime.datetime.fromisoformat(ultima_consulta_str.replace('Z', '+00:00'))
                    ultima_consulta = dt.timestamp()
                except (ValueError, TypeError):
                    ultima_consulta = 0
        else:
            ultima_consulta = 0

        respuesta_pendientes = {}
        codigo_respuesta = 200

        def capturar_pendientes(payload, codigo=200):
            nonlocal codigo_respuesta
            respuesta_pendientes.update(payload)
            codigo_respuesta = codigo
            return payload

        _handler_pendientes_perfil(qs, user, capturar_pendientes)
        if codigo_respuesta != 200:
            return json_fn(respuesta_pendientes, codigo_respuesta)

        import datetime
        nuevas = []
        for guia in respuesta_pendientes.get("notificaciones", []):
            try:
                fecha_str = guia.get("creada_en") or ""
                if fecha_str:
                    dt = datetime.datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
                    guia_timestamp = dt.timestamp()
                else:
                    guia_timestamp = 0
                if guia_timestamp > ultima_consulta:
                    nuevas.append(guia)
            except (ValueError, TypeError, OverflowError) as e:
                _log.warning("Error parseando fecha de guía: %s", e)
                continue

        return json_fn({
            "ok": True,
            "nuevas": nuevas,
            "has_new": len(nuevas) > 0,
            "timestamp": time.time(),
            "count": len(nuevas)
        })
    except Exception as e:
        _log.error("Error en polling nuevas guías: %s", e, exc_info=True)
        return json_fn({"ok": False, "error": "No se pudieron consultar las guías nuevas"}, 500)


def _handler_conteo_por_estado(qs, user, json_fn):
    """
    GET /api/notificaciones/conteo
    
    Retorna el conteo de guías por estado.
    Usado para mostrar badges de notificación.
    """
    if not user:
        return json_fn({"ok": False, "error": "Sesión inválida o expirada"}, 401)
    
    try:
        conteo = contar_por_estado()
        
        # Agrupar por estado
        estados = {}
        for item in conteo:
            estado = item.get("estado", "")
            n = item.get("n", 0)
            estados[estado] = n
        
        return json_fn({
            "ok": True,
            "estados": estados,
            "timestamp": time.time()
        })
    except Exception as e:
        _log.error(f"Error en conteo por estado: {e}", exc_info=True)
        return json_fn({"ok": False, "error": str(e)}, 500)


RUTAS_NOTIFICACIONES_GET = [
    (r"^/api/notificaciones/pendientes$", _handler_pendientes_perfil),
    (r"^/api/notificaciones/nuevas_guias$", _handler_polling_nuevas_guias),
    (r"^/api/notificaciones/conteo$", _handler_conteo_por_estado),
]
