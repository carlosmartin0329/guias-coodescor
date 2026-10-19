#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vista HTML del panel administrativo (usuarios, configuración, exportar).
"""
import json
from guias_coodescor.config import ROL_LABEL
from guias_coodescor.services.auth_service import listar_usuarios, obtener_config
from guias_coodescor.web.views.base import escape, page


def vista_admin(user: dict) -> str:
    if user.get("rol") != "admin":
        return page("Admin", "<p class='sin'>Sin permiso.</p>", user)
    us = listar_usuarios()
    filas_list = []
    for r in us:
        uid = r["id"]
        usuario_js = json.dumps(r["usuario"])
        nombre_js = json.dumps(r["nombre"])
        rol_js = json.dumps(r["rol"])
        activo_js = int(bool(r["activo"]))
        onclick = f"abrirEditarUsuario({uid}, {usuario_js}, {nombre_js}, {rol_js}, {activo_js})"
        filas_list.append(
            "<tr><td>{uid}</td><td>{usuario}</td><td>{nombre}</td>"
            "<td>{rol_label}</td><td>{estado}</td><td>{ultima_sesion}</td>"
            "<td><button class='btn mini' type='button' onclick=\"{onclick}\">Editar</button></td></tr>".format(
                uid=uid,
                usuario=escape(r["usuario"]),
                nombre=escape(r["nombre"]),
                rol_label=escape(ROL_LABEL.get(r["rol"], r["rol"])),
                estado="activo" if r["activo"] else "inactivo",
                ultima_sesion=escape(r.get("ultima_sesion") or "-"),
                onclick=onclick,
            )
        )
    filas = "".join(filas_list)
    siguiente = escape(obtener_config("siguiente", ""))
    pie = escape(obtener_config("pie", ""))
    empresa = escape(obtener_config("empresa", ""))

    # Configuración de listas de autollenado y vínculos externos
    lista_clientes = escape(obtener_config("lista_clientes_json", "[]") or "[]")
    vdb_tipo = escape(obtener_config("vinculo_db_externo_tipo", "ninguno") or "ninguno")
    vdb_url = escape(obtener_config("vinculo_db_externo_url", "") or "")
    vdb_tok = escape(obtener_config("vinculo_db_externo_token", "") or "")
    vdb_nombre = escape(obtener_config("vinculo_db_externo", "") or "")

    cuerpo_html = f"""<h2>Panel administrativo</h2>
    <section class="card"><h3>👥 Usuarios</h3>
      <table class="tabla"><tr><th>#</th><th>Usuario</th><th>Nombre</th><th>Rol</th><th>Estado</th><th>Última sesión</th></tr>{filas}</table>
      <form class="form grid" data-api="/api/usuarios" data-redirect="true">
        <label>Usuario<input name="usuario" required></label>
        <label>Nombre<input name="nombre" required></label>
        <label>Contraseña<input name="clave" type="password" required minlength="6"></label>
        <label>Rol<select name="rol"><option value="ventas">Ventas</option>
          <option value="administrativo">Administrativo (bodega / recepción)</option>
          <option value="cedis">CEDIS</option>
          <option value="admin">Admin. del sistema (total)</option>
          <option value="transportador">Transportador propio</option></select></label>
        <button class="btn primario">Crear usuario</button></form>
      <form class="form grid" data-api="/api/clave" style="margin-top:18px">
        <label class="wide">Cambiar mi contraseña
          <small class="ayuda">Al cambiarla se cerrarán todas tus otras sesiones abiertas.</small></label>
        <label>Contraseña actual<input name="clave_actual" type="password" required autocomplete="current-password"></label>
        <label>Contraseña nueva<input name="clave_nueva" type="password" required minlength="6" autocomplete="new-password"></label>
        <button class="btn">Actualizar mi contraseña</button></form>
    </section>

    <section class="card"><h3>🔐 Restablecer contraseña de un usuario</h3>
      <p class="nota">Usa esto cuando alguien olvidó su clave. Se cerrarán todas las sesiones de ese usuario.</p>
      <form class="form grid" id="form-reset-clave">
        <label>Usuario<input name="usuario" id="reset-clave-usuario" required placeholder="nombre de usuario"></label>
        <label>Contraseña nueva<input name="clave_nueva" type="password" required minlength="6"></label>
        <button class="btn" type="button" id="btn-reset-clave">Restablecer</button>
      </form>
    </section>

    <section class="card"><h3>🗄️ Base de datos</h3>
      <p class="nota">Explora y edita los datos directamente: tablas, filas, consultas SQL,
      respaldos, mantenimiento y migraciones. Todo queda registrado en la auditoría.</p>
      <p><a class="btn primario" href="/admin/db">Abrir el módulo de base de datos</a></p>
    </section>

    <section class="card"><h3>⚙️ Configuración general</h3>
      <form class="form grid" data-api="/api/config" data-redirect="true">
        <label>Próximo consecutivo<input name="siguiente" type="number" value="{siguiente}"></label>
        <label>Nombre empresa<input name="empresa" value="{empresa}"></label>
        <label class="wide">Pie de página<input name="pie" value="{pie}"></label>
        <button class="btn">Guardar</button></form>
      <p><a class="btn" href="/api/exportar.csv">⬇️ Exportar guías (CSV / Excel)</a></p></section>

    <section class="card"><h3>📊 Resultados Load Test</h3>
      <p class="nota">Reportes de la ejecución concurrente de 500 guías (usuarios Ventas + CEDIS).
      Descarga en formato Excel (CSV UTF-8 BOM) o exporta a PDF directamente desde el navegador.</p>
      <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:10px">
        <a class="btn primario" href="/admin/loadtest/ultimo">📄 Ver último reporte · imprimir PDF</a>
        <a class="btn" href="/api/loadtest/ultimo.csv" download>⬇️ Descargar resultados · Excel (CSV)</a>
      </div>
      <p style="margin-top:14px;font-size:13px;color:var(--texto-secundario)">
        Para regenerar una ejecución nueva de load test, ejecutar en línea de comandos:
        <br><code style="background:#0f172a12;padding:2px 6px;border-radius:6px">python loadtest_500_ventas_cedis.py --guias 500 --workers 50</code>
      </p></section>

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
    </section>

    <div id="modal-editar-usuario" hidden class="db-modal-wrap">
      <div class="db-modal" role="dialog" aria-modal="true" aria-label="Editar usuario">
        <button type="button" id="cerrar-editar-usuario" class="db-modal-cerrar" aria-label="Cerrar">×</button>
        <h3>Editar usuario</h3>
        <form id="form-editar-usuario" class="form grid">
          <input type="hidden" name="id">
          <label>Usuario<input name="usuario" required></label>
          <label>Nombre<input name="nombre" required></label>
          <label>Rol<select name="rol"><option value="ventas">Ventas</option><option value="administrativo">Administrativo</option><option value="cedis">CEDIS</option><option value="admin">Admin. del sistema</option><option value="transportador">Transportador propio</option></select></label>
          <label>Estado<select name="activo"><option value="1">Activo</option><option value="0">Inactivo</option></select></label>
          <button type="button" id="guardar-editar-usuario" class="btn primario">💾 Guardar cambios</button>
          <button type="button" id="cancelar-editar-usuario" class="btn">Cancelar</button>
        </form>
      </div>
    </div>
    """

    script_js = """
<script>
function abrirEditarUsuario(id, usuario, nombre, rol, activo) {
  var modal = document.getElementById("modal-editar-usuario");
  var form = document.getElementById("form-editar-usuario");
  form.querySelector("[name=id]").value = id;
  form.querySelector("[name=usuario]").value = usuario;
  form.querySelector("[name=nombre]").value = nombre;
  form.querySelector("[name=rol]").value = rol;
  form.querySelector("[name=activo]").value = String(activo === 1 || activo === "1" ? 1 : 0);
  modal.hidden = false;

  document.getElementById("cerrar-editar-usuario").onclick = function() { modal.hidden = true; };
  document.getElementById("cancelar-editar-usuario").onclick = function() { modal.hidden = true; };

  var guardarBtn = document.getElementById("guardar-editar-usuario");
  guardarBtn.onclick = async function() {
    var fd = new FormData(form);
    var body = {};
    fd.forEach(function(val, key) { body[key] = val; });
    body.activo = body.activo === "1";
    try {
      var r = await fetch("/api/usuarios/" + id + "/editar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      var d = await r.json();
      if (!r.ok || !d.ok) throw new Error(d.error || "Error guardando");
      modal.hidden = true;
      location.reload();
    } catch (ex) {
      alert(ex.message);
    }
  };
}
</script>
"""
    return page("Admin", cuerpo_html + script_js, user)
