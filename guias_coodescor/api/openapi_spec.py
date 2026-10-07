#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Especificación OpenAPI 3.1 estática para la API de Guías Coodescor.

Esta especificación documenta todos los endpoints JSON del backend.
No depende del framework: es un diccionario estático serializado a YAML.

Se sirve en:
  · /openapi.yaml  → spec YAML
  · /docs          → Swagger UI (HTML estática)
  · /redoc         → ReDoc (HTML estática)
"""
from __future__ import annotations

import yaml

INFO = {
    "title": "Guías Coodescor API",
    "version": "2.0.0",
    "description": (
        "API REST para el sistema de gestión de guías de remisión de Coodescor.\n\n"
        "**Autenticación:** Sesión basada en cookies. Envíe `sid` en el header Cookie.\n"
        "**Roles:** `ventas`, `administrativo`, `cedis`, `admin`, `transportador`, `publico`\n"
        "**CAPTCHA:** Requerido en `/api/login`. Use `/api/captcha/nuevo` para obtenerlo.\n"
        "**Todas las respuestas API siguen el formato `{ok: true/false}`."
    ),
    "contact": {"name": "Coodescor - Logística", "url": "https://coodescor.com"},
}

SERVERS = [
    {"url": "http://127.0.0.1:8000", "description": "Desarrollo local"},
    {"url": "http://localhost:8000", "description": "Desarrollo local (alternativo)"},
]

TAGS = [
    {"name": "auth", "description": "Autenticación y gestión de sesión"},
    {"name": "captcha", "description": "Generación y validación de CAPTCHA"},
    {"name": "guias", "description": "Gestión de guías de remisión (CRUD + workflow)"},
    {"name": "eventos", "description": "Eventos y transiciones del workflow de guías"},
    {"name": "tokens", "description": "Tokens de entrega pública"},
    {"name": "clientes", "description": "Búsqueda de clientes (NIT)"},
    {"name": "receptores", "description": "Gestión de receptores/reclamantes (DB cifrada)"},
    {"name": "admin-db", "description": "Administración de la base de datos (solo admin)"},
    {"name": "admin", "description": "Gestión de usuarios, configuración y exportación (solo admin)"},
    {"name": "loadtest", "description": "Reportes de pruebas de carga (solo admin)"},
    {"name": "ai", "description": "Servicios de Inteligencia Artificial"},
    {"name": "firma-publica", "description": "Confirmación de entrega por link público"},
]

PATHS: dict = {
    "/api/login": {
        "post": {
            "tags": ["auth"],
            "summary": "Iniciar sesión",
            "description": "Autentica al usuario. Requiere validación de CAPTCHA.",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["usuario", "clave", "captcha_token", "captcha_respuesta"],
                            "properties": {
                                "usuario": {"type": "string", "example": "admin"},
                                "clave": {"type": "string", "format": "password", "example": "admin123"},
                                "captcha_token": {"type": "string", "description": "Token del CAPTCHA obtenido en /api/captcha/nuevo"},
                                "captcha_respuesta": {"type": "string", "description": "Texto que el usuario escribió en el CAPTCHA"},
                            },
                        },
                    },
                },
            },
            "responses": {
                "200": {
                    "description": "Login exitoso. La sesión se establece vía cookie `sid`.",
                    "headers": {
                        "Set-Cookie": {"description": "Cookie de sesión `sid`", "schema": {"type": "string"}},
                    },
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LoginSuccessResponse"}}},
                },
                "400": {"description": "CAPTCHA inválido", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "401": {"description": "Credenciales incorrectas", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/logout": {
        "post": {
            "tags": ["auth"],
            "summary": "Cerrar sesión",
            "description": "Invalida la sesión actual y elimina la cookie.",
            "security": [{"session": []}],
            "responses": {
                "200": {
                    "description": "Sesión cerrada",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SuccessResponse"}}},
                },
                "401": {"description": "Sesión inválida o expirada", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
            },
        }
    },
    "/api/captcha/nuevo": {
        "get": {
            "tags": ["captcha"],
            "summary": "Generar un nuevo CAPTCHA",
            "description": "Devuelve un SVG con el desafío y un token que debe enviarse al iniciar sesión.",
            "responses": {
                "200": {
                    "description": "CAPTCHA generado",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CaptchaResponse"}}},
                },
            },
        },
        "post": {
            "tags": ["captcha"],
            "summary": "Regenerar CAPTCHA",
            "description": "Alternativa POST para regenerar el desafío. Útil para clientes que no soportan GET con body.",
            "responses": {
                "200": {"description": "CAPTCHA generado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CaptchaResponse"}}}},
            },
        },
    },
    "/api/usuarios/rol/transportador": {
        "get": {
            "tags": ["tokens"],
            "summary": "Listar transportadores activos",
            "description": "Devuelve la lista de usuarios con rol `transportador` para asignar entregas.",
            "security": [{"session": []}],
            "responses": {
                "200": {
                    "description": "Lista de transportadores",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/TransportadoresResponse"}}},
                },
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/guias": {
        "get": {
            "tags": ["guias"],
            "summary": "Listar guías (búsqueda)",
            "description": "Búsqueda paginada-ligera con filtros. Devuelve también el conteo por estado.",
            "security": [{"session": []}],
            "parameters": [
                {"name": "q", "in": "query", "schema": {"type": "string"}, "description": "Texto de búsqueda"},
                {"name": "estado", "in": "query", "schema": {"type": "string"}, "description": "Filtrar por estado"},
                {"name": "limite", "in": "query", "schema": {"type": "integer", "default": 200, "maximum": 500}, "description": "Número máximo de resultados"},
                {"name": "transportador", "in": "query", "schema": {"type": "integer"}, "description": "Filtrar por ID de transportador asignado"},
            ],
            "responses": {
                "200": {"description": "Lista de guías", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/GuiaListResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        },
        "post": {
            "tags": ["guias"],
            "summary": "Crear guía",
            "description": "Crea una nueva guía de remisión. El usuario debe tener rol `ventas` o superior.",
            "security": [{"session": []}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/GuiaCreateRequest"}}}},
            "responses": {
                "200": {"description": "Guía creada", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/GuiaCreateResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        },
    },
    "/api/guias/conteo": {
        "get": {
            "tags": ["guias"],
            "summary": "Contar guías por estado",
            "description": "Devuelve el número de guías en cada estado (para el tablero).",
            "security": [{"session": []}],
            "responses": {
                "200": {"description": "Conteo por estado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ConteoResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/guias/estados": {
        "get": {
            "tags": ["guias"],
            "summary": "Catálogo de estados",
            "description": "Devuelve los estados posibles con su etiqueta y color.",
            "security": [{"session": []}],
            "responses": {
                "200": {"description": "Catálogo de estados", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/EstadosResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/guias/{id}": {
        "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}, "description": "ID de la guía"}],
        "get": {
            "tags": ["guias"],
            "summary": "Detalle de guía",
            "description": "Obtiene la guía, sus eventos y el prellenado de ventas.",
            "security": [{"session": []}],
            "responses": {
                "200": {"description": "Detalle de la guía", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/GuiaDetalleResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "404": {"description": "Guía no encontrada", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        },
        "put": {
            "tags": ["guias"],
            "summary": "Editar guía (PUT)",
            "description": "Edición completa o parcial de la guía. Ver también PATCH.",
            "security": [{"session": []}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/GuiaEditRequest"}}}},
            "responses": {
                "200": {"description": "Guía actualizada", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/GuiaEditResponse"}}}},
                "400": {"description": "Bad request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "404": {"description": "Guía no encontrada", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        },
        "patch": {
            "tags": ["guias"],
            "summary": "Editar guía (PATCH)",
            "description": "Edición parcial de la guía. Alias de PUT.",
            "security": [{"session": []}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/GuiaEditRequest"}}}},
            "responses": {
                "200": {"description": "Guía actualizada", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/GuiaEditResponse"}}}},
                "400": {"description": "Bad request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "404": {"description": "Guía no encontrada", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        },
    },
    "/api/guias/{id}/eventos": {
        "get": {
            "tags": ["eventos"],
            "summary": "Historial de eventos",
            "description": "Devuelve el historial de eventos de una guía.",
            "security": [{"session": []}],
            "parameters": [
                {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}},
                {"name": "limite", "in": "query", "schema": {"type": "integer", "default": 100, "maximum": 500}},
            ],
            "responses": {
                "200": {"description": "Historial de eventos", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/EventosResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "404": {"description": "Guía no encontrada", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/guias/{id}/evento/{tipo}": {
        "parameters": [
            {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}},
            {"name": "tipo", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Tipo de evento"},
        ],
        "post": {
            "tags": ["eventos"],
            "summary": "Ejecutar un paso del workflow",
            "description": "Registra un evento/proceso en la guía.",
            "security": [{"session": []}],
            "requestBody": {"required": False, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/EventoRequest"}}}},
            "responses": {
                "200": {"description": "Evento registrado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/EventoResponse"}}}},
                "400": {"description": "Bad request / estado inválido", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "409": {"description": "Transición de estado inválida", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/guias/{id}/transicion/{tipo}": {
        "get": {
            "tags": ["eventos"],
            "summary": "Verificar si una transición es permitida",
            "description": "Comprueba si el usuario actual puede ejecutar una transición sin ejecutarla.",
            "security": [{"session": []}],
            "parameters": [
                {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}},
                {"name": "tipo", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Tipo de evento/transición"},
            ],
            "responses": {
                "200": {"description": "Resultado de la validación", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/TransicionResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/guias/{id}/generar_token_entrega": {
        "post": {
            "tags": ["tokens"],
            "summary": "Generar token de entrega pública",
            "description": "Genera o reutiliza el link público para confirmar la entrega. Requiere rol ventas/admin/administrativo.",
            "security": [{"session": []}],
            "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
            "responses": {
                "200": {"description": "Token y links generados", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/TokenEntregaResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/guias/{id}/asignar_transportador": {
        "post": {
            "tags": ["guias"],
            "summary": "Asignar tipo de transportador",
            "description": "Asigna o actualiza el tipo y transportador de una guía.",
            "security": [{"session": []}],
            "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AsignarTransportadorRequest"}}}},
            "responses": {
                "200": {"description": "Transportador asignado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RedirectResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/guias/{id}/registrar_transportador_externo": {
        "post": {
            "tags": ["guias"],
            "summary": "Registrar transportador externo",
            "description": "Registra un transportador externo (vehículo, placa, etc.) para una guía.",
            "security": [{"session": []}],
            "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RegistrarTransportadorRequest"}}}},
            "responses": {
                "200": {"description": "Resultado del registro", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RegistrarTransportadorResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/guias/{id}/proceso_administrativo_unificado": {
        "post": {
            "tags": ["eventos"],
            "summary": "Proceso administrativo unificado",
            "description": "Ejecuta el proceso administrativo unificado de recepción y asignación para una guía.",
            "security": [{"session": []}],
            "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ProcesoUnificadoRequest"}}}},
            "responses": {
                "200": {"description": "Resultado del proceso", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ProcesoUnificadoResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/guias/{id}/proceso_cedis_unificado": {
        "post": {
            "tags": ["eventos"],
            "summary": "Proceso CEDIS unificado",
            "description": "Ejecuta el proceso CEDIS unificado (control + entrega al transportador) para una guía.",
            "security": [{"session": []}],
            "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ProcesoUnificadoRequest"}}}},
            "responses": {
                "200": {"description": "Resultado del proceso", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ProcesoUnificadoResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/clientes/buscar": {
        "get": {
            "tags": ["clientes"],
            "summary": "Buscar clientes",
            "description": "Búsqueda de clientes por NIT, razón social, ciudad, teléfono, etc. (autocompletado Ventas).",
            "security": [{"session": []}],
            "parameters": [
                {"name": "q", "in": "query", "required": True, "schema": {"type": "string", "minLength": 1}, "description": "Texto de búsqueda"},
                {"name": "limite", "in": "query", "schema": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50}},
            ],
            "responses": {
                "200": {"description": "Resultados de búsqueda", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ClientesBuscarResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/receptores": {
        "get": {
            "tags": ["receptores"],
            "summary": "Consultar receptores",
            "description": "Obtiene receptores filtrados por NIT de cliente o por ID de guía.",
            "security": [{"session": []}],
            "parameters": [
                {"name": "nit", "in": "query", "schema": {"type": "string"}, "description": "NIT del cliente"},
                {"name": "guia", "in": "query", "schema": {"type": "integer"}, "description": "ID de la guía"},
            ],
            "responses": {
                "200": {"description": "Receptores encontrados", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ReceptoresNitResponse"}}}},
                "400": {"description": "Parámetro requerido faltante", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        },
        "post": {
            "tags": ["receptores"],
            "summary": "Registrar receptor",
            "description": "Registra un nuevo receptor/reclamante. Requiere rol admin, administrativo o cedis.",
            "security": [{"session": []}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ReceptorCreateRequest"}}}},
            "responses": {
                "201": {"description": "Receptor registrado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SuccessResponse"}}}},
                "400": {"description": "Bad request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        },
    },
    "/api/receptores/{id}": {
        "delete": {
            "tags": ["receptores"],
            "summary": "Eliminar receptor",
            "description": "Elimina un receptor por su ID temporal. **Solo admin**.",
            "security": [{"session": []}],
            "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}, "description": "ID temporal del receptor"}],
            "responses": {
                "200": {"description": "Receptor eliminado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SuccessResponse"}}}},
                "400": {"description": "ID inválido", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes (solo admin)", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/admin/db/bases": {
        "get": {
            "tags": ["admin-db"],
            "summary": "Listar bases de datos",
            "description": "Lista las bases de datos gestionadas (guias, receptores). Solo admin.",
            "security": [{"session": []}],
            "responses": {
                "200": {"description": "Lista de bases", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/BasesResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/admin/db/tablas": {
        "get": {
            "tags": ["admin-db"],
            "summary": "Listar tablas",
            "description": "Lista las tablas de una base. Solo admin.",
            "security": [{"session": []}],
            "parameters": [{"name": "base", "in": "query", "schema": {"type": "string", "default": "guias"}}],
            "responses": {
                "200": {"description": "Tablas de la base", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/TablasResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/admin/db/esquema": {
        "get": {
            "tags": ["admin-db"],
            "summary": "Describe una tabla",
            "description": "Devuelve columnas, índices y foráneas de una tabla. Solo admin.",
            "security": [{"session": []}],
            "parameters": [
                {"name": "base", "in": "query", "schema": {"type": "string", "default": "guias"}},
                {"name": "tabla", "in": "query", "schema": {"type": "string"}, "required": True},
            ],
            "responses": {
                "200": {"description": "Esquema de la tabla", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/EsquemaResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/admin/db/filas": {
        "get": {
            "tags": ["admin-db"],
            "summary": "Listar filas",
            "description": "Lista filas paginadas de una tabla. Solo admin.",
            "security": [{"session": []}],
            "parameters": [
                {"name": "base", "in": "query", "schema": {"type": "string", "default": "guias"}},
                {"name": "tabla", "in": "query", "schema": {"type": "string"}, "required": True},
                {"name": "q", "in": "query", "schema": {"type": "string"}, "description": "Búsqueda literal"},
                {"name": "pagina", "in": "query", "schema": {"type": "integer", "default": 1}},
                {"name": "page_size", "in": "query", "schema": {"type": "integer", "default": 50, "maximum": 200}},
                {"name": "orden", "in": "query", "schema": {"type": "string"}, "description": "Columna de ordenación"},
                {"name": "dir", "in": "query", "schema": {"type": "string", "enum": ["asc", "desc"], "default": "asc"}},
            ],
            "responses": {
                "200": {"description": "Filas de la tabla", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/FilasResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        },
        "post": {
            "tags": ["admin-db"],
            "summary": "Insertar fila",
            "description": "Inserta una nueva fila en una tabla (con respaldo previo). Solo admin.",
            "security": [{"session": []}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/FilaInsertarRequest"}}}},
            "responses": {
                "200": {"description": "Fila insertada", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SuccessResponse"}}}},
                "400": {"description": "Bad request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}}},
        },
        "delete": {
            "tags": ["admin-db"],
            "summary": "Eliminar fila",
            "description": "Elimina una fila por su clave (con respaldo previo). Solo admin.",
            "security": [{"session": []}],
            "parameters": [
                {"name": "base", "in": "query", "schema": {"type": "string", "default": "guias"}},
                {"name": "tabla", "in": "query", "schema": {"type": "string"}, "required": True},
                {"name": "clave", "in": "query", "schema": {"type": "string"}, "required": True},
            ],
            "responses": {
                "200": {"description": "Fila eliminada", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SuccessResponse"}}}},
                "400": {"description": "Bad request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        },
    },
    "/api/admin/db/actualizar": {
        "post": {
            "tags": ["admin-db"],
            "summary": "Actualizar fila",
            "description": "Actualiza campos de una fila existente (con respaldo previo). Solo admin.",
            "security": [{"session": []}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/FilaActualizarRequest"}}}},
            "responses": {
                "200": {"description": "Fila actualizada", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SuccessResponse"}}}},
                "400": {"description": "Bad request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/admin/db/consulta": {
        "post": {
            "tags": ["admin-db"],
            "summary": "Ejecutar consulta SQL",
            "description": "Ejecuta una consulta SELECT o (con confirmación) escritura. Solo admin. "
                         "Las consultas de escritura requieren `confirmar: true` y crean un respaldo automático.",
            "security": [{"session": []}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ConsultaRequest"}}}},
            "responses": {
                "200": {"description": "Resultado de la consulta", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ConsultaResponse"}}}},
                "400": {"description": "Bad request / confirmación requerida", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/admin/db/respaldos": {
        "get": {
            "tags": ["admin-db"],
            "summary": "Listar respaldos",
            "description": "Lista los respaldos disponibles de una base. Solo admin.",
            "security": [{"session": []}],
            "parameters": [{"name": "base", "in": "query", "schema": {"type": "string", "default": "guias"}}],
            "responses": {
                "200": {"description": "Lista de respaldos", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RespaldosResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/admin/db/respaldo/descargar": {
        "get": {
            "tags": ["admin-db"],
            "summary": "Descargar respaldo",
            "description": "Descarga un respaldo como archivo binario. Solo admin.",
            "security": [{"session": []}],
            "parameters": [{"name": "archivo", "in": "query", "schema": {"type": "string"}, "required": True, "description": "Nombre del archivo de respaldo"}],
            "responses": {
                "200": {"description": "Archivo binario del respaldo", "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}},
                "404": {"description": "Respaldo no encontrado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/admin/db/respaldo/crear": {
        "post": {
            "tags": ["admin-db"],
            "summary": "Crear respaldo",
            "description": "Crea y verifica un respaldo de una base. Solo admin.",
            "security": [{"session": []}],
            "requestBody": {"required": False, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RespaldoCrearRequest"}}}},
            "responses": {
                "200": {"description": "Respaldo creado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RespaldoResponse"}}}},
                "400": {"description": "Bad request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/admin/db/respaldo/restaurar": {
        "post": {
            "tags": ["admin-db"],
            "summary": "Restaurar respaldo",
            "description": "Restaura un respaldo (verifica integridad antes). Solo admin.",
            "security": [{"session": []}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RespaldoRestaurarRequest"}}}},
            "responses": {
                "200": {"description": "Respaldo restaurado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RespaldoResponse"}}}},
                "400": {"description": "Bad request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/admin/db/respaldo": {
        "delete": {
            "tags": ["admin-db"],
            "summary": "Eliminar respaldo",
            "description": "Elimina un archivo de respaldo. Solo admin.",
            "security": [{"session": []}],
            "parameters": [{"name": "archivo", "in": "query", "schema": {"type": "string"}, "required": True}],
            "responses": {
                "200": {"description": "Respaldo eliminado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SuccessResponse"}}}},
                "400": {"description": "Bad request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/admin/db/migraciones": {
        "get": {
            "tags": ["admin-db"],
            "summary": "Listar migraciones",
            "description": "Lista todas las migraciones aplicadas y pendientes. Solo admin.",
            "security": [{"session": []}],
            "responses": {
                "200": {"description": "Historial de migraciones", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/MigracionesResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/admin/db/migraciones/aplicar": {
        "post": {
            "tags": ["admin-db"],
            "summary": "Aplicar migraciones",
            "description": "Aplica las migraciones pendientes. Solo admin.",
            "security": [{"session": []}],
            "responses": {
                "200": {"description": "Migraciones aplicadas", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SuccessResponse"}}}},
                "400": {"description": "Bad request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/admin/db/auditoria": {
        "get": {
            "tags": ["admin-db"],
            "summary": "Ver auditoría",
            "description": "Historial de acciones de administración de la BD. Solo admin.",
            "security": [{"session": []}],
            "parameters": [
                {"name": "limite", "in": "query", "schema": {"type": "string", "default": "100"}},
                {"name": "offset", "in": "query", "schema": {"type": "string", "default": "0"}},
                {"name": "accion", "in": "query", "schema": {"type": "string"}, "description": "Filtrar por tipo de acción"},
                {"name": "usuario", "in": "query", "schema": {"type": "string"}, "description": "Filtrar por usuario"},
            ],
            "responses": {
                "200": {"description": "Historial de auditoría", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AuditoriaResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/admin/db/mantenimiento": {
        "post": {
            "tags": ["admin-db"],
            "summary": "Ejecutar mantenimiento",
            "description": "Ejecuta una operación de mantenimiento (vacuum, etc.). Solo admin.",
            "security": [{"session": []}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/MantenimientoRequest"}}}},
            "responses": {
                "200": {"description": "Mantenimiento ejecutado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SuccessResponse"}}}},
                "400": {"description": "Bad request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/usuarios": {
        "post": {
            "tags": ["admin"],
            "summary": "Crear usuario",
            "description": "Crea un nuevo usuario. Requiere rol admin.",
            "security": [{"session": []}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/UsuarioCreateRequest"}}}},
            "responses": {
                "200": {"description": "Usuario creado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RedirectResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/usuarios/{usuario}/restablecer_clave": {
        "post": {
            "tags": ["admin"],
            "summary": "Restablecer clave de usuario",
            "description": "Restablece la contraseña de un usuario. Requiere rol admin.",
            "security": [{"session": []}],
            "parameters": [{"name": "usuario", "in": "path", "required": True, "schema": {"type": "string"}}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RestablecerClaveRequest"}}}},
            "responses": {
                "200": {"description": "Contraseña restablecida", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SuccessResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/config": {
        "post": {
            "tags": ["admin"],
            "summary": "Actualizar configuración",
            "description": "Actualiza configuración del sistema. Requiere rol admin.",
            "security": [{"session": []}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ConfigUpdateRequest"}}}},
            "responses": {
                "200": {"description": "Configuración actualizada", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RedirectResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/clave": {
        "post": {
            "tags": ["admin"],
            "summary": "Cambiar contraseña propia",
            "description": "Cambia la contraseña del usuario autenticado.",
            "security": [{"session": []}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ClaveChangeRequest"}}}},
            "responses": {
                "200": {"description": "Contraseña actualizada", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SuccessResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "400": {"description": "Bad request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/exportar.csv": {
        "get": {
            "tags": ["admin"],
            "summary": "Exportar guías a CSV",
            "description": "Exporta las guías a CSV. Requiere rol admin o administrativo.",
            "security": [{"session": []}],
            "responses": {
                "200": {"description": "Archivo CSV", "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/loadtest/ultimo.csv": {
        "get": {
            "tags": ["loadtest"],
            "summary": "Exportar reporte CSV de load test",
            "description": "Genera y descarga el reporte CSV del último load test. Solo admin.",
            "security": [{"session": []}],
            "responses": {
                "200": {"description": "Archivo CSV", "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/loadtest/ultimo.xlsx": {
        "get": {
            "tags": ["loadtest"],
            "summary": "Exportar reporte XLSX de load test",
            "description": "Genera y descarga el reporte XLSX del último load test. Solo admin.",
            "security": [{"session": []}],
            "responses": {
                "200": {"description": "Archivo XLSX", "content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {"schema": {"type": "string", "format": "binary"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "Permisos insuficientes", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/ai/generate": {
        "get": {
            "tags": ["ai"],
            "summary": "Generar texto con IA (GET)",
            "description": "Genera texto usando un proveedor de IA gratuito. Requiere sesión autenticada.",
            "security": [{"session": []}],
            "parameters": [
                {"name": "prompt", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Texto de entrada"},
                {"name": "proveedor", "in": "query", "schema": {"type": "string", "default": "huggingface"}, "description": "Proveedor de IA"},
                {"name": "model", "in": "query", "schema": {"type": "string"}, "description": "Modelo específico"},
                {"name": "temperature", "in": "query", "schema": {"type": "number", "minimum": 0, "maximum": 1}},
                {"name": "max_tokens", "in": "query", "schema": {"type": "integer"}, "description": "Máximo de tokens"},
            ],
            "responses": {
                "200": {"description": "Respuesta de IA", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AiGenerateResponse"}}}},
                "400": {"description": "Prompt requerido", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "500": {"description": "Error del proveedor", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        },
        "post": {
            "tags": ["ai"],
            "summary": "Generar texto con IA (POST)",
            "description": "Genera texto usando un proveedor de IA gratuito. Requiere sesión autenticada.",
            "security": [{"session": []}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AiGeneratePostRequest"}}}},
            "responses": {
                "200": {"description": "Respuesta de IA", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AiGenerateResponse"}}}},
                "400": {"description": "Prompt requerido", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "401": {"description": "No autenticado", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "500": {"description": "Error del proveedor", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/ai/info": {
        "get": {
            "tags": ["ai"],
            "summary": "Información de proveedores de IA",
            "description": "Lista proveedores disponibles y sus modelos. No requiere autenticación.",
            "responses": {
                "200": {"description": "Info de proveedores", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AiInfoResponse"}}}},
                "500": {"description": "Error del servicio", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/api/ai/health": {
        "get": {
            "tags": ["ai"],
            "summary": "Salud del servicio de IA",
            "description": "Verifica el estado del servicio de IA. No requiere autenticación.",
            "responses": {
                "200": {"description": "Estado del servicio", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AiHealthResponse"}}}},
                "500": {"description": "Error del servicio", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
    "/firma/{token}": {
        "get": {
            "tags": ["firma-publica"],
            "summary": "Página de firma pública",
            "description": "Página HTML (no JSON) para que el cliente confirme la entrega sin login. Acceso público.",
            "parameters": [{"name": "token", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Token de entrega pública"}],
            "responses": {
                "200": {"description": "Página HTML de firma", "content": {"text/html": {"schema": {"type": "string"}}}},
                "404": {"description": "Token inválido o expirado", "content": {"text/html": {"schema": {"type": "string"}}}},
                "422": {"description": "Token no activo aún", "content": {"text/html": {"schema": {"type": "string"}}}},
            },
        }
    },
    "/api/firma_publica/{token}": {
        "post": {
            "tags": ["firma-publica"],
            "summary": "Confirmar entrega por link",
            "description": "Confirma la entrega de la guía usando un token público. Acceso público.",
            "parameters": [{"name": "token", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Token de entrega pública"}],
            "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/FirmaPublicaRequest"}}}},
            "responses": {
                "200": {"description": "Entrega confirmada", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/FirmaPublicaResponse"}}}},
                "404": {"description": "Token inválido", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
            },
        }
    },
}

COMPONENTS = {
    "securitySchemes": {
        "session": {
            "type": "apiKey",
            "in": "cookie",
            "name": "sid",
            "description": "Cookie de sesión obtenida al iniciar sesión en /api/login. "
                           "Requiere CAPTCHA válido. El cookie se establece como HttpOnly, SameSite=Lax (o None+Secure en producción).",
        },
    },
    "schemas": {
        "ErrorResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": False},
                "error": {"type": "string", "example": "Descripción del error"},
            },
            "required": ["ok", "error"],
        },
        "SuccessResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "msg": {"type": "string", "example": "Operación completada"},
                "redirect": {"type": "string", "example": "/tablero"},
            },
            "required": ["ok"],
        },
        "RedirectResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "redirect": {"type": "string", "example": "/admin"},
            },
            "required": ["ok", "redirect"],
        },
        "CaptchaResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "svg": {"type": "string", "description": "SVG del CAPTCHA para renderizar"},
                "token": {"type": "string", "description": "Token a enviar al hacer login"},
            },
            "required": ["ok", "svg", "token"],
        },
        "LoginSuccessResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "redirect": {"type": "string", "example": "/tablero"},
            },
            "required": ["ok", "redirect"],
        },
        "TransportadoresResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "transportadores": {
                    "type": "array",
                    "items": {"type": "object", "properties": {
                        "id": {"type": "integer"},
                        "usuario": {"type": "string"},
                        "nombre": {"type": "string"},
                    }},
                },
            },
            "required": ["ok", "transportadores"],
        },
        "GuiaCreateRequest": {
            "type": "object",
            "description": "Datos para crear una guía. Incluye información del cliente, receptor y totales.",
            "properties": {
                "cliente": {"type": "string", "example": "900123456-7 · Tienda Ejemplo"},
                "nit_cliente": {"type": "string", "example": "900123456-7"},
                "destino": {"type": "string", "example": "Bogotá, Cundinamarca"},
                "valor": {"type": "string", "example": "150000"},
                "totales": {"type": "object", "description": "Objeto con cajas, bolsas, sobres, cayvas"},
                "tipo": {"type": "string", "enum": ["normal", "directo"], "description": "Tipo de envío"},
                "obs_ventas": {"type": "string"},
                "documentos": {"type": "string", "example": "FACTURA #12345"},
            },
            "required": ["cliente"],
        },
        "GuiaCreateResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "id": {"type": "integer", "example": 42},
                "redirect": {"type": "string", "example": "/guia/42"},
            },
            "required": ["ok", "id", "redirect"],
        },
        "GuiaEditRequest": {
            "type": "object",
            "description": "Campos editables de la guía (los no enviados se conservan).",
            "properties": {
                "cliente": {"type": "string"},
                "nit_cliente": {"type": "string"},
                "destino": {"type": "string"},
                "valor": {"type": "string"},
                "totales": {"type": "object"},
                "tipo": {"type": "string"},
                "obs_ventas": {"type": "string"},
                "documentos": {"type": "string"},
                "dispositivo": {"type": "string"},
            },
        },
        "GuiaEditResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "redirect": {"type": "string", "example": "/guia/42"},
                "mensaje": {"type": "string"},
                "guia": {"type": "object", "description": "Guía actualizada"},
                "evento_id": {"type": "integer"},
            },
            "required": ["ok", "redirect", "mensaje"],
        },
        "GuiaListResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "guias": {"type": "array", "items": {"type": "object"}, "description": "Lista de guías"},
                "total": {"type": "integer", "example": 15},
                "conteo_por_estado": {"type": "object", "description": "Conteo por estado"},
            },
            "required": ["ok", "guias", "total", "conteo_por_estado"],
        },
        "ConteoResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "conteo": {"type": "object", "description": "Conteo por estado"},
            },
            "required": ["ok", "conteo"],
        },
        "EstadosResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "estados": {
                    "type": "array",
                    "items": {"type": "object", "properties": {
                        "clave": {"type": "string"},
                        "info": {"type": "object"},
                    }},
                },
            },
            "required": ["ok", "estados"],
        },
        "GuiaDetalleResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "guia": {"type": "object", "description": "Datos completos de la guía"},
                "eventos": {"type": "array", "items": {"type": "object"}, "description": "Historial de eventos"},
                "prellenado": {"type": "object", "description": "Datos prellenados de ventas"},
                "estado_info": {"type": "object", "properties": {
                    "estado": {"type": "string"},
                    "etiqueta": {"type": "string"},
                    "clase": {"type": "string"},
                }},
            },
            "required": ["ok", "guia", "eventos", "prellenado", "estado_info"],
        },
        "EventosResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "eventos": {"type": "array", "items": {"type": "object"}},
                "total": {"type": "integer"},
                "truncado": {"type": "boolean"},
            },
            "required": ["ok", "eventos", "total", "truncado"],
        },
        "EventoRequest": {
            "type": "object",
            "description": "Datos del evento. Pueden variar según el tipo de evento.",
            "properties": {
                "dispositivo": {"type": "string", "example": "web"},
            },
        },
        "EventoResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "mensaje": {"type": "string", "example": "Paso registrado"},
                "evento_id": {"type": "integer"},
                "guia": {"type": "object"},
                "eventos": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["ok", "mensaje", "evento_id"],
        },
        "TransicionResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "permitida": {"type": "boolean", "example": True},
                "mensaje": {"type": "string"},
                "rol_requerido": {"type": "string"},
            },
            "required": ["ok", "permitida"],
        },
        "TokenEntregaResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "ya_emitido": {"type": "boolean", "example": False},
                "token": {"type": "string"},
                "link": {"type": "string", "format": "uri"},
                "whatsapp": {"type": "string", "format": "uri"},
                "email": {"type": "string"},
                "resumen": {"type": "object"},
                "emision": {"type": "object"},
            },
            "required": ["ok", "ya_emitido", "token", "link"],
        },
        "AsignarTransportadorRequest": {
            "type": "object",
            "properties": {
                "tipo": {"type": "string", "description": "Tipo de transportador"},
                "transportador_asignado_id": {"type": "integer", "description": "ID del transportador asignado"},
            },
        },
        "RegistrarTransportadorRequest": {
            "type": "object",
            "properties": {
                "transportador_nombre": {"type": "string"},
                "transportador_cc": {"type": "string"},
                "transportador_tel": {"type": "string"},
                "transportador_vehiculo": {"type": "string"},
                "transportador_placa": {"type": "string"},
                "transportador_flete": {"type": "string"},
                "cliente_recibe_nombre": {"type": "string"},
                "firma_transportador": {"type": "string"},
            },
        },
        "RegistrarTransportadorResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "msg": {"type": "string"},
                "info": {"type": "object"},
                "redirect": {"type": "string"},
            },
        },
        "ProcesoUnificadoRequest": {
            "type": "object",
            "properties": {
                "dispositivo": {"type": "string", "example": "web"},
            },
        },
        "ProcesoUnificadoResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "msg": {"type": "string"},
                "info": {"type": "object"},
            },
        },
        "ClientesBuscarResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "resultados": {"type": "array", "items": {"type": "object"}, "description": "Clientes encontrados"},
                "query": {"type": "string"},
                "total": {"type": "integer"},
            },
            "required": ["ok", "resultados", "query", "total"],
        },
        "ReceptorCreateRequest": {
            "type": "object",
            "required": ["nit_cliente", "tipo_doc", "nombres_apellidos", "numero_doc"],
            "properties": {
                "nit_cliente": {"type": "string", "description": "NIT del cliente (FK)"},
                "guia_relacionada_id": {"type": "integer", "description": "ID de guía (FK, opcional)"},
                "tipo_doc": {"type": "string", "enum": ["CC", "CE", "TI", "PAS", "NIT", "RC", "Otro"]},
                "nombres_apellidos": {"type": "string"},
                "numero_doc": {"type": "string"},
                "telefono": {"type": "string"},
                "email": {"type": "string"},
                "parentesco_reclamante": {"type": "string"},
            },
        },
        "ReceptoresNitResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "nit": {"type": "string"},
                "total": {"type": "integer"},
                "data": {"type": "array", "items": {"type": "object"}},
            },
        },
        "BasesResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "bases": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["ok", "bases"],
        },
        "TablasResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "tablas": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["ok", "tablas"],
        },
        "EsquemaResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "esquema": {"type": "object", "description": "Columnas, índices y foráneas de la tabla"},
            },
            "required": ["ok", "esquema"],
        },
        "FilasResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "datos": {"type": "object", "description": "Datos tabulares, conteo y paginación"},
            },
        },
        "FilaInsertarRequest": {
            "type": "object",
            "required": ["tabla", "valores"],
            "properties": {
                "base": {"type": "string", "example": "guias"},
                "tabla": {"type": "string", "example": "clientes"},
                "valores": {"type": "object", "description": "Mapa de columna -> valor"},
            },
        },
        "FilaActualizarRequest": {
            "type": "object",
            "required": ["tabla", "clave", "valores"],
            "properties": {
                "base": {"type": "string", "example": "guias"},
                "tabla": {"type": "string"},
                "clave": {"type": "string", "description": "Clave primaria del registro"},
                "valores": {"type": "object", "description": "Mapa de columna -> nuevo valor"},
            },
        },
        "ConsultaRequest": {
            "type": "object",
            "required": ["sql"],
            "properties": {
                "base": {"type": "string", "example": "guias"},
                "sql": {"type": "string", "description": "Consulta SQL"},
                "escritura": {"type": "boolean", "example": False, "description": "True si es una operación de escritura"},
                "confirmar": {"type": "boolean", "example": False, "description": "Obligatorio si escritura=true"},
            },
        },
        "ConsultaResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "resultado": {"description": "Resultado de la consulta"},
                "respaldo": {"type": "string", "description": "Nombre del respaldo creado (si aplica)"},
            },
        },
        "RespaldosResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "respaldos": {"type": "array", "items": {"type": "object"}},
            },
        },
        "RespaldoCrearRequest": {
            "type": "object",
            "properties": {
                "base": {"type": "string", "example": "guias"},
                "motivo": {"type": "string", "example": "manual"},
            },
        },
        "RespaldoRestaurarRequest": {
            "type": "object",
            "required": ["archivo"],
            "properties": {
                "archivo": {"type": "string", "description": "Nombre del archivo de respaldo"},
            },
        },
        "RespaldoResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "mensaje": {"type": "string"},
                "respaldo": {"type": "string"},
            },
        },
        "MantenimientoRequest": {
            "type": "object",
            "required": ["operacion"],
            "properties": {
                "operacion": {"type": "string", "enum": ["vacuum", "integrity_check"], "example": "vacuum"},
            },
        },
        "MigracionesResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "migraciones": {"type": "array", "items": {"type": "object"}},
            },
        },
        "AuditoriaResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "historial": {"type": "array", "items": {"type": "object"}},
                "acciones": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["ok", "historial", "acciones"],
        },
        "UsuarioCreateRequest": {
            "type": "object",
            "required": ["usuario", "nombre", "clave", "rol"],
            "properties": {
                "usuario": {"type": "string"},
                "nombre": {"type": "string"},
                "clave": {"type": "string", "format": "password"},
                "rol": {"type": "string", "enum": ["ventas", "administrativo", "cedis", "admin", "transportador"]},
            },
        },
        "RestablecerClaveRequest": {
            "type": "object",
            "required": ["clave_nueva"],
            "properties": {
                "clave_nueva": {"type": "string", "format": "password"},
            },
        },
        "ConfigUpdateRequest": {
            "type": "object",
            "description": "Datos de configuración a actualizar.",
            "additionalProperties": True,
        },
        "ClaveChangeRequest": {
            "type": "object",
            "required": ["clave_actual", "clave_nueva"],
            "properties": {
                "clave_actual": {"type": "string", "format": "password"},
                "clave_nueva": {"type": "string", "format": "password"},
            },
        },
        "FirmaPublicaRequest": {
            "type": "object",
            "properties": {
                "firma": {"type": "string", "description": "Firma digital o foto en base64"},
                "cliente_recibe_nombre": {"type": "string"},
                "obs": {"type": "string"},
            },
        },
        "FirmaPublicaResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean", "example": True},
                "redirect": {"type": "string", "example": "/firma/abc123?entregada=1"},
            },
            "required": ["ok", "redirect"],
        },
        "AiGeneratePostRequest": {
            "type": "object",
            "required": ["prompt"],
            "properties": {
                "prompt": {"type": "string"},
                "proveedor": {"type": "string", "example": "huggingface"},
                "model": {"type": "string"},
                "temperature": {"type": "number", "minimum": 0, "maximum": 1},
                "max_tokens": {"type": "integer"},
            },
        },
        "AiGenerateResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "respuesta": {"type": "string"},
                "proveedor": {"type": "string"},
                "error": {"type": "string"},
            },
        },
        "AiInfoResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "proveedores": {"type": "array", "items": {"type": "object"}},
                "proveedor_por_defecto": {"type": "string"},
            },
        },
        "AiHealthResponse": {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "saludable": {"type": "boolean"},
                "proveedores_disponibles": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}


def build_spec() -> dict:
    """Construye y devuelve el diccionario completo de la especificación OpenAPI 3.1."""
    spec = {
        "openapi": "3.1.0",
        "info": INFO,
        "servers": SERVERS,
        "tags": TAGS,
        "paths": PATHS,
        "components": COMPONENTS,
    }
    return spec


def spec_yaml() -> str:
    """Serializa la especificación a YAML (string)."""
    return yaml.dump(
        build_spec(),
        allow_unicode=True,
        sort_keys=False,
        width=120,
        default_flow_style=False,
    )


# HTML estático para Swagger UI 5, sirviéndose localmente.
# Se apoya en archivos descargados en /static/swagger/
SWAGGER_UI_HTML = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Guías Coodescor — API Docs (Swagger UI)</title>
  <link rel="stylesheet" href="/static/swagger/swagger-ui.css">
  <style>
    html, body { margin: 0; padding: 0; height: 100%; }
    #swagger-ui { height: 100%; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="/static/swagger/swagger-ui-bundle.js"></script>
  <script src="/static/swagger/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = function() {
      window.ui = SwaggerUIBundle({
        url: '/openapi.yaml',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [SwaggerUIBundle.presets.apis],
        plugins: [SwaggerUIBundle.plugins.DownloadUrl],
        layout: 'StandaloneLayout',
      });
    };
  </script>
</body>
</html>"""

# HTML estático para ReDoc, sirviéndose localmente.
REDOCK_HTML = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Guías Coodescor — API Docs (ReDoc)</title>
  <style>
    html, body { margin: 0; padding: 0; height: 100%; }
    #redoc-container { height: 100vh; }
  </style>
</head>
<body>
  <div id="redoc-container"></div>
  <script src="/static/redoc/redoc-init-wrapper.js"></script>
  <script>
    window.onload = function() {
      initReDoc({
        specUrl: '/openapi.yaml',
        scrollYOffset: 50,
      });
    };
  </script>
</body>
</html>"""


def get_swagger_ui_html() -> str:
    return SWAGGER_UI_HTML


def get_redoc_html() -> str:
    return REDOCK_HTML
