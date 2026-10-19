#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rutas del módulo de administración de la base de datos (solo rol admin).

Se mantienen aparte de router.py por la misma razón que routes_clientes y
routes_receptores: el manejador HTTP solo debe despachar. Cada handler recibe
los datos ya leídos y devuelve (código, cuerpo) usando la función `json_fn`.

Todas las rutas exigen rol admin. Los errores del módulo llegan como
db_admin.DbAdminError y el router los traduce a 400/403 con su mensaje.
"""
from guias_coodescor.services import db_admin_service as db


# ---------------------------------------------------------------------------
# GET · lectura e inspección
# ---------------------------------------------------------------------------

def _h_bases(qs, user, json_fn):
    return json_fn({"ok": True, "bases": db.listar_bases()})


def _h_tablas(qs, user, json_fn):
    base = (qs.get("base", ["guias"])[0]) or "guias"
    return json_fn({"ok": True, "tablas": db.listar_tablas(base)})


def _h_esquema(qs, user, json_fn):
    base = (qs.get("base", ["guias"])[0]) or "guias"
    tabla = qs.get("tabla", [""])[0]
    return json_fn({"ok": True, "esquema": db.describir_tabla(base, tabla)})


def _h_filas(qs, user, json_fn):
    base = (qs.get("base", ["guias"])[0]) or "guias"
    return json_fn(
        {
            "ok": True,
            "datos": db.listar_filas(
                base,
                qs.get("tabla", [""])[0],
                q=qs.get("q", [""])[0],
                pagina=qs.get("pagina", ["1"])[0],
                page_size=qs.get("page_size", ["50"])[0],
                orden=qs.get("orden", [""])[0],
                direccion=qs.get("dir", ["asc"])[0],
            ),
        }
    )


def _h_respaldos(qs, user, json_fn):
    base = (qs.get("base", ["guias"])[0]) or "guias"
    return json_fn({"ok": True, "respaldos": db.listar_respaldos(base)})


def _h_migraciones(qs, user, json_fn):
    return json_fn({"ok": True, "migraciones": db.listar_migraciones()})


def _h_auditoria(qs, user, json_fn):
    return json_fn(
        {
            "ok": True,
            "historial": db.listar_auditoria(
                limite=qs.get("limite", ["100"])[0],
                offset=qs.get("offset", ["0"])[0],
                accion=qs.get("accion", [""])[0],
                usuario=qs.get("usuario", [""])[0],
            ),
            "acciones": db.acciones_auditadas(),
        }
    )


RUTAS_DB_ADMIN_GET = [
    (r"^/api/admin/db/bases$", _h_bases),
    (r"^/api/admin/db/tablas$", _h_tablas),
    (r"^/api/admin/db/esquema$", _h_esquema),
    (r"^/api/admin/db/filas$", _h_filas),
    (r"^/api/admin/db/respaldos$", _h_respaldos),
    (r"^/api/admin/db/migraciones$", _h_migraciones),
    (r"^/api/admin/db/auditoria$", _h_auditoria),
]


# ---------------------------------------------------------------------------
# POST · escritura, respaldos y mantenimiento
# ---------------------------------------------------------------------------

def _h_insertar(user, body, ip, json_fn):
    resultado = db.insertar_fila(
        (body.get("base") or "guias"),
        body.get("tabla") or "",
        body.get("valores") or {},
        user,
        ip,
    )
    return json_fn({"ok": True, "mensaje": "Fila insertada", **resultado})


def _h_actualizar(user, body, ip, json_fn):
    resultado = db.actualizar_fila(
        (body.get("base") or "guias"),
        body.get("tabla") or "",
        body.get("clave"),
        body.get("valores") or {},
        user,
        ip,
    )
    return json_fn({"ok": True, "mensaje": "Fila actualizada", **resultado})


def _h_consulta(user, body, ip, json_fn):
    resultado = db.ejecutar_consulta(
        body.get("base") or "guias",
        body.get("sql") or "",
        escritura=bool(body.get("escritura")),
        admin=user,
        ip=ip,
        confirmado=bool(body.get("confirmar")),
    )
    return json_fn({"ok": True, **resultado})


def _h_crear_respaldo(user, body, ip, json_fn):
    resultado = db.crear_respaldo(
        motivo=body.get("motivo") or "manual",
        base=body.get("base") or "guias",
    )
    return json_fn({"ok": True, "mensaje": "Respaldo creado y verificado", **resultado})


def _h_restaurar(user, body, ip, json_fn):
    resultado = db.restaurar_respaldo(body.get("archivo") or "", user, ip)
    return json_fn({"ok": True, **resultado})


def _h_mantenimiento(user, body, ip, json_fn):
    resultado = db.ejecutar_mantenimiento(body.get("operacion") or "", user, ip)
    return json_fn({"ok": True, "mensaje": "Mantenimiento ejecutado", **resultado})


def _h_aplicar_migraciones(user, body, ip, json_fn):
    resultado = db.aplicar_migraciones(user, ip)
    return json_fn({"ok": True, "mensaje": "Migraciones aplicadas", **resultado})


RUTAS_DB_ADMIN_POST = [
    (r"^/api/admin/db/filas$", _h_insertar),
    (r"^/api/admin/db/actualizar$", _h_actualizar),
    (r"^/api/admin/db/consulta$", _h_consulta),
    (r"^/api/admin/db/respaldo/crear$", _h_crear_respaldo),
    (r"^/api/admin/db/respaldo/restaurar$", _h_restaurar),
    (r"^/api/admin/db/mantenimiento$", _h_mantenimiento),
    (r"^/api/admin/db/migraciones/aplicar$", _h_aplicar_migraciones),
]


# ---------------------------------------------------------------------------
# DELETE · la fila a borrar viaja en la query string
#   DELETE /api/admin/db/filas?base=guias&tabla=clientes&clave=901234
# ---------------------------------------------------------------------------

def _h_eliminar_fila(user, qs, ip, json_fn):
    base = (qs.get("base", ["guias"])[0]) or "guias"
    tabla = qs.get("tabla", [""])[0]
    clave = qs.get("clave", [""])[0]
    resultado = db.eliminar_fila(base, tabla, clave, user, ip)
    return json_fn(
        {
            "ok": True,
            "mensaje": "Fila eliminada",
            "respaldo": resultado.get("respaldo"),
        }
    )


def _h_eliminar_respaldo(user, qs, ip, json_fn):
    db.eliminar_respaldo(qs.get("archivo", [""])[0], user, ip)
    return json_fn({"ok": True, "mensaje": "Respaldo eliminado"})


RUTAS_DB_ADMIN_DELETE = [
    (r"^/api/admin/db/filas$", _h_eliminar_fila),
    (r"^/api/admin/db/respaldo$", _h_eliminar_respaldo),
]