
"""tokens_service.py
Gestión de tokens públicos de UN SOLO USO para firma de entrega SIN que el cliente
sea usuario del sistema. El link público /firma/<TOKEN> se puede enviar por WhatsApp
(link wa.me) o correo electrónico desde Ventas o desde Administrativo.

Un token tiene: guia_id (UNIQUE: 1 token por guía, regenerable), creado_por/rol,
expira 7 días, usado_en/ip/ua para auditoría. Al marcar `usado` se dispara un evento
'entrega_cliente' en guias_service.procesar_evento() con un usuario falso público
(rol='publico') y la guía pasa a estado ENTREGADA, igual que si lo hiciera CEDIS
o el Transportador Propio.
"""
from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any, Dict, Optional

from guias_coodescor.core.logging_config import get_logger
from guias_coodescor.database.connection import db_connection
from guias_coodescor.core.utils import ahora_txt

logger = get_logger(__name__)

# Cuánto dura un token de entrega (por defecto 7 días naturales). Lo guardamos en
# horas para ser consistente con LOGIN_SESSION_DURATION_HOURS.
TOKEN_ENTREGA_DURATION_HOURS = 7 * 24  # 7 días

# Estados donde el link YA ESTÁ ACTIVO (Ventas puede generarlo desde CREADA; o CEDIS lo genera al marcar EN_RUTA).
# Cualquier estado NO cerrado / no anulado: si tiene token emitido, el link se puede usar.
_ESTADOS_LINK_ACTIVOS_CON_TOKEN = ("CREADA", "RECIBIDA_ADMIN", "EN_CEDIS", "EN_RUTA")
# Estado anterior de activación (mantener compatibilidad: EN_RUTA siempre está activo sin token explícito)
_ESTADO_LINK_ACTIVO = "EN_RUTA"
# Estados donde el link ya no tiene sentido (guía cerrada/anulada)
_ESTADOS_LINK_CERRADOS = ("ENTREGADA", "ANULADA")


def _fecha_expiracion() -> str:
    from datetime import datetime as _dt
    try:
        ahora_dt = _dt.fromisoformat(ahora_txt())
    except Exception:
        ahora_dt = _dt.now()
    exp = ahora_dt + timedelta(hours=TOKEN_ENTREGA_DURATION_HOURS)
    return exp.isoformat(timespec="seconds")


def generar_token_entrega(
    guia_id: int,
    user: Dict[str, Any],
    regenerar_si_existe: bool = False,
) -> str:
    """Genera token aleatorio URL-safe de 32 chars para la guía.

    POR DEFECTO, si la guía ya tenía un token: NO LO REGENERA (evita duplicados
    y garantiza que Ventas / Administrativo solo emitan 1 link por cliente).
    Use `regenerar_si_existe=True` solo para casos de soporte.

    Devuelve el string token (ya está guardado en DB).
    """
    if not guia_id or not isinstance(guia_id, int) or guia_id <= 0:
        raise ValueError("ID guia inválido")
    with db_connection(commit=True) as conn:
        existe = conn.execute(
            "SELECT id, token FROM entrega_tokens WHERE guia_id = ?", (guia_id,)
        ).fetchone()
        if existe and not regenerar_si_existe:
            logger.info(
                "Token entrega YA EXISTE guia_id=%s. Reutilizando (no regenera). "
                "Solicitado por usuario %s (rol %s)",
                guia_id,
                user.get("id"), user.get("rol"),
            )
            return existe["token"]
    token = secrets.token_urlsafe(32)  # ≈ 43 chars url-safe
    creado_por = int(user["id"]) if isinstance(user.get("id"), int) else None
    creado_rol = str(user.get("rol") or "")
    creado_en = ahora_txt()
    expira = _fecha_expiracion()
    with db_connection(commit=True) as conn:
        if regenerar_si_existe:
            existe = conn.execute(
                "SELECT id FROM entrega_tokens WHERE guia_id = ?", (guia_id,)
            ).fetchone()
            if existe:
                conn.execute(
                    """
                    UPDATE entrega_tokens
                       SET token = ?,
                           creado_por = ?,
                           creado_rol = ?,
                           creado_en = ?,
                           expira = ?,
                           usado_en = NULL,
                           usado_ip = NULL,
                           usado_ua = NULL
                     WHERE guia_id = ?
                    """,
                    (token, creado_por, creado_rol, creado_en, expira, guia_id),
                )
                logger.info(
                    "Token entrega REGENERADO (soporte) guia_id=%s por usuario %s (rol %s)",
                    guia_id, creado_por, creado_rol,
                )
                return token
        conn.execute(
            """
            INSERT INTO entrega_tokens (guia_id,token,creado_por,creado_rol,creado_en,expira)
            VALUES (?,?,?,?,?,?)
            """,
            (guia_id, token, creado_por, creado_rol, creado_en, expira),
        )
    logger.info(
        "Token entrega NUEVO creado para guia_id=%s por usuario %s (rol %s)",
        guia_id, creado_por, creado_rol,
    )
    return token


def obtener_info_token_guia(guia_id: int) -> Optional[Dict[str, Any]]:
    """Devuelve información del último token de la guía (para mostrar en UI
    el mensaje "Ya fue emitido por <rol> <fecha>" y evitar doble envío).

    Devuelve None si la guía no tiene token emitido aún.
    """
    if not guia_id or not isinstance(guia_id, int) or guia_id <= 0:
        return None
    with db_connection() as conn:
        row = conn.execute(
            """
            SELECT t.*, u.nombre as creado_por_nombre, u.usuario as creado_por_usuario
              FROM entrega_tokens t
              LEFT JOIN usuarios u ON t.creado_por = u.id
             WHERE t.guia_id = ?
             ORDER BY t.id DESC
             LIMIT 1
            """,
            (guia_id,),
        ).fetchone()
        return dict(row) if row else None


def obtener_por_token(token: str) -> Optional[Dict[str, Any]]:
    """Devuelve info del token (incluyendo guia_id) o None si no existe / expiró."""
    if not token or not isinstance(token, str):
        return None
    token = token.strip()
    ahora = ahora_txt()
    with db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM entrega_tokens WHERE token = ?", (token,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        if d.get("expira") and d["expira"] < ahora:
            logger.warning("Token entrega expirado: token=%s guia_id=%s", token, d["guia_id"])
            return None
        return d


def token_fue_usado(token_info: Dict[str, Any]) -> bool:
    return bool(token_info.get("usado_en"))


def marcar_usado(
    token_info: Dict[str, Any],
    ip: Optional[str] = None,
    ua: Optional[str] = None,
) -> None:
    """Marca token como usado. Auditoría. No cierra la guía — eso lo hace
       cerrar_entrega_por_token() en este mismo servicio que llama a marcar_usado + procesar_evento."""
    with db_connection(commit=True) as conn:
        conn.execute(
            "UPDATE entrega_tokens SET usado_en = ?, usado_ip = ?, usado_ua = ? WHERE id = ?",
            (ahora_txt(), ip, ua, int(token_info["id"])),
        )


def estado_activacion_link(guia_id: int) -> Dict[str, Any]:
    """
    Devuelve el estado de ACTIVACIÓN del link público para una guía.

    NUEVA REGLA (26/09/2026): Ventas puede generar link de recibido INMEDIATAMENTE
    al crear la guía (estado CREADA, checkbox). Por tanto:
      - El link ESTÁ ACTIVO SI (estado IN {CREADA, RECIBIDA_ADMIN, EN_CEDIS, EN_RUTA}
                                   Y EXISTE token emitido en entrega_tokens)
                              O  estado == EN_RUTA (por compatibilidad, aunque
                                   todavía no exista token por cualquier motivo)
      - El link NO está activo si la guía fue ANULADA o ENTREGADA (cerrada)
      - O si el estado es CREADA/RECIBIDA_ADMIN/EN_CEDIS y aún no emitieron token.
    """
    if not guia_id or not isinstance(guia_id, int) or guia_id <= 0:
        return {"activo": False, "codigo": "NO_EXISTE", "motivo": "Guía no existe", "estado_guia": None}
    try:
        from guias_coodescor.services.guias_service import obtener_guia
        g = obtener_guia(guia_id)
        if not g:
            return {"activo": False, "codigo": "NO_EXISTE", "motivo": "Guía no existe", "estado_guia": None}
        estado_guia = str(g.get("estado") or "")
        tiene_token = bool(obtener_info_token_guia(guia_id))
        if estado_guia in _ESTADOS_LINK_CERRADOS:
            return {"activo": False, "codigo": "CERRADA", "motivo": f"Guía en estado {estado_guia}. Ya fue entregada o anulada; no requiere confirmación adicional.", "estado_guia": estado_guia}
        if estado_guia == _ESTADO_LINK_ACTIVO or (estado_guia in _ESTADOS_LINK_ACTIVOS_CON_TOKEN and tiene_token):
            return {"activo": True, "codigo": "OK", "motivo": "Link activo. El cliente puede abrir y confirmar la entrega.", "estado_guia": estado_guia}
        if estado_guia in _ESTADOS_LINK_ACTIVOS_CON_TOKEN:
            motivo = (
                "Link disponible solo si genera primero el link.\n"
                "  • CREADA / RECIBIDA_ADMIN: marcar la casilla 🔗 Generar link de recibido al crear la guía (Ventas),\n"
                "    o desde el detalle de la guía con Ventas/Administrativo botón 'Generar link'.\n"
                "  • EN_CEDIS: cuando CEDIS complete su proceso unificado de entrega a transportador,\n"
                "    el link se genera automáticamente aquí y queda listo para enviar al cliente."
            )
            return {"activo": False, "codigo": "NO_ACTIVO", "motivo": motivo, "estado_guia": estado_guia}
        return {"activo": False, "codigo": "NO_ACTIVO", "motivo": f"Link no activo para estado {estado_guia}. Contacte a soporte.", "estado_guia": estado_guia}
    except Exception as e:
        logger.exception("Error validando activación link guia_id=%s", guia_id)
        return {"activo": False, "codigo": "NO_ACTIVO", "motivo": f"Error interno: {e}", "estado_guia": None}


def listar_pendientes_confirmacion_link(limite: int = 50) -> list[Dict[str, Any]]:
    """
    Lista las guías con link de confirmación PÚBLICO GENERADO y AÚN NO USADO por el cliente.
    NUEVO (26/09/2026): incluye TODOS los estados donde el link se puede generar
    (CREADA, RECIBIDA_ADMIN, EN_CEDIS, EN_RUTA) siempre que tenga token emitido y no usado.
    Antes solo incluía EN_RUTA; ahora Ventas lo genera desde CREADA.

    Devuelve lista de dicts: [ {guia_id, consecutivo, cliente, estado, creado_en,
    creado_por_nombre, creado_por_usuario, creado_rol, expira, token}, ... ]
    ordenados por creado_en DESC (los más recientes / urgentes primero).
    """
    ahora = ahora_txt()
    estados_validos = tuple(_ESTADOS_LINK_ACTIVOS_CON_TOKEN)
    placeholders = ",".join("?" * len(estados_validos))
    args: list = [ahora, *estados_validos, int(limite) if limite and int(limite) > 0 else 50]
    with db_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT t.guia_id,
                   t.token,
                   t.creado_en,
                   t.expira,
                   t.creado_rol,
                   u.nombre   as creado_por_nombre,
                   u.usuario  as creado_por_usuario,
                   g.consecutivo,
                   g.cliente,
                   g.estado
              FROM entrega_tokens t
              JOIN guias g ON g.id = t.guia_id
              LEFT JOIN usuarios u ON t.creado_por = u.id
             WHERE t.usado_en IS NULL
               AND (t.expira IS NULL OR t.expira >= ?)
               AND g.estado IN ({placeholders})
             ORDER BY t.creado_en DESC
             LIMIT ?
            """,
            tuple(args),
        ).fetchall()
        return [dict(r) for r in rows]


def listar_usuarios_transportadores_activos() -> list[Dict[str, Any]]:
    """Devuelve lista de usuarios con rol='transportador' y activo=1, para dropdown
       en el selector de Tipo Transportador PROPIO que usa Administrativo."""
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT id, usuario, nombre, rol, activo FROM usuarios WHERE rol = 'transportador' AND activo = 1 ORDER BY nombre ASC"
        ).fetchall()
        return [dict(r) for r in rows]
