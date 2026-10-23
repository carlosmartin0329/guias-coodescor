#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio para gestión de contactos de clientes (tabla clientes_contactos).

Esta tabla almacena información de las personas que vienen por los pedidos,
vinculadas a cada cliente mediante su NIT.

Reglas de negocio:
- nit_cliente es FK a clientes(nit)
- nombre es el nombre de la persona que recibe/retira
- Los datos se usan para autocompletado en el formulario de guías
- Se puede buscar por nombre o por nit_cliente
"""

from typing import Any, Dict, List, Optional, Tuple

from guias_coodescor.core.logging_config import get_logger
from guias_coodescor.core.utils import ahora_txt
from guias_coodescor.database.connection import db_connection

_log = get_logger("guias_coodescor.clientes_contactos")


# ---------------------------------------------------------------------------
# Lecturas
# ---------------------------------------------------------------------------

def obtener_contacto_por_id(contacto_id: int) -> Optional[Dict[str, Any]]:
    """Devuelve un contacto por su ID o None si no existe."""
    with db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM clientes_contactos WHERE id = ?",
            (contacto_id,),
        ).fetchone()
        return dict(row) if row else None


def listar_contactos_por_cliente(nit_cliente: str, limite: int = 50) -> List[Dict[str, Any]]:
    """Devuelve todos los contactos de un cliente ordenados por nombre."""
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM clientes_contactos WHERE nit_cliente = ? COLLATE NOCASE ORDER BY nombre ASC LIMIT ?",
            (nit_cliente, int(limite)),
        ).fetchall()
        return [dict(r) for r in rows]


def buscar_contactos(q: str, nit_cliente: Optional[str] = None, limite: int = 10) -> List[Dict[str, Any]]:
    """Búsqueda de contactos por nombre o teléfono.
    
    Args:
        q: Texto de búsqueda (nombre, teléfono, cédula)
        nit_cliente: Filtrar por NIT de cliente (opcional)
        limite: Máximo de resultados
    
    Returns:
        Lista de contactos ordenados por relevancia
    """
    q = (str(q or "")).strip()
    limite = max(1, int(limite or 10))
    
    if not q:
        # Si no hay query, devolver contactos recientes
        with db_connection() as conn:
            if nit_cliente:
                rows = conn.execute(
                    "SELECT * FROM clientes_contactos WHERE nit_cliente = ? COLLATE NOCASE ORDER BY created_at DESC LIMIT ?",
                    (nit_cliente, limite),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM clientes_contactos ORDER BY created_at DESC LIMIT ?",
                    (limite,),
                ).fetchall()
            return [dict(r) for r in rows]
    
    q_upper = q.upper()
    q_like = f"%{q}%"
    
    # Construir consulta con filtrado por nit_cliente si se proporciona
    where_clauses = []
    params: List[Any] = []
    
    if nit_cliente:
        where_clauses.append("nit_cliente = ? COLLATE NOCASE")
        params.append(nit_cliente)
    
    where_clauses.append(
        "(UPPER(nombre) LIKE ? OR UPPER(telefono) LIKE ? OR UPPER(cedula) LIKE ?)"
    )
    params.extend([q_like.upper(), q_like.upper(), q_like.upper()])
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Ranking: nombre exacto > nombre prefijo > teléfono > cédula
    query = f"""
    SELECT *,
      CASE
        WHEN UPPER(nombre) = ? THEN 1
        WHEN UPPER(nombre) LIKE ? THEN 2
        WHEN UPPER(telefono) LIKE ? THEN 3
        WHEN UPPER(cedula) LIKE ? THEN 4
        ELSE 99
      END AS score
    FROM clientes_contactos
    WHERE {where_sql}
    ORDER BY score ASC, nombre ASC
    LIMIT ?
    """
    
    params_extended = [q_upper, f"{q_upper}%", q_like.upper(), q_like.upper()] + params + [limite]
    
    with db_connection() as conn:
        rows = conn.execute(query, params_extended).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Escrituras
# ---------------------------------------------------------------------------

def guardar_contacto(
    datos: Dict[str, Any],
    nit_cliente: str,
) -> Tuple[bool, str, Optional[int]]:
    """Guarda un contacto de cliente. Devuelve (ok, mensaje, contacto_id).
    
    Args:
        datos: Diccionario con campos del contacto (nombre, telefono, cedula, etc.)
        nit_cliente: NIT del cliente al que pertenece el contacto
    """
    nit_cliente = (nit_cliente or "").strip()
    if not nit_cliente:
        return False, "El NIT del cliente es obligatorio", None
    
    nombre = (datos.get("nombre") or "").strip()
    if not nombre:
        return False, "El nombre del contacto es obligatorio", None
    
    # Validar que el cliente exista
    with db_connection() as conn:
        cliente_existe = conn.execute(
            "SELECT 1 FROM clientes WHERE nit = ? COLLATE NOCASE",
            (nit_cliente,),
        ).fetchone()
        if not cliente_existe:
            return False, f"El cliente con NIT {nit_cliente} no existe", None
    
    contacto_id = datos.get("id")
    ahora = ahora_txt()
    
    limpio = {
        "nit_cliente": nit_cliente,
        "nombre": nombre,
        "telefono": (datos.get("telefono") or "").strip() or None,
        "cedula": (datos.get("cedula") or "").strip() or None,
    }
    
    with db_connection(commit=True) as conn:
        if contacto_id:
            # Actualizar existente
            sets = ["nombre = ?", "telefono = ?", "cedula = ?"]
            params = [limpio["nombre"], limpio["telefono"], limpio["cedula"]]
            params.append(contacto_id)
            
            conn.execute(
                f"UPDATE clientes_contactos SET {', '.join(sets)} WHERE id = ?",
                params,
            )
            _log.info("Contacto ID=%s ACTUALIZADO", contacto_id)
            return True, "Contacto actualizado", contacto_id
        else:
            # Insertar nuevo
            cols = ["nit_cliente", "nombre", "telefono", "cedula", "created_at"]
            vals = [
                limpio["nit_cliente"],
                limpio["nombre"],
                limpio["telefono"],
                limpio["cedula"],
                ahora,
            ]
            cur = conn.execute(
                f"INSERT INTO clientes_contactos ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(vals))})",
                vals,
            )
            contacto_id = cur.lastrowid
            _log.info("Contacto ID=%s CREADO para cliente NIT=%s", contacto_id, nit_cliente)
            return True, "Contacto creado", contacto_id


def eliminar_contacto(contacto_id: int) -> Tuple[bool, str]:
    """Elimina un contacto de cliente."""
    with db_connection(commit=True) as conn:
        # Verificar que existe
        existe = conn.execute(
            "SELECT 1 FROM clientes_contactos WHERE id = ?",
            (contacto_id,),
        ).fetchone()
        if not existe:
            return False, "Contacto no encontrado"
        
        conn.execute("DELETE FROM clientes_contactos WHERE id = ?", (contacto_id,))
        _log.info("Contacto ID=%s ELIMINADO", contacto_id)
        return True, "Contacto eliminado"


def asegurar_contacto(
    nit_cliente: str,
    nombre: str,
    telefono: Optional[str] = None,
    cedula: Optional[str] = None,
) -> Tuple[bool, Optional[int]]:
    """Asegura que exista un contacto para un cliente. Si existe con mismo nombre, lo devuelve.
    Si no existe, lo crea. Devuelve (ok, contacto_id).
    
    Esto se usa cuando se guardan datos de entrega para auto-completar en futuras guías.
    """
    nit_cliente = (nit_cliente or "").strip()
    nombre = (nombre or "").strip()
    
    if not nit_cliente or not nombre:
        return False, None
    
    # Buscar si ya existe
    with db_connection() as conn:
        row = conn.execute(
            "SELECT id FROM clientes_contactos WHERE nit_cliente = ? COLLATE NOCASE AND UPPER(nombre) = ? COLLATE NOCASE",
            (nit_cliente, nombre.upper()),
        ).fetchone()
        
        if row:
            return True, row["id"]
    
    # Crear nuevo
    ok, msg, contacto_id = guardar_contacto(
        {"nombre": nombre, "telefono": telefono, "cedula": cedula},
        nit_cliente,
    )
    return ok, contacto_id
