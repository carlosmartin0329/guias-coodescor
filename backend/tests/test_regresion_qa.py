#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas de regresión del control de calidad.

Cubren los defectos corregidos durante la QA integral (ver docs/QA-INFORME.md):
creación de guía con NIT formateado, bultos en cero, anulación de estados
terminales, cierre directo, tokens, CAPTCHA, configuración, CSV, respaldos,
sesión y actualización de bases de datos antiguas.

Uso:
    py -3 -m pytest tests/test_regresion_qa.py -v
"""
import base64
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_ROOT)
for _p in (_BACKEND, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import guias_coodescor.config as _cfg

_TEMP_DIR = ""
_DATA = ""

FIRMA = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "+P+/HgAFhAJ/wlseKgAAAABJRU5ErkJggg=="
)


def setup_module(module):
    global _TEMP_DIR, _DATA
    _TEMP_DIR = tempfile.mkdtemp(prefix="coodescor_regresion_")
    _DATA = os.path.join(_TEMP_DIR, "data")
    for sub in ("", "adjuntos", "respaldos"):
        os.makedirs(os.path.join(_DATA, sub), exist_ok=True)
    _cfg.DATA_DIR = _DATA
    _cfg.ADJUNTOS_DIR = os.path.join(_DATA, "adjuntos")
    _cfg.BACKUP_DIR = os.path.join(_DATA, "respaldos")
    _cfg.DB_PATH = os.path.join(_DATA, "guias.db")
    _cfg.RECEPTORES_DB_PATH = os.path.join(_DATA, "receptores.db")
    _cfg.LOG_DIR = _DATA
    _cfg.LOG_FILE = os.path.join(_DATA, "test.log")
    from guias_coodescor.database.models import init_db
    init_db()


def teardown_module(module):
    shutil.rmtree(_TEMP_DIR, ignore_errors=True)


def _usuario(nombre):
    from guias_coodescor.database.connection import db_connection
    with db_connection() as conn:
        fila = conn.execute(
            "SELECT * FROM usuarios WHERE usuario = ? COLLATE NOCASE", (nombre,)
        ).fetchone()
    return dict(fila)


def _crear_guia(user, **extra):
    from guias_coodescor.services.guias_service import crear_guia
    datos = {
        "cliente": "Cliente Regresión",
        "ciudad": "Bogotá",
        "direccion": "Calle 1 # 2-3",
        "documentos": "FV 001",
    }
    datos.update(extra)
    gid, _cons = crear_guia(user, datos, dispositivo="test", ip="127.0.0.1")
    return gid


class TestCreacionGuia(unittest.TestCase):
    def test_nit_formateado_no_rompe_la_fk(self):
        """Un NIT como '900123456-1' debe guardarse normalizado y crear la guía."""
        from guias_coodescor.services.guias_service import obtener_guia
        ventas = _usuario("ventas")
        gid = _crear_guia(ventas, nit="900123456-1")
        guia = obtener_guia(gid)
        self.assertEqual(guia["nit"], "9001234561")
        self.assertEqual(guia["estado"], "CREADA")

    def test_consecutivo_se_resincroniza_si_el_config_queda_atrasado(self):
        """Si config.siguiente apunta a un valor usado, la creación se recupera."""
        from guias_coodescor.database.connection import db_connection
        from guias_coodescor.services.guias_service import crear_guia
        ventas = _usuario("ventas")
        gid1 = _crear_guia(ventas, cliente="Consecutivo 1")
        with db_connection() as conn:
            usados = conn.execute("SELECT MAX(consecutivo) AS m FROM guias").fetchone()["m"]
        # Simular panel admin con un consecutivo ya usado / no numérico.
        with db_connection(commit=True) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO config(clave, valor) VALUES ('siguiente', ?)",
                (str(usados),),
            )
        gid2, consecutivo = crear_guia(
            ventas, {"cliente": "Consecutivo 2", "ciudad": "Cali"}, ip="127.0.0.1"
        )
        self.assertGreater(consecutivo, usados)
        self.assertNotEqual(gid1, gid2)


class TestEventos(unittest.TestCase):
    def _hasta_cedis(self, **extra):
        from guias_coodescor.services.guias_service import procesar_evento
        ventas, admin, cedis = _usuario("ventas"), _usuario("administrativo"), _usuario("cedis")
        gid = _crear_guia(ventas, **extra)
        procesar_evento(gid, "recepcion_admin", admin, {"recibe": "Bodega", "firma": FIRMA})
        procesar_evento(
            gid, "control_cedis", cedis,
            {"firma": FIRMA, "cajas": 0, "bolsas": 0, "cayvas": 0, "sobres": 0,
             "cedis_funcionario": "FUNCIONARIO QA"},
        )
        return gid, cedis, admin

    def test_control_cedis_respeta_ceros_explicitos(self):
        """CEDIS puede corregir a 0 sin que se reimponga el prellenado de Ventas."""
        from guias_coodescor.services.eventos_service import obtener_evento_por_tipo
        gid, _cedis, _admin = self._hacia_cedis()
        evento = obtener_evento_por_tipo(gid, "control_cedis")
        self.assertEqual(evento["datos"]["cajas"], 0)
        self.assertEqual(evento["datos"]["totales"], 0)

    def _hacia_cedis(self):
        from guias_coodescor.services.guias_service import procesar_evento
        ventas, admin, cedis = _usuario("ventas"), _usuario("administrativo"), _usuario("cedis")
        gid = _crear_guia(ventas, cajas=5, bolsas=1)
        procesar_evento(gid, "recepcion_admin", admin, {"recibe": "Bodega", "firma": FIRMA})
        procesar_evento(
            gid, "control_cedis", cedis,
            {"firma": FIRMA, "cajas": 0, "bolsas": 0, "cayvas": 0, "sobres": 0,
             "cedis_funcionario": "FUNCIONARIO QA"},
        )
        return gid, cedis, admin

    def test_anular_guia_entregada_o_anulada_se_rechaza(self):
        from guias_coodescor.services.guias_service import EstadoInvalidoError, procesar_evento
        admin = _usuario("admin")
        gid = _crear_guia(_usuario("ventas"))
        procesar_evento(gid, "anular", admin, {"motivo": "primera"})
        with self.assertRaises(EstadoInvalidoError):
            procesar_evento(gid, "anular", admin, {"motivo": "segunda"})

    def test_entrega_cliente_no_salta_el_transporte_en_flujo_normal(self):
        from guias_coodescor.services.guias_service import EstadoInvalidoError, procesar_evento
        gid, cedis, _admin = self._hacia_cedis()
        with self.assertRaises(EstadoInvalidoError):
            procesar_evento(gid, "entrega_cliente", cedis, {"recibe": "Cliente", "firma": FIRMA})

    def test_control_cedis_exige_funcionario(self):
        from guias_coodescor.core.validators import ValidationError
        from guias_coodescor.services.guias_service import procesar_evento
        ventas, admin, cedis = _usuario("ventas"), _usuario("administrativo"), _usuario("cedis")
        gid = _crear_guia(ventas)
        procesar_evento(gid, "recepcion_admin", admin, {"recibe": "Bodega", "firma": FIRMA})
        with self.assertRaises(ValidationError):
            procesar_evento(gid, "control_cedis", cedis, {"firma": FIRMA, "cajas": 0})


class TestFlujoDirectoRecogidaEnSede(unittest.TestCase):
    """Ventas → CEDIS → cliente recoge en sede (envío directo, sin transportador)."""

    def _crear_directo(self):
        return _crear_guia(_usuario("ventas"), cliente="Cliente Recoge en Sede",
                           envio_directo_cedis=True)

    def _controlar(self, gid):
        from guias_coodescor.services.guias_service import procesar_evento
        procesar_evento(
            gid, "control_cedis", _usuario("cedis"),
            {"firma": FIRMA, "cajas": 1, "bolsas": 2, "cayvas": 0, "sobres": 0,
             "cedis_funcionario": "FUNCIONARIO QA"},
        )

    def test_envio_directo_se_crea_con_estado_inicial_en_cedis(self):
        """Ventas crea la guía; con envío directo el ESTADO INICIAL es EN_CEDIS.

        La guía siempre la crea el rol Ventas (el admin no puede crear guías).
        Lo que cambia el envío directo es el estado inicial, para saltar la
        recepción administrativa.
        """
        from guias_coodescor.services.guias_service import obtener_guia
        gid = self._crear_directo()
        self.assertEqual(obtener_guia(gid)["estado"], "EN_CEDIS")
        self.assertTrue(obtener_guia(gid)["envio_directo_cedis"])

    def test_admin_no_puede_crear_guias(self):
        """La creación está reservada al rol Ventas (regla vigente del sistema)."""
        from guias_coodescor.services.auth_service import ForbiddenError
        from guias_coodescor.services.guias_service import crear_guia
        with self.assertRaises(ForbiddenError):
            crear_guia(
                _usuario("admin"),
                {"cliente": "Intento admin", "ciudad": "Bogotá"},
                ip="127.0.0.1",
            )

    def test_no_cierra_sin_control_cedis(self):
        from guias_coodescor.services.guias_service import (
            EstadoInvalidoError, procesar_evento,
        )
        gid = self._crear_directo()
        with self.assertRaises(EstadoInvalidoError):
            procesar_evento(
                gid, "entrega_cliente", _usuario("cedis"),
                {"recibe": "Cliente Sede", "firma": FIRMA},
            )

    def test_cierra_directamente_tras_control_sin_evento_de_transporte(self):
        from guias_coodescor.services.eventos_service import listar_eventos
        from guias_coodescor.services.guias_service import obtener_guia, procesar_evento
        gid = self._crear_directo()
        self._controlar(gid)
        procesar_evento(
            gid, "entrega_cliente", _usuario("cedis"),
            {"recibe": "Cliente Sede", "firma": FIRMA, "obs": "Recogió en CEDIS"},
        )
        self.assertEqual(obtener_guia(gid)["estado"], "ENTREGADA")
        tipos = [e["tipo"] for e in listar_eventos(gid)]
        self.assertIn("control_cedis", tipos)
        self.assertIn("entrega_cliente", tipos)
        self.assertNotIn("entrega_transporte", tipos)

    def test_link_publico_directo_solo_tras_control_y_uso_unico(self):
        from guias_coodescor.services.guias_service import (
            cerrar_entrega_por_token_publico, obtener_guia,
        )
        from guias_coodescor.services.tokens_service import (
            estado_activacion_link, generar_token_entrega, obtener_por_token,
        )
        admin = _usuario("admin")
        gid = self._crear_directo()
        token = generar_token_entrega(gid, admin)
        # Antes del control el link no está activo (no se entrega sin verificar bultos).
        self.assertFalse(estado_activacion_link(gid)["activo"])
        self._controlar(gid)
        self.assertTrue(estado_activacion_link(gid)["activo"])
        info = obtener_por_token(token)
        cerrar_entrega_por_token_publico(
            info, {"recibe": "Cliente Sede", "firma": FIRMA}, ip="127.0.0.1"
        )
        self.assertEqual(obtener_guia(gid)["estado"], "ENTREGADA")
        # Un segundo intento no puede volver a cerrar.
        from guias_coodescor.core.validators import ValidationError
        with self.assertRaises(ValidationError):
            cerrar_entrega_por_token_publico(
                obtener_por_token(token) or info,
                {"recibe": "Otro", "firma": FIRMA}, ip="127.0.0.1",
            )

    def test_proceso_unificado_cedis_modo_directo(self):
        """El botón real de la UI: control + entrega al cliente en un solo paso."""
        from guias_coodescor.services.guias_service import (
            obtener_guia, proceso_unificado_cedis,
        )
        gid = self._crear_directo()
        ok, msg, info = proceso_unificado_cedis(
            guia_id=gid,
            user=_usuario("cedis"),
            datos={
                "firma_cedis_entrega": FIRMA,
                "cajas": 1, "bolsas": 2, "cayvas": 0, "sobres": 0,
                "cedis_funcionario": "FUNCIONARIO QA",
                "recibe": "Cliente Sede",
                "firma_recibe": FIRMA,
            },
        )
        self.assertTrue(ok, msg)
        self.assertEqual(info.get("estado"), "ENTREGADA")
        self.assertEqual(obtener_guia(gid)["estado"], "ENTREGADA")


class TestTransportador(unittest.TestCase):
    def test_transportador_no_puede_operar_guia_ajena(self):
        from guias_coodescor.services.auth_service import ForbiddenError
        from guias_coodescor.services.guias_service import (
            asignar_tipo_transportador, procesar_evento, validar_transicion,
        )
        ventas, admin, cedis = _usuario("ventas"), _usuario("administrativo"), _usuario("cedis")
        t1, t2 = _usuario("transportador"), _usuario("transportador2")
        gid = _crear_guia(ventas)
        procesar_evento(gid, "recepcion_admin", admin, {"recibe": "Bodega", "firma": FIRMA})
        asignar_tipo_transportador(gid, admin, "propio", t1["id"])
        procesar_evento(
            gid, "control_cedis", cedis,
            {"firma": FIRMA, "cajas": 1, "bolsas": 0, "cayvas": 0, "sobres": 0,
             "cedis_funcionario": "FUNCIONARIO QA"},
        )
        procesar_evento(gid, "entrega_transporte", cedis, {"firma": FIRMA, "nombre": "T1"})
        with self.assertRaises(ForbiddenError):
            validar_transicion(gid, "entrega_cliente", t2)
        # El asignado sí puede consultar su transición.
        self.assertEqual(validar_transicion(gid, "entrega_cliente", t1)["id"], gid)


class TestPracticanteCedis(unittest.TestCase):
    """El funcionario CEDIS puede ser PRACTICANTE_PASANTE: exige nombre y firma."""

    def _guia_recibida(self):
        from guias_coodescor.services.guias_service import procesar_evento
        gid = _crear_guia(_usuario("ventas"), cliente="Cliente Practicante CEDIS")
        procesar_evento(
            gid, "recepcion_admin", _usuario("administrativo"),
            {"recibe": "Bodega", "firma": FIRMA},
        )
        return gid

    def _control(self, gid, **extra):
        from guias_coodescor.services.guias_service import procesar_evento
        datos = {
            "firma": FIRMA,
            "cajas": 1, "bolsas": 0, "cayvas": 0, "sobres": 0,
            "vehiculo_cumple": "si",
            "cedis_funcionario": "PRACTICANTE_PASANTE",
        }
        datos.update(extra)
        return procesar_evento(gid, "control_cedis", _usuario("cedis"), datos)

    def test_practicante_requiere_nombre(self):
        from guias_coodescor.core.validators import ValidationError
        gid = self._guia_recibida()
        with self.assertRaises(ValidationError):
            self._control(gid, firma_practicante=FIRMA)

    def test_practicante_requiere_firma(self):
        from guias_coodescor.core.validators import ValidationError
        gid = self._guia_recibida()
        with self.assertRaises(ValidationError):
            self._control(gid, cedis_funcionario_practicante="Juan Pasante")

    def test_practicante_guarda_nombre_y_firma_en_el_evento(self):
        from guias_coodescor.services.eventos_service import obtener_evento_por_tipo
        gid = self._guia_recibida()
        self._control(
            gid,
            cedis_funcionario_practicante="Juan Pasante",
            firma_practicante=FIRMA,
        )
        datos = obtener_evento_por_tipo(gid, "control_cedis")["datos"]
        self.assertEqual(datos["cedis_funcionario"], "PRACTICANTE_PASANTE")
        self.assertEqual(datos["cedis_funcionario_practicante"], "Juan Pasante")
        self.assertIn("firma_practicante_archivo", datos)
        archivo = os.path.join(_DATA, datos["firma_practicante_archivo"])
        self.assertTrue(os.path.isfile(archivo), f"no se guardó la firma: {archivo}")

    def test_funcionario_normal_no_exige_firma_de_practicante(self):
        from guias_coodescor.services.eventos_service import obtener_evento_por_tipo
        gid = self._guia_recibida()
        self._control(gid, cedis_funcionario="Aldair Hoyos")
        datos = obtener_evento_por_tipo(gid, "control_cedis")["datos"]
        self.assertNotIn("firma_practicante_archivo", datos)

    def test_unificado_directo_con_practicante(self):
        from guias_coodescor.services.eventos_service import obtener_evento_por_tipo
        from guias_coodescor.services.guias_service import (
            obtener_guia, proceso_unificado_cedis,
        )
        gid = _crear_guia(
            _usuario("ventas"), cliente="Cliente Practicante Directo",
            envio_directo_cedis=True,
        )
        ok, msg, info = proceso_unificado_cedis(
            guia_id=gid,
            user=_usuario("cedis"),
            datos={
                "firma_cedis_entrega": FIRMA,
                "cajas": 1, "bolsas": 0, "cayvas": 0, "sobres": 0,
                "cedis_funcionario": "PRACTICANTE_PASANTE",
                "cedis_funcionario_practicante": "María Pasante",
                "firma_practicante": FIRMA,
                "recibe": "Cliente Sede",
                "firma_recibe": FIRMA,
            },
        )
        self.assertTrue(ok, msg)
        self.assertEqual(info.get("estado"), "ENTREGADA")
        datos = obtener_evento_por_tipo(gid, "control_cedis")["datos"]
        self.assertEqual(datos["cedis_funcionario_practicante"], "María Pasante")
        self.assertIn("firma_practicante_archivo", datos)
        self.assertEqual(obtener_guia(gid)["estado"], "ENTREGADA")


class TestTokensYCaptcha(unittest.TestCase):
    def test_token_captcha_no_contiene_la_respuesta(self):
        from guias_coodescor.services.captcha_service import generar_captcha, validar_captcha
        desafio, _svg, token = generar_captcha(ip="127.0.0.1", ua="test")
        payload = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode()
        self.assertNotIn(desafio, payload, "la respuesta no debe viajar en el token")
        ok, _msg = validar_captcha(token, desafio, ip="127.0.0.1", ua="test")
        self.assertTrue(ok)

    def test_captcha_con_respuesta_no_ascii_no_revienta(self):
        from guias_coodescor.services.captcha_service import generar_captcha, validar_captcha
        _d, _s, token = generar_captcha(ip="127.0.0.1", ua="test")
        ok, msg = validar_captcha(token, "ÁÉÍÓÚ", ip="127.0.0.1", ua="test")
        self.assertFalse(ok)
        self.assertIn("incorrecto", msg.lower())

    def test_expiracion_token_mismo_formato_que_la_bd(self):
        from guias_coodescor.services.tokens_service import _fecha_expiracion
        from guias_coodescor.core.utils import fecha_pasada
        expira = _fecha_expiracion()
        self.assertNotIn("T", expira, "la fecha debe usar el formato 'YYYY-MM-DD HH:MM:SS'")
        self.assertFalse(fecha_pasada(expira))

    def test_token_de_guia_cerrada_se_rechaza(self):
        from guias_coodescor.services.guias_service import procesar_evento
        from guias_coodescor.services.tokens_service import generar_token_entrega
        admin = _usuario("admin")
        gid = _crear_guia(_usuario("ventas"))
        procesar_evento(gid, "anular", admin, {"motivo": "cierre"})
        with self.assertRaises(ValueError):
            generar_token_entrega(gid, admin)


class TestConfiguracionYSesion(unittest.TestCase):
    def test_config_guarda_todas_las_claves_documentadas(self):
        from guias_coodescor.database.models import get_config
        from guias_coodescor.services.auth_service import actualizar_configuracion
        admin = _usuario("admin")
        actualizar_configuracion(
            {
                "empresa": "Coodescor QA",
                "lista_clientes_json": json.dumps([{"nit": "900"}]),
                "vinculo_db_externo_tipo": "ninguno",
                "vinculo_db_externo_url": "https://ejemplo",
            },
            admin,
        )
        self.assertEqual(get_config("empresa"), "Coodescor QA")
        self.assertEqual(json.loads(get_config("lista_clientes_json")), [{"nit": "900"}])
        self.assertEqual(get_config("vinculo_db_externo_url"), "https://ejemplo")

    def test_config_rechaza_consecutivo_invalido_o_usado(self):
        from guias_coodescor.core.validators import ValidationError
        from guias_coodescor.services.auth_service import actualizar_configuracion
        admin = _usuario("admin")
        with self.assertRaises(ValidationError):
            actualizar_configuracion({"siguiente": "abc"}, admin)
        with self.assertRaises(ValidationError):
            actualizar_configuracion({"siguiente": "1"}, admin)

    def test_sesion_no_expone_hash_ni_sal(self):
        from guias_coodescor.core.security import validar_sesion
        from guias_coodescor.services.auth_service import login
        sid, _cookie, _datos = login("admin", "admin123", ip="127.0.0.1", user_agent="test")
        usuario = validar_sesion(sid)
        self.assertIsNotNone(usuario)
        self.assertNotIn("pass_hash", usuario)
        self.assertNotIn("sal", usuario)
        self.assertEqual(usuario["rol"], "admin")


class TestExportYRespaldos(unittest.TestCase):
    def test_csv_neutraliza_formulas(self):
        from guias_coodescor.services.export_service import exportar_guias_csv
        ventas = _usuario("ventas")
        _crear_guia(ventas, cliente="=cmd|' /C calc'!A0")
        data, _nombre = exportar_guias_csv()
        texto = data.decode("utf-8-sig")
        self.assertIn("'=cmd", texto)
        self.assertNotIn(";=cmd", texto)

    def test_no_se_restaura_un_respaldo_de_receptores(self):
        from guias_coodescor.services.db_admin_service import (
            RespaldoNoValido, restaurar_respaldo,
        )
        from guias_coodescor.services.db_admin_service import _directorio_respaldos
        admin = _usuario("admin")
        directorio = _directorio_respaldos("guias")
        archivo = os.path.join(directorio, "receptores_falso_qa.db")
        conn = sqlite3.connect(archivo)
        conn.execute("CREATE TABLE receptores (id INTEGER)")
        conn.commit()
        conn.close()
        try:
            with self.assertRaises(RespaldoNoValido):
                restaurar_respaldo(os.path.basename(archivo), admin, "127.0.0.1")
        finally:
            try:
                os.remove(archivo)
            except OSError:
                pass


class TestActualizacionBD(unittest.TestCase):
    def test_bd_sin_columnas_nuevas_se_completa_sin_perder_datos(self):
        """Simula una instalación anterior (sin metadata/cliente_descubierto y
        sin índices) y comprueba que init_db la actualiza conservando los datos."""
        global _DATA
        from guias_coodescor.database.models import SCHEMA_SQL, init_db
        temp = tempfile.mkdtemp(prefix="coodescor_upgrade_")
        try:
            db = os.path.join(temp, "guias.db")
            conn = sqlite3.connect(db)
            conn.executescript(SCHEMA_SQL)
            # Reconstruir clientes SIN las columnas nuevas (como una BD vieja).
            conn.executescript(
                """
                PRAGMA foreign_keys=OFF;
                CREATE TABLE clientes_vieja (
                    nit TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
                    razon_social TEXT NOT NULL,
                    direccion TEXT, ciudad TEXT, telefono TEXT, email TEXT,
                    creado_en TEXT NOT NULL, actualizado_en TEXT NOT NULL
                );
                INSERT INTO clientes_vieja (nit, razon_social, creado_en, actualizado_en)
                    SELECT nit, razon_social, creado_en, actualizado_en FROM clientes;
                DROP TABLE clientes;
                ALTER TABLE clientes_vieja RENAME TO clientes;
                """
            )
            conn.execute(
                "INSERT INTO guias(consecutivo, cliente, creada_en, estado) VALUES (100, 'Cliente antiguo', '2026-01-01 10:00:00', 'CREADA')"
            )
            conn.commit()
            guia_id = conn.execute("SELECT id FROM guias").fetchone()[0]
            conn.execute(
                "INSERT INTO eventos(guia_id, tipo, en, datos) VALUES (?, 'creacion', '2026-01-01 10:00:00', '{}')",
                (guia_id,),
            )
            conn.execute("DELETE FROM schema_migrations")
            conn.execute("DROP INDEX IF EXISTS idx_guias_estado")
            conn.commit()
            conn.close()

            original = (_cfg.DB_PATH, _cfg.RECEPTORES_DB_PATH, _cfg.DATA_DIR,
                        _cfg.ADJUNTOS_DIR, _cfg.BACKUP_DIR, _cfg.LOG_DIR, _cfg.LOG_FILE)
            try:
                _cfg.DB_PATH = db
                _cfg.RECEPTORES_DB_PATH = os.path.join(temp, "receptores.db")
                _cfg.DATA_DIR = temp
                _cfg.ADJUNTOS_DIR = os.path.join(temp, "adjuntos")
                _cfg.BACKUP_DIR = os.path.join(temp, "respaldos")
                _cfg.LOG_DIR = temp
                _cfg.LOG_FILE = os.path.join(temp, "test.log")
                init_db()
                conn = sqlite3.connect(db)
                columnas = {r[1] for r in conn.execute("PRAGMA table_info(clientes)")}
                self.assertIn("metadata", columnas)
                self.assertIn("cliente_descubierto", columnas)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM eventos").fetchone()[0], 1)
                self.assertEqual(
                    conn.execute("SELECT cliente FROM guias WHERE id = ?", (guia_id,)).fetchone()[0],
                    "Cliente antiguo",
                )
                indices = {r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )}
                self.assertIn("idx_guias_estado", indices)
                conn.close()
            finally:
                (_cfg.DB_PATH, _cfg.RECEPTORES_DB_PATH, _cfg.DATA_DIR,
                 _cfg.ADJUNTOS_DIR, _cfg.BACKUP_DIR, _cfg.LOG_DIR, _cfg.LOG_FILE) = original
        finally:
            shutil.rmtree(temp, ignore_errors=True)


class TestConfiguracionEntorno(unittest.TestCase):
    def test_settings_lee_variables_con_prefijo_coodescor(self):
        from guias_coodescor.core.settings import Settings
        os.environ["COODESCOR_PORT"] = "9999"
        os.environ["COODESCOR_ENVIRONMENT"] = "staging"
        try:
            s = Settings()
            self.assertEqual(s.port, 9999)
            self.assertEqual(s.environment, "staging")
        finally:
            os.environ.pop("COODESCOR_PORT", None)
            os.environ.pop("COODESCOR_ENVIRONMENT", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
