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
        # Obtener timestamp de última consulta
        ultima_consulta_str = (qs.get("ultima_consulta") or [""])[0].strip()
        
        # Parsear timestamp
        if ultima_consulta_str:
            try:
                ultima_consulta = float(ultima_consulta_str)
            except ValueError:
                # Intentar parsear ISO format
                import datetime
                try:
                    dt = datetime.datetime.fromisoformat(ultima_consulta_str.replace('Z', '+00:00'))
                    ultima_consulta = dt.timestamp()
                except (ValueError, TypeError):
                    ultima_consulta = 0
        else:
            ultima_consulta = 0
        
        # Obtener guías creadas desde ese timestamp
        # Buscar todas las guías y filtrar por fecha de creación
        todas_guias = buscar_guias(limite=100)
        
        nuevas = []
        for g in todas_guias:
            # Convertir creada_en a timestamp
            try:
                import datetime
                fecha_str = g.get("creada_en") or ""
                if fecha_str:
                    dt = datetime.datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                    g_timestamp = dt.timestamp()
                else:
                    g_timestamp = 0
                
                if g_timestamp > ultima_consulta:
                    nuevas.append(g)
            except Exception as e:
                _log.warning(f"Error parseando fecha: {e}")
                continue
        
        return json_fn({
            "ok": True,
            "nuevas": nuevas,
            "has_new": len(nuevas) > 0,
            "timestamp": time.time(),
            "count": len(nuevas)
        })
    except Exception as e:
        _log.error(f"Error en polling nuevas guías: {e}", exc_info=True)
        return json_fn({"ok": False, "error": str(e)}, 500)


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
    (r"^/api/notificaciones/nuevas_guias$", _handler_polling_nuevas_guias),
    (r"^/api/notificaciones/conteo$", _handler_conteo_por_estado),
]
