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
import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from guias_coodescor.config import (
    ADJUNTOS_DIR,
    DATA_DIR,
    HOST,
    MAX_REQUEST_BODY,
    PORT,
    STATIC_DIR,
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
    crear_usuario,
    login as svc_login,
    logout as svc_logout,
    requerir_rol,
)
from guias_coodescor.services.export_service import exportar_guias_csv
from guias_coodescor.services.guias_service import (
    EstadoInvalidoError,
    GuiaNoExisteError,
    crear_guia,
    editar_guia,
    procesar_evento,
)
from guias_coodescor.web.views.admin_views import vista_admin
from guias_coodescor.web.views.auth_views import vista_login, vista_tablero
from guias_coodescor.web.views.base import escape, page
from guias_coodescor.web.views.guias_views import (
    vista_detalle_guia,
    vista_imprimir_guia,
    vista_listado_guias,
    vista_nueva_guia,
)

configurar_logging()
logger = get_logger("guias_coodescor.http")


class RequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "CoodescorGuias/2.0"

    def log_message(self, format, *args):
        logger.debug("%s - %s", self.address_string(), format % args)

    # -- helpers ----------------------------------------------------------------

    def _out(self, code: int, body, ctype: str = "text/html; charset=utf-8", extra: dict | None = None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _redirect(self, ruta: str):
        self._out(303, b"", "text/plain", {"Location": ruta})

    def _json_body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_REQUEST_BODY:
            raise ValueError("payload muy grande")
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            raise ValueError("JSON inválido en el cuerpo de la petición")

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
        xff = self.headers.get("X-Forwarded-For") or ""
        if xff:
            return xff.split(",", 1)[0].strip()
        return self.client_address[0] if self.client_address else ""

    def _user_agent(self) -> str:
        return self.headers.get("User-Agent") or ""

    # -- GET --------------------------------------------------------------------

    def do_GET(self):
        u = urlparse(self.path)
        ruta = u.path.rstrip("/") or "/"
        qs = parse_qs(u.query)
        user, _sid = self._user()
        try:
            if ruta in ("/static/style.css", "/static/app.js"):
                return self._servir_estatico(ruta[len("/static/"):])
            if ruta.startswith("/static_file/"):
                return self._servir_adjunto(ruta[len("/static_file/"):])
            if not user:
                if ruta in ("/", "/login"):
                    return self._out(200, vista_login())
                return self._redirect("/login")
            if ruta == "/":
                return self._redirect("/tablero")
            if ruta == "/tablero":
                return self._out(200, vista_tablero(user))
            if ruta == "/guias":
                return self._out(200, vista_listado_guias(user, qs))
            if ruta == "/guia/nueva":
                return self._out(200, vista_nueva_guia(user))
            if ruta == "/admin":
                return self._out(200, vista_admin(user))
            if ruta.startswith("/guia/") and ruta.endswith("/imprimir"):
                gid = int(ruta.split("/")[2])
                return self._out(200, vista_imprimir_guia(gid, user))
            if ruta.startswith("/guia/"):
                gid = int(ruta.split("/")[2])
                return self._out(200, vista_detalle_guia(gid, user))
            if ruta == "/api/exportar.csv":
                return self._servir_export_csv()
            return self._out(404, page("404", "<h1>404 · Página no encontrada</h1>", user))
        except ForbiddenError as ex:
            logger.warning("Forbidden: %s user=%s", ex, (user or {}).get("usuario"))
            return self._out(403, page("403", f"<h1>403 · Acceso denegado</h1><p>{escape(str(ex))}</p>", user))
        except ValueError as ex:
            logger.warning("Bad request GET %s: %s", ruta, ex)
            return self._out(400, page("400", f"<h1>400 · Solicitud inválida</h1><p>{escape(str(ex))}</p>", user))
        except Exception as ex:
            logger.exception("Error no manejado en GET %s: %s", ruta, ex)
            msg = "<h1>500 · Error interno</h1><p>Consulte al administrador.</p>"
            return self._out(500, page("Error", msg, user))

    # -- POST -------------------------------------------------------------------

    def do_POST(self):
        u = urlparse(self.path)
        ruta = u.path.rstrip("/") or "/"
        user, sid = self._user()
        ip = self._client_ip()
        ua = self._user_agent()
        try:
            if ruta == "/api/login":
                return self._api_login(ip, ua)
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
            if ruta == "/api/usuarios":
                return self._api_crear_usuario(user)
            if ruta == "/api/config":
                return self._api_config(user)
            trozos = ruta.split("/")
            if len(trozos) == 5 and trozos[1] == "api" and trozos[2] == "guias":
                gid = int(trozos[3])
                tipo = trozos[4]
                if tipo == "editar":
                    return self._api_editar_guia(gid, user, ip, ua)
                return self._api_evento_guia(gid, tipo, user, ip, ua)
            return self._json({"ok": False, "error": "ruta no existe"}, 404)
        except AuthError as ex:
            logger.info("Auth error: %s ip=%s", ex, ip)
            return self._json({"ok": False, "error": str(ex)}, 401)
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

    # -- sub-métodos GET --------------------------------------------------------

    def _servir_estatico(self, nombre: str):
        p = os.path.normpath(os.path.join(STATIC_DIR, nombre))
        if not p.startswith(os.path.normpath(STATIC_DIR)) or not os.path.isfile(p):
            # Intentar buscar en subdirectorios (icons, etc.)
            # Verificar si es un archivo en subdirectorios
            if ".." not in nombre and "\\" not in nombre:
                # Probar buscar en subdirectorios
                test_path = os.path.normpath(os.path.join(STATIC_DIR, nombre))
                if os.path.isfile(test_path) and test_path.startswith(os.path.normpath(STATIC_DIR)):
                    p = test_path
                else:
                    return self._out(404, "no")
            else:
                return self._out(404, "no")
        ext = p.rsplit(".", 1)[-1].lower() if "." in p else ""
        ctype = mime_por_extension(ext)
        # Cache más largo para assets estáticos
        cache_time = 86400 if ext in ("css", "js", "png", "jpg", "jpeg", "gif", "svg", "json") else 3600
        with open(p, "rb") as f:
            self._out(200, f.read(), ctype, extra={"Cache-Control": f"public, max-age={cache_time}"})

    def _servir_adjunto(self, rel: str):
        try:
            p = ruta_adjunto_segura(rel)
        except ValueError:
            return self._out(404, "no")
        ext = p.rsplit(".", 1)[-1].lower() if "." in p else ""
        ctype = mime_por_extension(ext)
        with open(p, "rb") as f:
            self._out(200, f.read(), ctype)

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
        _sid, cookie, _u = svc_login(usuario, clave, ip=ip, user_agent=ua)
        return self._json(
            {"ok": True, "redirect": "/tablero"},
            extra={"Set-Cookie": cookie},
        )

    def _api_crear_guia(self, user: dict, ip: str, ua: str):
        d = self._json_body()
        guia_id, _cons = crear_guia(user, d, dispositivo=ua, ip=ip)
        return self._json({"ok": True, "redirect": f"/guia/{guia_id}"})

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

    def _api_config(self, user: dict):
        d = self._json_body()
        actualizar_configuracion(d, user)
        return self._json({"ok": True, "redirect": "/admin"})

    def _api_evento_guia(self, gid: int, tipo: str, user: dict, ip: str, ua: str):
        d = self._json_body()
        procesar_evento(gid, tipo, user, d, dispositivo=ua, ip=ip)
        return self._json({"ok": True, "redirect": f"/guia/{gid}"})

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
