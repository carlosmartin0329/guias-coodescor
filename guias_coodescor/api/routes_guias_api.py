#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API REST de guías y eventos.

Este módulo es el contrato entre el backend y el frontend: devuelve JSON puro y
no toca el HTML. Cualquier cliente (la interfaz actual, una SPA, un móvil o un
script) consume exactamente los mismos endpoints, así que la interfaz se puede
reescribir sin volver a tocar la lógica de negocio.

Convenciones:
  · Toda respuesta es {"ok": true, ...} o {"ok": false, "error": "..."}.
  · Los errores de dominio (AuthError, ForbiddenError, ValidationError) los
    traduce el router; aquí solo se lanzan.
  · Los handlers reciben los datos ya leídos del cuerpo o de la query string,
    igual que routes_clientes y routes_receptores.
"""
import re

from guias_coodescor.services import eventos_service as ev
from guias_coodescor.services import guias_service as g

# Cuántos eventos devolvemos por defecto. La lista completa de una guía puede
# tener dozens de entradas y el frontend solo necesita las recientes.
_EVENTOS_POR_DEFECTO = 100


def _entero(valor, defecto=None):
    """Convierte a int tolerando '' y None. Devuelve el defecto si no es un número."""
    if valor is None or valor == "":
        return defecto
    try:
        return int(valor)
    except (TypeError, ValueError):
        return defecto


def _limite(valor, defecto: int, tope: int) -> int:
    """Acota el límite para que un cliente no pida el mundo entero."""
    n = _entero(valor, defecto)
    if n is None:
        return defecto
    return max(1, min(n, tope))


# ---------------------------------------------------------------------------
# Guías
# ---------------------------------------------------------------------------

def _h_listar(qs, user, json_fn):
    """
    GET /api/guias?q=&estado=&limite=&transportador=

    Búsqueda paginada-ligera. Devuelve también el conteo por estado para que el
    frontend pueda pintar las pestañas sin una segunda llamada.
    """
    estado = (qs.get("estado", [""])[0] or "").strip()
    solo_estado = (qs.get("solo_estado", [""])[0] or "").strip() or None
    transportador = _entero(qs.get("transportador", [""])[0])
    guias = g.buscar_guias(
        q=(qs.get("q", [""])[0] or "").strip(),
        estado=estado,
        limite=_limite(qs.get("limite", [""])[0], 200, 500),
        solo_estado=solo_estado,
        transportador_asignado_id=transportador,
    )
    return json_fn(
        {
            "ok": True,
            "guias": guias,
            "total": len(guias),
            "conteo_por_estado": g.contar_por_estado(),
        }
    )


def _h_conteo(qs, user, json_fn):
    """GET /api/guias/conteo · números del tablero."""
    return json_fn({"ok": True, "conteo": g.contar_por_estado()})


def _h_detalle(qs, user, json_fn, guia_id):
    """
    GET /api/guias/<id> · guía, eventos y prellenado de ventas.

    Es lo que necesita la pantalla de detalle para renderizarse sin HTML.
    """
    guia = g.obtener_guia(guia_id)
    if not guia:
        return json_fn({"ok": False, "error": "La guía no existe."}, 404)
    return json_fn(
        {
            "ok": True,
            "guia": guia,
            "eventos": ev.listar_eventos(guia_id),
            "prellenado": g.obtener_prellenado_ventas(guia_id),
            "estado_info": _estado_info(guia),
        }
    )


def _h_editar(user, body, ip, json_fn, guia_id):
    """PUT|PATCH /api/guias/<id> · edición de los datos de cabecera."""
    evento_id, datos = g.editar_guia(
        guia_id, user, body or {}, dispositivo=body.get("dispositivo"), ip=ip
    )
    if evento_id is None:
        return json_fn({"ok": False, "error": "No se pudo editar la guía."}, 400)
    guia = g.obtener_guia(guia_id)
    return json_fn({"ok": True, "mensaje": "Guía actualizada", "guia": guia, "evento_id": evento_id, **datos})


def _h_transicion(user, qs, json_fn, guia_id, tipo_evento):
    """
    GET /api/guias/<id>/transicion/<tipo> · si el usuario actual puede ejecutar
    el paso. Permite que el frontend muestre u oculte botones sin adivinar.
    """
    return json_fn({"ok": True, **g.validar_transicion(guia_id, tipo_evento, user)})


def _h_evento(user, body, ip, json_fn, guia_id, tipo_evento):
    """POST /api/guias/<id>/evento/<tipo> · ejecuta un paso del proceso."""
    evento_id = g.procesar_evento(
        guia_id, tipo_evento, user, body or {}, dispositivo=body.get("dispositivo"), ip=ip
    )
    return json_fn(
        {
            "ok": True,
            "mensaje": "Paso registrado",
            "evento_id": evento_id,
            "guia": g.obtener_guia(guia_id),
            "eventos": ev.listar_eventos(guia_id),
        }
    )


def _h_eventos(qs, user, json_fn, guia_id):
    """GET /api/guias/<id>/eventos · historial de la guía."""
    limite = _limite(qs.get("limite", [""])[0], _EVENTOS_POR_DEFECTO, 500)
    todos = ev.listar_eventos(guia_id)
    return json_fn(
        {
            "ok": True,
            "eventos": todos[-limite:],
            "total": len(todos),
            "truncado": len(todos) > limite,
        }
    )


def _h_estados(user, json_fn):
    """GET /api/guias/estados · catálogo de estados con su etiqueta y color."""
    return json_fn({"ok": True, "estados": [{"clave": k, "info": v} for k, v in g.ESTADOS.items()]})


def _estado_info(guia: dict) -> dict:
    """Etiqueta y clase CSS del estado, para que el HTML no tenga que saberlo."""
    etiqueta, clase = g.estado_info(guia.get("estado", ""))
    return {"estado": guia.get("estado"), "etiqueta": etiqueta, "clase": clase}


# Rutas con id en el camino. El router las resuelve con re.match.
RUTA_GUIA_ID_REGEX = r"^/api/guias/(\d+)$"
RUTA_GUIA_EVENTOS_REGEX = r"^/api/guias/(\d+)/eventos$"
RUTA_GUIA_EVENTO_REGEX = r"^/api/guias/(\d+)/evento/([a-z_]+)$"
RUTA_GUIA_TRANSICION_REGEX = r"^/api/guias/(\d+)/transicion/([a-z_]+)$"


def listar_guias_api(qs, user, json_fn):
    """GET /api/guias"""
    return _h_listar(qs, user, json_fn)


def conteo_guias_api(qs, user, json_fn):
    """GET /api/guias/conteo"""
    return _h_conteo(qs, user, json_fn)


def estados_guias_api(user, json_fn):
    """GET /api/guias/estados"""
    return _h_estados(user, json_fn)


def editar_guia_api(guia_id: int, body, user, ip, json_fn):
    """PUT|PATCH /api/guias/<id>"""
    return _h_editar(user, body, ip, json_fn, guia_id)


def eventos_guia_api(qs, user, guia_id: int, json_fn):
    """GET /api/guias/<id>/eventos"""
    return _h_eventos(qs, user, json_fn, guia_id)


def evento_post_guia_api(user, body, ip, json_fn, guia_id: int, tipo_evento: str):
    """POST /api/guias/<id>/evento/<tipo>"""
    return _h_evento(user, body, ip, json_fn, guia_id, tipo_evento)


def transicion_guia_api(qs, user, guia_id: int, tipo_evento: str, json_fn):
    """GET /api/guias/<id>/transicion/<tipo>"""
    return _h_transicion(user, qs, json_fn, guia_id, tipo_evento)


def detalle_guia_api(qs, user, guia_id: int, json_fn):
    """GET /api/guias/<id>"""
    return _h_detalle(qs, user, json_fn, guia_id)