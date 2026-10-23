#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio para gestión de transportadores externos.

Almacena información de transportadores externos registrados por el usuario
administrativo para su reutilización en futuras guías.
"""

from typing import Any, Dict, List, Optional, Tuple

from guias_coodescor.core.logging_config import get_logger
from guias_coodescor.core.utils import ahora_txt
from guias_coodescor.database.connection import db_connection

_log = get_logger("guias_coodescor.transportadores_externos")


# ---------------------------------------------------------------------------
# Lecturas
# ---------------------------------------------------------------------------

def obtener_transportador_externo_por_id(transportador_id: int) -> Optional[Dict[str, Any]]:
    """Devuelve un transportador externo por su ID o None si no existe."""
    with db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM transportadores_externos WHERE id = ?",
            (transportador_id,),
        ).fetchone()
        return dict(row) if row else None


def listar_transportadores_externos(activo: bool = True, limite: int = 50) -> List[Dict[str, Any]]:
    """Devuelve todos los transportadores externos."""
    with db_connection() as conn:
        sql = "SELECT * FROM transportadores_externos"
        params: List[Any] = []
        if activo:
            sql += " WHERE activo = 1"
        sql += " ORDER BY nombre ASC LIMIT ?"
        params.append(limite)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def buscar_transportadores_externos(q: str, limite: int = 10) -> List[Dict[str, Any]]:
    """Búsqueda de transportadores externos por nombre, CC, placa o teléfono."""
    q = (str(q or "")).strip()
    limite = max(1, int(limite or 10))
    
    if not q:
        return listar_transportadores_externos(limite=limite)
    
    q_upper = q.upper()
    q_like = f"%{q}%"
    
    query = """
    SELECT *,
      CASE
        WHEN UPPER(nombre) LIKE ? THEN 1
        WHEN UPPER(cc) LIKE ? THEN 2
        WHEN UPPER(placa) LIKE ? THEN 3
        WHEN UPPER(telefono) LIKE ? THEN 4
        ELSE 99
      END AS score
    FROM transportadores_externos
    WHERE activo = 1 AND (
      UPPER(nombre) LIKE ? OR
      UPPER(cc) LIKE ? OR
      UPPER(placa) LIKE ? OR
      UPPER(telefono) LIKE ?
    )
    ORDER BY score ASC, nombre ASC
    LIMIT ?
    """
    
    params = [
        q_like.upper(),  # nombre exacto
        q_like.upper(),  # cc exacto
        q_like.upper(),  # placa exacto
        q_like.upper(),  # telefono exacto
        q_like.upper(),  # nombre any
        q_like.upper(),  # cc any
        q_like.upper(),  # placa any
        q_like.upper(),  # telefono any
        limite,
    ]
    
    with db_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Escrituras
# ---------------------------------------------------------------------------

def guardar_transportador_externo(
    datos: Dict[str, Any],
    user: Dict[str, Any],
) -> Tuple[bool, str, Optional[int]]:
    """Guarda un transportador externo. Devuelve (ok, mensaje, transportador_id).
    
    Args:
        datos: Diccionario con campos del transportador
        user: Usuario que realiza la acción
    """
    nombre = (datos.get("nombre") or "").strip()
    cc = (datos.get("cc") or "").strip()
    telefono = (datos.get("telefono") or "").strip()
    
    if not nombre:
        return False, "El nombre del transportador es obligatorio", None
    if not cc:
        return False, "La cédula del transportador es obligatoria", None
    if not telefono:
        return False, "El teléfono del transportador es obligatorio", None
    
    transportador_id = datos.get("id")
    ahora = ahora_txt()
    
    limpio = {
        "nombre": nombre,
        "cc": cc,
        "telefono": telefono,
        "vehiculo": (datos.get("vehiculo") or "").strip() or None,
        "placa": (datos.get("placa") or "").strip() or None,
        "flete": (datos.get("flete") or "").strip() or None,
        "observaciones": (datos.get("observaciones") or "").strip() or None,
        "creado_por": user.get("id"),
        "creado_rol": user.get("rol"),
    }
    
    with db_connection(commit=True) as conn:
        if transportador_id:
            # Actualizar existente
            sets = [
                "nombre = ?", "cc = ?", "telefono = ?",
                "vehiculo = ?", "placa = ?", "flete = ?",
                "observaciones = ?", "actualizado_en = ?"
            ]
            params = [
                limpio["nombre"], limpio["cc"], limpio["telefono"],
                limpio["vehiculo"], limpio["placa"], limpio["flete"],
                limpio["observaciones"], ahora,
                transportador_id,
            ]
            
            conn.execute(
                f"UPDATE transportadores_externos SET {', '.join(sets)} WHERE id = ?",
                params,
            )
            _log.info("Transportador externo ID=%s ACTUALIZADO por %s", transportador_id, user.get("usuario"))
            return True, "Transportador externo actualizado", transportador_id
        else:
            # Insertar nuevo
            cols = ["nombre", "cc", "telefono", "vehiculo", "placa", "flete", 
                   "observaciones", "creado_por", "creado_rol", "creado_en", "actualizado_en", "activo"]
            vals = [
                limpio["nombre"], limpio["cc"], limpio["telefono"],
                limpio["vehiculo"], limpio["placa"], limpio["flete"],
                limpio["observaciones"], limpio["creado_por"], limpio["creado_rol"],
                ahora, ahora, 1,
            ]
            cur = conn.execute(
                f"INSERT INTO transportadores_externos ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(vals))})",
                vals,
            )
            transportador_id = cur.lastrowid
            _log.info("Transportador externo ID=%s CREADO por %s", transportador_id, user.get("usuario"))
            return True, "Transportador externo creado", transportador_id


def eliminar_transportador_externo(transportador_id: int, user: Dict[str, Any]) -> Tuple[bool, str]:
    """Elimina un transportador externo (desactiva en lugar de borrar)."""
    with db_connection(commit=True) as conn:
        existe = conn.execute(
            "SELECT 1 FROM transportadores_externos WHERE id = ?",
            (transportador_id,),
        ).fetchone()
        if not existe:
            return False, "Transportador externo no encontrado"
        
        conn.execute(
            "UPDATE transportadores_externos SET activo = 0, actualizado_en = ? WHERE id = ?",
            (ahora_txt(), transportador_id),
        )
        _log.info("Transportador externo ID=%s DESACTIVADO por %s", transportador_id, user.get("usuario"))
        return True, "Transportador externo desactivado"


def asegurar_transportador_externo(
    datos: Dict[str, Any],
    user: Dict[str, Any],
) -> Tuple[bool, Optional[int]]:
    """Asegura que exista un transportador externo. Si existe con misma CC, lo devuelve.
    Si no existe, lo crea. Devuelve (ok, transportador_id).
    """
    cc = (datos.get("cc") or "").strip()
    if not cc:
        return False, None
    
    # Buscar si ya existe
    with db_connection() as conn:
        row = conn.execute(
            "SELECT id FROM transportadores_externos WHERE cc = ? AND activo = 1",
            (cc,),
        ).fetchone()
        
        if row:
            return True, row["id"]
    
    # Crear nuevo
    ok, msg, transportador_id = guardar_transportador_externo(datos, user)
    return ok, transportador_id
