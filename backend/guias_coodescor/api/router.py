#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Router del servidor HTTP. Contiene el manejador de peticiones (BaseHTTPRequestHandler)
y delega en servicios y vistas. Proporciona:
  - Archivos estáticos y adjuntos seguros.
  - Vistas HTML renderizadas por módulos.
  - API JSON de autenticación, guías y administración.
  - Manejo de errores seguro (sin exponer tracebacks al cliente).
"""
import ipaddress
import json
import os
import re
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from guias_coodescor.config import (
    CORS_ORIGINS,
    FRONTEND_DIST,
    FRONTEND_INDEX,
    HOST,
    MAX_REQUEST_BODY,
    PERMISO_EXPORTAR_AUDITORIA,
    PERMISO_IMPRIMIR_GUIA,
    PORT,
    STATIC_DIR,
    TRUSTED_PROXIES,
)
from guias_coodescor.core.logging_config import configurar_logging, get_logger
from guias_coodescor.core.security import (
    parsear_cookie_sid,
    validar_sesion,
)
from guias_coodescor.core.utils import (
    mime_por_extension,
    ruta_adjunto_segura,
)
from guias_coodescor.core.validators import ValidationError
from guias_coodescor.services.auth_service import (
    AuthError,
    ForbiddenError,
    actualizar_configuracion,
    cambiar_clave_propia,
    crear_usuario,
    editar_usuario,
    login as svc_login,
    logout as svc_logout,
    requerir_rol,
    restablecer_clave,
)
from guias_coodescor.services.db_admin_service import DbAdminError
from guias_coodescor.services.export_service import exportar_guias_csv
from guias_coodescor.services.captcha_service import (
    ENV_BYPASS_KEY,
    generar_captcha as captcha_generar,
    validar_captcha as captcha_validar,
)
from guias_coodescor.services.loadtest_report_service import (
    generar_csv_bytes as loadtest_csv_bytes,
    vista_reporte_admin as loadtest_vista_admin,
)
from guias_coodescor.services.guias_service import (
    EstadoInvalidoError,
    GuiaNoExisteError,
    asignar_tipo_transportador,
    cerrar_entrega_por_token_publico,
    crear_guia,
    editar_guia,
    obtener_guia,
    obtener_ultima_firma_transportador_admin,
    proceso_unificado_administrativo,
    proceso_unificado_cedis,
    procesar_evento,
    registrar_transportador_externo,
)
from guias_coodescor.services.tokens_service import (
    generar_token_entrega,
    listar_usuarios_transportadores_activos,
     obtener_info_token_guia,
    obtener_por_token,
    estado_activacion_link,
)
from guias_coodescor.services.sse_service import emitter, notify_nueva_guia, notify_estado_actualizado, SSEClient
from guias_coodescor.api.routes_clientes import RUTAS_CLIENTES_GET
from guias_coodescor.api.routes_clientes_contactos import (
    RUTAS_CLIENTES_CONTACTOS_GET,
    RUTAS_CLIENTES_CONTACTOS_POST,
)
from guias_coodescor.api.routes_transportadores_externos import (
    RUTAS_TRANSPORTADORES_EXTERNOS_GET,
    RUTAS_TRANSPORTADORES_EXTERNOS_POST,
)
from guias_coodescor.api.routes_admin_db import (
    RUTAS_DB_ADMIN_DELETE,
    RUTAS_DB_ADMIN_GET,
    RUTAS_DB_ADMIN_POST,
)
from guias_coodescor.api.routes_notificaciones import RUTAS_NOTIFICACIONES_GET


from guias_coodescor.services.db_admin_service import leer_respaldo as db_leer_respaldo
from guias_coodescor.api.routes_receptores import (
    RUTAS_RECEPTORES_GET,
    RUTAS_RECEPTORES_POST,
    RUTAS_RECEPTORES_DELETE_REGEX,
)
from guias_coodescor.api.openapi_spec import (
    get_redoc_html,
    get_swagger_ui_html,
    spec_yaml,
)
from guias_coodescor.api.routes_ai import (
    RUTAS_AI_GET,
    RUTAS_AI_POST,
)
from guias_coodescor.api.routes_guias_api import (
    RUTA_GUIA_EVENTOS_REGEX,
    RUTA_GUIA_EVENTO_REGEX,
    RUTA_GUIA_ID_REGEX,
    RUTA_GUIA_TRANSICION_REGEX,
    conteo_guias_api,
    detalle_guia_api,
    editar_guia_api,
    estados_guias_api,
    evento_post_guia_api,
    eventos_guia_api,
    listar_guias_api,
    transicion_guia_api,
)
from guias_coodescor.web.views.admin_views import vista_admin
from guias_coodescor.web.views.db_views import vista_admin_db
from guias_coodescor.web.views.auth_views import vista_login, vista_tablero
from guias_coodescor.web.views.base import escape, page
from guias_coodescor.web.views.guias_views import (
    vista_detalle_guia,
    vista_firma_publica,
    vista_imprimir_guia,
    vista_listado_guias,
    vista_nueva_guia,
)

configurar_logging()
logger = get_logger("guias_coodescor.http")

# Política de seguridad de contenido. Restringe los recursos a este origen y
# bloquea Object/Base tags. Se permite script inline porque las vistas actuales
# lo usan; se eliminará al separar el frontend del backend.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "img-src 'self' data: blob:; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "connect-src 'self'; "
    "font-src 'self' data:; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'self'"
)

# Rutas API que se atienden sin sesión a propósito (documentadas como públicas).
RUTAS_API_PUBLICAS_GET = frozenset({"/api/ai/health", "/api/ai/info"})

# Campos del usuario que pueden salir al cliente (nunca hash/sal/contadores).
CAMPOS_USUARIO_PUBLICOS = (
    "id", "usuario", "nombre", "rol", "activo", "ultima_sesion",
)


def _usuario_publico(user) -> dict:
    if not user:
        return {}
    return {k: user.get(k) for k in CAMPOS_USUARIO_PUBLICOS if k in user}



def _ip_confiable(ip: str) -> bool:
    """Indica si una IP pertenece a TRUSTED_PROXIES (acepta IPs y rangos CIDR)."""
    ip = (ip or "").strip()
    if not ip:
        return False
    try:
        direccion = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for entrada in TRUSTED_PROXIES:
        entrada = (entrada or "").strip()
        if not entrada:
            continue
        try:
            if "/" in entrada:
                if direccion in ipaddress.ip_network(entrada, strict=False):
                    return True
            elif direccion == ipaddress.ip_address(entrada):
                return True
        except ValueError:
            continue
    return False



class RequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "CoodescorGuias/2.0"
    _METODOS_VALIDOS = {"GET", "HEAD", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"}

    def log_message(self, format, *args):
        logger.debug("%s - %s", self.address_string(), format % args)

    def handle_error(self, request, client_address):
        try:
            import traceback
            logger.exception(
                "Error no manejado en hilo de petición desde %s: %s",
                client_address,
                traceback.format_exc(limit=5),
            )
        except Exception:
            pass
        super().handle_error(request, client_address)

    def parse_request(self):
        """Override parse_request() para SANEAR antes del handle principal.
        1) Llamamos a la lógica estándar.
        2) Si el self.command (método HTTP) llega CON BASURA (llaves {},
           símbolos raros, método no conocido: típico '{}GET' de cache viejo
           del service worker PWA con JS corrupto):
           - LOGUEAMOS el método corrupto recibido.
           - ESCRIBIMOS directamente la respuesta (303 a /login) sobre el
             raw socket, sin usar send_response/send_header que a veces no
             se aplican cuando parse_request retorna False.
           - Marcamos close_connection=True y retornamos True para NO
             levantar 501 Unsuported method. La respuesta ya fue enviada.
        """
        import re as _re
        ok = super().parse_request()
        if ok and self.command:
            original_cmd = self.command
            cleaned = _re.sub(r"[^A-Za-z]", "", original_cmd).upper()
            cmd_invalido = (
                (original_cmd != cleaned) or
                (original_cmd not in self._METODOS_VALIDOS) or
                (not original_cmd)
            )
            if cmd_invalido:
                logger.warning(
                    "Método HTTP corrupto recibido: %r (saneado=%r) de %s → "
                    "respondemos 303→/login manualmente (Clear-Site-Data)",
                    original_cmd, cleaned, self.address_string(),
                )
                try:
                    # Respuesta HTTP raw manual (garantiza que se envía sin
                    # depender de send_header/flush/send_response).
                    # Incluimos Clear-Site-Data para limpiar el cache/storage
                    # del navegador que probablemente tenía el Service Worker
                    # obsoleto que generó este método corrupto.
                    raw = (
                        b"HTTP/1.1 303 See Other\r\n"
                        b"Location: /login\r\n"
                        b"Cache-Control: no-store, no-cache, must-revalidate, max-age=0\r\n"
                        b'Clear-Site-Data: "cache","cookies","storage","executionContexts"\r\n'
                        b"Content-Length: 0\r\n"
                        b"Connection: close\r\n"
                        b"\r\n"
                    )
                    self.wfile.write(raw)
                    self.wfile.flush()
                except Exception:
                    pass
                self.close_connection = True
                # Ya enviamos la respuesta 303 manualmente. Retornar False le
                # dice a BaseHTTPRequestHandler que hubo error de parseo y
                # cierre la conexión. No intentará invocar do_XXX ni send_error(501).
                return False
        return ok

    # -- helpers ----------------------------------------------------------------

    def _out(self, code: int, body, ctype: str = "text/html; charset=utf-8", extra: dict | None = None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        extra = dict(extra or {})
        # Un único Cache-Control: el anterior emitía dos cabeceras contradictorias
        # cuando el handler pasaba una política de caché propia.
        cache_control = extra.pop("Cache-Control", None) or "no-store, no-cache, must-revalidate, max-age=0"
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        self.send_header("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        self.send_header("X-Permitted-Cross-Domain-Policies", "none")
        for origen in self._cors_origins_permitidos():
            self.send_header("Access-Control-Allow-Origin", origen)
            self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Vary", "Origin")
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _cors_origins_permitidos(self) -> tuple:
        """Orígenes con CORS habilitado.

        Solo se acepta la lista explícita de config. Antes, en "development" se
        reflejaba cualquier Origin con credenciales, lo que permitía que
        cualquier otro sitio (u otro puerto del mismo equipo) leyera la API con
        la cookie de la víctima. Con CORS vacío no se emite ninguna cabecera:
        mismo origen únicamente.
        """
        origen = (self.headers.get("Origin") or "").strip()
        if not origen or not CORS_ORIGINS:
            return ()
        return (origen,) if origen in CORS_ORIGINS else ()

    def _origen_es_mismo_sitio(self, origen: str) -> bool:
        host = (self.headers.get("Host") or "").strip().lower()
        if not host:
            return False
        origen = (origen or "").strip().lower().rstrip("/")
        return origen in (f"http://{host}", f"https://{host}")

    def _validar_origen_csrf(self) -> None:
        """Rechaza peticiones de escritura con Origin de otro sitio.

        Los navegadores envían ``Origin`` en todo POST/PUT/PATCH/DELETE, así
        que una petición de un sitio ajeno (CSRF) se puede distinguir del uso
        normal. Las peticiones sin ``Origin`` (clientes no navegador: scripts,
        app Android) se aceptan para no romper integraciones locales.
        """
        origen = (self.headers.get("Origin") or "").strip()
        if not origen:
            return
        if self._origen_es_mismo_sitio(origen) or origen in self._cors_origins_permitidos():
            return
        logger.warning(
            "Petición de escritura con Origin no permitido: %s %s origin=%r",
            self.command, self.path, origen,
        )
        raise ForbiddenError("Origen no permitido para esta operación")


    def _redirect(self, ruta: str):
        self._out(303, b"", "text/plain", {"Location": ruta})

    def _json_body(self) -> dict:
        """Lee y valida el cuerpo JSON de la petición.

        Todo el contrato de la API espera un OBJETO. Antes se devolvía cualquier
        JSON válido (lista, número, cadena) y los handlers llamaban ``.get()``
        sobre él, lo que producía un 500 por entrada del cliente en lugar de un
        400. Los cuerpos vacíos se tratan como objeto vacío.
        """
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            raise ValueError("Content-Length inválido")
        if n < 0:
            raise ValueError("Content-Length inválido")
        if n > MAX_REQUEST_BODY:
            raise ValueError("payload muy grande")
        raw = self.rfile.read(n) if n else b"{}"
        try:
            datos = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            raise ValueError("JSON inválido en el cuerpo de la petición")
        if not isinstance(datos, dict):
            raise ValueError("El cuerpo JSON debe ser un objeto")
        return datos

    def _user(self):
        cookie = self.headers.get("Cookie") or ""
        sid = parsear_cookie_sid(cookie)
        user = validar_sesion(sid)
        return user, sid

    def _json(self, obj, code: int = 200, extra: dict | None = None):
        self._out(
            code,
            json.dumps(obj, ensure_ascii=False),
            "application/json; charset=utf-8",
            extra,
        )

    def _client_ip(self) -> str:
        """
        IP real del cliente.

        X-Forwarded-For solo se respeta si la conexión viene de un proxy de
        confianza (config.TRUSTED_PROXIES). Se recorre la cadena de DERECHA a
        IZQUIERDA y se devuelve el primer salto no confiable: los proxies
        (nginx, ngrok) *añaden* su cliente a la derecha, así que el primer
        elemento de la izquierda lo controla quien llama y no debe usarse para
        el bloqueo por IP ni para la auditoría.
        """
        peer = self._canonical_ip(self.address_string() or "")
        if not _ip_confiable(peer):
            return peer
        xff = self.headers.get("X-Forwarded-For") or ""
        saltos = [self._canonical_ip(p) for p in xff.split(",") if p.strip()]
        for salto in reversed(saltos):
            if not salto:
                continue
            if _ip_confiable(salto):
                continue
            return salto
        return peer

    def _peer_es_proxy_confiable(self) -> bool:
        return _ip_confiable(self._canonical_ip(self.address_string() or ""))

    def _exigir_acceso_guia(self, user, gid: int) -> None:
        """Un transportador solo puede ver u operar las guías asignadas a él.

        El listado y las notificaciones ya filtraban por
        ``transportador_asignado_id``; el detalle, los eventos y las acciones no,
        lo que permitía leer datos de cualquier guía (incluidas firmas y datos
        personales) y cerrar entregas ajenas conociendo el id.
        """
        if (user or {}).get("rol") != "transportador":
            return
        guia = obtener_guia(gid)
        if not guia:
            raise GuiaNoExisteError("Guía no existe")
        try:
            asignado = int(guia.get("transportador_asignado_id") or 0)
        except (TypeError, ValueError):
            asignado = 0
        try:
            propio = int((user or {}).get("id") or 0)
        except (TypeError, ValueError):
            propio = 0
        if asignado != propio:
            raise ForbiddenError("No tiene acceso a esta guía")


    def _base_url_publica(self) -> str:
        """Base URL para los links que se envían al cliente.

        Si COODESCOR_PUBLIC_BASE_URL está configurada se usa tal cual. Si no,
        se deriva del Host de la petición, pero solo después de validar el
        formato: un Host arbitrario permitía devolver links de phishing con el
        token real del cliente. El esquema https solo se acepta si el salto
        directo es un proxy de confianza (y así lo indica X-Forwarded-Proto).
        """
        from guias_coodescor.config import settings as _settings

        base = (getattr(_settings, "public_base_url", "") or "").strip().rstrip("/")
        if base:
            return base
        host = (self.headers.get("Host") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9.\-:\[\]]{1,255}", host or ""):
            host = f"{HOST}:{PORT}"
        scheme = (
            "https"
            if self._peer_es_proxy_confiable()
            and str(self.headers.get("X-Forwarded-Proto", "")).lower() == "https"
            else "http"
        )
        return f"{scheme}://{host}"

    @staticmethod
    def _canonical_ip(raw: str) -> str:
        """Normaliza IPv4-mapped IPv6 y loopback para comparaciones estables."""
        raw = (raw or "").strip()
        if raw.startswith("::ffff:"):
            raw = raw[7:]
        if raw == "::1":
            raw = "127.0.0.1"
        return raw

    def _user_agent(self) -> str:
        return self.headers.get("User-Agent") or ""

    def do_HEAD(self):
        """Cabeceras idénticas a GET pero sin cuerpo."""
        self.do_GET()

    def do_OPTIONS(self):
        """Preflight CORS. Sin esto el navegador rechaza la petición antes de
        llegar al handler, y separar el frontend en otro origen es imposible."""
        permitidos = self._cors_origins_permitidos()
        if not permitidos:
            return self._out(204, b"", "text/plain", {"Allow": "GET, HEAD, POST, DELETE, OPTIONS"})
        headers = {
            "Access-Control-Allow-Methods": "GET, HEAD, POST, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-CSRF-Token",
            "Access-Control-Max-Age": "600",
        }
        return self._out(204, b"", "text/plain", headers)

    # -- GET --------------------------------------------------------------------

    def do_GET(self):
        u = urlparse(self.path)
        ruta = u.path.rstrip("/") or "/"
        qs = parse_qs(u.query)
        user, _sid = self._user()
        
        try:
            # =============================================================
            # RUTAS PÚBLICAS (SIN LOGIN):
            #  · /firma/<TOKEN> : página para que el cliente firme SIN usuario.
            # =============================================================
            if ruta.startswith("/firma/"):
                token = ruta[len("/firma/"):]
                if not token:
                    return self._out(404, page("404", "<h1>404 · Link inválido</h1>", user=None))
                tinfo = obtener_por_token(token)
                if not tinfo:
                    return self._out(404, page(
                        "Link no válido",
                        (
                            "<h1>🔗 Link de firma no encontrado o expirado</h1>"
                            "<p>Este link de confirmación ya fue usado, venció o no existe.</p>"
                            "<p>Por favor contacta con Ventas o con la persona que te lo envió para solicitar uno nuevo.</p>"
                            '<p><a href="/login" class="btn">Ir al inicio del sistema</a></p>'
                        ),
                        user=None,
                    ))
                gid = int(tinfo["guia_id"])
                guia = obtener_guia(gid)
                # SPEC v1.0 T5: Link SÓLO se activa DESPUÉS del paso único de CEDIS (estado = EN_RUTA).
                # Si estado es anterior → mostrar página "Link aún no activo".
                activ = estado_activacion_link(gid)
                if not activ["activo"] and activ["codigo"] == "NO_ACTIVO":
                    return self._out(422, page(
                        "Link aún no activo",
                        f"""
<section class="card warning">
  <h2>⏳ Link de confirmación AÚN NO ESTÁ ACTIVO</h2>
  <p class="nota" style="font-size:1.05em;line-height:1.6">
    <b>Estado actual de la guía:</b> <span class="chip">{escape(str(activ['estado_guia'] or '-'))}</span>
  </p>
  <p style="line-height:1.6;margin-top:12px">{escape(str(activ['motivo']))}</p>
  <ul style="margin-top:16px;line-height:1.9">
    <li>✅ El link <b>fue generado correctamente</b> y se encuentra registrado en el sistema.</li>
    <li>⏳ Su activación es <b>automática</b> cuando el personal de <b>CEDIS</b> complete su proceso único de control y entrega a transportador.</li>
    <li>📅 Una vez activado, dispondrás de 7 días para confirmar la recepción.</li>
    <li>📞 Si pasaron más de 24 h y sigue inactivo, contacta a la persona que te envió este link (Ventas o Administrativo).</li>
  </ul>
  <div style="margin-top:20px">
    <a class="btn" href="/login">Volver al inicio</a>
    <button class="btn" onclick="location.reload()" style="margin-left:8px">🔄 Recargar para comprobar</button>
  </div>
</section>""",
                        user=None,
                    ))
                return self._out(200, vista_firma_publica(token_info=tinfo, guia=guia))

            if ruta.startswith("/static/"):
                return self._servir_estatico(ruta[len("/static/"):])
            # Build de la SPA React: assets con hash (públicos, cache inmutable).
            if ruta.startswith("/assets/"):
                return self._servir_asset_frontend(ruta[len("/assets/"):])
            # ===== RUTAS PÚBLICAS API GET (sin sesión) =====
            if ruta == "/api/captcha/nuevo":
                _d, svg, tok = captcha_generar(ip=self._client_ip(), ua=self._user_agent())
                return self._json({"ok": True, "svg": svg, "token": tok}, extra={"Cache-Control": "no-store, no-cache, must-revalidate, private, max-age=0", "Pragma": "no-cache"})
            # ===== OpenAPI / Swagger UI / ReDoc (públicas) =====
            if ruta == "/openapi.yaml":
                return self._out(
                    200, spec_yaml(), "application/yaml; charset=utf-8",
                    extra={"Cache-Control": "public, max-age=300"},
                )
            if ruta == "/docs":
                return self._out(200, get_swagger_ui_html())
            if ruta == "/redoc":
                return self._out(200, get_redoc_html())
            # Rutas API sin sesión: 401 JSON explícito. Antes se dejaba que cada
            # handler respondiera, pero varios asumen que `user` existe y
            # terminaban en 500 (o servían datos sin autenticar, como el detalle
            # de guías). Se exceptúan solo las rutas documentadas como públicas.
            if not user:
                if ruta.startswith("/api/"):
                    if ruta in RUTAS_API_PUBLICAS_GET:
                        pass
                    else:
                        return self._json(
                            {"ok": False, "error": "Sesión expirada o inválida"},
                            401,
                            extra={"Cache-Control": "no-store, no-cache, private, max-age=0"},
                        )
                elif ruta in ("/", "/login"):
                    # La entrada pública ya es la SPA nueva (la antigua vista
                    # HTML queda solo como respaldo histórico).
                    return self._servir_spa()
                else:
                    return self._redirect("/login")
            # Con sesión activa no tiene sentido mostrar el formulario: se iba a
            # caer en un 404 al no existir una ruta /login en el bloque autenticado.
            if ruta == "/login":
                return self._redirect("/tablero")
            # Los adjuntos (firmas y fotos) exigen sesión. Antes se servían
            # anónimos y con la ruta resuelta contra DATA_DIR, lo que permitía
            # descargar guias.db, receptores.db y los logs con un GET simple.
            if ruta.startswith("/static_file/"):
                return self._servir_adjunto(ruta[len("/static_file/"):])
            if ruta == "/":
                return self._redirect("/tablero")
            if ruta == "/tablero":
                return self._servir_spa()
            if ruta == "/nueva-guia":
                return self._servir_spa()
            # Enlaces antiguos que aún puedan existir en marcadores/PWA.
            if ruta == "/guias":
                return self._redirect("/tablero?vista=guias")
            if ruta == "/guia/nueva":
                return self._redirect("/nueva-guia")
            if ruta == "/admin":
                return self._redirect("/admin/db")
            # Sesión actual: el frontend SPA lo usa al montar para restaurar el
            # usuario tras una recarga o enlace directo (la cookie sigue viva).
            if ruta == "/api/session":
                return self._json(
                    {"ok": True, "usuario": _usuario_publico(user)},
                    extra={"Cache-Control": "no-store, no-cache, private, max-age=0"},
                )
            if ruta == "/admin/db":
                requerir_rol(user, "admin")
                return self._servir_spa()
            if ruta == "/admin/loadtest":
                requerir_rol(user, "admin")
                return self._servir_spa()
            if ruta == "/admin/loadtest/ultimo":
                return self._redirect("/admin/loadtest")
            if ruta.startswith("/guia/") and ruta.endswith("/imprimir"):
                gid = int(ruta.split("/")[2])
                rol_u = (user or {}).get("rol") or ""
                if rol_u not in PERMISO_IMPRIMIR_GUIA:
                    raise ForbiddenError(
                        "No tiene permiso para imprimir guías. "
                        "Roles permitidos: " + ", ".join(sorted(PERMISO_IMPRIMIR_GUIA))
                    )
                self._exigir_acceso_guia(user, gid)
                return self._out(200, vista_imprimir_guia(gid, user))
            if ruta.startswith("/guia/"):
                gid = int(ruta.split("/")[2])
                self._exigir_acceso_guia(user, gid)
                return self._servir_spa()
            # --- API JSON auténticadas (GET) -----------------------------------------
            # API REST de guías. Va antes de los handlers genéricos porque
            # /api/guias/<id>/... comparte prefijo con otras rutas.
            if ruta == "/api/guias":
                return listar_guias_api(qs, user, self._json)
            if ruta == "/api/guias/conteo":
                return conteo_guias_api(qs, user, self._json)
            if ruta == "/api/guias/estados":
                return estados_guias_api(user, self._json)
            m = re.match(RUTA_GUIA_EVENTOS_REGEX, ruta)
            if m:
                self._exigir_acceso_guia(user, int(m.group(1)))
                return eventos_guia_api(qs, user, int(m.group(1)), self._json)
            m = re.match(RUTA_GUIA_TRANSICION_REGEX, ruta)
            if m:
                self._exigir_acceso_guia(user, int(m.group(1)))
                return transicion_guia_api(qs, user, int(m.group(1)), m.group(2), self._json)
            m = re.match(RUTA_GUIA_ID_REGEX, ruta)
            if m:
                self._exigir_acceso_guia(user, int(m.group(1)))
                return detalle_guia_api(qs, user, int(m.group(1)), self._json)
            if ruta == "/api/usuarios/rol/transportador":
                requerir_rol(user, "admin", "administrativo", "cedis", "ventas")
                return self._json({"ok": True, "transportadores": listar_usuarios_transportadores_activos()})
            if ruta == "/api/exportar.csv":
                rol_u = (user or {}).get("rol") or ""
                if rol_u not in PERMISO_EXPORTAR_AUDITORIA:
                    raise ForbiddenError(
                        "No tiene permiso para exportar auditoría. "
                        "Roles permitidos: " + ", ".join(sorted(PERMISO_EXPORTAR_AUDITORIA))
                    )
                return self._servir_export_csv()
            # ===== Reportes Load Test (solo admin) =====
            if ruta == "/api/loadtest/ultimo":
                requerir_rol(user, "admin")
                from guias_coodescor.services.loadtest_report_service import leer_ultimo_resumen as _lt_last
                return self._json({"ok": True, "resumen": _lt_last()})
            if ruta == "/api/loadtest/ultimo.csv" or ruta == "/api/loadtest/ultimo.xlsx":
                requerir_rol(user, "admin")
                # Rebuild el resumen dentro (si no hay, empty state)
                from guias_coodescor.services.loadtest_report_service import leer_ultimo_resumen as _lt_last
                _r = _lt_last()
                data_bytes, filename = loadtest_csv_bytes(_r)
                return self._out(
                    200,
                    data_bytes,
                    "text/csv; charset=utf-8",
                    {"Content-Disposition": f'attachment; filename="{filename}"',
                     "Cache-Control": "no-store, no-cache, private, max-age=0"},
                )
            # ----- API IA (GET) -----
            for _patron, _handler in RUTAS_AI_GET:
                if re.match(_patron, ruta):
                    return _handler(qs, user, self._json)
            # ----- API notificaciones (GET) -----
            for _patron, _handler in RUTAS_NOTIFICACIONES_GET:
                if re.match(_patron, ruta):
                    return _handler(qs, user, self._json)
            # ----- API clientes + clientes_contactos + receptores (GET) -----
            for _patron, _handler in RUTAS_CLIENTES_GET:
                if re.match(_patron, ruta):
                    return _handler(qs, user, self._json)
            for _patron, _handler in RUTAS_CLIENTES_CONTACTOS_GET:
                if re.match(_patron, ruta):
                    return _handler(qs, user, self._json)
            for _patron, _handler in RUTAS_TRANSPORTADORES_EXTERNOS_GET:
                if re.match(_patron, ruta):
                    return _handler(qs, user, self._json)
            for _patron, _handler in RUTAS_RECEPTORES_GET:
                if re.match(_patron, ruta):
                    return _handler(qs, user, self._json)
            # ----- API administración de base de datos (solo admin) -----
            if ruta.startswith("/api/admin/db/"):
                requerir_rol(user, "admin")
            # La descarga de un respaldo devuelve el archivo binario, no JSON,
            # así que se atiende antes del despacho genérico.
            if ruta == "/api/admin/db/respaldo/descargar":
                contenido, nombre = db_leer_respaldo(
                    qs.get("archivo", [""])[0], user, self._client_ip()
                )
                return self._out(
                    200,
                    contenido,
                    "application/octet-stream",
                    {
                        "Content-Disposition": f'attachment; filename="{nombre}"',
                        "Cache-Control": "no-store, no-cache, private, max-age=0",
                    },
                )
            for _patron, _handler in RUTAS_DB_ADMIN_GET:
                if re.match(_patron, ruta):
                    return _handler(qs, user, self._json)
            if ruta.startswith("/api/"):
                return self._json({"ok": False, "error": "ruta no existe"}, 404)
            return self._out(404, page("404", "<h1>404 · Página no encontrada</h1>", user))
        except ForbiddenError as ex:
            logger.warning("Forbidden: %s user=%s", ex, (user or {}).get("usuario"))
            if ruta.startswith("/api/"):
                return self._json({"ok": False, "error": "Sin permisos para realizar esta acción"}, 403)
            return self._out(403, page("403", f"<h1>403 · Acceso denegado</h1><p>{escape(str(ex))}</p>", user))
        except AuthError as ex:
            logger.info("Auth error GET %s: %s", ruta, ex)
            if ruta.startswith("/api/"):
                return self._json({"ok": False, "error": str(ex)}, 401)
            return self._redirect("/login")
        except DbAdminError as ex:
            logger.warning("Error del módulo de BD en GET %s: %s", ruta, ex)
            if ruta.startswith("/api/"):
                return self._json({"ok": False, "error": str(ex)}, 400)
            return self._out(400, page("400", f"<h1>400 · Solicitud inválida</h1><p>{escape(str(ex))}</p>", user))
        except ValueError as ex:
            logger.warning("Bad request GET %s: %s", ruta, ex)
            if ruta.startswith("/api/"):
                return self._json({"ok": False, "error": str(ex)}, 400)
            return self._out(400, page("400", f"<h1>400 · Solicitud inválida</h1><p>{escape(str(ex))}</p>", user))
        except GuiaNoExisteError as ex:
            logger.info("Guía no existe GET %s: %s", ruta, ex)
            if ruta.startswith("/api/"):
                return self._json({"ok": False, "error": str(ex)}, 404)
            return self._out(404, page("404", "<h1>404 · Guía no encontrada</h1>", user))
        except Exception as ex:
            logger.exception("Error no manejado en GET %s: %s", ruta, ex)
            if ruta.startswith("/api/"):
                return self._json({"ok": False, "error": "Error interno del servidor"}, 500)
            msg = "<h1>500 · Error interno</h1><p>Consulte al administrador.</p>"
            return self._out(500, page("Error", msg, user))

    # -- POST -------------------------------------------------------------------

    def do_POST(self):
        u = urlparse(self.path)
        ruta = u.path.rstrip("/") or "/"
        qs = parse_qs(u.query)
        user, sid = self._user()
        ip = self._client_ip()
        ua = self._user_agent()
        try:
            self._validar_origen_csrf()
            if ruta == "/api/login":
                return self._api_login(ip, ua)
            # =============================================================
            # RUTAS POST PÚBLICAS (sin sesión):
            #   · /api/captcha/nuevo : regenerar desafío
            #   · /api/firma_publica/<TOKEN> : confirmar entrega por link
            # =============================================================
            if ruta == "/api/captcha/nuevo":
                _d, svg, tok = captcha_generar(ip=ip, ua=ua)
                return self._json(
                    {"ok": True, "svg": svg, "token": tok},
                    extra={"Cache-Control": "no-store, no-cache, must-revalidate, private, max-age=0", "Pragma": "no-cache"},
                )
            if ruta.startswith("/api/firma_publica/"):
                token = ruta[len("/api/firma_publica/"):]
                if not token:
                    return self._json({"ok": False, "error": "token inválido"}, 400)
                tinfo = obtener_por_token(token)
                if not tinfo:
                    return self._json({
                        "ok": False,
                        "error": "Este link no existe, venció o ya fue usado. Contacte con Ventas para solicitar uno nuevo."
                    }, 404)
                d = self._json_body()
                cerrar_entrega_por_token_publico(tinfo, datos=d, ip=ip, ua=ua)
                return self._json({"ok": True, "redirect": "/firma/" + token + "?entregada=1"})
            if not user:
                return self._json({"ok": False, "error": "Sesión expirada o inválida"}, 401)
            if ruta == "/api/logout":
                cookie = svc_logout(sid)
                return self._json(
                    {"ok": True, "redirect": "/login"},
                    extra={"Set-Cookie": cookie},
                )
            if ruta == "/api/guias":
                return self._api_crear_guia(user, ip, ua)
            # Un paso del proceso (POST /api/guias/<id>/evento/<tipo>).
            m = re.match(RUTA_GUIA_EVENTO_REGEX, ruta)
            if m:
                self._exigir_acceso_guia(user, int(m.group(1)))
                return evento_post_guia_api(
                    user, self._json_body(), ip, self._json, int(m.group(1)), m.group(2)
                )
            if ruta == "/api/usuarios":
                return self._api_crear_usuario(user)
            m = re.match(r"^/api/usuarios/(\d+)/editar$", ruta)
            if m:
                return self._api_editar_usuario(user, int(m.group(1)))
            if ruta == "/api/config":
                return self._api_config(user)
            if ruta == "/api/clave":
                d = self._json_body()
                cambiar_clave_propia(user, d.get("clave_actual", ""), d.get("clave_nueva", ""))
                return self._json({"ok": True, "msg": "Contraseña actualizada"})
            m = re.match(r"^/api/usuarios/([^/]+)/restablecer_clave$", ruta)
            if m:
                requerir_rol(user, "admin")
                d = self._json_body()
                from urllib.parse import unquote

                restablecer_clave(user, unquote(m.group(1)), d.get("clave_nueva", ""))
                return self._json({"ok": True, "msg": "Contraseña restablecida"})
            m = re.match(r"^/api/guias/(\d+)/proceso_administrativo_unificado$", ruta)
            if m:
                gid = int(m.group(1))
                d = self._json_body()
                ok, msg, extra = proceso_unificado_administrativo(
                    guia_id=gid, user=user, datos=d, dispositivo="web", ip=ip
                )
                return self._json({"ok": bool(ok), "msg": str(msg), **(extra or {})})
            m = re.match(r"^/api/guias/(\d+)/proceso_cedis_unificado$", ruta)
            if m:
                gid = int(m.group(1))
                d = self._json_body()
                ok, msg, extra = proceso_unificado_cedis(
                    guia_id=gid, user=user, datos=d, dispositivo="web", ip=ip
                )
                return self._json({"ok": bool(ok), "msg": str(msg), **(extra or {})})
            trozos = ruta.split("/")
            # RUTAS: POST /api/guias/<id>/<accion>
            if len(trozos) == 5 and trozos[1] == "api" and trozos[2] == "guias":
                gid = int(trozos[3])
                tipo = trozos[4]
                self._exigir_acceso_guia(user, gid)
                # Nuevas acciones además de las de eventos
                if tipo == "generar_token_entrega":
                    requerir_rol(user, "ventas", "administrativo", "admin")
                    _g_tok = obtener_guia(gid)
                    if not _g_tok:
                        raise GuiaNoExisteError("Guía no existe")
                    if str(_g_tok.get("estado")) in ("ENTREGADA", "ANULADA"):
                        raise EstadoInvalidoError(
                            f"No se puede generar un link para una guía en estado {_g_tok.get('estado')}"
                        )
                    # 1) Verificamos si YA TIENE un token emitido para esta guía (1 link por guía, no se regenera a menos que sea admin explícitamente)
                    info_token_anterior = obtener_info_token_guia(gid)
                    ya_emitido = bool(info_token_anterior)
                    tok = generar_token_entrega(gid, user, regenerar_si_existe=False)
                    # Si ya existía y lo reutilizamos: obtener data de quién lo generó ORIGINALMENTE
                    if ya_emitido and info_token_anterior:
                        info_creador = {
                            "rol_original": info_token_anterior.get("creado_rol") or "-",
                            "usuario_original": info_token_anterior.get("creado_por_usuario") or "-",
                            "nombre_original": info_token_anterior.get("creado_por_nombre") or "-",
                            "fecha_original": info_token_anterior.get("creado_en") or "-",
                            "usado": bool(info_token_anterior.get("usado_en")),
                        }
                    else:
                        info_nuevo = obtener_info_token_guia(gid) or {}
                        info_creador = {
                            "rol_original": user.get("rol"),
                            "usuario_original": user.get("usuario"),
                            "nombre_original": user.get("nombre"),
                            "fecha_original": info_nuevo.get("creado_en") or "-",
                            "usado": False,
                        }
                    link_publico = f"{self._base_url_publica()}/firma/{tok}"
                    import re as _re_token
                    from guias_coodescor.services.guias_service import obtener_prellenado_ventas as _opv
                    gdat = obtener_guia(gid) or {}
                    pre = _opv(gid) or {}
                    cliente = (gdat.get("cliente") or "").strip() or "Cliente"
                    docs = (gdat.get("documentos") or "").strip()
                    obs = (gdat.get("obs_ventas") or "").strip()
                    if not docs and obs:
                        _m = _re_token.findall(
                            r"(?:FV|FAC|F\.V|FACTURA|NC|REM)[\s\-_]*#?\s*\d+(?:[-_/]\d+)?",
                            obs, flags=_re_token.IGNORECASE,
                        )
                        if _m:
                            docs = " - ".join(_m)
                    if not docs:
                        docs = f"Guía N° {gid}"
                    total_bultos = 0
                    try:
                        total_bultos = int(gdat.get("totales") or pre.get("totales") or 0)
                    except (ValueError, TypeError):
                        total_bultos = sum(
                            int(pre.get(k) or 0) for k in ("cajas", "bolsas", "cayvas", "sobres")
                        )
                    lbl_recibe = pre.get("cliente_recibe_nombre") or ""
                    resumen = (
                        f"👤 Cliente: {cliente}"
                        f"{' · '+lbl_recibe if lbl_recibe else ''}\n"
                        f"🧾 Documento(s): {docs}\n"
                        f"📦 Total bultos: {total_bultos}"
                    )
                    msj_wa = (
                        f"🚚 *COODESCOR - Recibe tu pedido*\n"
                        f"{resumen}\n\n"
                        f"👉 Confirmar entrega 👇 {link_publico}\n\n"
                        f"Por favor abre el enlace, revisa tus datos y confirma la recepción "
                        f"(firma digital, o foto). ¡Gracias por tu compra!"
                    )
                    wa_link = "https://wa.me/?text=" + __import__("urllib.parse").parse.quote(msj_wa)
                    import urllib.parse
                    subject_mail = f"Coodescor · Recibe tu pedido - {cliente} ({docs})"
                    body_mail = (
                        f"Buen día {cliente},\n\n"
                        f"Tenemos listo tu pedido.\n{resumen}\n\n"
                        f"👉 Confirma la recepción aquí: {link_publico}\n\n"
                        f"Atentamente,\nCoodescor - Logística\n"
                    )
                    mailto_link = (
                        "mailto:?subject=" + urllib.parse.quote(subject_mail)
                        + "&body=" + urllib.parse.quote(body_mail)
                    )
                    return self._json({
                        "ok": True,
                        "ya_emitido": ya_emitido,
                        "token": tok,
                        "link": link_publico,
                        "whatsapp": wa_link,
                        "email": mailto_link,
                        "resumen": {
                            "cliente": cliente,
                            "documentos": docs,
                            "total_bultos": total_bultos,
                            "persona_recibe": lbl_recibe,
                        },
                        "emision": info_creador,
                    })
                if tipo == "asignar_transportador":
                    d = self._json_body()
                    _tipo = str(d.get("tipo") or "").strip().lower() or None
                    _asig = d.get("transportador_asignado_id")
                    _asig = int(_asig) if isinstance(_asig, int) or (isinstance(_asig, str) and str(_asig).isdigit()) else None
                    asignar_tipo_transportador(
                        guia_id=gid, user=user, tipo=_tipo,
                        transportador_asignado_id=_asig,
                    )
                    return self._json({"ok": True, "redirect": f"/guia/{gid}"})
                if tipo == "registrar_transportador_externo":
                    requerir_rol(user, "administrativo", "cedis", "admin")
                    d = self._json_body()
                    datos_payload = {
                        "transportador_nombre":    d.get("transportador_nombre"),
                        "transportador_cc":        d.get("transportador_cc"),
                        "transportador_tel":       d.get("transportador_tel"),
                        "transportador_vehiculo":  d.get("transportador_vehiculo"),
                        "transportador_placa":     d.get("transportador_placa"),
                        "transportador_flete":     d.get("transportador_flete"),
                        "cliente_recibe_nombre":   d.get("cliente_recibe_nombre"),
                        "firma_transportador":     d.get("firma_transportador"),
                    }
                    ok, msj, info = registrar_transportador_externo(
                        guia_id=gid, user=user, datos=datos_payload, dispositivo="web", ip=ip,
                    )
                    return self._json({
                        "ok": bool(ok),
                        "msg": msj,
                        "info": info,
                        "redirect": f"/guia/{gid}",
                    })
                if tipo == "editar":
                    return self._api_editar_guia(gid, user, ip, ua)
                return self._api_evento_guia(gid, tipo, user, ip, ua)
            # ----- API clientes_contactos (POST) -----
            for _patron, _handler in RUTAS_CLIENTES_CONTACTOS_POST:
                if re.match(_patron, ruta):
                    return _handler(qs, user, self._json, self._json_body())
            # ----- API transportadores_externos (POST) -----
            for _patron, _handler in RUTAS_TRANSPORTADORES_EXTERNOS_POST:
                if re.match(_patron, ruta):
                    return _handler(qs, user, self._json, self._json_body())
            # ----- API receptores (POST) -----
            for _patron, _handler in RUTAS_RECEPTORES_POST:
                if re.match(_patron, ruta):
                    return _handler(user, self._json_body(), ip, self._json)
            # ----- API IA (POST) -----
            for _patron, _handler in RUTAS_AI_POST:
                if re.match(_patron, ruta):
                    return _handler(user, self._json_body(), ip, self._json)
            # ----- API administración de base de datos (solo admin) -----
            if ruta.startswith("/api/admin/db/"):
                requerir_rol(user, "admin")
                for _patron, _handler in RUTAS_DB_ADMIN_POST:
                    if re.match(_patron, ruta):
                        return _handler(user, self._json_body(), ip, self._json)
                return self._json({"ok": False, "error": "ruta no existe"}, 404)
            return self._json(
                {"ok": False, "error": "ruta no existe"},
                404,
            )
        except AuthError as ex:
            logger.info("Auth error: %s ip=%s", ex, ip)
            return self._json({"ok": False, "error": str(ex)}, 401)
        except DbAdminError as ex:
            logger.warning("Error del módulo de BD en POST %s: %s", ruta, ex)
            return self._json({"ok": False, "error": str(ex)}, 400)
        except ForbiddenError as ex:
            logger.warning("Forbidden POST %s user=%s: %s", ruta, (user or {}).get("usuario"), ex)
            return self._json({"ok": False, "error": "Sin permisos para realizar esta acción"}, 403)
        except ValidationError as ex:
            return self._json({"ok": False, "error": ex.mensaje}, 400)
        except GuiaNoExisteError as ex:
            return self._json({"ok": False, "error": str(ex)}, 404)
        except EstadoInvalidoError as ex:
            return self._json({"ok": False, "error": str(ex)}, 409)
        except ValueError as ex:
            return self._json({"ok": False, "error": str(ex)}, 400)
        except Exception as ex:
            logger.exception("Error no manejado en POST %s: %s", ruta, ex)
            return self._json({"ok": False, "error": "Error interno del servidor"}, 500)

    # -- DELETE -----------------------------------------------------------------

    def do_DELETE(self):
        u = urlparse(self.path)
        ruta = u.path.rstrip("/") or "/"
        qs = parse_qs(u.query)
        user, _sid = self._user()
        ip = self._client_ip()
        try:
            self._validar_origen_csrf()
            if not user:
                return self._json({"ok": False, "error": "Sesión expirada o inválida"}, 401)
            if ruta.startswith("/api/admin/db/"):
                requerir_rol(user, "admin")
                for _patron, _handler in RUTAS_DB_ADMIN_DELETE:
                    if re.match(_patron, ruta):
                        return _handler(user, qs, ip, self._json)
                return self._json({"ok": False, "error": "ruta no existe"}, 404)
            m = re.match(RUTAS_RECEPTORES_DELETE_REGEX[0], ruta)
            if m:
                return RUTAS_RECEPTORES_DELETE_REGEX[1](m, user, self._json)
            return self._json({"ok": False, "error": "ruta no existe"}, 404)
        except DbAdminError as ex:
            return self._json({"ok": False, "error": str(ex)}, 400)
        except ForbiddenError as ex:
            logger.warning("Forbidden DELETE %s user=%s: %s", ruta, (user or {}).get("usuario"), ex)
            return self._json({"ok": False, "error": "Sin permisos para realizar esta acción"}, 403)
        except ValueError as ex:
            logger.warning("Bad request DELETE %s: %s", ruta, ex)
            return self._json({"ok": False, "error": str(ex)}, 400)
        except Exception as ex:
            logger.exception("Error no manejado en DELETE %s: %s", ruta, ex)
            return self._json({"ok": False, "error": "Error interno del servidor"}, 500)

    # -- PUT / PATCH -------------------------------------------------------------

    def do_PUT(self):
        """PUT y PATCH se comportan igual: edición parcial de la guía."""
        u = urlparse(self.path)
        ruta = u.path.rstrip("/") or "/"
        user, _sid = self._user()
        ip = self._client_ip()
        try:
            self._validar_origen_csrf()
            if not user:
                return self._json({"ok": False, "error": "Sesión expirada o inválida"}, 401)
            m = re.match(RUTA_GUIA_ID_REGEX, ruta)
            if m:
                return editar_guia_api(
                    int(m.group(1)), self._json_body(), user, ip, self._json
                )
            return self._json({"ok": False, "error": "ruta no existe"}, 404)
        except ValidationError as ex:
            return self._json({"ok": False, "error": str(ex)}, 400)
        except AuthError as ex:
            return self._json({"ok": False, "error": str(ex)}, 401)
        except ForbiddenError as ex:
            logger.warning("Forbidden PUT %s user=%s: %s", ruta, (user or {}).get("usuario"), ex)
            return self._json({"ok": False, "error": "Sin permisos para realizar esta acción"}, 403)
        except GuiaNoExisteError as ex:
            return self._json({"ok": False, "error": str(ex)}, 404)
        except EstadoInvalidoError as ex:
            return self._json({"ok": False, "error": str(ex)}, 409)
        except ValueError as ex:
            return self._json({"ok": False, "error": str(ex)}, 400)
        except Exception as ex:
            logger.exception("Error no manejado en PUT %s: %s", ruta, ex)
            return self._json({"ok": False, "error": "Error interno del servidor"}, 500)

    do_PATCH = do_PUT

    # -- sub-métodos GET --------------------------------------------------------

    def _servir_estatico(self, nombre: str):
        """
        Sirve un archivo de guias_coodescor/static/.

        Acepta subdirectorios (manifest.json, service-worker.js, icons/…) y
        valida que la ruta resuelta no escape del directorio de estáticos.
        """
        base = os.path.normpath(STATIC_DIR)
        if not nombre or nombre.startswith("."):
            return self._out(404, "no")
        p = os.path.normpath(os.path.join(base, nombre.replace("\\", "/")))
        if os.path.commonpath([p, base]) != base or not os.path.isfile(p):
            return self._out(404, "no")
        ext = p.rsplit(".", 1)[-1].lower() if "." in p else ""
        ctype = mime_por_extension(ext)
        if ext in ("css", "js"):
            cache_time = 300
        elif ext in ("png", "jpg", "jpeg", "gif", "svg", "webp", "ico"):
            cache_time = 86400
        else:
            cache_time = 3600
        extra = {"Cache-Control": f"public, max-age={cache_time}"}
        # Sin esto el service worker queda limitado a /static/ y no controla
        # /, /login ni /tablero.
        if os.path.basename(p) == "service-worker.js":
            extra["Service-Worker-Allowed"] = "/"
            extra["Cache-Control"] = "no-store, no-cache, must-revalidate"
        with open(p, "rb") as f:
            self._out(200, f.read(), ctype, extra=extra)

    def _servir_spa(self):
        """Sirve el index del build React para las rutas de la SPA.

        El backend es el servidor principal (8000): así localhost y ngrok
        muestran la interfaz nueva sin depender de Vite. Si falta el build se
        devuelve un mensaje de despliegue, nunca la interfaz vieja.
        """
        if not os.path.isfile(FRONTEND_INDEX):
            html = (
                "<!doctype html><html lang='es'><meta charset='utf-8'>"
                "<title>Guías Coodescor · falta el build</title>"
                "<body style='font-family:system-ui;padding:40px;max-width:640px;margin:auto'>"
                "<h1>Interfaz nueva pendiente de compilar</h1>"
                "<p>Ejecuta <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code> "
                "y reinicia el servidor.</p></body></html>"
            )
            return self._out(
                503, html, "text/html; charset=utf-8",
                extra={"Cache-Control": "no-store, no-cache, must-revalidate"},
            )
        try:
            with open(FRONTEND_INDEX, "rb") as f:
                data = f.read()
        except OSError:
            return self._out(500, "No se pudo leer el build de la interfaz.")
        # no-store: un despliegue nuevo debe verse al recargar, incluso con la
        # PWA antigua instalada.
        return self._out(
            200, data, "text/html; charset=utf-8",
            extra={"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"},
        )

    def _servir_asset_frontend(self, rel: str):
        """Sirve /assets/* del build React con validación de ruta y cache largo."""
        base = os.path.normpath(os.path.join(FRONTEND_DIST, "assets"))
        if not rel or rel.startswith("."):
            return self._out(404, "no")
        p = os.path.normpath(os.path.join(base, rel.replace("\\", "/")))
        if os.path.commonpath([p, base]) != base or not os.path.isfile(p):
            return self._out(404, "no")
        ext = p.rsplit(".", 1)[-1].lower() if "." in p else ""
        with open(p, "rb") as f:
            self._out(
                200, f.read(), mime_por_extension(ext),
                extra={"Cache-Control": "public, max-age=31536000, immutable"},
            )

    def _servir_adjunto(self, rel: str):
        """
        Sirve una firma o foto. ruta_adjunto_segura() solo admite imágenes
        dentro de ADJUNTOS_DIR, así que la base de datos y los logs que están
        en DATA_DIR quedan fuera de alcance aunque se conozca el nombre.
        """
        try:
            p = ruta_adjunto_segura(rel)
        except ValueError:
            return self._out(404, "no")
        ext = p.rsplit(".", 1)[-1].lower() if "." in p else ""
        with open(p, "rb") as f:
            self._out(
                200,
                f.read(),
                mime_por_extension(ext),
                extra={"Cache-Control": "private, max-age=3600"},
            )

    def _servir_export_csv(self):
        data, nombre = exportar_guias_csv()
        self._out(
            200,
            data,
            "text/csv; charset=utf-8",
            {"Content-Disposition": f'attachment; filename="{nombre}"'},
        )

    # -- sub-métodos POST (API) -------------------------------------------------

    def _api_login(self, ip: str, ua: str):
        d = self._json_body()
        usuario = d.get("usuario", "")
        clave = d.get("clave", "")
        captcha_tok = d.get("captcha_token", "")
        captcha_rta = d.get("captcha_respuesta", "")
        bypass_header = self.headers.get("X-CAPTCHA-Bypass", "") if hasattr(self, "headers") else ""
        ok_c, msg_c = captcha_validar(captcha_tok, captcha_rta, ip=ip, ua=ua, bypass_header=bypass_header)
        if not ok_c:
            logger.info(
                "CAPTCHA invalid login intent usuario=%s ip=%s motivo=%s",
                usuario[:32], ip, (msg_c or "")[:200],
            )
            return self._json(
                {"ok": False, "error": "⚠️ " + (msg_c or "Verificación CAPTCHA fallida. Intenta de nuevo."), "captcha_error": True},
                400,
                extra={"Cache-Control": "no-store, no-cache, private, max-age=0"},
            )
        _sid, cookie, usuario_datos = svc_login(usuario, clave, ip=ip, user_agent=ua)
        return self._json(
            {"ok": True, "redirect": "/tablero", "usuario": _usuario_publico(usuario_datos)},
            extra={"Set-Cookie": cookie},
        )

    def _api_crear_guia(self, user: dict, ip: str, ua: str):
        d = self._json_body()
        guia_id, _cons = crear_guia(user, d, dispositivo=ua, ip=ip)
        return self._json({"ok": True, "id": guia_id, "redirect": "/guia/{0}".format(guia_id)})

    def _api_crear_usuario(self, user: dict):
        requerir_rol(user, "admin")
        d = self._json_body()
        crear_usuario(
            d.get("usuario", ""),
            d.get("nombre", ""),
            d.get("clave", ""),
            d.get("rol", "ventas"),
            creador=user,
        )
        return self._json({"ok": True, "redirect": "/admin"})

    def _api_editar_usuario(self, user: dict, uid: int):
        requerir_rol(user, "admin")
        d = self._json_body()
        editar_usuario(
            uid,
            usuario=d.get("usuario", ""),
            nombre=d.get("nombre", ""),
            rol=d.get("rol", "ventas"),
            activo=bool(d.get("activo", 1)),
            editor=user,
        )
        return self._json({"ok": True, "redirect": "/admin"})

    def _api_config(self, user: dict):
        d = self._json_body()
        actualizar_configuracion(d, user)
        return self._json({"ok": True, "redirect": "/admin"})

    def _api_evento_guia(self, gid: int, tipo: str, user: dict, ip: str, ua: str):
        d = self._json_body()
        procesar_evento(gid, tipo, user, d, dispositivo=ua, ip=ip)
        redirect_to = f"/guia/{gid}"
        if tipo in ("recepcion_admin", "control_cedis", "entrega_transporte", "entrega_cliente"):
            redirect_to = "/tablero"
        return self._json({"ok": True, "redirect": redirect_to})

    def _api_editar_guia(self, gid: int, user: dict, ip: str, ua: str):
        d = self._json_body()
        _evid, diff = editar_guia(gid, user, d, dispositivo=ua, ip=ip)
        if not diff:
            return self._json({"ok": True, "redirect": f"/guia/{gid}", "mensaje": "No hubo cambios"})
        n = len(diff)
        return self._json({
            "ok": True,
            "redirect": f"/guia/{gid}",
            "mensaje": f"Se actualizaron {n} campo(s): {', '.join(diff.keys())}",
        })


def get_host_port():
    return HOST, PORT
