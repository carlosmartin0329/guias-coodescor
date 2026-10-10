# Bitácora de Desarrollo de Software: Sistema de Guías Coodescor

## Información General del Proyecto

**Nombre del Proyecto:** Sistema Local de Actas de Entrega Digitales para Transporte de Mercancías - "Guías Coodescor"
**Fecha de Inicio:** 2026-09-01 (Referencia histórica)
**Fecha de Finalización Esperada:** Por definir según alcance
**Equipo de Desarrollo:** [Equipo responsable]
**Gerencia / Cliente:** Coodescor
**Ubicación del Repositorio:** D:\Users\57323\Downloads\guias coodescor

### Descripción del Proyecto

Sistema web local de actas de entrega digitales para transporte de mercancías. Funciona 100% sin internet, sin dependencias externas (solo Python 3 estándar + SQLite) y se accede desde navegador de PC o móvil en la misma red Wi-Fi.

**Alcance Principal:**
- Gestión de guías de entrega con múltiples estados (Creada, En Bodega/Recepción, En CEDIS, En Ruta, Entregada, Anulada)
- Control de bultos (Cajas, Bolsas, Cayvas, Sobres)
- Sistema de roles diferenciados (Ventas, Administrativo, CEDIS, Admin Sistema)
- Recepción, control CEDIS, entrega a transportador y entrega final al cliente
- Adjuntos (firmas digitales, fotos) almacenados localmente
- Exportación CSV para Excel
- Documentación OpenAPI disponible
- Importación de base de clientes desde Excel
- Autocompletado de NIT/Cliente en Ventas

### Tecnologías Utilizadas

| Componente | Tecnología | Versión |
|---|---|---|
| Backend | Python HTTP Server (stdlib) | Python 3.11+ |
| Base de Datos | SQLite | Incorporado a Python |
| Frontend | HTML, CSS, JavaScript | Vanilla (sin frameworks) |
| Build Frontend | Vite | 6.x |
| React | React | 19.x |
| CORS/Proxy | Vite Dev Server | Configurado |
| QR (opcional) | segno | Según requirements.txt |
| Servidor Desarrollo | ThreadingHTTPServer | stdlib |

### Estructura del Proyecto

```
guias_coodescor/
├── guias_coodescor/        # Paquete principal (app, api, services, web, core, database)
├── frontend/               # Frontend React + Vite
├── static/                 # Archivos estáticos servidos
├── data/                   # BD SQLite, logs, adjuntos (en C:\ProgramData\Coodescor\Guias)
├── tests/                  # Pruebas (test_*.py)
├── README.md              # Documentación general
└── *.md                   # Informes, revisiones, debug
```

---

## 1. FASE 1: RECOLECCIÓN DE INFORMACIÓN Y REQUISITOS

### 1.1 Objetivo de la Fase
Recopilar, documentar y validar todos los requisitos funcionales, no funcionales, reglas de negocio y restricciones del sistema.

### 1.2 Actividades Realizadas

- [ ] **Levantamiento inicial:** Identificación del problema y necesidades del negocio
- [ ] **Revisión de documentación existente:** README, review.md, debug-*.md, CAMBIOS_ANDROID.md
- [ ] **Análisis del sistema actual:** Revisión de código fuente, BD, flujo de estados
- [ ] **Identificación de usuarios/actores:** 5 roles identificados (admin, administrativo, ventas, ventas2-4, cedis)
- [ ] **Mapeo de procesos de negocio:** Creación → Recepción Bodega → CEDIS → Entrega Transportador → Entrega Cliente
- [ ] **Recolección de requisitos de integración:** Clientes desde Excel, OpenAPI, ngrok para pruebas externas
- [ ] **Definición de restricciones técnicas:** 100% local, sin internet, solo stdlib Python

### 1.3 Requisitos Funcionales (RF)

| ID | Requisito | Prioridad | Estado | Observaciones |
|---|---|---|---|---|
| RF-01 | Gestión de guías (crear, ver, imprimir) | Alta | Completado | Operado por Ventas |
| RF-02 | Recepción en Bodega por rol "administrativo" | Alta | Completado | Solo recepción, sin creación usuarios |
| RF-03 | Control CEDIS: conteo de bultos por tipo | Alta | Completado | Cajas/Bolsas/Cayvas/Sobres |
| RF-04 | Entrega al transportador | Alta | Completado | Requiere CEDIS funcionario |
| RF-05 | Entrega final al cliente (firma + foto) | Alta | Completado | Validaciones aplicadas |
| RF-06 | Anulación con justificación | Alta | Completado | Solo roles autorizados |
| RF-07 | Envío directo a CEDIS | Alta | Completado | Flag `envio_directo` |
| RF-08 | Gestión de usuarios y roles | Alta | Completado | Panel Admin |
| RF-09 | Búsqueda/autocompletado clientes por NIT | Alta | Completado | Normalización NIT sin guiones |
| RF-10 | Documentación OpenAPI (/openapi.yaml, /docs, /redoc) | Media | Completado | 46 rutas, 52 schemas |
| RF-11 | Importación clientes desde Excel | Media | Completado | 154 registros importados |
| RF-12 | Dropdown CEDIS funcionario en flujos CEDIS | Media | Completado | Visible en 3 ubicaciones |

### 1.4 Requisitos No Funcionales (RNF)

| ID | Requisito | Prioridad | Estado | Observaciones |
|---|---|---|---|---|
| RNF-01 | Funcionamiento 100% offline/local | Crítica | Completado | Sin dependencias externas |
| RNF-02 | Acceso desde red Wi-Fi local | Alta | Completado | http://[IP-PC]:8000 |
| RNF-03 | Almacenamiento local (SQLite + archivos) | Crítica | Completado | En C:\ProgramData\Coodescor\Guias |
| RNF-04 | Seguridad: sesiones HttpOnly, rate-limit login | Alta | Completado | Implementado en core/security.py |
| RNF-05 | Validación de inputs | Alta | Completado | core/validators.py |
| RNF-06 | Logging rotativo | Media | Completado | guias_coodescor.log |
| RNF-07 | CORS configurable para desarrollo | Media | Completado | Permite origen ngrok en dev |
| RNF-08 | Compatibilidad móvil (Android) | Media | Completado | Ver CAMBIOS_ANDROID.md |

### 1.5 Stakeholders

- **Usuario Final (Ventas):** Creación de guías
- **Usuario Final (Administrativo/Bodega):** Recepción
- **Usuario Final (CEDIS):** Control y entrega
- **Administrador Sistema:** Configuración, usuarios, anulación
- **Cliente/Patrocinador:** Revisión y aprobación

### 1.6 Entregables Fase 1
- [x] Documento de requisitos (README.md actualizado)
- [x] Matriz RF/RNF
- [x] Diagrama de flujo de estados
- [x] Identificación de actores
- [x] Acta de inicio del proyecto

**Estado Fase 1:** COMPLETADO

---

## 2. FASE 2: MODELADO DE DATOS

### 2.1 Objetivo de la Fase
Diseñar el modelo de datos relacional que soporte la lógica del negocio.

### 2.2 Entidades Identificadas

| Entidad | Descripción | Clave Primaria |
|---|---|---|
| usuarios | Usuarios del sistema con roles | id |
| guias | Guías de entrega principal | id (o numero_guia) |
| eventos | Auditoría y trazabilidad de cambios de estado | id |
| receptores_temporales | Receptores temporales para flujo específico | id |

### 2.3 Esquema Detallado (guias)

Campos relevantes según models.py:
- id, numero_guia (único)
- fecha_creacion, usuario_creacion
- cliente_nombre, cliente_nit, cliente_direccion, cliente_ciudad, cliente_telefono
- receptor_nombre, receptor_identificacion, receptor_direccion, receptor_telefono
- transportador_nombre, transportador_identificacion, transportador_placa, transportador_telefono
- tipo_envio (normal / directo)
- envio_directo (bool)
- estado (creada, en_bodega, en_cedis, en_ruta, entregada, anulada)
- bultos: cajas, bolsas, cayvas, sobres (enteros)
- cedis_funcionario
- quien_entrega, quien_recibe
- observaciones, motivo_anulacion
- firmas, fotos (rutas)
- timestamps y campos de auditoría

### 2.4 Relaciones
- guias.usuario_creacion → usuarios.id
- eventos.guia_id → guias.id
- eventos.usuario_id → usuarios.id

### 2.5 Índices y Constraints
- UNIQUE(numero_guia)
- FOREIGN KEYs con ON DELETE/RESTRICT según lógica
- Índices para búsquedas por estado, fechas, cliente

### 2.6 Migraciones
Ubicadas en `database/migrations/`:
- V2_campos_auditoria.sql
- V3_envio_directo_rol_administrativo.sql

### 2.7 Datos Maestros
- Roles: admin_sistema, administrativo, ventas, cedis
- Tipos de bulto: cajas, bolsas, cayvas, sobres
- Usuarios iniciales seed en models.py

### 2.8 Entregables Fase 2
- [x] Diagrama entidad-relación (implícito en models.py)
- [x] DDL SQLite
- [x] Diccionario de datos
- [x] Script de inicialización/migraciones
- [x] Validación de integridad referencial

**Estado Fase 2:** COMPLETADO

---

## 3. FASE 3: DISEÑO FUNCIONAL

### 3.1 Objetivo de la Fase
Definir la arquitectura funcional, flujos de trabajo, reglas de negocio y diseño de API/UI.

### 3.2 Arquitectura General

**Patrón:** Modular monolítico
- `core/` - Utilidades, seguridad, validadores, logging
- `services/` - Lógica de negocio (auth, guias, eventos, export)
- `api/router.py` - HTTP routing + CORS + OpenAPI
- `web/views/` - Renderizado HTML server-side
- `database/` - Conexión, modelos, migraciones
- `static/` - CSS/JS cliente

**Servidor:** ThreadingHTTPServer (stdlib), puerto 8000 por defecto

### 3.3 Flujos de Estado de Guía

| Estado | Actor Permitido | Transición Hacia | Reglas |
|---|---|---|---|
| CREADA | Ventas/Admin | EN_BODEGA / ANULADA | Requiere datos mínimos. Envío directo puede saltar flujo |
| EN_BODEGA | Administrativo | EN_CEDIS / ANULADA | Solo rol "administrativo". Firma recepción |
| EN_CEDIS | CEDIS | EN_RUTA / ANULADA | Conteo bultos obligatorio. Requiere cedis_funcionario |
| EN_RUTA | CEDIS | ENTREGADA / ANULADA | Entrega a transportador registrada |
| ENTREGADA | Sistema (audit) | - | Estado terminal (no editable) |
| ANULADA | Autorizados | - | Estado terminal. Requiere motivo |

### 3.4 Casos de Uso Principales

| CU | Actor | Descripción | Estado |
|---|---|---|---|
| CU-01 | Ventas | Crear nueva guía | Completado |
| CU-02 | Ventas | Crear guía con envío directo | Completado |
| CU-03 | Administrativo | Recibir guía en bodega | Completado |
| CU-04 | CEDIS | Registrar control CEDIS | Completado |
| CU-05 | CEDIS | Entregar a transportador | Completado |
| CU-06 | CEDIS | Entregar al cliente (firma+foto) | Completado |
| CU-07 | Admin/Ventas autorizados | Anular guía | Completado |
| CU-08 | Admin | Gestionar usuarios | Completado |
| CU-09 | Todos (autenticados) | Consultar/listar guías | Completado |
| CU-10 | Ventas | Buscar cliente por NIT (autocomplete) | Completado |

### 3.5 Diseño de API REST

**Base:** `/api/*` proxied vía Vite en dev

Endpoints implementados (OpenAPI 46 paths):
- `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`
- `/api/guias/crear`, `/api/guias/listar`, `/api/guias/detalle/:id`, `/api/guias/transicion`
- `/api/guias/recepcion_bodega`, `/api/guias/cedis_control`, `/api/guias/cedis_entrega_transporte`, `/api/guias/cedis_entrega_cliente`
- `/api/clientes/buscar` - Búsqueda NIT/razón social
- `/api/admin/*` - Administración DB/usuarios
- `/openapi.yaml`, `/docs`, `/redoc`

### 3.6 Diseño UI/UX

**Server-side rendered HTML** con CSS/JS vanilla.
- Login con captcha
- Dashboard por rol con filtros
- Wizard/flujo paso a paso para transiciones
- Stepper de estados visual
- Modal/autocompletado NIT
- Responsive (móvil Android) - ver CAMBIOS_ANDROID.md

### 3.7 Reglas de Negocio Críticas

1. **Normalización NIT:** Eliminar caracteres no numéricos y ceros a la izquierda antes de consultar BD (buscar_clientes)
2. **CEDIS funcionario obligatorio:** En transiciones que requieren CEDIS (entrega transporte, control según flujo)
3. **Solo "administrativo":** Puede ejecutar recepción bodega exclusivamente
4. **Estados terminales:** ENTREGADA y ANULADA no permiten modificaciones
5. **Envío directo:** Puede omitir paso "EN_BODEGA" según lógica de negocio
6. **Unicidad número guía:** Generación/validación única
7. **Rate-limit login:** Protección contra brute-force
8. **Sesiones con expiración:** Timeout configurable

### 3.8 Entregables Fase 3
- [x] Arquitectura técnica documentada
- [x] Diagrama de flujos (estados + casos uso)
- [x] Especificación API (OpenAPI)
- [x] Diseño UI componentes
- [x] Matriz permisos por rol
- [x] Reglas de negocio formalizadas

**Estado Fase 3:** COMPLETADO

---

## 4. FASE 4: IMPLEMENTACIÓN Y DESARROLLO

### 4.1 Objetivo de la Fase
Desarrollar, integrar y probar los componentes según diseño.

### 4.2 Períodos de Desarrollo (Informe Quincenal)

Se documentarán aquí los avances quincenales (cada 15 días). Rellenar al cierre de cada periodo.

#### PERIODO Q-01: [dd-mm-yyyy] a [dd-mm-yyyy]

**Objetivo del Periodo:** Inicialización y reestructuración modular

**Actividades Realizadas:**
- [x] Reestructuración del proyecto a arquitectura modular
- [x] Implementación core/ (utils, security, validators, logging)
- [x] Implementación services/ (auth, guias, eventos, export)
- [x] Migración de rutas a api/router.py
- [x] Separación views (web/views/)
- [x] Configuración database layer

**Funcionalidades Completadas:**
- Base modular funcional
- Autenticación y sesiones
- CRUD básico guías
- Transiciones de estado base

**Hitos Técnicos Alcanzados:**
- Servidor stdlib funcional
- SQLite con WAL/FC
- Sistema de logging

**Incidencias/Desviaciones:** Ninguna significativa
**Próximos Pasos:** Completar flujos CEDIS

**Responsable:** [Equipo]
**% Avance Periodo:** 100%

---

#### PERIODO Q-02: [dd-mm-yyyy] a [dd-mm-yyyy]

**Objetivo del Periodo:** Flujos CEDIS, roles y validaciones

**Actividades Realizadas:**
- [x] Implementación flujo recepción bodega (rol administrativo)
- [x] Implementación control CEDIS
- [x] Implementación entrega transportador
- [x] Implementación entrega cliente (firma+foto)
- [x] Envío directo a CEDIS
- [x] Mejoras en validaciones

**Funcionalidades Completadas:**
- Flujo completo CEDIS
- Control de bultos
- Adjuntos (firmas/fotos)

**Hitos Técnicos:** Integración completa de transiciones
**Avance:** 100%

---

#### PERIODO Q-03: [10-10-2026 inicio aprox] - Periodo reciente

**Objetivo del Periodo:** OpenAPI, CEDIS dropdown, NIT autocomplete, integración clientes Excel

**Actividades Realizadas:**
- [x] Corrección openapi_spec.py (merge conflicts, sintaxis)
- [x] Wiring rutas /openapi.yaml, /docs, /redoc en router.py
- [x] Adición dropdown "Funcionario CEDIS" en 3 ubicaciones (envío directo, flujo normal, ya ejecutado read-only)
- [x] Normalización NIT en buscar_clientes() (strip non-digits, leading zeros)
- [x] Importación 154 clientes desde "Base de datos cliente V2.xlsx"
- [x] Corrección CORS para permitir ngrok en dev
- [x] Fix test_api_guias.py (indentación)
- [x] Fix transicion_guia_api response shape
- [x] Ajustes CSS frontend/static (card/grid layout review)
- [x] Verificación end-to-end autocomplete con ngrok

**Funcionalidades Completadas:**
- Documentación OpenAPI accesible
- Selector funcionario CEDIS funcional
- Autocompletado NIT con datos Excel
- CORS resuelto para pruebas remotas

**Hitos Técnicos Alcanzados:**
- 103 core tests OK
- 14/14 API integration tests OK (aislados)
- Service buscar_clientes() retorna resultados correctamente
- Servidor estable con ngrok

**Incidencias:** Cache navegador afectó visibilidad dropdown (resuelto con hard refresh)
**Próximos Pasos:** Ajustes UI menores si requeridos, monitoreo estabilidad

**% Avance Periodo:** 100%

#### PERIODO Q-04: [dd-mm-yyyy] a [dd-mm-yyyy]
*(Completar en futuro)*

**Objetivo:** ...
**Actividades:** ...
**Funcionalidades:** ...
**Hitos:** ...
**Avance:** __%

#### PERIODO Q-05: [dd-mm-yyyy] a [dd-mm-yyyy]
*(Completar según duración proyecto)*

---

### 4.3 Métricas de Desarrollo

| Métrica | Valor | Observaciones |
|---|---|---|
| Archivos Python | ~40 | Paquete modular + scripts |
| Líneas de código aprox | ~8000-10000 | Estimado |
| Tests ejecutados | 117+ | Core + API integration |
| Tests OK | 117 | 100% pass |
| Endpoints API | 46 | En OpenAPI |
| Schemas OpenAPI | 52 | Validación estructural |
| Clientes importados | 154 | Desde Excel |
| Roles implementados | 5 | admin, administrativo, ventas(1-4), cedis |

### 4.4 Control de Versiones

**Rama activa:** main
**Commits relevantes:** Merge commits + agent host sessions (histórico)
**Estado working tree:** limpio (tras cambios CSS revertidos)

### 4.5 Entregables Fase 4
- [x] Código fuente funcional
- [x] Tests unitarios/integración pasando
- [x] Documentación técnica inline
- [x] Scripts de arranque (run.bat/run.ps1/run_app.py)
- [x] Configuración dev/prod
- [x] Informes quincenales (Q-01 a Q-03 documentados)

**Estado Fase 4:** EN PROGRESO (mayor funcionalidad completa)

---

## 5. FASE 5: PRUEBAS Y VALIDACIÓN

### 5.1 Objetivo de la Fase
Verificar calidad, funcionalidad, seguridad y cumplimiento de requisitos.

### 5.2 Estrategia de Pruebas

- **Pruebas unitarias:** Validación servicios (clientes_service, guias_service)
- **Pruebas integración API:** test_api_guias.py (14 casos)
- **Pruebas sistema completo:** test_sistema.py (103 casos)
- **Pruebas específicas:** clientes_receptores, db_admin, CORS
- **Pruebas manuales:** Flujos end-to-end con navegador + ngrok
- **Pruebas regresión:** Tras cada fix crítico

### 5.3 Matriz de Pruebas

| ID Test | Alcance | Tipo | Resultado | Fecha |
|---|---|---|---|---|
| T-01 | Core sistema (test_sistema.py) | Sistema | 103/103 PASS | 2026-10-10 |
| T-02 | API guías (test_api_guias.py) | Integración | 14/14 PASS | 2026-10-10 |
| T-03 | Clientes receptores | Integración | PASS | 2026-10-10 |
| T-04 | Admin DB | Integración | PASS | 2026-10-10 |
| T-05 | CORS | Integración | PASS | 2026-10-10 |
| T-06 | Login/auth | Sistema | PASS | Verificado |
| T-07 | Flujo completo CEDIS | E2E Manual | OK | 2026-10-10 |
| T-08 | Autocomplete NIT | E2E Manual | OK (ngrok) | 2026-10-10 |
| T-09 | OpenAPI endpoints | Manual | OK (/openapi.yaml, /docs, /redoc) | 2026-10-10 |
| T-10 | Dropdown CEDIS funcionario | Manual | OK (3 ubicaciones) | 2026-10-10 |

### 5.4 Validación de Requisitos

| RF | Validado Por | Evidencia | OK |
|---|---|---|---|
| RF-01 a RF-09 | Tests + manual | test_sistema, test_api_guias | Sí |
| RF-10 | Manual HTTP 200 | curl/browser /openapi.yaml,/docs,/redoc | Sí |
| RF-11 | Manual + BD | 154 registros importados | Sí |
| RF-12 | Manual UI | Dropdown presente 3 ubicaciones | Sí |

### 5.5 Pruebas de Seguridad

- [x] Rate-limit login implementado
- [x] Sesiones HttpOnly
- [x] Validación inputs (core/validators.py)
- [x] Rutas seguras con auth_required
- [x] Control permisos por rol
- [x] Sanitización de rutas (adjuntos)
- [x] SQL con parámetros (evita SQLi)

### 5.6 Pruebas Compatibilidad

| Plataforma | Navegador | Estado | Notas |
|---|---|---|---|
| Windows 10/11 | Chrome/Edge | OK | Desarrollo/pruebas |
| Android | Chrome móvil | OK | Según CAMBIOS_ANDROID.md |
| Windows | Firefox | Pendiente validación | Generalmente compatible |

### 5.7 Bugs Corregidos

| Fecha | Bug | Solución | Estado |
|---|---|---|---|
| 2026-10-10 | openapi_spec.py merge conflicts (missing `},`) | Reparado sintaxis, validado compilación | Resuelto |
| 2026-10-10 | test_api_guias.py indentation error (self a nivel módulo) | Corregida indentación | Resuelto |
| 2026-10-10 | transicion_guia_api response shape incorrecto | Ajustado a {"ok":true,"puede":bool,"razon":str} | Resuelto |
| 2026-10-10 | NIT autocomplete: formato con guiones vs normalizado | Normalización en buscar_clientes() | Resuelto |
| 2026-10-10 | CORS bloqueaba ngrok | Fallback permite any origin en dev | Resuelto |

### 5.8 Entregables Fase 5
- [x] Plan de pruebas ejecutado
- [x] Matriz de pruebas con resultados
- [x] Reporte de bugs y correcciones
- [x] Validación requisitos 100%
- [x] Checklist seguridad básica
- [x] Evidencias de pruebas (logs/tests)

**Estado Fase 5:** COMPLETADO (validación satisfactoria)

---

## 6. FASE 6: DESPLIEGUE Y CIERRE

### 6.1 Objetivo de la Fase
Preparar para puesta en producción/local, documentar y cerrar ciclo.

### 6.2 Preparación Despliegue Local

**Requisitos de servidor:**
- Windows PC (o Linux) con Python 3.11+
- Red Wi-Fi local accesible
- Espacio disco para BD + adjuntos (~MBs inicial)
- Puerto 8000 libre

**Pasos despliegue:**
1. Copiar proyecto a ruta destino
2. Verificar Python disponible (py -3)
3. Ejecutar run.bat / run.ps1 / run_app.py
4. Acceder http://localhost:8000 o http://[IP]:8000
5. Cambiar claves usuarios iniciales en Panel Admin
6. Verificar rutas datos: C:\ProgramData\Coodescor\Guias

### 6.3 Configuración de Datos

**Ubicación datos:** `C:\ProgramData\Coodescor\Guias\` (definido por core/paths.py)
- `guias.db` - Base de datos
- `guias_coodescor.log` - Logs
- `adjuntos/` - Firmas y fotos

**Respaldo recomendado:**
- Copiar carpeta completa periódicamente
- Exportar CSV desde sistema (Exportar a Excel)

### 6.4 Documentación Entregada

| Documento | Ubicación | Estado |
|---|---|---|
| README.md | Raíz | Actualizado |
| review.md | Raíz | Sprint 03 documentado |
| CAMBIOS_ANDROID.md | Raíz | Adaptaciones Android |
| GUIA_ANTIGRAVITY.md | Raíz | Guía uso Gemini |
| debug-*.md | Raíz | Sesiones debug cerradas |
| reporte_contraste_WCAG_AA.md | Raíz | Accesibilidad |
| OpenAPI Spec | /openapi.yaml (vivo) | Generado dinámicamente |
| Este documento BITACORA.md | Raíz (crear) | En elaboración |

### 6.5 Checklist Despliegue

- [x] Código estable (tests OK)
- [x] Configuración paths correcta
- [x] Scripts arranque probados
- [x] Usuarios iniciales documentados
- [x] Seguridad básica aplicada
- [x] Logs configurados
- [x] CORS ajustado para contexto
- [ ] Respaldos definidos
- [ ] Instrucciones operación entregadas a cliente
- [ ] Monitoreo post-despliegue planificado

### 6.6 Cierre Proyecto

**Criterios de cierre:**
- [x] Todos RF críticos completados
- [x] Pruebas satisfactorias
- [x] Documentación mínima entregada
- [x] Funcionalidad validada end-to-end

**Estado General:** FUNCIONAL - LISTO PARA USO LOCAL

**Fecha Cierre Propuesto:** [Por confirmar con cliente]

### 6.7 Lecciones Aprendidas

1. **Arquitectura modular stdlib:** Funciona bien, evita dependencias externas
2. **Normalización datos:** Crítico para autocompletado (NIT con guiones)
3. **CORS en dev:** ngrok requiere ajustes; fallback por origen vacío útil
4. **Tests aislados:** test_api_guias requiere imports correctos (indentación)
5. **Cache navegador:** Afecta CSS/JS tras cambios - hard refresh necesario
6. **OpenAPI merge conflicts:** Requiere revisión cuidadosa sintaxis

---

## 7. SEGUIMIENTO QUINCENAL (PLANTILLA REUTILIZABLE)

Usar esta sección para cada nuevo informe quincenal. Copiar y completar.

### REPORTE QUINCENAL N° [XX] | Periodo: DD-MM-YYYY a DD-MM-YYYY

**Elaborado por:** [Nombre]
**Revisado por:** [Nombre]
**Fecha elaboración:** DD-MM-YYYY

#### 7.1 Resumen Ejecutivo (2-3 líneas)
[Describir estado general, logros principales]

#### 7.2 Avance por Fase
| Fase | % Completado | Estado | Comentarios |
|---|---|---|---|
| F1 Requisitos | __% | ☐ Pendiente ☐ En Proceso ☐ Completo | |
| F2 Modelo Datos | __% | ☐ Pendiente ☐ En Proceso ☐ Completo | |
| F3 Diseño Funcional | __% | ☐ Pendiente ☐ En Proceso ☐ Completo | |
| F4 Implementación | __% | ☐ Pendiente ☐ En Proceso ☐ Completo | |
| F5 Pruebas/Validación | __% | ☐ Pendiente ☐ En Proceso ☐ Completo | |
| F6 Despliegue/Cierre | __% | ☐ Pendiente ☐ En Proceso ☐ Completo | |

#### 7.3 Funcionalidades Completadas esta Quincena
- [ ] Item 1 (ID RF/Task)
- [ ] Item 2
- [ ] ...

#### 7.4 Funcionalidades en Progreso
- [ ] Item con % avance estimado
- [ ] ...

#### 7.5 Hitos Técnicos Alcanzados
- [Descripción técnica relevante]

#### 7.6 Issues/Bugs Abiertos/Cerrados
| ID | Título | Severidad | Estado | Fecha | Comentario |
|---|---|---|---|---|---|
| BUG-XX | ... | Alta/Media/Baja | Abierto/Cerrado | DD-MM | |

#### 7.7 Riesgos Identificados
| Riesgo | Probabilidad (A/M/B) | Impacto (A/M/B) | Mitigación | Responsable |
|---|---|---|---|---|
| ... | A/M/B | A/M/B | ... | ... |

#### 7.8 Próximas Actividades (Próxima Quincena)
- [ ] Actividad 1 - Prioridad Alta
- [ ] Actividad 2 - Prioridad Media
- [ ] Actividad 3 - Prioridad Baja

#### 7.9 Métricas Quincenales
| Métrica | Inicio Quincena | Fin Quincena | Variación |
|---|---|---|---|
| Commits | __ | __ | __ |
| Tests PASS | __ | __ | __ |
| Archivos modificados | __ | __ | __ |
| Líneas + / - | __ | __ | __ |

#### 7.10 Aprobación
**Aprobado por Cliente:** ___________ Fecha: ___________
**Aprobado por Líder Técnico:** ___________ Fecha: ___________

---

## 8. ANEXOS

### 8.1 Comandos Útiles para Seguimiento

```bash
# Ejecutar servidor
py -3 run_app.py

# Ejecutar todos los tests
py -m pytest -v

# Tests específicos
py -m pytest test_sistema.py -v
py -m pytest test_api_guias.py -v

# Ver logs servidor
type guias_coodescor\data\guias_coodescor.log | tail -30

# Verificar puertos
netstat -ano | findstr :8000
```

### 8.2 Referencias
- README.md (documentación general)
- review.md (Sprint 03)
- GUIA_ANTIGRAVITY.md (desarrollo con IA)
- OpenAPI: http://127.0.0.1:8000/docs (cuando servidor activo)

### 8.3 Contactos/Responsables
- **Desarrollo:** [Equipo/Kilo AI]
- **Cliente:** Coodescor
- **Repositorio:** github.com/carlosmartin0329/guias-coodescor

---

**VERSIÓN DEL DOCUMENTO:** 1.0
**FECHA CREACIÓN:** 2026-10-15
**ÚLTIMA ACTUALIZACIÓN:** 2026-10-15
**AUTOR:** Sistema de Documentación (Generado por Kilo)
**ESTADO:** ACTIVO - EN USO CONTINUO
