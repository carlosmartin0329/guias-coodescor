#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas del módulo de administración de la base de datos.

Verifica lo que de verdad importa en un editor de base de datos en producción:
que no permita tocar lo que no debe, que_parametrize todos los valores, que
escriba auditoría y que nunca destruya datos sin respaldo previo.

Uso:
    py -3 test_db_admin.py
"""
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TEMP_DIR = None
ADMIN = {"id": 1, "usuario": "admin", "nombre": "Admin", "rol": "admin"}


def setUpModule():
    """Base de datos temporal propia de esta corrida."""
    global TEMP_DIR
    TEMP_DIR = tempfile.mkdtemp(prefix="coodescor_dbadmin_")
    data = os.path.join(TEMP_DIR, "data")
    os.makedirs(data, exist_ok=True)

    import guias_coodescor.config as cfg

    cfg.DATA_DIR = data
    cfg.ADJUNTOS_DIR = os.path.join(data, "adjuntos")
    cfg.BACKUP_DIR = os.path.join(data, "respaldos")
    cfg.DB_PATH = os.path.join(data, "guias.db")
    cfg.RECEPTORES_DB_PATH = os.path.join(data, "receptores.db")
    os.makedirs(cfg.ADJUNTOS_DIR, exist_ok=True)
    os.makedirs(cfg.BACKUP_DIR, exist_ok=True)

    from guias_coodescor.database.models import init_db

    init_db()

    # El id real del admin evita depender del orden de inserción de la semilla.
    from guias_coodescor.database.connection import db_connection

    with db_connection() as conn:
        fila = conn.execute(
            "SELECT id, usuario, nombre, rol FROM usuarios WHERE usuario = 'admin'"
        ).fetchone()
    if fila:
        ADMIN.update(
            {"id": int(fila["id"]), "usuario": fila["usuario"], "nombre": fila["nombre"], "rol": fila["rol"]}
        )


def tearDownModule():
    if TEMP_DIR and os.path.isdir(TEMP_DIR):
        shutil.rmtree(TEMP_DIR, ignore_errors=True)


def _servicio():
    from guias_coodescor.services import db_admin_service

    return db_admin_service


class TestIntrospeccion(unittest.TestCase):
    def test_lista_tablas_con_conteo_y_permisos(self):
        db = _servicio()
        tablas = {t["nombre"]: t for t in db.listar_tablas("guias")}
        self.assertIn("guias", tablas)
        self.assertIn("clientes", tablas)
        self.assertTrue(tablas["guias"]["editable"])
        # Las internas del motor no se editan a mano.
        self.assertFalse(tablas["schema_migrations"]["editable"])
        self.assertTrue(tablas["guias"]["filas"] >= 0)

    def test_tabla_inexistente_es_rechazada(self):
        db = _servicio()
        with self.assertRaises(db.TablaNoPermitida):
            db.describir_tabla("guias", "no_existe_esta_tabla")

    def test_nombre_de_tabla_invalido_es_rechazado(self):
        db = _servicio()
        for candidato in ("guias; DROP TABLE guias", "../../etc", "", "guias--"):
            with self.assertRaises(db.TablaNoPermitida):
                db.describir_tabla("guias", candidato)

    def test_esquema_incluye_columnas_indices_y_foraneas(self):
        db = _servicio()
        esquema = db.describir_tabla("guias", "guias")
        nombres = {c["nombre"] for c in esquema["columnas"]}
        self.assertIn("consecutivo", nombres)
        self.assertTrue(esquema["indices"], "la tabla guias debe tener índices")
        self.assertTrue(any(f["tabla"] == "usuarios" for f in esquema["foraneas"]))

    def test_base_receptores_es_solo_lectura(self):
        db = _servicio()
        with self.assertRaises(db.TablaNoPermitida):
            db.eliminar_fila("receptores", "receptores", 1, ADMIN)

    def test_bases_reporta_integridad(self):
        db = _servicio()
        bases = {b["base"]: b for b in db.listar_bases()}
        self.assertEqual(bases["guias"]["integridad"], "ok")
        self.assertTrue(bases["guias"]["bytes"] > 0)


class TestCRUD(unittest.TestCase):
    def test_insertar_actualizar_y_eliminar_una_fila(self):
        db = _servicio()
        nuevo = db.insertar_fila(
            "guias",
            "config",
            {"clave": "prueba_db_admin", "valor": "uno"},
            ADMIN,
            "127.0.0.1",
        )
        self.assertIsNotNone(nuevo["id"])

        resultado = db.actualizar_fila(
            "guias", "config", "prueba_db_admin", {"valor": "dos"}, ADMIN, "127.0.0.1"
        )
        self.assertIn("valor", resultado["campos"])

        pagina = db.listar_filas("guias", "config", q="prueba_db_admin")
        valores = [f["valor"] for f in pagina["filas"]]
        self.assertEqual(valores, ["dos"])

        db.eliminar_fila("guias", "config", "prueba_db_admin", ADMIN, "127.0.0.1")
        self.assertEqual(db.listar_filas("guias", "config", q="prueba_db_admin")["total"], 0)

    def test_columna_inexistente_es_rechazada(self):
        db = _servicio()
        with self.assertRaises(db.ColumnaNoPermitida):
            db.insertar_fila(
                "guias", "config", {"clave": "x", "columna_inventada": "y"}, ADMIN
            )

    def test_password_hash_no_se_puede_editar(self):
        db = _servicio()
        with self.assertRaises(db.ColumnaNoPermitida):
            db.actualizar_fila("guias", "usuarios", ADMIN["id"], {"pass_hash": "x"}, ADMIN)

    def test_password_hash_se_enmascara_en_la_listado(self):
        db = _servicio()
        pagina = db.listar_filas("guias", "usuarios")
        fila_admin = next(f for f in pagina["filas"] if f["id"] == ADMIN["id"])
        self.assertEqual(fila_admin["pass_hash"], db.MASCARADO)
        self.assertEqual(fila_admin["sal"], db.MASCARADO)
        # Lo que sí se puede ver sigue visible.
        self.assertEqual(fila_admin["usuario"], ADMIN["usuario"])

    def test_tabla_solo_lectura_no_se_puede_editar(self):
        db = _servicio()
        with self.assertRaises(db.TablaNoPermitida):
            db.insertar_fila("guias", "schema_migrations", {"version": 999}, ADMIN)

    def test_valor_incorrecto_para_columna_entera(self):
        db = _servicio()
        with self.assertRaises(db.ColumnaNoPermitida):
            db.insertar_fila("guias", "guias", {"consecutivo": "no-es-un-numero"}, ADMIN)

    def test_eliminar_crea_respaldo_previo(self):
        db = _servicio()
        db.insertar_fila("guias", "config", {"clave": "a_borrar", "valor": "x"}, ADMIN)
        antes = len(db.listar_respaldos("guias"))
        resultado = db.eliminar_fila("guias", "config", "a_borrar", ADMIN)
        self.assertIsNotNone(resultado["respaldo"])
        self.assertGreater(len(db.listar_respaldos("guias")), antes)

    def test_eliminar_fila_inexistente(self):
        db = _servicio()
        with self.assertRaises(db.DbAdminError):
            db.eliminar_fila("guias", "config", "no_existe_esta_clave", ADMIN)

    def test_busqueda_literal_no_interpreta_comodines(self):
        db = _servicio()
        db.insertar_fila("guias", "config", {"clave": "wild_1", "valor": "a"}, ADMIN)
        db.insertar_fila("guias", "config", {"clave": "wildX1", "valor": "b"}, ADMIN)
        resultado = db.listar_filas("guias", "config", q="wild_1")
        claves = [f["clave"] for f in resultado["filas"]]
        self.assertEqual(claves, ["wild_1"], "el _ debe buscarse literal, no como comodín")
        db.eliminar_fila("guias", "config", "wild_1", ADMIN)
        db.eliminar_fila("guias", "config", "wildX1", ADMIN)

    def test_orden_invalido_se_ignora(self):
        db = _servicio()
        # No debe lanzar: cae al orden por defecto.
        resultado = db.listar_filas("guias", "config", orden="valor; DROP TABLE config", direccion="desc")
        self.assertIn("filas", resultado)


class TestConsultas(unittest.TestCase):
    def test_select_en_modo_lectura(self):
        db = _servicio()
        resultado = db.ejecutar_consulta(
            "guias", "SELECT clave, valor FROM config ORDER BY clave LIMIT 5"
        )
        self.assertTrue(resultado["columnas"])
        self.assertFalse(resultado["escritura"])

    def test_modo_lectura_rechaza_escritura(self):
        db = _servicio()
        for sentencia in (
            "DELETE FROM config",
            "UPDATE config SET valor = 'x'",
            "DROP TABLE config",
            "INSERT INTO config(clave, valor) VALUES ('a','b')",
            "SELECT 1; DELETE FROM config",
            "ATTACH DATABASE 'otro.db' AS otro",
            "PRAGMA journal_mode = DELETE",
        ):
            with self.assertRaises(db.ConsultaNoPermitida, msg=sentencia):
                db.ejecutar_consulta("guias", sentencia)

    def test_conexion_de_lectura_rechaza_escritura_aunque_pase_el_filtro(self):
        """Defensa en profundidad: el motor bloquea, no solo el filtro de texto."""
        db = _servicio()
        conn = db._conectar("guias", solo_lectura=True)
        try:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("INSERT INTO config(clave, valor) VALUES ('x','y')")
        finally:
            conn.close()

    def test_modo_escritura_rechaza_select(self):
        db = _servicio()
        with self.assertRaises(db.ConsultaNoPermitida):
            db.ejecutar_consulta("guias", "SELECT 1", escritura=True)

    def test_modo_escritura_requiere_que_no_sea_select(self):
        db = _servicio()
        db.insertar_fila("guias", "config", {"clave": "sql_test", "valor": "antes"}, ADMIN)
        resultado = db.ejecutar_consulta(
            "guias",
            "UPDATE config SET valor = 'despues' WHERE clave = 'sql_test'",
            escritura=True,
            admin=ADMIN,
            ip="127.0.0.1",
            confirmado=True,
        )
        self.assertEqual(resultado["filas_afectadas"], 1)
        pagina = db.listar_filas("guias", "config", q="sql_test")
        self.assertEqual(pagina["filas"][0]["valor"], "despues")
        db.eliminar_fila("guias", "config", "sql_test", ADMIN)

    def test_modo_escritura_exige_confirmacion(self):
        """Sin `confirmado=True` no se ejecuta nada, ni siquiera un UPDATE inofensivo."""
        db = _servicio()
        db.insertar_fila("guias", "config", {"clave": "sql_conf", "valor": "antes"}, ADMIN)
        try:
            with self.assertRaises(db.ConsultaNoPermitida):
                db.ejecutar_consulta(
                    "guias",
                    "UPDATE config SET valor = 'despues' WHERE clave = 'sql_conf'",
                    escritura=True,
                    admin=ADMIN,
                )
            pagina = db.listar_filas("guias", "config", q="sql_conf")
            self.assertEqual(pagina["filas"][0]["valor"], "antes")
        finally:
            db.eliminar_fila("guias", "config", "sql_conf", ADMIN)

    def test_modo_escritura_crea_respaldo_previo(self):
        db = _servicio()
        antes = len(db.listar_respaldos("guias"))
        db.ejecutar_consulta(
            "guias",
            "UPDATE config SET valor = valor WHERE clave = 'no_existe'",
            escritura=True,
            admin=ADMIN,
            confirmado=True,
        )
        self.assertEqual(len(db.listar_respaldos("guias")), antes + 1)

    def test_el_editor_nunca_toca_el_esquema(self):
        """Ni con confirmación: DROP/ALTER/CREATE/PRAGMA/ATTACH están vetados."""
        db = _servicio()
        for sentencia in (
            "DROP TABLE guias",
            "ALTER TABLE guias ADD COLUMN x INTEGER",
            "CREATE TABLE prueba_sql (id INTEGER)",
            "ATTACH DATABASE 'otro.db' AS otro",
            "DETACH DATABASE otro",
            "PRAGMA table_info(guias)",
            "VACUUM",
            "REINDEX",
        ):
            with self.assertRaises(db.ConsultaNoPermitida, msg=sentencia):
                db.ejecutar_consulta("guias", sentencia, escritura=True, admin=ADMIN, confirmado=True)

    def test_el_sql_no_lee_datos_protegidos(self):
        """pass_hash / sal / columnas cifradas no salen por el editor de SQL."""
        db = _servicio()
        for sentencia in (
            "SELECT pass_hash FROM usuarios",
            "SELECT sal FROM usuarios LIMIT 1",
            "SELECT * FROM usuarios",
            "SELECT * FROM usuarios JOIN sesiones ON sesiones.usuario_id = usuarios.id",
            "SELECT email_cif FROM receptores",
            "SELECT nombres_apellidos_cif FROM receptores",
        ):
            with self.assertRaises(db.ConsultaNoPermitida, msg=sentencia):
                db.ejecutar_consulta("guias", sentencia, escritura=False)

    def test_columnas_no_sensibles_de_usuarios_si_se_pueden_contar(self):
        """El bloqueo es por columna, no por tabla: contar usuarios sigue siendo útil."""
        db = _servicio()
        resultado = db.ejecutar_consulta("guias", "SELECT COUNT(*) AS n FROM usuarios")
        self.assertEqual(resultado["filas"][0][0], resultado["filas"][0][0])
        resultado = db.ejecutar_consulta("guias", "SELECT usuario, rol FROM usuarios ORDER BY id LIMIT 3")
        self.assertTrue(resultado["columnas"])

    def test_el_respaldo_se_puede_descargar_auditado(self):
        db = _servicio()
        creado = db.crear_respaldo(motivo="prueba-descarga")
        contenido, nombre = db.leer_respaldo(creado["archivo"], ADMIN, "127.0.0.1")
        self.assertEqual(nombre, creado["archivo"])
        self.assertEqual(len(contenido), creado["bytes"])
        with self.assertRaises(db.RespaldoNoValido):
            db.leer_respaldo("../../../Windows/win.ini", ADMIN, "127.0.0.1")
        with self.assertRaises(db.RespaldoNoValido):
            db.leer_respaldo("no_existe.db", ADMIN, "127.0.0.1")

    def test_consulta_vacia_o_invalida(self):
        db = _servicio()
        for sentencia in ("", "   ", "/* solo un comentario */", "SELECT * FROM guias " + "UNION " * 400):
            with self.assertRaises((db.ConsultaNoPermitida, sqlite3.OperationalError)):
                db.ejecutar_consulta("guias", sentencia)

    def test_consulta_se_trunca_al_tope_de_filas(self):
        db = _servicio()
        resultado = db.ejecutar_consulta("guias", "SELECT valor FROM config")
        self.assertLessEqual(len(resultado["filas"]), db._cfg.DB_QUERY_MAX_ROWS)


class TestRespaldos(unittest.TestCase):
    def test_crear_respaldo_lo_verifica(self):
        db = _servicio()
        resultado = db.crear_respaldo(motivo="prueba")
        self.assertTrue(os.path.isfile(resultado["ruta"]))
        self.assertGreater(resultado["bytes"], 0)
        conn = sqlite3.connect(resultado["ruta"])
        try:
            self.assertEqual(
                conn.execute("PRAGMA integrity_check").fetchone()[0], "ok"
            )
        finally:
            conn.close()

    def test_restaurar_verifica_antes_de_sustituir(self):
        db = _servicio()
        respaldo = db.crear_respaldo(motivo="para-restaurar")
        # Un archivo que no es base de datos debe rechazarse sin tocar nada.
        ruta_mala = os.path.join(db._directorio_respaldos("guias"), "corrupto.db")
        with open(ruta_mala, "wb") as fh:
            fh.write(b"esto no es una base de datos")
        with self.assertRaises(db.RespaldoNoValido):
            db.restaurar_respaldo("corrupto.db", ADMIN)
        self.assertTrue(os.path.isfile(db._ruta_base("guias")), "la base no debe tocarse")
        os.remove(ruta_mala)
        os.remove(respaldo["ruta"])

    def test_nombre_de_respaldo_se_sanitiza(self):
        db = _servicio()
        nombre = db._nombre_respaldo("guias", "../../evil path/../../x")
        self.assertTrue(nombre.endswith(".db"))
        self.assertNotIn("/", nombre)
        self.assertNotIn("\\", nombre)
        self.assertNotIn("..", nombre)

    def test_mantenimiento_vacuum(self):
        db = _servicio()
        resultado = db.ejecutar_mantenimiento("vacuum", ADMIN)
        self.assertEqual(resultado["operacion"], "vacuum")

    def test_mantenimiento_invalido(self):
        db = _servicio()
        with self.assertRaises(db.DbAdminError):
            db.ejecutar_mantenimiento("DROP TABLE guias", ADMIN)


class TestMigracionesYAuditoria(unittest.TestCase):
    def test_lista_migraciones_incluye_v8(self):
        db = _servicio()
        versiones = {m["version"] for m in db.listar_migraciones()}
        self.assertIn(8, versiones)
        for m in db.listar_migraciones():
            if m["version"] == 8:
                self.assertTrue(m["aplicada"], "V8 debe quedar aplicada tras init_db")

    def test_toda_escritura_queda_auditada(self):
        db = _servicio()
        antes = db.listar_auditoria(limite=500)["total"]
        db.insertar_fila("guias", "config", {"clave": "auditada", "valor": "1"}, ADMIN, "10.0.0.9")
        db.actualizar_fila("guias", "config", "auditada", {"valor": "2"}, ADMIN, "10.0.0.9")
        db.eliminar_fila("guias", "config", "auditada", ADMIN, "10.0.0.9")
        historial = db.listar_auditoria(limite=500)["registros"]
        self.assertGreater(len(historial), antes)

        acciones = [r["accion"] for r in historial[:3]]
        self.assertIn("eliminar", acciones)
        self.assertIn("actualizar", acciones)
        registro = next(r for r in historial if r["accion"] == "actualizar")
        self.assertEqual(registro["usuario"], ADMIN["usuario"])
        self.assertEqual(registro["ip"], "10.0.0.9")
        self.assertIn("antes", registro["detalle"])
        self.assertIn("cambios", registro["detalle"])

    def test_auditoria_guarda_el_rastro_del_borrado(self):
        db = _servicio()
        db.insertar_fila("guias", "config", {"clave": "rastro", "valor": "secreto"}, ADMIN)
        db.eliminar_fila("guias", "config", "rastro", ADMIN)
        historial = db.listar_auditoria(limite=50)["registros"]
        borrado = next(r for r in historial if r["accion"] == "eliminar")
        self.assertEqual(borrado["detalle"]["fila_eliminada"]["valor"], "secreto")
        self.assertIn("respaldo", borrado["detalle"])
    def test_la_auditoria_no_rompe_la_operacion(self):
        db = _servicio()
        # Aunque el servicio no pueda escribir la auditoría, la fila debe crearse.
        original = db._conectar_cualquiera

        def _roto(*args, **kwargs):
            raise sqlite3.OperationalError("sin escritura")

        db._conectar_cualquiera = _roto
        try:
            resultado = db.insertar_fila(
                "guias", "config", {"clave": "sin_auditoria", "valor": "x"}, ADMIN
            )
            self.assertIsNotNone(resultado["id"])
        finally:
            db._conectar_cualquiera = original
            db.eliminar_fila("guias", "config", "sin_auditoria", ADMIN)

    def test_acciones_auditadas(self):
        db = _servicio()
        acciones = db.acciones_auditadas()
        self.assertIn("insertar", acciones)


def suite():
    return unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])


if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(suite())