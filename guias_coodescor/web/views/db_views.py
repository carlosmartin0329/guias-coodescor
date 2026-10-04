#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interfaz del módulo de administración de la base de datos.

El HTML de esta página es deliberadamente mínimo: un contenedor por sección y
nada más. Todo el trabajo lo hace static/db-admin.js contra /api/admin/db/*, de
modo que la página siga siendo utilizable cuando el frontend se separe por
completo del backend.
"""
from guias_coodescor.core.utils import ahora_txt
from guias_coodescor.services import db_admin_service as db
from guias_coodescor.web.views.base import escape, page


_SECCIONES = [
    ("resumen", "Resumen", "Archivos, tamaño e integridad de las bases de datos."),
    ("explorador", "Explorador", "Ver, buscar, agregar y editar filas de cualquier tabla."),
    ("sql", "Consultas SQL", "Ejecutar consultas de lectura o de escritura."),
    ("respaldos", "Respaldos", "Crear, descargar, restaurar y eliminar respaldos."),
    ("mantenimiento", "Mantenimiento", "VACUUM, optimize, WAL y migraciones."),
    ("auditoria", "Auditoría", "Historial de todo lo que se ha modificado desde aquí."),
]


def vista_admin_db(user: dict) -> str:
    """Página del módulo de base de datos. Solo accesible para el rol admin."""
    if not user or user.get("rol") != "admin":
        return page(
            "Base de datos",
            "<h2>Base de datos</h2><p class='sin'>Sin permiso. Se requiere rol admin.</p>",
            user,
        )

    navegacion = "".join(
        f'<button type="button" class="btn db-tab{" activo" if clave == "resumen" else ""}" '
        f'data-db-seccion="{clave}">{escape(titulo)}</button>'
        for clave, titulo, _ in _SECCIONES
    )
    secciones = "".join(
        f'<section class="card db-seccion" id="db-sec-{clave}"'
        f'{" " if clave == "resumen" else " hidden"}>'
        f'<h3>{escape(titulo)}</h3>'
        f'<p class="nota">{escape(descripcion)}</p>'
        f'<div id="db-cuerpo-{clave}"><p class="sin">Cargando…</p></div>'
        f"</section>"
        for clave, titulo, descripcion in _SECCIONES
    )

    cuerpo = f"""
    <h2>🗄️ Base de datos</h2>
    <p class="nota" style="margin-bottom:14px">
      Archivos en <code>{escape(db._ruta_base('guias'))}</code> y
      <code>{escape(db._ruta_base('receptores'))}</code> ·
      servidor iniciado el {escape(ahora_txt())}.
      Todo lo que hagas aquí queda registrado en la auditoría y no se puede
      deshacer sin restaurar un respaldo.
    </p>

    <nav class="db-nav" aria-label="Secciones de base de datos">{navegacion}</nav>

    <div id="db-aviso" class="db-aviso" role="status" aria-live="polite" hidden></div>

    {secciones}

    <div class="db-modal-wrap" id="db-modal-wrap" hidden>
      <div class="db-modal" role="dialog" aria-modal="true" aria-label="Editor de fila">
        <button type="button" class="db-modal-cerrar" id="db-modal-cerrar" aria-label="Cerrar">×</button>
        <div id="db-modal"></div>
      </div>
    </div>
    """
    return page(
        "Base de datos",
        cuerpo,
        user,
        extra='<script src="/static/db-admin.js"></script>',
    )