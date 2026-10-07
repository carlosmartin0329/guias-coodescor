#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas del contrato REST de /api/guias.

Comprueban que el backend expone todo lo que un frontend necesita sin depender
del HTML: listar, conteo, estados, detalle con eventos, transiciones, ediciÃ³n y
ejecuciÃ³n de un paso del proceso.
"""
import sys
import unittest

sys.path.insert(0, ".")

from guias_coodescor.api import routes_guias_api as api
from guias_coodescor.core.validators import ValidationError
from guias_coodescor.services import guias_service as g
from guias_coodescor.services.auth_service import AuthError, ForbiddenError

ADMIN = {"id": 1, "usuario": "admin", "rol": "admin", "nombre": "Admin"}
# crear_guia() exige rol ventas; los datos se crean con un usuario de ventas
# para no saltarse la regla de permisos del servicio.
VENTAS_ADMIN = {"id": 3, "usuario": "vtest", "rol": "ventas", "nombre": "Ventas Test"}
VENTAS = {"id": 2, "usuario": "ventas", "rol": "ventas", "nombre": "Ventas"}


class RespuestaFalsa:
    """Sustituto de self._json del router: guarda lo que se devuelve."""

    def __init__(self):
        self.datos = None
        self.codigo = 200

    def __call__(self, payload, codigo=200):
        self.datos = payload
        self.codigo = codigo
        return payload


def pedir_json(fn, *args, **kwargs):
    """Ejecuta un handler y devuelve (payload, codigo).

    json_fn se pasa por nombre porque no todos los handlers lo reciben en la
    misma posición: en unos va al final y en otros en medio.
    """
    r = RespuestaFalsa()
    kwargs["json_fn"] = r
    return fn(*args, **kwargs), r.codigo


class TestNormalizacion(unittest.TestCase):
    def test_entero_tolera_vacios_y_basura(self):
        self.assertIsNone(api._entero(""))
        self.assertIsNone(api._entero(None))
        self.assertIsNone(api._entero("abc"))
        self.assertEqual(api._entero("7"), 7)

    def test_limite_acotado(self):
        self.assertEqual(api._limite("10", 200, 500), 10)
        self.assertEqual(api._limite("9999", 200, 500), 500)
        self.assertEqual(api._limite("0", 200, 500), 1)
        self.assertEqual(api._limite("", 200, 500), 200)
        self.assertEqual(api._limite("basura", 200, 500), 200)


class TestListadoYConteo(unittest.TestCase):
    def test_listar_devuelve_guias_y_conteo(self):
        datos, codigo = pedir_json(
            api.listar_guias_api, {"q": [""]}, ADMIN
        )
        self.assertEqual(codigo, 200)
        self.assertTrue(datos["ok"])
        self.assertIn("guias", datos)
        self.assertIn("conteo_por_estado", datos)
        self.assertEqual(datos["total"], len(datos["guias"]))

    def test_listar_filtrando_por_estado(self):
        datos, _ = pedir_json(
            api.listar_guias_api, {"estado": ["CREADA"], "limite": ["50"]}, ADMIN
        )
        for guia in datos["guias"]:
            self.assertEqual(guia.get("estado"), "CREADA")

    def test_listar_con_busqueda_no_encuentra_nada(self):
        datos, _ = pedir_json(
            api.listar_guias_api, {"q": ["__no_existe_xyz__"]}, ADMIN
        )
        self.assertEqual(datos["guias"], [])

    def test_conteo(self):
        datos, codigo = pedir_json(
            api.conteo_guias_api, {}, ADMIN
        )
        self.assertEqual(codigo, 200)
        self.assertIn("conteo", datos)

    def test_catalogo_de_estados(self):
        datos, codigo = pedir_json(api.estados_guias_api, ADMIN)
        self.assertEqual(codigo, 200)
        self.assertTrue(datos["estados"])
        for item in datos["estados"]:
            self.assertIn("clave", item)
            self.assertIn("info", item)


class TestDetalleYEventos(unittest.TestCase):
    def _crear(self):
        gid, _consec = g.crear_guia(
            VENTAS_ADMIN,
            {
                "cliente": "Cliente de prueba API",
                "ciudad": "Bogota",
                "direccion": "Calle 1 # 2-3",
                "creada_por": ADMIN["usuario"],
            },
        )
        return gid

    def test_detalle_de_guia_inexistente_es_404(self):
        datos, codigo = pedir_json(
            api.detalle_guia_api, {}, ADMIN, 999999
        )
        self.assertEqual(codigo, 404)
        self.assertFalse(datos["ok"])

    def test_detalle_incluye_eventos_prellenado_y_estado(self):
        gid = self._crear()
        try:
            datos, codigo = pedir_json(
                api.detalle_guia_api, {}, ADMIN, gid
            )
            self.assertEqual(codigo, 200)
            self.assertTrue(datos["ok"])
            self.assertEqual(datos["guia"]["id"], gid)
            self.assertIsInstance(datos["eventos"], list)
            self.assertIn("prellenado", datos)
            self.assertIn("estado_info", datos)
            self.assertIn("etiqueta", datos["estado_info"])
        finally:
            g.editar_guia(gid, ADMIN, {})

    def test_eventos_de_guia_inexistente(self):
        datos, codigo = pedir_json(
            api.eventos_guia_api, {}, ADMIN, 999999
        )
        self.assertEqual(codigo, 200)
        self.assertEqual(datos["eventos"], [])

    def test_transicion_informa_si_se_puede_ejecutar(self):
        gid = self._crear()
        try:
            datos, codigo = pedir_json(
                api.transicion_guia_api, {}, ADMIN, gid, "recepcion_admin"
            )
            self.assertEqual(codigo, 200)
            self.assertIn("puede", datos)
        finally:
            g.editar_guia(gid, ADMIN, {})


class TestEdicion(unittest.TestCase):
    def _crear(self):
        gid, _consec = g.crear_guia(
            VENTAS_ADMIN,
            {
                "cliente": "Cliente edicion API",
                "ciudad": "Medellin",
                "direccion": "Av 1 # 2-3",
                "creada_por": ADMIN["usuario"],
            },
        )
        return gid

    def test_editar_devuelve_guia_actualizada(self):
        gid = self._crear()
        try:
            datos, codigo = pedir_json(
                api.editar_guia_api, gid, {"ciudad": "Cali"}, ADMIN, "127.0.0.1"
            )
            self.assertLess(codigo, 400)
            self.assertTrue(datos["ok"])
            if datos.get("guia"):
                self.assertEqual(datos["guia"].get("ciudad"), "Cali")
        finally:
            g.editar_guia(gid, ADMIN, {})

    def test_editar_con_datos_invalidos_no_revienta(self):
        gid = self._crear()
        try:
            datos, codigo = pedir_json(
                api.editar_guia_api, gid, {"ciudad": "x" * 300}, ADMIN, "127.0.0.1"
            )
            self.assertGreaterEqual(codigo, 400)
            self.assertFalse(datos["ok"])
        except (ValidationError, ValueError):
            pass
        finally:
            try:
                g.editar_guia(gid, ADMIN, {})
            except Exception:
                pass


class TestPermisos(unittest.TestCase):
    def test_transicion_para_ventas_no_puede_ejecutar_paso_de_cedis(self):
        gid, _consec = g.crear_guia(
            VENTAS_ADMIN,
            {
                "cliente": "Cliente permisos API",
                "ciudad": "Cali",
                "direccion": "Calle 9 # 9-9",
                "creada_por": "admin",
            },
        )
        try:
            datos, _ = pedir_json(
                api.transicion_guia_api, {}, VENTAS, gid, "control_cedis"
            )
            self.assertIn("puede", datos)
            if datos["puede"]:
                self.fail("ventas no debería poder ejecutar el paso de CEDIS")
        except (ForbiddenError, AuthError, ValueError):
            pass  # lanza directo: también es un resultado válido
        finally:
            try:
                g.editar_guia(gid, ADMIN, {})
            except Exception:
                pass
            try:
                import sqlite3
                from guias_coodescor.config import DATA_DIR
                conn = sqlite3.connect(DATA_DIR + "/guias.db")
                conn.execute("DELETE FROM eventos WHERE guia_id = ?", (gid,))
                conn.execute("DELETE FROM guias WHERE id = ?", (gid,))
                conn.commit()
                conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main(verbosity=2)



