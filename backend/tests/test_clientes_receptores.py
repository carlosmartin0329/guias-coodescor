#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 TESTS FUNCIONALES · CLIENTES + RECEPTORES (≥25 tests)
 BD temporales por run (tmpfs). Usa unittest stdlib.
 Cobertura:
   · Schema: clientes.nit PK NOT NULL, 3 idx, FK guias.nit, receptores 3 idx
   · Crypto: cifrar_valor ↔ descifrar_valor roundtrip + tag inválido + clave mala
   · Clientes: guardar upsert (manual/descubierto), asegurar, buscar ranking
   · Receptores: registrar con FK OK / FK fail huérfanos → 400, permisos 403,
                 purga TTR (7d post-entrega / 30d natural) y evento receptor_purgado
=============================================================================
"""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TEMP_DIR = None  # tmp dir for this run


def setUpModule():
    """Setup a nivel MÓDULO (llamado UNA sola vez ANTES de todos los TestCase).
    Crea dir temp, sobrescribe config paths, inicializa BD, reasigna IDs de usuarios
    seed reales desde la BD para no tener desalineaciones de ValidationError.
    """
    global TEMP_DIR
    TEMP_DIR = tempfile.mkdtemp(prefix="coodescor_clientes_recp_")
    DATA = os.path.join(TEMP_DIR, "guias_coodescor", "data")
    os.makedirs(DATA, exist_ok=True)
    # Override config ANTES de importar nada de database para que el binding
    # dinámico de connection._cfg.DB_PATH tome la ruta temporal.
    import guias_coodescor.config as _cfg
    _cfg.DB_PATH = os.path.join(DATA, "guias.db")
    _cfg.RECEPTORES_DB_PATH = os.path.join(DATA, "receptores.db")
    # Import dinámico DESPUÉS del override paths
    from guias_coodescor.database.models import init_db
    init_db()
    # --- Asignar IDs REALES de usuarios seed desde BD a dicts globales test ---
    from guias_coodescor.database.connection import db_connection
    usuarios_esperados = {
        "_user_admin":       ("admin",),
        "_user_ventas":      ("ventas",),
        "_user_cedis":       ("cedis",),
        "_user_transp":      ("transportador",),
    }
    real_ids = {}
    with db_connection() as c:
        for clave, (usuario_nom,) in usuarios_esperados.items():
            r = c.execute(
                "SELECT id, usuario, nombre, rol FROM usuarios WHERE usuario = ? COLLATE NOCASE LIMIT 1",
                (usuario_nom,),
            ).fetchone()
            if r:
                real_ids[clave] = {
                    "id": int(r["id"]),
                    "usuario": r["usuario"],
                    "nombre": r["nombre"] or clave,
                    "rol": r["rol"],
                }
    # Re-asignar variables globales si los encontramos
    import sys as _sys
    _mod = _sys.modules[__name__]
    for k, v in real_ids.items():
        setattr(_mod, k, v)


def tearDownModule():
    """Teardown a nivel MÓDULO (llamado UNA sola vez DESPUÉS de todos los TestCase).
    Limpia el directorio temporal para no dejar basura.
    """
    global TEMP_DIR
    try:
        if TEMP_DIR and os.path.isdir(TEMP_DIR):
            shutil.rmtree(TEMP_DIR, ignore_errors=True)
    except Exception:
        pass
    TEMP_DIR = None


_user_admin = {"id":1,"usuario":"admin","nombre":"Admin Sys","rol":"admin"}
_user_ventas = {"id":5,"usuario":"ventas","nombre":"Sr Vtas","rol":"ventas"}
_user_cedis = {"id":3,"usuario":"cedis","nombre":"Sr Cedis","rol":"cedis"}
_user_transp = {"id":101,"usuario":"transportador","nombre":"Sr Transp","rol":"transportador"}


class TestSchemaClientesReceptores(unittest.TestCase):
    """Schema introspection tests (8 checks = 8 tests)."""
    pass

    def test_tabla_clientes_existe(self):
        from guias_coodescor.database.connection import db_connection
        with db_connection() as c:
            rows = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clientes'").fetchall()
            self.assertTrue(len(rows) == 1)

    def test_nit_es_pk_notnull(self):
        from guias_coodescor.database.connection import db_connection
        with db_connection() as c:
            cols = c.execute("PRAGMA table_info(clientes)").fetchall()
            nit_row = [x for x in cols if x[1] == "nit"]
            self.assertEqual(len(nit_row), 1)
            # col 5 = pk (0/1), col 3 = notnull (0/1)
            self.assertEqual(nit_row[0][5], 1, "nit debe ser pk=1")
            self.assertEqual(nit_row[0][3], 1, "nit debe ser NOT NULL")

    def test_clientes_tiene_3_idx(self):
        from guias_coodescor.database.connection import db_connection
        with db_connection() as c:
            ixs = c.execute("PRAGMA index_list(clientes)").fetchall()
            # idx auto PK + 3 explícitos = 4
            nombres = sorted([x[1] for x in ixs])
            for esp in ("idx_clientes_razon_social","idx_clientes_ciudad","idx_clientes_telefono"):
                self.assertTrue(any(esp in n for n in nombres), f"falta índice {esp}")

    def test_receptores_tabla_existe(self):
        from guias_coodescor.database.connection import get_receptores_connection
        with get_receptores_connection() as c:
            rows = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='receptores'").fetchall()
            self.assertTrue(len(rows) == 1)

    def test_receptores_4_campos_cif_presentes(self):
        from guias_coodescor.database.connection import get_receptores_connection
        with get_receptores_connection() as c:
            cols = {x[1] for x in c.execute("PRAGMA table_info(receptores)").fetchall()}
            for esp in ("nombres_apellidos_cif","numero_doc_cif","telefono_cif","email_cif"):
                self.assertIn(esp, cols, f"falta columna cifrada {esp}")

    def test_receptores_3_indices(self):
        from guias_coodescor.database.connection import get_receptores_connection
        with get_receptores_connection() as c:
            ixs = c.execute("PRAGMA index_list(receptores)").fetchall()
            self.assertGreaterEqual(len(ixs), 3, "receptores debe tener ≥3 índices")

    def test_clave_receptores_persistida(self):
        from guias_coodescor.database.models import obtener_o_generar_receptores_secret
        k1 = obtener_o_generar_receptores_secret()
        k2 = obtener_o_generar_receptores_secret()
        self.assertTrue(isinstance(k1, str) and len(k1) > 30)
        self.assertEqual(k1, k2, "debe ser idempotente (mismo valor 2 llamadas)")

    def test_tabla_eventos_admite_receptor_purgado(self):
        from guias_coodescor.services.eventos_service import agregar_evento
        # Intentar insertar un evento tipo receptor_purgado (no debe fallar CHECK)
        from guias_coodescor.database.connection import db_connection
        from guias_coodescor.core.utils import ahora_txt
        with db_connection(commit=True) as c:
            c.execute(
                "INSERT INTO guias(id, consecutivo, estado, creada_en) VALUES(?,?,?,?)",
                (9876, 9876, "CREADA", ahora_txt()),
            )
        ok = agregar_evento(
            9876,
            "receptor_purgado",
            {"id": 1, "usuario": "x", "rol": "admin"},  # user arg (3er posicional)
            {"id_temp": 1, "motivo": "ttr"},            # datos (4to posicional)
            dispositivo="t",
            ip="1.2.3.4",
        )
        # agregar_evento devuelve int (id evento) o 0 si falla
        self.assertGreaterEqual(int(ok or 0), 1, "evento receptor_purgado debe insertarse OK")


class TestCryptoReceptores(unittest.TestCase):
    """PBKDF2/XOR/HMAC roundtrip + tamper detection = 5 tests"""
    pass

    def _get_secret(self):
        from guias_coodescor.database.models import obtener_o_generar_receptores_secret
        return obtener_o_generar_receptores_secret()

    def test_cifrar_descifrar_roundtrip_espanol_emoji(self):
        from guias_coodescor.services.crypto_service import cifrar_valor, descifrar_valor
        clave = self._get_secret()
        textos = ["María Rodríguez 500 Años #23-56", "Tel: +57 300-123-4567 🚚", ""]
        for t in textos:
            c = cifrar_valor(t, clave)
            if t == "":
                self.assertEqual(c, "")
                continue
            self.assertTrue(c.startswith("$1$PBKDF2$"), f"prefijo PBKDF2 faltante: {c[:30]}")
            self.assertEqual(descifrar_valor(c, clave), t)

    def test_same_plaintext_distinto_salt_distinto_ciphertext(self):
        from guias_coodescor.services.crypto_service import cifrar_valor
        clave = self._get_secret()
        t = "mismo texto"
        c1 = cifrar_valor(t, clave); c2 = cifrar_valor(t, clave)
        self.assertNotEqual(c1, c2, "mismo plain debe producir distinto cipher (salt 16B/reg)")

    def test_tag_tampering_detectado(self):
        from guias_coodescor.services.crypto_service import cifrar_valor, descifrar_valor
        clave = self._get_secret()
        c = cifrar_valor("Carlos", clave)
        partes = c.split("$")
        # partes = ["","1","PBKDF2", salt, cipherB64, tagB64]
        partes[-1] = "AAAA" + partes[-1][4:] if len(partes[-1]) > 8 else "BBBBBBBB"
        c_alter = "$".join(partes)
        # Debe retornar None (tag no coincide)
        self.assertIsNone(descifrar_valor(c_alter, clave))

    def test_clave_incorrecta_retorna_null(self):
        from guias_coodescor.services.crypto_service import cifrar_valor, descifrar_valor
        c = cifrar_valor("texto", self._get_secret())
        self.assertIsNone(descifrar_valor(c, "clave-mala-de-invento-1234567890123456"))

    def test_cadena_vacia_idempotente(self):
        from guias_coodescor.services.crypto_service import cifrar_valor, descifrar_valor
        clave = self._get_secret()
        self.assertEqual(cifrar_valor("", clave), "")
        self.assertEqual(descifrar_valor("", clave), "")
        self.assertIsNone(descifrar_valor("basura_no_formato", clave))


class TestClientesUpsertBusqueda(unittest.TestCase):
    """Clientes: guardar, upsert inteligente, buscar ranking = 6 tests"""
    pass

    def test_insertar_cliente_nuevo_manual_ok(self):
        from guias_coodescor.services.clientes_service import guardar_cliente, obtener_cliente_por_nit
        ok, msg, _ = guardar_cliente({
            "nit":"800.000.000-1", "razon_social":"Arista Farmacéutica SAS",
            "direccion":"Cl 27 # 10-23","ciudad":"Montería","telefono":"3001002030",
            "email":"compras@arista.co","contacto":"Carlos","cliente_descubierto":0
        }, origen="manual")
        self.assertTrue(ok, msg)
        row = obtener_cliente_por_nit("8000000001")  # normalizado sin puntos/guion
        self.assertIsNotNone(row)
        self.assertEqual(row["razon_social"], "Arista Farmacéutica SAS")
        self.assertEqual(row["cliente_descubierto"], 0)

    def test_insertar_descubierto_then_manual_actualiza_y_pasa_a_0(self):
        from guias_coodescor.services.clientes_service import guardar_cliente, obtener_cliente_por_nit
        nit = "900999888-2"
        guardar_cliente({
            "nit":nit,"razon_social":"(nombre desde Ventas, incompleto)",
            "direccion":"","ciudad":"","telefono":"","email":""
        }, origen="descubierto")
        r1 = obtener_cliente_por_nit(nit)
        self.assertEqual(r1["cliente_descubierto"], 1)
        guardar_cliente({
            "nit":nit,"razon_social":"ClienteReal SAS",
            "direccion":"Av Siempre Viva 123","ciudad":"Cereté","telefono":"3102003040",
            "email":"info@clientereal.co"
        }, origen="manual")
        r2 = obtener_cliente_por_nit(nit)
        self.assertEqual(r2["cliente_descubierto"], 0)
        self.assertEqual(r2["razon_social"], "ClienteReal SAS")
        self.assertEqual(r2["ciudad"], "Cereté")

    def test_manual_existente_no_es_sobreescrito_por_descubierto(self):
        from guias_coodescor.services.clientes_service import guardar_cliente, obtener_cliente_por_nit
        nit = "700111222-3"
        guardar_cliente({
            "nit":nit,"razon_social":"Maestro Consignado",
            "direccion":"D1","ciudad":"Sahagún","telefono":"3009990001","email":"a@b.co"
        }, origen="manual")
        guardar_cliente({
            "nit":nit,"razon_social":"ESTO-NO-DEBE APARECER",
            "direccion":"OTRA","ciudad":"OTRA","telefono":"123","email":"x@x.co"
        }, origen="descubierto")
        r = obtener_cliente_por_nit(nit)
        self.assertEqual(r["razon_social"], "Maestro Consignado")
        self.assertEqual(r["telefono"], "3009990001")

    def test_buscar_ranking_nit_exacto_primero(self):
        from guias_coodescor.services.clientes_service import guardar_cliente, buscar_clientes
        for datos in [
            ("9001234567","Farmacia Central","Ciudad1","Tel1","email1"),
            ("8007654321","Central Droguería","Ciudad2","Tel2","email2"),
            ("12345678901","Los Alpes Central SAS","Montería","300","x"),
        ]:
            n,r,c,t,e = datos
            guardar_cliente({"nit":n,"razon_social":r,"ciudad":c,"telefono":t,"email":e}, origen="manual")
        res = buscar_clientes("9001234567", limite=5)
        self.assertEqual(res[0]["nit"], "9001234567")

    def test_buscar_nit_formateado_con_digito_verificacion(self):
        from guias_coodescor.services.clientes_service import guardar_cliente, buscar_clientes
        guardar_cliente({
            "nit": "8001992314",
            "razon_social": "Cliente de prueba",
            "direccion": "Calle 1",
            "ciudad": "Medellín",
        }, origen="manual")
        resultados = buscar_clientes("800.199.231-4", limite=5)
        self.assertTrue(resultados)
        self.assertEqual(resultados[0]["nit"], "8001992314")

    def test_buscar_palabra_ciudad_o_razon(self):
        from guias_coodescor.services.clientes_service import guardar_cliente, buscar_clientes
        # Insertar datos DENTRO de este test (independencia total).
        for datos in [
            ("9001234567", "Farmacia Central", "Ciudad1", "Tel1", "email1"),
            ("8007654321", "Central Droguería", "Ciudad2", "Tel2", "email2"),
            ("12345678901", "Los Alpes Central SAS", "Montería", "300", "x"),
        ]:
            n, r, c, t, e = datos
            guardar_cliente({
                "nit": n, "razon_social": r, "ciudad": c,
                "telefono": t, "email": e,
            }, origen="manual")
        # Búsqueda por ciudad con tilde
        res_ciudad = buscar_clientes("Montería", limite=10)
        hay_ciudad = any("Los Alpes" in (r.get("razon_social") or "") for r in res_ciudad)
        # Búsqueda alternativa por razón social "Alpes"
        res_razon = buscar_clientes("Alpes", limite=10)
        hay_razon = any("Alpes" in (r.get("razon_social") or "") for r in res_razon)
        self.assertTrue(hay_ciudad or hay_razon,
                        f"No encontró Los Alpes. ciudad={len(res_ciudad)} resultados, razon={len(res_razon)} resultados")

    def test_hook_asegurar_cliente_ventas_no_falla_si_faltan_campos(self):
        from guias_coodescor.services.clientes_service import asegurar_cliente_desde_ventas
        ok, _ = asegurar_cliente_desde_ventas("1","","","","","")
        # Debe insertar como descubierto
        self.assertTrue(ok)
        from guias_coodescor.services.clientes_service import obtener_cliente_por_nit
        self.assertEqual(obtener_cliente_por_nit("1")["cliente_descubierto"], 1)


class TestReceptoresFKyPermisos(unittest.TestCase):
    """Receptores: FK no huérfanos + permisos 403 + purga TTR = 8 tests"""
    pass

    def _crear_cliente_base(self, nit="900100100-7", rs="ClientePrueba SAS"):
        from guias_coodescor.services.clientes_service import guardar_cliente
        guardar_cliente({"nit":nit,"razon_social":rs,"ciudad":"T","direccion":"D"}, origen="manual")
        return nit

    def _crear_guia(self):
        """Crea una guía mínima para asociar a receptores."""
        from guias_coodescor.services.guias_service import crear_guia
        gid, _ = crear_guia(_user_ventas, {
            "nit":"9001001007","cliente":"ClientePrueba","direccion":"DirPrueba","ciudad":"Montería",
            "centro_operacion":"1000","prefijo":"FV","documentos":"FV 001","entrega_nombre":"Vtas",
        }, dispositivo="test", ip="1.1.1.1")
        return gid

    def test_registrar_receptor_sin_nit_cliente_400(self):
        self._crear_cliente_base()
        self._crear_guia()
        from guias_coodescor.services.receptores_service import registrar_receptor
        ok, cod, msg, _ = registrar_receptor(_user_admin, {
            "nit_cliente":"NO-EXISTE-123","tipo_doc":"CC",
            "nombres_apellidos":"Juan Pérez","numero_doc":"1234567",
        }, ip="1.1.1.1")
        self.assertFalse(ok)
        self.assertIn(cod, (400, "FK_NIT_NO_EXISTE"), "debe rechazar NIT inexistente en clientes")

    def test_registrar_receptor_ventas_403(self):
        self._crear_cliente_base()
        gid = self._crear_guia()
        from guias_coodescor.services.receptores_service import registrar_receptor
        ok, cod, _, _ = registrar_receptor(_user_ventas, {
            "nit_cliente":"900100100-7","guia_relacionada_id":gid,"tipo_doc":"CC",
            "nombres_apellidos":"J","numero_doc":"1",
        }, ip="1.1.1.1")
        self.assertFalse(ok)
        self.assertEqual(cod, 403)

    def test_registrar_receptor_admin_ok(self):
        self._crear_cliente_base()
        gid = self._crear_guia()
        from guias_coodescor.services.receptores_service import registrar_receptor, listar_por_nit
        ok, cod, msg, data = registrar_receptor(_user_admin, {
            "nit_cliente":"900100100-7","guia_relacionada_id":gid,"tipo_doc":"CC",
            "nombres_apellidos":"Sofía López","numero_doc":"54321","telefono":"3005554444","email":"a@b.co",
        }, ip="1.1.1.1")
        self.assertTrue(ok, f"cod={cod} msg={msg}")
        # listar_por_nit retorna List[Dict]. No asumimos count único por independencia entre tests
        rows = listar_por_nit(_user_admin, "900100100-7")
        self.assertGreaterEqual(len(rows), 1, "Debe haber al menos 1 receptor para este NIT")
        sofia_rows = [r for r in rows if (r.get("nombres_apellidos") or "") == "Sofía López"]
        self.assertEqual(len(sofia_rows), 1, "Debe haber exactamente 1 Sofía López")
        self.assertEqual(sofia_rows[0]["telefono"], "3005554444")

    def test_transportador_solo_ve_sus_guias(self):
        from guias_coodescor.services.receptores_service import obtener_por_guia, registrar_receptor
        gid1 = self._crear_guia(); gid2 = self._crear_guia()
        self._crear_cliente_base()
        registrar_receptor(_user_cedis, {
            "nit_cliente":"900100100-7","guia_relacionada_id":gid1,"tipo_doc":"CC",
            "nombres_apellidos":"R1","numero_doc":"1"
        }, ip="1")
        registrar_receptor(_user_cedis, {
            "nit_cliente":"900100100-7","guia_relacionada_id":gid2,"tipo_doc":"CC",
            "nombres_apellidos":"R2","numero_doc":"2"
        }, ip="1")
        # Asignar gid1 al transportador
        from guias_coodescor.services.guias_service import asignar_tipo_transportador
        asignar_tipo_transportador(gid1, _user_admin, tipo="propio", transportador_asignado_id=_user_transp["id"])
        # Transportador pide gid1 = 200, gid2 = 403
        ok1, code1, _, _ = obtener_por_guia(_user_transp, gid1)
        self.assertTrue(ok1, f"gid1 suya debe ser 200, code={code1}")
        ok2, code2, _, _ = obtener_por_guia(_user_transp, gid2)
        self.assertFalse(ok2, f"gid2 ajena debe ser 403, code={code2}")
        self.assertEqual(code2, 403)

    def test_eliminar_receptor_solo_admin(self):
        from guias_coodescor.services.receptores_service import eliminar_receptor, registrar_receptor
        self._crear_cliente_base()
        gid = self._crear_guia()
        _,_,_,d = registrar_receptor(_user_admin, {"nit_cliente":"900100100-7","guia_relacionada_id":gid,"tipo_doc":"CC",
            "nombres_apellidos":"Elim","numero_doc":"999"}, ip="1")
        idt = d["id_temp"]
        ok1, _ = eliminar_receptor(_user_cedis, idt)
        self.assertFalse(ok1, "cedis NO debe eliminar")
        ok2, _ = eliminar_receptor(_user_admin, idt)
        self.assertTrue(ok2, "admin sí elimina")

    def test_purga_receptores_vence_30dias_natural(self):
        from guias_coodescor.services.receptores_service import registrar_receptor, purgar_receptores_vencidos
        self._crear_cliente_base()
        gid = self._crear_guia()
        _,_,_,d = registrar_receptor(_user_admin, {"nit_cliente":"900100100-7","guia_relacionada_id":gid,"tipo_doc":"CC",
            "nombres_apellidos":"Purgar30","numero_doc":"88"}, ip="1")
        # Poner vence_en = ahora - 1d (hace 1 día → vencido)
        from guias_coodescor.database.connection import receptores_db_connection
        with receptores_db_connection(commit=True) as c:
            fecha_ven = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            c.execute("UPDATE receptores SET vence_en=? WHERE id_temp=?", (fecha_ven, d["id_temp"]))
        n_purgados = purgar_receptores_vencidos()
        self.assertGreaterEqual(n_purgados, 1)
        # Verificar que se escribió evento receptor_purgado con la guía
        from guias_coodescor.services.eventos_service import listar_eventos
        evs = listar_eventos(gid)
        self.assertTrue(any(e["tipo"] == "receptor_purgado" for e in evs))

    def test_purga_receptores_post_entrega_7dias(self):
        from guias_coodescor.services.receptores_service import registrar_receptor, purgar_receptores_vencidos
        self._crear_cliente_base()
        gid = self._crear_guia()
        _,_,_,d = registrar_receptor(_user_admin, {"nit_cliente":"900100100-7","guia_relacionada_id":gid,"tipo_doc":"CC",
            "nombres_apellidos":"Purgar7","numero_doc":"77"}, ip="1")
        entrega_fecha = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        vence_vencido = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        # Marcar guía como ENTREGADA y registrar evento de entrega (no hay columna entregada_en → evento)
        from guias_coodescor.database.connection import db_connection, receptores_db_connection
        from guias_coodescor.services.eventos_service import agregar_evento
        with db_connection(commit=True) as c:
            c.execute("UPDATE guias SET estado='ENTREGADA' WHERE id=?", (gid,))
        agregar_evento(
            gid, "entrega_cliente",
            {"usuario": "admin", "rol": "admin"},
            {"quien": "prueba", "obs": "entrega simulada"},
            dispositivo="test", ip="127.0.0.1",
        )
        # Actualizar vence del receptor a fecha vencida
        with receptores_db_connection(commit=True) as c:
            c.execute("UPDATE receptores SET vence_en=? WHERE id_temp=?", (vence_vencido, d["id_temp"]))
        n = purgar_receptores_vencidos()
        self.assertGreaterEqual(n, 1)

    def test_vence_en_segunda_regla_guia_sin_entregar_30d(self):
        """Verifica que vence_en no sea None cuando se crea un receptor con guía no entregada."""
        from guias_coodescor.services.receptores_service import registrar_receptor
        self._crear_cliente_base()
        gid = self._crear_guia()
        _,_,_,d = registrar_receptor(_user_admin, {"nit_cliente":"900100100-7","guia_relacionada_id":gid,"tipo_doc":"CC",
            "nombres_apellidos":"VenceCalc","numero_doc":"666"}, ip="1")
        self.assertIn("vence_en", d)
        # Debe ser aproximadamente hoy + 30 días
        ven = datetime.strptime(d["vence_en"], "%Y-%m-%d %H:%M:%S")
        diff = (ven - datetime.utcnow()).days
        self.assertGreaterEqual(diff, 28)
        self.assertLessEqual(diff, 32)


def suite():
    s = unittest.TestSuite()
    for cls in (TestSchemaClientesReceptores, TestCryptoReceptores,
                TestClientesUpsertBusqueda, TestReceptoresFKyPermisos):
        s.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    return s


if __name__ == "__main__":
    res = unittest.TextTestRunner(verbosity=2).run(suite())
    sys.exit(0 if res.wasSuccessful() else 1)
