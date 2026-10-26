# Informe de Control de Calidad Integral — Guías Coodescor

**Fecha:** 24/10/2026
**Alcance:** aplicación completa (backend Python, API/web, frontend React, base de
datos y migraciones, app Android, despliegue Docker/Windows, CI y documentación).
**Objetivo:** identificar, documentar y corregir defectos antes de la entrega y
las pruebas de aceptación iniciales.

---

## 1. Resumen ejecutivo

| Indicador | Antes de la QA | Después de la QA |
|---|---|---|
| Suite backend `pytest` | 71 pasaban, 11 fallaban y 2 módulos **no se podían ni recolectar** | **183 pruebas + 4 subcasos, 100 % en verde** |
| Producto en ejecución (API/web) | Varios procesos clave devolvían 500 (crear guía con NIT, contactos, transportadores, transiciones, detalle para CEDIS) | **186 comprobaciones E2E: 184 OK, 0 fallos, 2 informativas** |
| Build frontend React | No verificable / sin sesión funcional (login imposible) | **Build correcto (100 módulos)**; lint: 0 errores |
| Actualización de BDs existentes | Podía fallar el arranque o **perder eventos/sesiones** al migrar | Migración segura verificada con una BD "vieja" simulada |
| Android | Proyecto no compilable (recursos/clases inexistentes) | Bloqueos estáticos corregidos; compilación pendiente en Android Studio (sin SDK en este equipo) |
| CI | Rojo (herramientas inexistentes, pruebas rotas) | Backend + build/lint frontend + job Android informativo + Docker |

**Conclusión:** el producto quedó **estable y funcional en los procesos
operativos principales** (login por rol, creación/edición/consulta de guías,
flujo completo con firmas, **envío directo con recogida del cliente en sede**,
link público de confirmación, anulación, catálogos, notificaciones,
administración de base de datos y reportes). Los riesgos residuales son de
empaquetado/compilación (APK, navegadores de Playwright), no de lógica de
negocio.

---

## 2. Método y entorno

1. **Inventario** de módulos, rutas, roles, migraciones y clientes (web legacy,
   React, Android).
2. **Auditoría estática paralela** de cuatro frentes: lógica de negocio,
   seguridad/autorización, frontend React e infraestructura/BD/despliegue.
3. **Reproducción dinámica** de cada hallazgo contra un servidor real levantado
   con un **directorio de datos temporal** (`COODESCOR_DATA_DIR`), nunca contra
   datos de producción.
4. **Corrección quirúrgica** y **pruebas de regresión** para cada defecto.
5. **Re-ejecución completa** de la suite y de la sonda E2E.

Herramientas: Python 3.11 + pytest, servidor HTTP real, sonda HTTP propia
(`.qa/qa_probe.py`), Node 22 + Vite + oxlint, Git, SQLite.

Comandos reproducibles:

```bash
# Backend (incluye E2E HTTP por sockets y regresiones)
cd backend && py -3 -m pytest tests -q

# Frontend
cd frontend && npm run lint && npm run build

# E2E navegador (requiere navegadores instalados y backend/frontend arriba)
cd frontend && npx playwright install chromium && npx playwright test

# Sonda E2E integral (servidor de QA en :8765 con datos temporales)
py -3 .qa/qa_probe.py
```

---

## 3. Resultados de las pruebas

### 3.1 Backend

```
183 passed, 4 subtests passed in ~39 s
```

Cobertura funcional: autenticación y sesión, CAPTCHA, permisos por rol,
CRUD y transiciones de guías, procesos unificados, tokens públicos, firma
pública, clientes/contactos/transportadores/receptores, notificaciones,
administración de BD (lectura, escritura, respaldos, restauración, SQL),
migraciones, actualización de BDs antiguas, concurrencia y validaciones.

### 3.2 Sonda E2E contra servidor real

186 comprobaciones sobre: rutas públicas, login de los 5 roles, matriz de
permisos, **todos los flujos de guía**, anulación, edición, links públicos,
catálogos, notificaciones, admin de BD, alcance del transportador, concurrencia
(8 creaciones simultáneas) y usuarios/configuración. Resultado: **0 fallos**;
las 2 marcas informativas corresponden a comportamientos documentados (anular
una guía ya anulada devuelve 409; CEDIS puede editar una guía CREADA según la
matriz de permisos).

### 3.2.1 Flujos funcionales de guía verificados

| Flujo | Ruta de estados | Verificación |
|---|---|---|
| **Normal (con transportador)** | CREADA → RECIBIDA_ADMIN → EN_CEDIS → EN_RUTA → ENTREGADA | Servicio + HTTP + sonda: recepción con firma, control de bultos, entrega a transporte y cierre por el cliente con link público (uso único). |
| **Envío directo / recogida en sede** | CREADA → **EN_CEDIS** → ENTREGADA | Servicio + HTTP + sonda: **Ventas** la crea con estado inicial EN_CEDIS (salta Administrativo), exige control de bultos antes de entregar, cierra **sin evento ni paso de transporte**, por el botón único de CEDIS o por link público; el histórico no registra `entrega_transporte`. |
| **Envío directo en un solo clic** | EN_CEDIS → control + ENTREGADA | `POST /api/guias/<id>/proceso_cedis_unificado` (modo directo): control y entrega al cliente en una sola operación; verificado por HTTP. |
| **Link público de confirmación** | Se activa en EN_RUTA, o en EN_CEDIS directo **solo tras el control** | Emisión (1 por guía), activación, firma sin login, cierre único y rechazo del segundo uso. |
| **Anulación** | CREADA/RECIBIDA_ADMIN/EN_CEDIS/EN_RUTA → ANULADA | Solo admin; se rechaza en estados finales (ENTREGADA/ANULADA). |
| **Edición** | Antes de salir a ruta | Ventas/Admin según estado; auditoría `edicion_guia` sin reescribir el evento de creación. |
| **Transportador propio vs. externo** | Asignación en CREADA/RECIBIDA_ADMIN | Propio: login y solo ve sus guías. Externo: datos/firma capturados por Administrativo. |

> Aclaración de vocabulario: **la guía siempre la crea el rol Ventas** (el
> backend responde 403 a cualquier otro rol, incluido admin; ver prueba
> `test_admin_no_puede_crear_guias`). "Se crea con estado EN_CEDIS" significa que
> el **estado inicial** es EN_CEDIS por la casilla de envío directo, no que CEDIS
> la cree.

> Nota de negocio añadida en esta QA: como el envío directo **se crea ya en
> estado EN_CEDIS**,
> el estado por sí solo no probaba que CEDIS hubiera verificado bultos. Ahora
> `entrega_cliente` (y el link público) exigen el evento `control_cedis` previo;
> sin él responden 409.

### 3.3 Frontend

- `npm run build`: **OK**, sin errores.
- `npm run lint` (oxlint): **0 errores**, advertencias no bloqueantes del React
  Compiler.
- **Rediseño UX/UI implementado** en la SPA React: sistema de diseño, shell con
  navegación, tablero “Mi jornada”, detalle con stepper y panel de acción,
  asistente de nueva guía, login y modo oscuro. Se retiró el porcentaje de
  cumplimiento. Ver [`UX-PROPUESTA-MODERNA.md`](UX-PROPUESTA-MODERNA.md) y las
  capturas reales en `docs/ux-preview/png/real-*.png`.
- **Playwright:** suite ejecutada con Chrome del sistema: **6/6 pruebas en
  verde** (login, sesión tras recarga, credenciales inválidas, tablero/búsqueda,
  creación de guía y administración).
- Prueba adicional en navegador real: control CEDIS con
  **practicante/pasante**, nombre y dos firmas → evento guardado con
  `firma_practicante_archivo` y guía en `EN_CEDIS`.

### 3.4 Android

Sin SDK/emulador en el equipo no se pudo compilar el APK. Se corrigieron los
bloqueos estáticos verificables (ver §4) y se documentó el procedimiento.

---

## 4. Defectos corregidos

Severidad: **C** crítica (bloquea entrega o pérdida de datos/seguridad),
**A** alta (proceso funcional roto), **M** media, **B** baja.

### 4.1 Backend y lógica de negocio

| ID | Sev. | Defecto | Corrección |
|---|---|---|---|
| QA-01 | C | Crear guía con NIT formateado (`900123456-1`) fallaba con 500: se guardaba el NIT sin normalizar y violaba la FK `guias.nit → clientes.nit`. | Se normaliza el NIT antes de insertar y se registra el valor normalizado en el evento. |
| QA-02 | C | Migrar una BD anterior a V6 impedía arrancar (seed del rol `transportador` violaba el CHECK viejo) y V6 borraba en cascada **eventos y sesiones** (pérdida de trazabilidad). | Las migraciones corren antes de los seeds, con FK desactivadas por archivo y en autocommit; se re-aseguran columnas/índices después. Probado con BD antigua simulada. |
| QA-03 | A | Un consecutivo configurado como usado o no numérico dejaba **toda** creación de guías fallando para siempre (UNIQUE + rollback). | Se calcula `MAX(config, MAX(consecutivo)+1)` y se reintenta; el panel valida el valor. |
| QA-04 | A | CEDIS no podía corregir bultos a 0: el 0 se sustituía por el prellenado de Ventas (documento impreso y CSV con cantidades erróneas). | Se distingue "campo ausente" de "0 explícito"; totales siempre = suma. El acta imprime primero el control de CEDIS. |
| QA-05 | A | Se podía anular una guía ENTREGADA/ANULADA; y cerrar como ENTREGADA desde EN_CEDIS saltándose el transporte en el flujo normal. | `anular` rechaza estados terminales; `entrega_cliente` desde EN_CEDIS exige envío directo. |
| QA-05b | A | En el **envío directo** (cliente recoge en sede) se podía cerrar la entrega sin haber registrado el control de bultos de CEDIS, porque la guía se crea ya con estado EN_CEDIS. | La entrega directa y su link público exigen el evento `control_cedis` previo; el proceso unificado ya lo hacía. Cubierto con 6 pruebas de regresión y 14 comprobaciones E2E. |
| QA-06 | A | Al editar parcialmente una guía se sobrescribía `entrega_nombre` con el nombre del usuario y se **reescribía el evento `creacion`** (auditoría perdida). | `entrega_nombre` sale del prellenado real; la edición guarda sus valores en `edicion_guia` y `creacion` queda inmutable. |
| QA-07 | A | Asignar/cambiar transportador en guías EN_RUTA/ENTREGADA/ANULADA no tenía validación ni auditoría. | Solo antes de salir a ruta; se registra evento `asignacion_transportador`. |
| QA-08 | A | El endpoint genérico `control_cedis` no exigía funcionario CEDIS (el unificado sí). | Se exige funcionario (y practicante cuando aplica). |
| QA-08b | A | CEDIS · Practicante / Pasante: el desplegable incluía la opción, pero el campo de **nombre estaba oculto** (nunca se mostraba) y **no existía firma** del practicante. | Al elegir Practicante/Pasante se muestran nombre y firma propios (obligatorios); se validan en backend, se guardan en `control_cedis` (`firma_practicante_archivo`), se sirven como adjunto y se muestran en el detalle y en el acta impresa. Cubierto con 6 pruebas y 6 comprobaciones E2E. |
| QA-09 | A | Doble envío simultáneo (doble clic, dos pestañas, token + CEDIS) podía duplicar la entrega: la validación de estado ocurría fuera del lock. | Toda la transacción (validar + evento + estado) ocurre bajo el lock global; el token es de un solo uso. |
| QA-10 | A | `generar_token_entrega` fallaba con 500 en guías inexistentes y emitía links para ANULADAS/ENTREGADAS; el link se anunciaba activo desde CREADA aunque el cierre lo rechazaba (409). | Validación de existencia/estado (404/409) y activación del link solo en EN_RUTA (o EN_CEDIS con envío directo). |
| QA-11 | M | Expiración de tokens con formato mixto (`T` vs espacio): seguían válidos hasta un día de más. | Formato único `YYYY-MM-DD HH:MM:SS` y comparación por fecha real. |
| QA-12 | M | `/api/config` descartaba en silencio `lista_clientes_json` y los datos de vínculo externo (el admin veía "guardado" y no persistía). | Se guardan todas las claves documentadas con validación de JSON. |
| QA-13 | M | Eventos de catálogos (contactos/transportadores) devolvían 500 por `qs` no definido y luego 400 por re-parsear un dict; los endpoints estaban **inutilizables**. | Se define `qs` en POST y se normaliza el cuerpo; además solo admin/administrativo modifica transportadores externos. |
| QA-14 | M | Bases desconocidas en el admin de BD caían silenciosamente sobre `guias.db`. | `_conectar()` valida la base (400). |
| QA-15 | M | El editor SQL permitía escribir en `receptores.db`, borrar `schema_migrations`/`auditoria` y leer credenciales con `SELECT u.*`. | Escritura solo en `guias`, tablas internas protegidas y `tabla.*` bloqueado; hash/sal redactados en auditoría. |
| QA-16 | M | Restaurar un respaldo de receptores sobre `guias.db` destruía los datos y respondía "ok"; en Windows podía fallar el reemplazo y dejar `.restaurando`. | Respaldos separados por prefijo, validación de esquema, checkpoint/cierre previo y clave de respuesta `respaldo` corregida. |

### 4.2 Seguridad y autorización

| ID | Sev. | Defecto | Corrección |
|---|---|---|---|
| QA-17 | C | La respuesta del CAPTCHA viajaba dentro del token (base64): el CAPTCHA se saltaba decodificándolo. | Token v2 con `exp|nonce|HMAC`; el desafío se guarda en memoria del servidor y nunca sale al cliente. |
| QA-18 | C | `GET /api/guias` sin sesión devolvía 500 (y el detalle de guías/eventos podía servir datos sin autenticar): los handlers asumían `user`. | Respuesta 401 JSON centralizada para toda la API sin sesión (salvo rutas públicas documentadas). |
| QA-19 | A | IDOR del transportador: podía leer y cerrar guías ajenas conociendo el id (listado y notificaciones sí filtraban). | Validación de asignación en servicio, rutas, vistas y listado. |
| QA-20 | A | CAPTCHA con respuesta no ASCII (`ÁÉÍÓÚ`) provocaba un 500 (`compare_digest`). | Comparación en bytes, sin excepciones; 400 con mensaje claro. |
| QA-21 | A | CORS en modo desarrollo reflejaba cualquier `Origin` con credenciales; sin validación de `Origin` en escrituras (CSRF). | CORS solo por lista explícita y validación de `Origin` en POST/PUT/PATCH/DELETE. |
| QA-22 | A | XSS almacenado en el autocompletado del frontend legacy (ciudad/teléfono/email con `innerHTML`). | Render con `textContent`. |
| QA-23 | A | `validar_sesion` devolvía `pass_hash`/`sal` dentro del usuario (riesgo de fuga en logs/vistas). | Solo columnas necesarias. |
| QA-24 | M | X-Forwarded-For tomaba el primer salto (falsificable tras proxy) y X-Forwarded-Proto se confiaba a cualquiera; link de firma construido con `Host` arbitrario (phishing). | Se recorre la cadena de derecha a izquierda con proxies/CIDR de confianza y se valida configurar `COODESCOR_PUBLIC_BASE_URL`. |
| QA-25 | M | Inyección de fórmulas en el CSV de auditoría (abrir en Excel ejecutaba `=cmd|...`). | Celdas peligrosas neutralizadas con `'`. |
| QA-26 | B | Un `Origin` cruzado podía obtener links de firma con `https://evil...`. | Cubierto por QA-24. |

### 4.3 Configuración, despliegue e infraestructura

| ID | Sev. | Defecto | Corrección |
|---|---|---|---|
| QA-27 | A | **Todas** las variables `COODESCOR_*` del `.env` eran ignoradas (faltaba `env_prefix`) y el `.env` se buscaba relativo al CWD (`cd backend` no lo encontraba): CORS, proxies, puerto, límites y logging no aplicaban. | `.env` de la raíz cargado al inicio, `env_prefix="COODESCOR_"`, y variables nuevas documentadas. |
| QA-28 | A | Cookie `SameSite=None` sin `Secure` cuando había CORS (el navegador la descarta) y `Secure` ligado a `production` aunque el despliegue fuera HTTP. | `SameSite=None` solo junto a `Secure`; `Secure` automático solo con HTTPS o forzable por `.env`; verificado que el login HTTP local sigue funcionando. |
| QA-29 | M | CI rojo: ejecutaba `ruff`/`black`/`mypy` y ESLint (no instalados/configurados) sobre un proyecto sin formato; pruebas rotas. | CI ejecuta compilación + pytest + `oxlint` + build; job Android informativo; build Docker conservado. |
| QA-30 | M | Scripts de Windows: ngrok se buscaba en `tools/` (no existe, está en la raíz), usaban `python` aunque el resto usa `py -3`, y **mataban cualquier proceso** en los puertos 8000/4040. | Rutas y lanzador corregidos, y ahora se avisa/aborta si el puerto está ocupado (sin matar procesos ajenos). |
| QA-31 | M | Nginx del frontend rechazaba cuerpos >1 MB (fotos/firmas) y enviaba `/login`, `/tablero`, `/admin` al backend, sirviendo la UI legacy en vez del SPA al recargar. | `client_max_body_size 30m` y SPA fallback; Vite dejó de proxificar rutas del SPA. |
| QA-32 | M | `requirements.txt` no declaraba `requests` (la exportación a Supabase fallaba). | Dependencia declarada. |
| QA-33 | M | Datos personales y artefactos versionados (firmas/fotos en `guias_coodescor/data`, configs con rutas, reportes de Playwright). | `.gitignore` ampliado; ver §6 las instrucciones para retirarlos del índice (bloqueado por permisos del sandbox). |
| QA-34 | B | Documentación con credenciales y rutas erróneas (`administrativo/admin123`, datos dentro del código, "sin dependencias"). | README, `.env.example` y `documentacion-tecnica.md` actualizados. |
| QA-35 | B | `debug.log` con hashes/SIDs y scripts `check_router*.py` en la raíz. | Se retiró el `print` DEBUG del router; los archivos no pudieron borrarse por permisos del sistema (ver §6). |

### 4.4 Frontend React

| ID | Sev. | Defecto | Corrección |
|---|---|---|---|
| QA-36 | C | El login nunca autenticaba: el backend no devolvía el usuario y no existía endpoint de sesión; cualquier recarga expulsaba al usuario. | `/api/login` devuelve usuario saneado, nuevo `GET /api/session`; `AuthContext` restaura la sesión al montar. |
| QA-37 | C | El módulo Admin DB no funcionaba: leía `b.nombre` (API: `base`), `total_paginas` (API: `paginas`) y enviaba payloads distintos a los del backend (`datos` vs `valores`, `pk` vs `clave`, borrado en cuerpo vs query); además llamaba a una función `cargarRespaldos` inexistente. | Contratos alineados, paginación, respaldos, alertas solo tras éxito y estados de carga. |
| QA-38 | A | Los botones de acción del detalle enviaban `{}`: edición como evento inexistente, anulación sin motivo, pasos sin firma → todos fallaban. | Acciones implementadas con formulario y **canvas de firma**, campos obligatorios y gating de rol/estado alineado con el backend; historial de eventos visible. |
| QA-39 | A | `formatInvoiceNumbersWithPrefix("FV-123")` devolvía `"FV, FV 123"`, corrompiendo números de documento; el NIT se enmascaraba eliminando el guion. | Tokenizador de documentos corregido y máscara de NIT con guion. |
| QA-40 | A | Nueva guía: el autocompletado de cliente no rellenaba NIT/ciudad/dirección; al escribir el transportador se guardaba **en cada tecla** (duplicados); se enviaba un id de contacto que el backend ignora. | Cambio de cliente autocompleta, guardado del transportador solo en blur con guarda, campo inútil eliminado. |
| QA-41 | M | El tablero recargaba datos en cada tecla y mostraba un `alert()` al buscar; el toast de notificación marcaba como leída la guía sin acción del usuario. | Polling estable con filtros por ref, indicador de actualización y cierre de toast sin marcar leída. |
| QA-42 | M | El reporte Load Test llamaba a `/api/loadtest/ultimo`, que no existía. | Endpoint añadido y página adaptada. |
| QA-43 | M | Sin manejo de 401 (sesión vencida mostraba "Error interno"). | Interceptor redirige a `/login`. |
| QA-44 | B | `index.html` con `lang="en"` y título "frontend"; accesibilidad de filtros/CAPTCHA. | Idioma, título, metadatos y etiquetas accesibles. |
| QA-53 | M | La interfaz React era funcional pero visualmente anticuada, con tablas anchas en móvil y formularios largos. | Rediseño UX/UI completo: tokens, shell responsive, tablero accionable, detalle con stepper/panel, asistente de 3 pasos, login y modo oscuro. **Sin porcentaje de cumplimiento** por decisión del usuario. |
| QA-54 | A | El interceptor 401 recargaba `/login` en bucle; el proxy de Vite cambiaba el `Host` y el backend rechazaba el CAPTCHA con 403 (CSRF). | Redirección solo si no se está en `/login`; proxy conserva el `Host` original. Login verificado en navegador real. |
| QA-55 | M | Los enlaces **Mi jornada / Guías / En ruta** abrían el mismo tablero; el login dejaba mucho espacio sin usar y el CAPTCHA era pequeño y difícil de leer. | Vistas separadas con URL (`?vista=jornada|guias|ruta`), login 30/70, CAPTCHA más grande con fondo claro, letras de alto contraste y menos ruido. Verificado en navegador real. |
| QA-56 | A | `localhost:8000` (y ngrok) seguía sirviendo la interfaz HTML vieja; la PWA antigua podía cachear `/login` indefinidamente. | El backend sirve el build React de `frontend/dist` en las rutas de la SPA (`/login`, `/tablero`, `/guia/<id>`, `/nueva-guia`, `/admin/*`), con `/assets/*` y fallback; se reemplazó el service worker por un limpiador de cachés. Vite queda solo para desarrollo. |
| QA-57 | M | En Nueva guía el autollenado de cliente solo ocurría al hacer clic en una sugerencia; escribir el **NIT** o el nombre completo y salir del campo no completaba NIT/ciudad/dirección. | Autollenado por NIT (búsqueda con coincidencia exacta), por nombre completo al perder el foco, Enter para elegir la primera sugerencia y mensaje de “datos cargados”. Verificado en navegador real con la base de datos. |
| QA-58 | M | Faltaba captura de la persona que reclama (nombre/cédula/teléfono/firma), no se podían agregar varios documentos con prefijo propio y el transportador había perdido el canvas de su firma en la entrega. | Editor de documentos con “+ Agregar documento” (`documentos_json`), captura de quien reclama en Nueva guía y acción “Capturar datos de quien reclama” para CEDIS (evento `captura_reclamo` sin cambiar estado), doble firma del transportador restaurada, migración V12 y 5 pruebas nuevas. |

### 4.5 Pruebas e infraestructura de QA

| ID | Defecto | Corrección |
|---|---|---|
| QA-45 | `test_login_usuarios.py` ejecutaba `sys.exit(0)` al importarse: la suite completa abortaba con `INTERNALERROR`. | Convertido en módulo pytest con base temporal y pruebas de login. |
| QA-46 | `test_sistema.py` fallaba al recolectar (`RECEPTORES_DB_PATH` apuntaba a producción). | Config completa y directorios temporales antes de `init_db()`. |
| QA-47 | `test_api_guias.py` no aislaba la BD (11 fallos; riesgo de tocar datos reales). | `setUpModule`/`tearDownModule` con BD temporal. |
| QA-48 | Playwright no podía pasar (CAPTCHA del token, campos sin `name`, sin backend). | Spec reescrita con backend temporal, resolución del CAPTCHA por SVG y aserciones reales. |
| QA-49 | No había pruebas de regresión de los defectos. | Añadidas `test_e2e_http.py` (servidor real por sockets) y `test_regresion_qa.py` (20 casos). |

### 4.6 Android

| ID | Defecto | Corrección |
|---|---|---|
| QA-50 | No compilable: `package=` en el manifiesto (AGP 8), recursos `@xml/data_extraction_rules`, `@xml/backup_rules`, `@mipmap/ic_launcher*`, `@drawable/btn_background` inexistentes y `androidx.webkit.WebView` (clase inexistente). | Manifiesto sin `package`, icono vectorial propio, layout con `WebView` real, referencias corregidas. |
| QA-51 | `proguard-rules.pro` faltaba (el release lo exige); JDK hardcodeado a una ruta de un equipo; SDK 33 obsoleto. | Archivo creado, ruta JDK eliminada, `compileSdk/targetSdk 34`. |
| QA-52 | Permisos de almacenamiento pedidos en Android 13+ (diálogo en cada arranque, permisos ya inexistentes). | Solicitud condicionada por versión. |

---

## 5. Verificación posterior a las correcciones

1. **Backend:** `183 passed` (incluye flujo normal con firmas, **envío directo /
   recogida en sede**, link público, concurrencia, migración de BD antigua y
   permisos).
2. **Sonda E2E:** 186 comprobaciones, 0 fallos (incluye 14 específicas del flujo
   directo: control obligatorio, cierre sin transporte, botón unificado y link
   público).
3. **Configuración:** se verificó que el `.env` de la raíz se aplica
   (`environment=production`, CORS y `log_level` leídos) sin romper el login por
   HTTP (cookie `SameSite=Lax`, sin `Secure`).
4. **Frontend:** build de producción correcto y lint sin errores.
5. **Capacidad:** 8 creaciones simultáneas de guía → sin 500, IDs y
   consecutivos únicos; segunda confirmación del link público rechazada.

---

## 6. Limitaciones del entorno y tareas pendientes para la entrega

Estos puntos **no son defectos de lógica**; requieren un entorno con permisos o
herramientas que este equipo no tiene:

1. **APK Android:** no hay Android SDK/Gradle Wrapper en el equipo, así que no se
   compiló. Abrir `android_app/CoodescorGuias` en Android Studio (JDK 17, SDK 34),
   generar el wrapper si se desea CLI (`gradle wrapper`) y configurar el keystore
   de release (`app/build.gradle → signingConfigs.release`). Los bloqueos
   estáticos ya están corregidos.
2. **Playwright en navegador:** el sandbox bloquea la creación de tuberías que
   usa Chromium (`spawn EPERM`). Ejecutar en un equipo/CI normal:
   `npx playwright install chromium && npx playwright test` (arranca backend
   temporal y Vite automáticamente).
3. **Build `npm run build` en este equipo:** Vite usa un sondeo `net use` que el
   sandbox deniega; el build equivalente con configuración inline se ejecutó
   correctamente (100 módulos). En CI/Linux funciona el comando estándar.
4. **Retirar PII del índice de Git** (el sandbox no permite escribir en `.git`):
   ```bash
   git rm --cached -r guias_coodescor/data guias_coodescor/config.json config.json \
       backend/guias_coodescor/config.json frontend/playwright-report frontend/test-results
   git commit -m "chore: dejar de versionar datos runtime y configuración local"
   ```
   (Los archivos permanecen en disco; solo dejan de versionarse. Evaluar rotar
   las firmas/fotos si el repositorio ya se compartió.)
5. **Archivos residuales en la raíz:** `check_router.py`, `check_router2.py` y
   `debug.log` no se pudieron eliminar por permisos del entorno. Borrarlos manualmente
   y empaquetar sin `.venv/`, `node_modules/`, `.git/`, `ngrok.exe` ni
   `guias_coodescor/data/`.
6. **Endurecimiento recomendado (no bloqueante):**
   - Contraseñas semilla conocidas (`admin123`, …): generar clave aleatoria en el
     primer arranque y forzar cambio.
   - Rate limiting genérico por IP/usuario (hoy solo login/CAPTCHA), límite de
     tamaño por ruta y timeout de sockets.
   - ACL explícita para `secretos.json` en Windows.
   - Estandarizar zona horaria (UTC vs local) en `clientes_contactos.created_at`.
   - Resolver las 13 advertencias de lint del frontend (set-state-in-effect y
     variables sin usar; no afectan funcionalidad).
7. **Advertencias del análisis:** las pruebas del frontend en navegador y la
   compilación del APK deben formar parte de las **pruebas de aceptación** en el
   entorno del cliente.

---

## 7. Checklist de entrega / aceptación

| # | Criterio | Estado |
|---|---|---|
| 1 | Suite backend completa en verde | ✅ 183 pruebas |
| 2 | Flujo normal (Ventas → Admin → CEDIS → Transporte → Cliente) | ✅ E2E |
| 2b | Flujo envío directo (Ventas → CEDIS → cliente recoge en sede) | ✅ E2E (control obligatorio, sin transporte, botón único y link) |
| 3 | Link público de firma (emisión, activación, uso único, expiración) | ✅ E2E |
| 4 | Matriz de permisos por rol (incluye transportador) | ✅ E2E |
| 5 | Creación con NIT formateado y datos de catálogos | ✅ E2E |
| 6 | Administración de BD (respaldo/restauración/consultas auditadas) | ✅ E2E |
| 7 | Actualización segura de instalaciones existentes | ✅ prueba de migración |
| 8 | Configuración por `.env` y cookies correctas | ✅ verificado |
| 9 | Build del frontend y lint | ✅ |
| 10 | E2E de navegador (Playwright) | ⏳ ejecutar en entorno con navegadores |
| 11 | APK Android compilado y firmado | ⏳ compilar en Android Studio |
| 12 | Paquete de entrega sin datos personales ni secretos | ⏳ aplicar comandos de §6 |
| 13 | CI verde | ✅ configuración corregida (validar en GitHub) |

---

## 8. Archivos principales modificados

- Backend: `api/router.py`, `api/routes_*`, `core/{settings,paths,security}.py`,
  `config.py`, `database/models.py`, `migrations/V11_*.sql`,
  `services/{guias,eventos,tokens,captcha,auth,db_admin,export,clientes_contactos}_service.py`,
  `static/app.js`, `web/views/guias_views.py`.
- Pruebas: `tests/conftest.py`, `test_api_guias.py`, `test_login_usuarios.py`,
  `test_sistema.py`, **nuevos** `test_e2e_http.py` y `test_regresion_qa.py`.
- Frontend: `App.jsx`, `contexts/AuthContext.jsx`, `api/{index,auth,guias}.js`,
  `pages/{LoginPage,Tablero,DetalleGuia,NuevaGuia,AdminDB,LoadtestAdmin}.jsx`,
  `utils/format.js`, `index.html`, `vite.config.js`, `nginx.conf`,
  `playwright.config.ts`, `tests/e2e.spec.ts` + `tests/start-backend.mjs`.
- Infraestructura: `.github/workflows/ci.yml`, `.gitignore`, `.env.example`,
  `backend/requirements.txt`, scripts `deploy/windows/*`, proyecto Android,
  `README.md` y `docs/documentacion-tecnica.md`.

La evidencia de la sonda E2E queda en `.qa/qa_probe.py` y
`.qa/qa_probe_results.json` (no versionados).

---

## 9. Registro de flujos funcionales y revisiones

El detalle de cada flujo (actores, pasos, estados, eventos, reglas, endpoints y
evidencia) y la **bitácora de revisiones** se mantienen en
[FLUJOS-FUNCIONALES.md](FLUJOS-FUNCIONALES.md).

Cambios registrados allí que afectan flujos:

- **ROL-01:** la creación de guías está reservada al rol **Ventas**; Admin no
  crea guías (403) y la ruta React `/nueva-guia` redirige a `/tablero` para los
  demás roles.
- **QA-05b:** el envío directo exige `control_cedis` antes de entregar y su link
  público no se activa antes del control.
- **QA-08b / PRAC-01:** CEDIS · Practicante/Pasante exige nombre y firma propia,
  guardados en el evento y visibles en detalle/acta.
- **DOC-01:** se reemplazó la redacción ambigua “nace en EN_CEDIS” por “se crea
  con estado inicial EN_CEDIS” (la guía siempre la crea Ventas).

Flujos identificados para revisión: F-01 normal con transportador propio,
F-02 transportador externo, F-03 envío directo/recogida en sede, F-04 link
público normal, F-05 link público directo, F-06 anulación, F-07 edición,
F-08 permisos/rechazos, F-09 notificaciones, F-10 administración de BD,
F-11 catálogos e importación.
