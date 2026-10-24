#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas de aceptación por HTTP contra el servidor real.

Levanta el mismo RequestHandler que usa la aplicación en un puerto efímero,
con una base de datos temporal, y ejercita los procesos de extremo a extremo:
autenticación, autorización, creación/edición de guías, flujo completo con
firmas, link público de confirmación, endpoints de catálogos, administración de
la base y validación de entradas.

Uso:
    py -3 -m pytest tests/test_e2e_http.py -v
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer

_ROOT = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_ROOT)
for _p in (_BACKEND, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import guias_coodescor.config as _cfg

_TEMP_DIR = ""
_SERVER = None
_THREAD = None
_PORT = 0
_BYPASS = "e2e-bypass-key"

FIRMA = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "+P+/HgAFhAJ/wlseKgAAAABJRU5ErkJggg=="
)


def _configurar(data_dir):
    _cfg.DATA_DIR = data_dir
    _cfg.ADJUNTOS_DIR = os.path.join(data_dir, "adjuntos")
    _cfg.BACKUP_DIR = os.path.join(data_dir, "respaldos")
    _cfg.DB_PATH = os.path.join(data_dir, "guias.db")
    _cfg.RECEPTORES_DB_PATH = os.path.join(data_dir, "receptores.db")
    _cfg.LOG_DIR = data_dir
    _cfg.LOG_FILE = os.path.join(data_dir, "test.log")


def setup_module(module):
    global _TEMP_DIR, _SERVER, _THREAD, _PORT
    _TEMP_DIR = tempfile.mkdtemp(prefix="coodescor_e2e_")
    data = os.path.join(_TEMP_DIR, "data")
    for sub in ("", "adjuntos", "respaldos"):
        os.makedirs(os.path.join(data, sub), exist_ok=True)
    _configurar(data)
    os.environ["COODESCOR_CAPTCHA_BYPASS_KEY"] = _BYPASS

    from guias_coodescor.database.models import init_db
    init_db()
    from guias_coodescor.api.router import RequestHandler

    _SERVER = ThreadingHTTPServer(("127.0.0.1", 0), RequestHandler)
    _PORT = _SERVER.server_address[1]
    _THREAD = threading.Thread(target=_SERVER.serve_forever, daemon=True)
    _THREAD.start()


def teardown_module(module):
    if _SERVER is not None:
        _SERVER.shutdown()
        _SERVER.server_close()
    shutil.rmtree(_TEMP_DIR, ignore_errors=True)
    os.environ.pop("COODESCOR_CAPTCHA_BYPASS_KEY", None)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Cliente:
    def __init__(self):
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar), NoRedirect()
        )

    def pedir(self, metodo, ruta, payload=None, headers=None):
        hdrs = {"User-Agent": "e2e-test/1.0", "X-CAPTCHA-Bypass": _BYPASS}
        if headers:
            hdrs.update(headers)
        datos = None
        if payload is not None:
            datos = json.dumps(payload).encode()
            hdrs["Content-Type"] = "application/json"
        req = urllib.request.Request(
            f"http://127.0.0.1:{_PORT}{ruta}", data=datos, headers=hdrs, method=metodo
        )
        try:
            resp = self.opener.open(req, timeout=20)
            estado, cab, cuerpo = resp.status, resp.headers, resp.read()
        except urllib.error.HTTPError as ex:
            estado, cab, cuerpo = ex.code, ex.headers, ex.read()
        try:
            payload_json = json.loads(cuerpo.decode())
        except (ValueError, UnicodeDecodeError):
            payload_json = None
        return estado, payload_json, cab, cuerpo

    def login(self, usuario, clave):
        estado, data, _h, _b = self.pedir(
            "POST", "/api/login", {"usuario": usuario, "clave": clave}
        )
        assert estado == 200 and data.get("ok"), f"login {usuario} falló: {estado} {data}"
        return data


def _usuario(nombre):
    from guias_coodescor.database.connection import db_connection
    with db_connection() as conn:
        fila = conn.execute(
            "SELECT * FROM usuarios WHERE usuario = ? COLLATE NOCASE", (nombre,)
        ).fetchone()
    return dict(fila)


class TestAutenticacionHTTP(unittest.TestCase):
    def test_api_sin_sesion_devuelve_401_json(self):
        c = Cliente()
        for ruta in ("/api/guias", "/api/guias/conteo", "/api/guias/1",
                     "/api/guias/1/eventos", "/api/session",
                     "/api/usuarios/rol/transportador"):
            estado, data, _h, _b = c.pedir("GET", ruta)
            self.assertEqual(estado, 401, f"{ruta} debía ser 401, fue {estado}")
            self.assertIsInstance(data, dict)
            self.assertFalse(data.get("ok"))

    def test_cuerpo_json_no_objeto_devuelve_400(self):
        c = Cliente()
        estado, data, _h, _b = c.pedir("POST", "/api/login", ["admin", "x"])
        self.assertEqual(estado, 400, data)
        self.assertFalse(data.get("ok"))

        c.login("ventas", "ventas123")
        estado, data, _h, _b = c.pedir("POST", "/api/guias", ["no", "objeto"])
        self.assertEqual(estado, 400, data)
        estado, data, _h, _b = c.pedir("PUT", "/api/guias/1", ["no", "objeto"])
        self.assertEqual(estado, 400, data)

    def test_login_devuelve_usuario_y_sesion(self):
        c = Cliente()
        data = c.login("admin", "admin123")
        self.assertEqual(data["usuario"]["rol"], "admin")
        self.assertNotIn("pass_hash", data["usuario"])
        estado, sesion, _h, _b = c.pedir("GET", "/api/session")
        self.assertEqual(estado, 200)
        self.assertEqual(sesion["usuario"]["rol"], "admin")

    def test_ruta_api_inexistente_es_json(self):
        c = Cliente()
        c.login("admin", "admin123")
        estado, data, h, _b = c.pedir("GET", "/api/no-existe")
        self.assertEqual(estado, 404)
        self.assertIsInstance(data, dict)
        self.assertIn("application/json", h.get("Content-Type", ""))

    def test_origen_cruzado_no_puede_escribir(self):
        c = Cliente()
        c.login("admin", "admin123")
        estado, data, _h, _b = c.pedir(
            "POST", "/api/config", {"empresa": "HACK"},
            headers={"Origin": "https://evil.example"},
        )
        self.assertEqual(estado, 403, data)


class TestProcesosHTTP(unittest.TestCase):
    def test_flujo_completo_con_link_publico(self):
        ventas, admin, cedis = Cliente(), Cliente(), Cliente()
        ventas.login("ventas", "ventas123")
        admin.login("admin", "admin123")
        cedis.login("cedis", "cedis123")

        estado, data, _h, _b = ventas.pedir("POST", "/api/guias", {
            "cliente": "Cliente E2E", "ciudad": "Bogotá",
            "direccion": "Calle 9", "nit": "900123456-1",
            "documentos": "FV 100", "cajas": 2, "bolsas": 1,
        })
        self.assertEqual(estado, 200, data)
        gid = data["id"]

        # Prellenado y estado inicial
        estado, detalle, _h, _b = ventas.pedir("GET", f"/api/guias/{gid}")
        self.assertEqual(estado, 200)
        self.assertEqual(detalle["guia"]["estado"], "CREADA")
        self.assertEqual(detalle["guia"]["nit"], "9001234561")

        # Recepción administrativa
        estado, data, _h, _b = admin.pedir(
            "POST", f"/api/guias/{gid}/evento/recepcion_admin",
            {"recibe": "Bodega", "firma": FIRMA},
        )
        self.assertEqual(estado, 200, data)

        # Control CEDIS (con funcionario obligatorio)
        estado, data, _h, _b = cedis.pedir(
            "POST", f"/api/guias/{gid}/evento/control_cedis",
            {"firma": FIRMA, "cajas": 2, "bolsas": 1, "cayvas": 0, "sobres": 0,
             "cedis_funcionario": "FUNCIONARIO E2E"},
        )
        self.assertEqual(estado, 200, data)

        # Entrega al transportador
        estado, data, _h, _b = cedis.pedir(
            "POST", f"/api/guias/{gid}/evento/entrega_transporte",
            {"firma": FIRMA, "nombre": "Transportador E2E"},
        )
        self.assertEqual(estado, 200, data)

        # Token público y confirmación del cliente sin sesión
        estado, data, _h, _b = admin.pedir(
            "POST", f"/api/guias/{gid}/generar_token_entrega", {}
        )
        self.assertEqual(estado, 200, data)
        token = data["token"]

        anon = Cliente()
        estado, pagina, _h, cuerpo = anon.pedir("GET", f"/firma/{token}")
        self.assertEqual(estado, 200)
        self.assertIn(b"firma", cuerpo.lower())

        estado, data, _h, _b = anon.pedir(
            "POST", f"/api/firma_publica/{token}",
            {"firma": FIRMA, "cliente_recibe_nombre": "Cliente E2E"},
        )
        self.assertEqual(estado, 200, data)

        estado, detalle, _h, _b = ventas.pedir("GET", f"/api/guias/{gid}")
        self.assertEqual(detalle["guia"]["estado"], "ENTREGADA")

        # El token es de un solo uso
        estado, data, _h, _b = anon.pedir(
            "POST", f"/api/firma_publica/{token}", {"firma": FIRMA, "cliente_recibe_nombre": "X"}
        )
        self.assertIn(estado, (400, 404, 409), data)

    def test_contactos_y_transportadores_externos(self):
        ventas, admin, cedis = Cliente(), Cliente(), Cliente()
        ventas.login("ventas", "ventas123")
        admin.login("admin", "admin123")
        cedis.login("cedis", "cedis123")

        # Asegura un cliente con NIT (se crea al crear la guía)
        ventas.pedir("POST", "/api/guias", {
            "cliente": "Cliente Contactos", "ciudad": "Cali", "nit": "901111222-3",
        })

        estado, data, _h, _b = ventas.pedir(
            "POST", "/api/clientes_contactos/guardar",
            {"nit_cliente": "901111222-3", "nombre": "Contacto E2E", "cedula": "123"},
        )
        self.assertEqual(estado, 200, data)
        self.assertTrue(data.get("ok"))
        contacto_id = data.get("contacto_id")

        estado, data, _h, _b = ventas.pedir(
            "POST", "/api/clientes_contactos/eliminar", {"contacto_id": contacto_id}
        )
        self.assertEqual(estado, 200, data)

        # Solo admin/administrativo puede modificar el maestro de transportadores
        estado, data, _h, _b = ventas.pedir(
            "POST", "/api/transportadores_externos/guardar", {"nombre": "Trans E2E"}
        )
        self.assertEqual(estado, 403, data)

        estado, data, _h, _b = admin.pedir(
            "POST", "/api/transportadores_externos/guardar",
            {"nombre": "Trans E2E", "cc": "123456", "telefono": "3001112233"},
        )
        self.assertEqual(estado, 200, data)
        self.assertTrue(data.get("ok"))
        tid = data.get("transportador_id")
        estado, data, _h, _b = cedis.pedir("GET", "/api/transportadores_externos/listar")
        self.assertEqual(estado, 200, data)
        self.assertTrue(any(t.get("id") == tid for t in data["transportadores"]))
        estado, data, _h, _b = admin.pedir(
            "POST", "/api/transportadores_externos/eliminar", {"transportador_id": tid}
        )
        self.assertEqual(estado, 200, data)

    def test_transportador_solo_ve_sus_guias(self):
        from guias_coodescor.services.guias_service import (
            asignar_tipo_transportador, procesar_evento,
        )
        ventas, admin, cedis = Cliente(), Cliente(), Cliente()
        ventas.login("ventas", "ventas123")
        admin.login("admin", "admin123")
        cedis.login("cedis", "cedis123")

        t1, t2 = _usuario("transportador"), _usuario("transportador2")
        estado, data, _h, _b = ventas.pedir("POST", "/api/guias", {
            "cliente": "Cliente Asignado", "ciudad": "Medellín", "nit": "902222333-4",
        })
        gid = data["id"]
        procesar_evento(gid, "recepcion_admin", _usuario("administrativo"),
                        {"recibe": "Bodega", "firma": FIRMA})
        asignar_tipo_transportador(gid, _usuario("administrativo"), "propio", t1["id"])

        cli1, cli2 = Cliente(), Cliente()
        cli1.login("transportador", "transpor123")
        cli2.login("transportador2", "transpor123")

        estado, data, _h, _b = cli1.pedir("GET", f"/api/guias/{gid}")
        self.assertEqual(estado, 200, data)
        estado, data, _h, _b = cli2.pedir("GET", f"/api/guias/{gid}")
        self.assertEqual(estado, 403, data)
        estado, data, _h, _b = cli2.pedir("GET", f"/api/guias/{gid}/eventos")
        self.assertEqual(estado, 403, data)

        estado, data, _h, _b = cli2.pedir("GET", "/api/guias")
        self.assertEqual(estado, 200)
        ids = [g["id"] for g in data["guias"]]
        self.assertNotIn(gid, ids)

    def test_admin_db_y_reportes(self):
        admin = Cliente()
        admin.login("admin", "admin123")
        for ruta in ("/api/admin/db/bases", "/api/admin/db/tablas?base=guias",
                     "/api/admin/db/respaldos", "/api/admin/db/migraciones",
                     "/api/admin/db/auditoria?limite=5", "/api/loadtest/ultimo"):
            estado, data, _h, _b = admin.pedir("GET", ruta)
            self.assertEqual(estado, 200, f"{ruta}: {data}")
            self.assertTrue(data.get("ok"))

        estado, data, _h, _b = admin.pedir("GET", "/api/admin/db/tablas?base=no-existe")
        self.assertEqual(estado, 400, data)

        estado, data, _h, _b = admin.pedir(
            "POST", "/api/admin/db/consulta", {"sql": "SELECT u.* FROM usuarios u"}
        )
        self.assertEqual(estado, 400, data)

        # Escritura sobre migraciones/auditoría bloqueada
        for sql in ("DELETE FROM schema_migrations", "DELETE FROM admin_auditoria"):
            estado, data, _h, _b = admin.pedir(
                "POST", "/api/admin/db/consulta",
                {"sql": sql, "escritura": True, "confirmar": True},
            )
            self.assertEqual(estado, 400, f"{sql}: {data}")

    def test_csv_exporta_y_neutraliza_formulas(self):
        ventas, admin = Cliente(), Cliente()
        ventas.login("ventas", "ventas123")
        admin.login("admin", "admin123")
        ventas.pedir("POST", "/api/guias", {
            "cliente": "=cmd|' /C calc'!A0", "ciudad": "Bogotá", "nit": "903333444-5",
        })
        estado, _data, h, cuerpo = admin.pedir("GET", "/api/exportar.csv")
        self.assertEqual(estado, 200)
        texto = cuerpo.decode("utf-8-sig")
        self.assertIn("'=cmd", texto)
        self.assertNotIn(";=cmd", texto)

    def test_flujo_envio_directo_recogida_en_sede(self):
        """Ventas → CEDIS → entrega al cliente que recoge en sede (sin transportador)."""
        ventas, admin, cedis = Cliente(), Cliente(), Cliente()
        ventas.login("ventas", "ventas123")
        admin.login("admin", "admin123")
        cedis.login("cedis", "cedis123")

        estado, data, _h, _b = ventas.pedir("POST", "/api/guias", {
            "cliente": "Cliente Recoge E2E", "ciudad": "Bogotá",
            "direccion": "Sede CEDIS", "nit": "904444555-6",
            "envio_directo_cedis": True,
        })
        self.assertEqual(estado, 200, data)
        gid = data["id"]
        estado, detalle, _h, _b = ventas.pedir("GET", f"/api/guias/{gid}")
        self.assertEqual(detalle["guia"]["estado"], "EN_CEDIS")
        self.assertTrue(detalle["guia"]["envio_directo_cedis"])

        # No se puede entregar sin control de bultos de CEDIS.
        estado, data, _h, _b = cedis.pedir(
            "POST", f"/api/guias/{gid}/evento/entrega_cliente",
            {"recibe": "Cliente Sede", "firma": FIRMA},
        )
        self.assertEqual(estado, 409, data)

        estado, data, _h, _b = cedis.pedir(
            "POST", f"/api/guias/{gid}/evento/control_cedis",
            {"firma": FIRMA, "cajas": 1, "bolsas": 2, "cayvas": 0, "sobres": 0,
             "cedis_funcionario": "FUNCIONARIO E2E"},
        )
        self.assertEqual(estado, 200, data)

        estado, data, _h, _b = cedis.pedir(
            "POST", f"/api/guias/{gid}/evento/entrega_cliente",
            {"recibe": "Cliente Sede", "firma": FIRMA, "obs": "Recogió en sede"},
        )
        self.assertEqual(estado, 200, data)

        estado, detalle, _h, _b = ventas.pedir("GET", f"/api/guias/{gid}")
        self.assertEqual(detalle["guia"]["estado"], "ENTREGADA")
        estado, evs, _h, _b = ventas.pedir("GET", f"/api/guias/{gid}/eventos")
        tipos = [e["tipo"] for e in evs["eventos"]]
        self.assertIn("control_cedis", tipos)
        self.assertIn("entrega_cliente", tipos)
        self.assertNotIn("entrega_transporte", tipos)

    def test_flujo_directo_unificado_y_link_publico(self):
        """El botón único de CEDIS (control+entrega) y el link público en envío directo."""
        ventas, admin, cedis = Cliente(), Cliente(), Cliente()
        ventas.login("ventas", "ventas123")
        admin.login("admin", "admin123")
        cedis.login("cedis", "cedis123")

        def crear(cliente):
            estado, data, _h, _b = ventas.pedir("POST", "/api/guias", {
                "cliente": cliente, "ciudad": "Bogotá",
                "direccion": "Sede CEDIS", "nit": "904444555-6",
                "envio_directo_cedis": True,
            })
            self.assertEqual(estado, 200, data)
            return data["id"]

        # Proceso unificado en un solo clic (lo que usa la interfaz).
        gid = crear("Cliente Unificado Directo E2E")
        estado, data, _h, _b = cedis.pedir(
            "POST", f"/api/guias/{gid}/proceso_cedis_unificado",
            {
                "firma_cedis_entrega": FIRMA,
                "cajas": 1, "bolsas": 1, "cayvas": 0, "sobres": 0,
                "cedis_funcionario": "FUNCIONARIO E2E",
                "recibe": "Cliente Sede",
                "firma_recibe": FIRMA,
            },
        )
        self.assertEqual(estado, 200, data)
        self.assertTrue(data.get("ok"), data)
        estado, detalle, _h, _b = ventas.pedir("GET", f"/api/guias/{gid}")
        self.assertEqual(detalle["guia"]["estado"], "ENTREGADA")

        # Link público: inactivo antes del control, activo después y de un solo uso.
        gid2 = crear("Cliente Link Directo E2E")
        estado, data, _h, _b = admin.pedir("POST", f"/api/guias/{gid2}/generar_token_entrega", {})
        self.assertEqual(estado, 200, data)
        token = data["token"]
        anon = Cliente()
        estado, _p, _h, _cuerpo = anon.pedir("GET", f"/firma/{token}")
        self.assertEqual(estado, 422, "sin control CEDIS el link no debe estar activo")

        estado, data, _h, _b = cedis.pedir(
            "POST", f"/api/guias/{gid2}/evento/control_cedis",
            {"firma": FIRMA, "cajas": 1, "bolsas": 1, "cayvas": 0, "sobres": 0,
             "cedis_funcionario": "FUNCIONARIO E2E"},
        )
        self.assertEqual(estado, 200, data)
        estado, _p, _h, _cuerpo = anon.pedir("GET", f"/firma/{token}")
        self.assertEqual(estado, 200)

        estado, data, _h, _b = anon.pedir(
            "POST", f"/api/firma_publica/{token}",
            {"firma": FIRMA, "cliente_recibe_nombre": "Cliente Sede"},
        )
        self.assertEqual(estado, 200, data)
        estado, detalle, _h, _b = ventas.pedir("GET", f"/api/guias/{gid2}")
        self.assertEqual(detalle["guia"]["estado"], "ENTREGADA")

    def test_validaciones_de_entrada(self):
        ventas = Cliente()
        ventas.login("ventas", "ventas123")
        estado, data, _h, _b = ventas.pedir("POST", "/api/guias", {"ciudad": "Bogotá"})
        self.assertEqual(estado, 400)
        estado, data, _h, _b = ventas.pedir("POST", "/api/guias", {"cliente": "X" * 500, "ciudad": "B"})
        self.assertEqual(estado, 400)
        estado, data, _h, _b = ventas.pedir("GET", "/api/guias/999999")
        self.assertEqual(estado, 404)
        estado, data, _h, _b = ventas.pedir("PUT", "/api/guias/999999", {"ciudad": "Cali"})
        self.assertEqual(estado, 404, data)
        estado, data, _h, _b = ventas.pedir("DELETE", "/api/receptores/999999")
        self.assertEqual(estado, 403, data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
