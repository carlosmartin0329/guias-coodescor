#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suite de pruebas para el sistema de Guías Coodescor.
Prueba servicios core: auth, guias, eventos + utilidades (seguridad, validación).
Usa una base de datos TEMPORAL separada para no afectar datos de producción.

Uso:
    py -3 test_sistema.py
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_TEMP_DIR = tempfile.mkdtemp(prefix="coodescor_test_")
_TEMP_DATA = os.path.join(_TEMP_DIR, "data")
_TEMP_DB = os.path.join(_TEMP_DATA, "guias.db")
_TEMP_ADJ = os.path.join(_TEMP_DATA, "adjuntos")
_TEMP_LOG = os.path.join(_TEMP_DATA, "test.log")
os.makedirs(_TEMP_DATA, exist_ok=True)
os.makedirs(_TEMP_ADJ, exist_ok=True)

import guias_coodescor.config as _config_mod
_config_mod.DATA_DIR = _TEMP_DATA
_config_mod.ADJUNTOS_DIR = _TEMP_ADJ
_config_mod.DB_PATH = _TEMP_DB
_config_mod.LOG_DIR = _TEMP_DATA
_config_mod.LOG_FILE = _TEMP_LOG
os.makedirs(_config_mod.MIGRATIONS_DIR, exist_ok=True)

from guias_coodescor.core.utils import (
    ahora_txt,
    codigo_verificacion,
    extraer_extension_data_url,
    fecha_pasada,
    guardar_adjunto_bytes,
    hash_password_puro,
    ruta_adjunto_segura,
    sumar_segundos,
    verificar_password_puro,
)
from guias_coodescor.core.security import (
    crear_sesion,
    cookie_set_sid,
    cookie_unset_sid,
    generar_sid,
    hash_password,
    parsear_cookie_sid,
    validar_password_fuerte,
    validar_sesion,
    verificar_password,
)
from guias_coodescor.core.validators import (
    ValidationError,
    longitud_maxima,
    requerir,
    validar_clave_nueva,
    validar_entero_positivo,
    validar_estado_guia,
    validar_nombre_persona,
    validar_rol_input,
    validar_usuario,
)
from guias_coodescor.database.models import (
    init_db,
    get_config,
)
from guias_coodescor.database.connection import db_connection
from guias_coodescor.services.auth_service import (
    AuthError,
    ForbiddenError,
    crear_usuario,
    listar_usuarios,
    login,
    logout,
    requerir_rol,
)
from guias_coodescor.services.guias_service import (
    EstadoInvalidoError,
    GuiaNoExisteError,
    buscar_guias,
    contar_por_estado,
    crear_guia,
    editar_guia,
    generar_codigo_verificacion,
    obtener_guia,
    obtener_prellenado_ventas,
    procesar_evento,
    siguiente_consecutivo,
    validar_datos_evento,
    validar_transicion,
)
from guias_coodescor.services.eventos_service import (
    agregar_evento,
    listar_eventos,
    obtener_evento_por_tipo,
)

init_db()


def _firma_dataurl(png_b64: str = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+P+/HgAFhAJ/wlseKgAAAABJRU5ErkJggg==") -> str:
    return f"data:image/png;base64,{png_b64}"


class TestCoreUtils(unittest.TestCase):
    def test_hash_y_verificar_password_puro(self):
        h, sal = hash_password_puro("claveSecreta123")
        self.assertTrue(verificar_password_puro("claveSecreta123", h, sal))
        self.assertFalse(verificar_password_puro("claveMala", h, sal))
        self.assertFalse(verificar_password_puro("", h, sal))

    def test_ahora_y_fechas(self):
        ahora = ahora_txt()
        self.assertIn("-", ahora)
        self.assertIn(":", ahora)
        futuro = sumar_segundos(ahora, 3600)
        self.assertFalse(fecha_pasada(futuro))
        pasado = sumar_segundos(ahora, -10)
        self.assertTrue(fecha_pasada(pasado))

    def test_codigo_verificacion(self):
        c = codigo_verificacion(1, 100)
        self.assertTrue(c.startswith("CD-100-"))
        self.assertEqual(len(c), len("CD-100-XXXX"))

    def test_extraer_extension_dataurl(self):
        self.assertEqual(extraer_extension_data_url("data:image/png;base64,abc"), "png")
        self.assertEqual(extraer_extension_data_url("data:image/jpeg;base64,abc"), "jpg")
        self.assertEqual(extraer_extension_data_url("no es data url"), "bin")

    def test_guardar_y_resolver_adjunto(self):
        nombre = f"test_{os.getpid()}.png"
        ruta = guardar_adjunto_bytes(nombre, b"\x89PNG\r\n\x1a\nfake")
        self.assertTrue(ruta.startswith("adjuntos/"))
        resuelta = ruta_adjunto_segura(ruta)
        self.assertTrue(os.path.isfile(resuelta))
        with self.assertRaises(ValueError):
            ruta_adjunto_segura("../archivo_ilegal.txt")


class TestCoreSecurity(unittest.TestCase):
    def test_hash_wrapper(self):
        h, s = hash_password("MiClave987")
        self.assertTrue(verificar_password("MiClave987", h, s))
        self.assertFalse(verificar_password("Mala", h, s))

    def test_password_fuerte(self):
        self.assertIsNone(validar_password_fuerte("abcdef"))
        self.assertIsNotNone(validar_password_fuerte(""))
        self.assertIsNotNone(validar_password_fuerte("abc"))

    def test_generar_sid_aleatorio(self):
        s1 = generar_sid()
        s2 = generar_sid()
        self.assertNotEqual(s1, s2)
        self.assertGreaterEqual(len(s1), 40)

    def test_cookies_sesion(self):
        cookie = cookie_set_sid("sidprueba123")
        self.assertIn("sid=sidprueba123", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertEqual(parsear_cookie_sid(cookie.replace("Set-Cookie: ", "")), "sidprueba123")
        unset = cookie_unset_sid()
        self.assertIn("Max-Age=0", unset)

    def test_crear_y_validar_sesion(self):
        with db_connection() as conn:
            u = conn.execute("SELECT id FROM usuarios WHERE usuario='admin'").fetchone()
            uid = u["id"]
        sid = crear_sesion(uid, ip="127.0.0.1", user_agent="test")
        user = validar_sesion(sid)
        self.assertIsNotNone(user)
        self.assertEqual(user["usuario"], "admin")
        self.assertIsNone(validar_sesion("sid_inexistente"))


class TestValidators(unittest.TestCase):
    def test_requerir(self):
        self.assertEqual(requerir("hola", "c"), "hola")
        with self.assertRaises(ValidationError):
            requerir("", "c")
        with self.assertRaises(ValidationError):
            requerir(None, "c")

    def test_longitud_maxima(self):
        self.assertEqual(longitud_maxima("abc", "c", 5), "abc")
        with self.assertRaises(ValidationError):
            longitud_maxima("abcde", "c", 3)

    def test_validar_usuario(self):
        self.assertEqual(validar_usuario("user_1@test"), "user_1@test")
        with self.assertRaises(ValidationError):
            validar_usuario("ab")
        with self.assertRaises(ValidationError):
            validar_usuario("usuario con espacio")

    def test_validar_nombre_persona(self):
        self.assertEqual(validar_nombre_persona("Juan Pérez"), "Juan Pérez")
        with self.assertRaises(ValidationError):
            validar_nombre_persona("A")

    def test_validar_clave_nueva(self):
        self.assertEqual(validar_clave_nueva("clave6"), "clave6")
        with self.assertRaises(ValidationError):
            validar_clave_nueva("abc")

    def test_validar_rol_input(self):
        self.assertEqual(validar_rol_input("Admin"), "admin")
        with self.assertRaises(ValidationError):
            validar_rol_input("superadmin")

    def test_validar_estado_guia(self):
        self.assertEqual(validar_estado_guia("creada"), "CREADA")
        with self.assertRaises(ValidationError):
            validar_estado_guia("NOEXISTE")

    def test_validar_entero_positivo(self):
        self.assertEqual(validar_entero_positivo("10", "n"), 10)
        self.assertEqual(validar_entero_positivo("", "n", 5), 5)
        with self.assertRaises(ValidationError):
            validar_entero_positivo("-1", "n")


class TestAuthService(unittest.TestCase):
    def test_login_exitoso_admin(self):
        sid, cookie, user = login("admin", "admin123", ip="127.0.0.1")
        self.assertIsNotNone(sid)
        self.assertEqual(user["rol"], "admin")
        self.assertIn("HttpOnly", cookie)
        logout(sid)
        self.assertIsNone(validar_sesion(sid))

    def test_login_credenciales_malas(self):
        with self.assertRaises(AuthError):
            login("admin", "clavemala", ip="127.0.0.1")
        with self.assertRaises(AuthError):
            login("usuario_no_existe", "x", ip="127.0.0.1")
        with self.assertRaises(AuthError):
            login("", "", ip="127.0.0.1")

    def test_requerir_rol(self):
        admin = {"rol": "admin", "id": 1}
        ventas = {"rol": "ventas", "id": 2}
        self.assertTrue(requerir_rol(admin, "admin"))
        self.assertTrue(requerir_rol(admin, "admin", "ventas"))
        with self.assertRaises(ForbiddenError):
            requerir_rol(ventas, "admin")
        with self.assertRaises(ForbiddenError):
            requerir_rol(None, "admin")

    def test_listar_usuarios(self):
        users = listar_usuarios()
        self.assertGreaterEqual(len(users), 7)
        roles = {u["rol"] for u in users}
        self.assertIn("admin", roles)
        self.assertIn("ventas", roles)
        self.assertIn("cedis", roles)
        self.assertIn("administrativo", roles)

    def test_crear_usuario_y_duplicado(self):
        admin_user = listar_usuarios()[0]
        nuevo_nombre = f"testuser_{os.getpid()}"
        uid = crear_usuario(nuevo_nombre, "Usuario Prueba", "clave123", "ventas", creador=admin_user)
        self.assertGreater(uid, 0)
        with self.assertRaises(ValidationError):
            crear_usuario(nuevo_nombre, "Dup", "clave123", "ventas", creador=admin_user)


class TestGuiasService(unittest.TestCase):
    @classmethod
    def _user(cls, usuario: str) -> dict:
        with db_connection() as conn:
            return dict(conn.execute("SELECT * FROM usuarios WHERE usuario=?", (usuario,)).fetchone())

    def test_siguiente_consecutivo(self):
        c = siguiente_consecutivo()
        self.assertIsInstance(c, int)
        self.assertGreater(c, 0)

    def test_crear_guia_solo_ventas(self):
        admin = self._user("admin")
        with self.assertRaises(ForbiddenError):
            crear_guia(admin, {"cliente": "X", "ciudad": "Y"})
        ventas = self._user("ventas")
        gid, consec = crear_guia(
            ventas,
            {
                "cliente": "Farmacia Prueba",
                "ciudad": "Cali",
                "direccion": "Calle 1 # 2-3",
                "documentos": "Factura 001",
                "obs_ventas": "Frágil",
                "transportador_nombre": "Carlos",
                "transportador_placa": "ABC123",
                "cajas": "2",
                "bolsas": "3",
                "totales": "5",
            },
            dispositivo="test",
            ip="127.0.0.1",
        )
        self.assertGreater(gid, 0)
        g = obtener_guia(gid)
        self.assertEqual(g["cliente"], "Farmacia Prueba")
        self.assertEqual(g["estado"], "CREADA")
        pre = obtener_prellenado_ventas(gid)
        self.assertEqual(pre["transportador_nombre"], "Carlos")
        self.assertEqual(pre["cajas"], 2)
        self.assertEqual(pre["totales"], 5)
        codigo = generar_codigo_verificacion(g)
        self.assertTrue(codigo.startswith("CD-"))
        return gid, ventas

    def test_crear_guia_envio_directo(self):
        ventas = self._user("ventas")
        gid, _ = crear_guia(
            ventas,
            {
                "cliente": "Farmacia Directa",
                "ciudad": "Medellín",
                "envio_directo_cedis": "si",
            },
            dispositivo="test",
            ip="127.0.0.1",
        )
        g = obtener_guia(gid)
        self.assertEqual(g["estado"], "EN_CEDIS")
        self.assertEqual(g["envio_directo_cedis"], 1)
        eventos = listar_eventos(gid)
        tipos = [e["tipo"] for e in eventos]
        self.assertIn("envio_directo_cedis", tipos)

    def test_buscar_y_contar_guias(self):
        ventas = self._user("ventas")
        crear_guia(
            ventas,
            {"cliente": "Busqueda Test", "ciudad": "Cartagena"},
            dispositivo="test",
        )
        todas = buscar_guias(limite=50)
        self.assertGreaterEqual(len(todas), 1)
        solo_creadas = buscar_guias(estado="CREADA", limite=50)
        self.assertGreaterEqual(len(solo_creadas), 1)
        self.assertTrue(all(g["estado"] == "CREADA" for g in solo_creadas))
        por_estado = contar_por_estado()
        estados = {r["estado"] for r in por_estado}
        self.assertIn("CREADA", estados)

    def test_validar_transicion_permisos_y_estados(self):
        ventas = self._user("ventas")
        gid, _ = crear_guia(
            ventas,
            {"cliente": "Guía Transición", "ciudad": "Bogotá"},
            dispositivo="test",
        )
        cedis = self._user("cedis")
        with self.assertRaises(ForbiddenError):
            validar_transicion(gid, "recepcion_admin", cedis)
        with self.assertRaises(EstadoInvalidoError):
            validar_transicion(gid, "entrega_transporte", cedis)
        administrativo = self._user("administrativo")
        with self.assertRaises(GuiaNoExisteError):
            validar_transicion(999999, "recepcion_admin", administrativo)

    def test_flujo_completo_normal(self):
        ventas = self._user("ventas")
        gid, _ = crear_guia(
            ventas,
            {
                "cliente": "Flujo Completo",
                "ciudad": "Barranquilla",
                "transportador_nombre": "Luis T.",
                "transportador_cc": "12345",
                "transportador_tel": "3001234567",
                "transportador_vehiculo": "Camioneta",
                "transportador_placa": "XYZ987",
                "transportador_flete": "$50000",
                "cliente_recibe_nombre": "Ana María",
                "cajas": "1",
                "totales": "1",
            },
            dispositivo="test",
            ip="10.0.0.1",
        )
        firma = _firma_dataurl()
        admin = self._user("administrativo")
        procesar_evento(
            gid, "recepcion_admin", admin,
            {"recibe": "Pedro Bodega", "firma": firma},
            dispositivo="pc", ip="10.0.0.2",
        )
        self.assertEqual(obtener_guia(gid)["estado"], "RECIBIDA_ADMIN")

        cedis = self._user("cedis")
        procesar_evento(
            gid, "control_cedis", cedis,
            {
                "firma": firma,
                "cajas": "1", "bolsas": "0", "cayvas": "0", "sobres": "0", "totales": "1",
                "vehiculo_cumple": "si",
            },
            dispositivo="cel", ip="10.0.0.3",
        )
        self.assertEqual(obtener_guia(gid)["estado"], "EN_CEDIS")

        procesar_evento(
            gid, "entrega_transporte", cedis,
            {"firma": firma, "nombre": "Luis T."},
            ip="10.0.0.4",
        )
        self.assertEqual(obtener_guia(gid)["estado"], "EN_RUTA")

        foto = _firma_dataurl()
        procesar_evento(
            gid, "entrega_cliente", cedis,
            {"recibe": "Ana María", "firma": firma, "foto": foto, "obs": "Entregado correctamente"},
            ip="10.0.0.5",
        )
        self.assertEqual(obtener_guia(gid)["estado"], "ENTREGADA")

        eventos = listar_eventos(gid)
        self.assertEqual(len(eventos), 5)
        tipos = [e["tipo"] for e in eventos]
        self.assertEqual(
            tipos,
            ["creacion", "recepcion_admin", "control_cedis", "entrega_transporte", "entrega_cliente"],
        )
        ev_entrega = obtener_evento_por_tipo(gid, "entrega_cliente")
        self.assertIn("firma_archivo", ev_entrega["datos"])
        self.assertIn("foto_archivo", ev_entrega["datos"])
        return gid, cedis

    def test_anular_guia_solo_admin(self):
        ventas = self._user("ventas")
        gid, _ = crear_guia(
            ventas,
            {"cliente": "Anular", "ciudad": "Cali"},
            dispositivo="test",
        )
        cedis = self._user("cedis")
        with self.assertRaises(ForbiddenError):
            procesar_evento(gid, "anular", cedis, {"motivo": "x"})
        admin = self._user("admin")
        procesar_evento(gid, "anular", admin, {"motivo": "Cliente canceló"})
        g = obtener_guia(gid)
        self.assertEqual(g["estado"], "ANULADA")
        self.assertEqual(g["anulada_motivo"], "Cliente canceló")
        self.assertIsNotNone(g["anulada_por"])

    def test_editar_guia_ventas(self):
        ventas = self._user("ventas")
        gid, _ = crear_guia(
            ventas,
            {"cliente": "EditMe", "ciudad": "Bogotá", "obs_ventas": "Original"},
            dispositivo="test",
        )
        ev_id, diff = editar_guia(
            gid, ventas,
            {"cliente": "Editado Cliente", "obs_ventas": "Modificado", "cajas": "5"},
            dispositivo="test",
        )
        self.assertGreater(ev_id, 0)
        self.assertIn("cliente", diff)
        self.assertEqual(diff["cliente"]["anterior"], "EditMe")
        self.assertEqual(diff["cliente"]["nuevo"], "Editado Cliente")
        self.assertIn("obs_ventas", diff)
        g = obtener_guia(gid)
        self.assertEqual(g["cliente"], "Editado Cliente")
        self.assertEqual(g["obs_ventas"], "Modificado")
        ev = obtener_evento_por_tipo(gid, "edicion_guia")
        self.assertIsNotNone(ev)
        self.assertIn("campos_modificados", ev["datos"])

    def test_validar_datos_evento_errores(self):
        with self.assertRaises(ValidationError):
            validar_datos_evento("recepcion_admin", {})
        with self.assertRaises(ValidationError):
            validar_datos_evento("entrega_cliente", {"recibe": "Juan"})
        with self.assertRaises(ValidationError):
            validar_datos_evento("anular", {})
        ok = validar_datos_evento(
            "entrega_transporte",
            {"firma": _firma_dataurl(), "nombre": "Transportador"},
            prellenado={"transportador_cc": "999"},
        )
        self.assertEqual(ok["cc"], "999")


class TestEventosService(unittest.TestCase):
    def test_agregar_y_listar_evento(self):
        with db_connection() as conn:
            v = conn.execute("SELECT * FROM usuarios WHERE usuario='cedis'").fetchone()
            u = dict(v)
            g = conn.execute("SELECT id FROM guias ORDER BY id DESC LIMIT 1").fetchone()
        if g is None:
            ventas = dict(db_connection().execute("SELECT * FROM usuarios WHERE usuario='ventas'").fetchone())
            gid, _ = crear_guia(ventas, {"cliente": "E", "ciudad": "C"}, dispositivo="t")
        else:
            gid = g["id"]
        ev_id = agregar_evento(gid, "control_cedis", u, {"nota": "prueba"}, dispositivo="t", ip="1.1.1.1")
        self.assertGreater(ev_id, 0)
        evs = listar_eventos(gid)
        self.assertGreaterEqual(len(evs), 1)
        self.assertEqual(evs[-1]["usuario"], "cedis")
        self.assertEqual(evs[-1]["rol"], "cedis")
        self.assertEqual(evs[-1]["ip"], "1.1.1.1")
        self.assertIsInstance(evs[-1]["datos"], dict)


class TestAuditoria(unittest.TestCase):
    def test_eventos_tienen_usuario_rol_fecha(self):
        with db_connection() as conn:
            filas = conn.execute(
                "SELECT tipo, usuario, rol, en, ip FROM eventos ORDER BY id DESC LIMIT 20"
            ).fetchall()
        self.assertGreaterEqual(len(filas), 1)
        for r in filas:
            self.assertIsNotNone(r["tipo"])
            self.assertIsNotNone(r["en"])
            self.assertIn(r["rol"], {"ventas", "administrativo", "cedis", "admin"})


def _suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [
        TestCoreUtils,
        TestCoreSecurity,
        TestValidators,
        TestAuthService,
        TestGuiasService,
        TestEventosService,
        TestAuditoria,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    return suite


if __name__ == "__main__":
    print("=" * 62)
    print("  Suite de pruebas · Guías Coodescor")
    print(f"  BD temporal: {_TEMP_DB}")
    print("=" * 62)
    try:
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        result = runner.run(_suite())
    finally:
        try:
            shutil.rmtree(_TEMP_DIR, ignore_errors=True)
        except Exception:
            pass
    sys.exit(0 if result.wasSuccessful() else 1)
