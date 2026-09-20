#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vista HTML del panel administrativo (usuarios, configuración, exportar).
"""
from guias_coodescor.config import ROL_LABEL
from guias_coodescor.services.auth_service import listar_usuarios, obtener_config
from guias_coodescor.web.views.base import escape, page


def vista_admin(user: dict) -> str:
    if user.get("rol") != "admin":
        return page("Admin", "<p class='sin'>Sin permiso.</p>", user)
    us = listar_usuarios()
    filas = "".join(
        f"<tr><td>{r['id']}</td><td>{escape(r['usuario'])}</td><td>{escape(r['nombre'])}</td>"
        f"<td>{escape(ROL_LABEL.get(r['rol'], r['rol']))}</td>"
        f"<td>{'activo' if r['activo'] else 'inactivo'}</td>"
        f"<td>{escape(r.get('ultima_sesion') or '-')}</td></tr>"
        for r in us
    )
    siguiente = escape(obtener_config("siguiente", ""))
    pie = escape(obtener_config("pie", ""))
    empresa = escape(obtener_config("empresa", ""))

    # Configuración de listas de autollenado y vínculos externos
    lista_clientes = escape(obtener_config("lista_clientes_json", "[]") or "[]")
    vdb_tipo = escape(obtener_config("vinculo_db_externo_tipo", "ninguno") or "ninguno")
    vdb_url = escape(obtener_config("vinculo_db_externo_url", "") or "")
    vdb_tok = escape(obtener_config("vinculo_db_externo_token", "") or "")
    vdb_nombre = escape(obtener_config("vinculo_db_externo", "") or "")

    cuerpo = f"""<h2>Panel administrativo</h2>
    <section class="card"><h3>👥 Usuarios</h3>
      <table class="tabla"><tr><th>#</th><th>Usuario</th><th>Nombre</th><th>Rol</th><th>Estado</th><th>Última sesión</th></tr>{filas}</table>
      <form class="form grid" data-api="/api/usuarios" data-redirect="true">
        <label>Usuario<input name="usuario" required></label>
        <label>Nombre<input name="nombre" required></label>
        <label>Contraseña<input name="clave" type="password" required minlength="6"></label>
        <label>Rol<select name="rol"><option value="ventas">Ventas</option>
          <option value="administrativo">Administrativo (bodega / recepción)</option>
          <option value="cedis">CEDIS</option>
          <option value="transportador">Transportador (entrega en ruta)</option>
          <option value="admin">Admin. del sistema (total)</option></select></label>
        <button class="btn primario">Crear usuario</button></form></section>

    <section class="card"><h3>⚙️ Configuración general</h3>
      <form class="form grid" data-api="/api/config" data-redirect="true">
        <label>Próximo consecutivo<input name="siguiente" type="number" value="{siguiente}"></label>
        <label>Nombre empresa<input name="empresa" value="{empresa}"></label>
        <label class="wide">Pie de página<input name="pie" value="{pie}"></label>
        <button class="btn">Guardar</button></form>
      <p><a class="btn" href="/api/exportar.csv">⬇️ Exportar guías (CSV / Excel)</a></p></section>

    <section class="card"><h3>📇 Listas de autollenado · clientes</h3>
      <p class="nota">Administra la lista de clientes para que el formulario de <b>Nueva guía</b> los autocomplete.
      Pegue un JSON con el formato: <code>[{'{'}"nombre":"Cliente SAS","direccion":"Cl...","ciudad":"Montería"{'}'},…]</code></p>
      <form class="form grid" data-api="/api/config" data-redirect="true">
        <label class="wide">Lista de clientes (JSON)
          <textarea name="lista_clientes_json" rows="8" spellcheck="false" style="font-family:monospace;font-size:12px">{lista_clientes}</textarea></label>
        <button class="btn primario">💾 Guardar lista de clientes</button></form>
      <p class="nota">Ejemplo rápido: <code style="background:#f0f0f0;padding:2px 4px">[{'{'}"nombre":"Droguería La Esperanza","direccion":"Cl 25 # 5-33","ciudad":"Montería"{'}'}]</code></p>
    </section>

    <section class="card"><h3>🔗 Vínculos / conexiones a bases externas</h3>
      <p class="nota">Configura aquí conexiones para importar listados de clientes desde sistemas externos
      (actualmente se guarda la configuración para uso futuro; el vínculo manual vía JSON es la opción inmediata).
      Todos los datos de conexión se almacenan LOCALMENTE en la tabla <code>config</code>.</p>
      <form class="form grid" data-api="/api/config" data-redirect="true">
        <label>Nombre del vínculo<input name="vinculo_db_externo" value="{vdb_nombre}" placeholder="Ej: ERP Coodescor / SIIGO"></label>
        <label>Tipo de vínculo<select name="vinculo_db_externo_tipo">
          <option value="ninguno" {"selected" if vdb_tipo=="ninguno" else ""}>Ninguno (solo JSON local)</option>
          <option value="api_rest" {"selected" if vdb_tipo=="api_rest" else ""}>API REST (HTTP JSON)</option>
          <option value="sqlite" {"selected" if vdb_tipo=="sqlite" else ""}>SQLite · archivo local</option>
          <option value="postgres" {"selected" if vdb_tipo=="postgres" else ""}>PostgreSQL</option>
          <option value="mysql" {"selected" if vdb_tipo=="mysql" else ""}>MySQL / MariaDB</option>
          <option value="excel_csv" {"selected" if vdb_tipo=="excel_csv" else ""}>Excel / CSV importado</option>
        </select></label>
        <label class="wide">URL / Ruta del archivo / Host<input name="vinculo_db_externo_url" value="{vdb_url}" placeholder="https://erp…  o  C:/datos/clientes.db  o  192.168.1.10"></label>
        <label class="wide">Token / usuario:clave (se guarda LOCALMENTE)<input name="vinculo_db_externo_token" type="password" value="{vdb_tok}" placeholder="Bearer eyJ… o usuario:********"></label>
        <button class="btn primario">💾 Guardar configuración de vínculo</button>
      </form>
    </section>"""
    return page("Admin", cuerpo, user)
