#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio de gestión de eventos y adjuntos de las guías.
Maneja la firma digital, fotos y el registro de eventos.
"""
import json
from typing import Any, Dict, List, Optional

from guias_coodescor.config import TRANSICION
from guias_coodescor.core.logging_config import get_logger
from guias_coodescor.core.utils import (
    ahora_milis,
    ahora_txt,
    data_url_a_bytes,
    extraer_extension_data_url,
    guardar_adjunto_bytes,
)
from guias_coodescor.database.connection import db_connection, get_db_lock

logger = get_logger("guias_coodescor.eventos")


def _procesar_adjuntos(guia_id: int, tipo: str, datos: Dict[str, Any]) -> Dict[str, Any]:
    """
    De los datos entrantes, extrae firma/foto como data URL, los guarda en
    disco y reemplaza el campo por la ruta 'adjuntos/xxx'.
    """
    for campo in ("firma", "foto", "entrega_firma"):
        data_url = datos.pop(campo, "") or ""
        if not isinstance(data_url, str) or not data_url.startswith("data:image"):
            continue
        ext = extraer_extension_data_url(data_url)
        if ext == "bin":
            raise ValueError(f"Formato de imagen no reconocido en campo '{campo}'")
        bytes_img = data_url_a_bytes(data_url)
        if not bytes_img:
            raise ValueError(f"No se pudo decodificar la imagen '{campo}'")
        nombre_archivo = f"g{guia_id}_{tipo}_{campo}_{ahora_milis()}.{ext}"
        ruta_rel = guardar_adjunto_bytes(nombre_archivo, bytes_img)
        datos[campo + "_archivo"] = ruta_rel
    return datos


def agregar_evento(
    guia_id: int,
    tipo: str,
    user: dict,
    datos: Optional[Dict[str, Any]] = None,
    dispositivo: Optional[str] = None,
    ip: Optional[str] = None,
) -> int:
    """
    Agrega un evento a una guía y cambia el estado de la guía si corresponde.
    Usa un lock global para evitar race conditions en escritura crítica.
    """
    datos = dict(datos or {})
    ahora = ahora_txt()

    with get_db_lock():
        with db_connection(commit=True) as conn:
            fila = conn.execute(
                "SELECT id, estado FROM guias WHERE id = ?", (guia_id,)
            ).fetchone()
            if not fila:
                raise ValueError("Guía no existe")

            datos = _procesar_adjuntos(guia_id, tipo, datos)

            cur = conn.execute(
                """
                INSERT INTO eventos(guia_id, tipo, usuario_id, usuario, rol, en, dispositivo, ip, datos)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guia_id,
                    tipo,
                    user.get("id"),
                    user.get("usuario"),
                    user.get("rol"),
                    ahora,
                    dispositivo or "",
                    ip or "",
                    json.dumps(datos, ensure_ascii=False),
                ),
            )
            evento_id = cur.lastrowid

            if tipo in TRANSICION:
                nuevo_estado = TRANSICION[tipo]
                if nuevo_estado is not None:
                    conn.execute(
                        "UPDATE guias SET estado = ? WHERE id = ?",
                        (nuevo_estado, guia_id),
                    )
                if tipo == "anular":
                    conn.execute(
                        "UPDATE guias SET anulada_motivo = ?, anulada_por = ?, anulada_en = ? WHERE id = ?",
                        (datos.get("motivo", ""), user.get("id"), ahora, guia_id),
                    )
    logger.info(
        "Evento tipo=%s agregado a guia_id=%s usuario=%s",
        tipo, guia_id, user.get("usuario"),
    )
    return evento_id


def listar_eventos(guia_id: int) -> List[Dict[str, Any]]:
    """Devuelve los eventos de una guía con el campo 'datos' parseado."""
    with db_connection() as conn:
        filas = conn.execute(
            "SELECT * FROM eventos WHERE guia_id = ? ORDER BY id",
            (guia_id,),
        ).fetchall()
        out = []
        for r in filas:
            d = dict(r)
            try:
                d["datos"] = json.loads(d["datos"] or "{}")
            except (TypeError, ValueError):
                d["datos"] = {}
            out.append(d)
        return out


def obtener_evento_por_tipo(guia_id: int, tipo: str) -> Optional[Dict[str, Any]]:
    for e in listar_eventos(guia_id):
        if e["tipo"] == tipo:
            return e
    return None
