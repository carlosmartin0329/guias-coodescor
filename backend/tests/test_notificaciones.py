import unittest
from unittest.mock import patch

from guias_coodescor.api import routes_notificaciones as rutas


class RespuestaFalsa:
    def __init__(self):
        self.datos = None
        self.codigo = 200

    def __call__(self, payload, codigo=200):
        self.datos = payload
        self.codigo = codigo
        return payload


class TestNotificacionesPorPerfil(unittest.TestCase):
    def test_requiere_sesion(self):
        respuesta = RespuestaFalsa()
        rutas._handler_pendientes_perfil({}, None, respuesta)

        self.assertEqual(respuesta.codigo, 401)

    def test_transportador_solo_recibe_guias_asignadas(self):
        respuesta = RespuestaFalsa()
        guia = {
            "id": 12,
            "consecutivo": 120,
            "cliente": "Cliente",
            "ciudad": "Monteria",
            "estado": "EN_RUTA",
            "creada_en": "2026-01-01",
            "firma": "dato privado",
        }
        with patch.object(rutas, "buscar_guias", return_value=[guia]) as buscar:
            with patch.object(
                rutas,
                "contar_por_estado",
                return_value=[
                    {"estado": "EN_CEDIS", "n": 4},
                    {"estado": "EN_RUTA", "n": 3},
                ],
            ):
                rutas._handler_pendientes_perfil(
                    {}, {"id": 7, "rol": "transportador"}, respuesta
                )

        self.assertEqual(buscar.call_count, 2)
        self.assertEqual(
            [call.kwargs["estado"] for call in buscar.call_args_list],
            ["EN_CEDIS", "EN_RUTA"],
        )
        self.assertTrue(all(
            call.kwargs["transportador_asignado_id"] == 7
            for call in buscar.call_args_list
        ))
        self.assertEqual(
            {item["id"] for item in respuesta.datos["notificaciones"]},
            {"12:EN_CEDIS", "12:EN_RUTA"},
        )
        self.assertEqual(respuesta.datos["estados"], {"EN_CEDIS": 4, "EN_RUTA": 3})
        self.assertNotIn("firma", respuesta.datos["notificaciones"][0])

    def test_perfiles_consultan_solo_sus_estados_pendientes(self):
        casos = {
            "ventas": ["CREADA", "RECIBIDA_ADMIN", "EN_CEDIS", "EN_RUTA"],
            "administrativo": ["CREADA"],
            "cedis": ["RECIBIDA_ADMIN", "EN_CEDIS"],
            "admin": ["CREADA", "RECIBIDA_ADMIN", "EN_CEDIS", "EN_RUTA"],
        }
        for rol, estados in casos.items():
            with self.subTest(rol=rol):
                respuesta = RespuestaFalsa()
                with patch.object(rutas, "buscar_guias", return_value=[]) as buscar:
                    with patch.object(rutas, "contar_por_estado", return_value=[]):
                        rutas._handler_pendientes_perfil(
                            {}, {"id": 1, "rol": rol}, respuesta
                        )

                self.assertEqual(respuesta.codigo, 200)
                self.assertEqual(
                    [call.kwargs["estado"] for call in buscar.call_args_list],
                    estados,
                )

    def test_rechaza_perfil_no_operativo(self):
        respuesta = RespuestaFalsa()
        rutas._handler_pendientes_perfil({}, {"rol": "publico"}, respuesta)

        self.assertEqual(respuesta.codigo, 403)
