# Registro y revisión de flujos funcionales — Guías Coodescor

**Documento de trabajo vivo.** Aquí se registran los flujos del aplicativo, las
reglas de negocio vigentes, los cambios que los afectan y la bitácora de las
revisiones que haremos juntos. Complementa a [QA-INFORME.md](QA-INFORME.md).

- **Fecha de apertura:** 24/10/2026
- **Uso:** el usuario indica el flujo a revisar; el equipo de QA lo ejecuta en un
  entorno aislado (base de datos temporal), documenta la evidencia y explica
  cómo se ve y funciona en la aplicación. Cada revisión se anota en la bitácora
  del final.

---

## 1. Reglas transversales (aplican a todos los flujos)

### 1.1 Quién puede hacer qué

| Rol | Crear guía | Recepción admin | Asignar transportador | Control CEDIS | Entrega a transporte | Entrega al cliente | Anular | Editar |
|---|---|---|---|---|---|---|---|---|
| **Ventas** | ✅ **único rol** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ solo en CREADA |
| **Administrativo** | ❌ | ✅ | ✅ (propio/externo) | ❌ | ❌ | ❌ | ❌ | ✅ antes de ruta |
| **CEDIS** | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ (también directo) | ❌ | ✅ antes de ruta |
| **Admin** | ❌ | ✅ (respaldo) | ✅ | ✅ (respaldo) | ✅ (respaldo) | ✅ (respaldo) | ✅ | ✅ (respaldo) |
| **Transportador propio** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ solo guías asignadas a él | ❌ | ❌ |
| **Cliente / público** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ solo con link `/firma/<token>` | ❌ | ❌ |

> **Regla fijada:** la creación está reservada al rol **Ventas**; el backend
> responde 403 a cualquier otro rol (incluido admin). Prueba:
> `test_admin_no_puede_crear_guias`. En React, `/nueva-guia` redirige a
> `/tablero` si el rol no es Ventas.

### 1.2 Estados y transiciones válidas

```
CREADA ──recepcion_admin──> RECIBIDA_ADMIN ──control_cedis──> EN_CEDIS
   │                                                              │
   │ (envío directo: estado inicial EN_CEDIS)                     │
   │                                                              ├──entrega_transporte──> EN_RUTA ──entrega_cliente──> ENTREGADA
   │                                                              └──entrega_cliente (SOLO envío directo)──> ENTREGADA
   └────────────────────────── anular (solo admin) ──────────────────────────────────────> ANULADA
```

- `ENTREGADA` y `ANULADA` son **terminales**: no se editan ni se vuelven a anular.
- En envío directo la guía se crea ya en `EN_CEDIS`; aun así **exige el control
  de bultos de CEDIS** antes de entregar.
- La entrega al cliente desde `EN_CEDIS` solo se permite en envío directo; en el
  flujo normal hay que pasar por `EN_RUTA`.

### 1.3 Eventos registrados (auditoría en tabla `eventos`)

`creacion`, `envio_directo_cedis`, `recepcion_admin`, `control_cedis`,
`entrega_transporte`, `entrega_cliente`, `anular`, `edicion_guia`,
`asignacion_transportador`, `receptor_purgado`.

Cada evento guarda usuario, rol, fecha/hora, IP, dispositivo y datos del paso.
Las firmas/fotos se guardan en disco y en el evento queda la ruta del adjunto.

### 1.4 Códigos de respuesta de la API

| Situación | HTTP |
|---|---|
| Paso ejecutado correctamente | 200 |
| Datos inválidos / faltantes (validación) | 400 |
| Sin sesión | 401 |
| Sin permiso por rol o guía no asignada | 403 |
| Guía o recurso inexistente | 404 |
| Estado incompatible con el paso (p. ej. doble envío) | 409 |

---

## 2. Catálogo de flujos

| ID | Flujo | Actores principales | Estado final | Cobertura automatizada |
|---|---|---|---|---|
| F-01 | **Normal con transportador propio** | Ventas → Administrativo → CEDIS → Transportador → Cliente | ENTREGADA | ✅ servicio + HTTP + sonda |
| F-02 | **Normal con transportador externo** | Ventas → Administrativo (datos/firma) → CEDIS → Cliente | ENTREGADA | ⚠️ registro del externo probado; falta recorrido completo dedicado |
| F-03 | **Envío directo / cliente recoge en sede** | Ventas → CEDIS → Cliente | ENTREGADA | ✅ servicio + HTTP + sonda |
| F-04 | **Link público de confirmación (flujo normal)** | Emisor (Ventas/Admin/Administrativo) → Cliente sin login | ENTREGADA | ✅ HTTP + sonda |
| F-05 | **Link público en envío directo** | Ventas/Admin → CEDIS controla → Cliente sin login | ENTREGADA | ✅ servicio + HTTP + sonda |
| F-06 | **Anulación de guía** | Admin | ANULADA | ✅ servicio + sonda |
| F-07 | **Edición de datos de la guía** | Ventas (CREADA) / Administrativo-CEDIS (antes de ruta) / Admin | Mismo estado | ✅ servicio + sonda |
| F-08 | **Permisos y rechazos por rol** | Todos | — | ✅ matriz E2E |
| F-09 | **Notificaciones y tablero en tiempo real** | Todos | — | ✅ sonda |
| F-10 | **Administración de base de datos / respaldos** | Admin | — | ✅ HTTP + pruebas |
| F-11 | **Importación/catálogos de clientes, contactos y transportadores** | Ventas / Administrativo | — | ✅ HTTP + pruebas |

---

## 3. Detalle de los flujos principales

### F-01 · Normal con transportador propio

**Cómo funciona en la aplicación**

1. **Ventas** entra a *Nueva guía*, registra cliente/NIT/ciudad/dirección,
   documentos, bultos (cajas/bolsas/cavas/sobres), datos del transportador y de
   quién recibe. Al guardar, la guía queda en **CREADA** con el evento
   `creacion` (los bultos quedan como prellenado para CEDIS).
2. **Administrativo** abre la guía en el tablero y ejecuta el *proceso único
   administrativo*: firma la recepción, elige **transportador propio** y lo
   asigna. Estado → **RECIBIDA_ADMIN** (`recepcion_admin` +
   `asignacion_transportador`).
3. **CEDIS** hace el *control de bultos* (confirma/corrige cantidades, marca si
   el vehículo cumple, selecciona el funcionario CEDIS y firma). Estado →
   **EN_CEDIS** (`control_cedis`). El total se recalcula como suma.
   - Si el funcionario es **Practicante / Pasante**, se habilita un campo para
     su **nombre** y un recuadro para **su firma**; ambos son obligatorios y
     quedan guardados en el evento (nombre + archivo `firma_practicante_archivo`)
     y visibles en el detalle y en el acta impresa.
4. **CEDIS** entrega al transportador (firma de entrega; si el transportador es
   externo puede reutilizarse la firma capturada por Administrativo). Estado →
   **EN_RUTA** (`entrega_transporte`). En el proceso unificado se emite
   automáticamente el **link público** para el cliente.
5. **Transportador propio** (si tiene login) o **CEDIS** cierra la entrega al
   cliente: nombre de quien recibe + firma o foto (el transportador propio
   además firma él mismo). Estado → **ENTREGADA** (`entrega_cliente`).

**Validaciones clave:** solo Ventas crea; recepción con firma; control con
funcionario y bultos ≥ 0; entrega a transporte solo desde EN_CEDIS; entrega al
cliente solo desde EN_RUTA (o EN_CEDIS en directo); no se edita tras salir a
ruta; no se anula una guía entregada.

**Evidencia automatizada:** `test_flujo_completo_con_link_publico`
(`backend/tests/test_e2e_http.py`) y sección *flujo normal* de
`.qa/qa_probe.py`.

---

### F-02 · Normal con transportador externo

Igual que F-01, con estas diferencias:

1. En la recepción, Administrativo elige **transportador EXTERNO** y captura
   sus datos (nombre, CC, teléfono, vehículo, placa, flete) **y su firma**.
2. CEDIS verifica el control y entrega; si ya existe la firma del externo, solo
   firma CEDIS como constancia; si no existe (fallback), el externo firma en
   CEDIS.
3. El externo **no tiene usuario ni login**; el cierre al cliente lo hace CEDIS
   o el cliente por link público.

**Cobertura actual:** registro y permisos del maestro de transportadores
probados (`test_contactos_y_transportadores_externos`), y el flujo usa los
mismos eventos que F-01. **Pendiente sugerido:** caso E2E dedicado de principio
a fin (candidato para esta ronda de revisión, F-02).

---

### F-03 · Envío directo / recogida en sede

**Cómo funciona en la aplicación**

1. **Ventas** crea la guía y marca **“Envío directo a CEDIS”**.
   - La guía **se crea con estado inicial EN_CEDIS** (no pasa por
     Administrativo). Se registra `creacion` + `envio_directo_cedis`.
   - **Importante:** la guía la crea Ventas; CEDIS no la crea.
2. **CEDIS** registra el **control de bultos** (obligatorio) con firma,
   funcionario y cantidades. El estado sigue en EN_CEDIS.
   - Si quien entrega es **Practicante / Pasante**, se muestra su **nombre** y su
     **firma** (obligatorios); sin ellos el proceso se rechaza (400).
3. **CEDIS** entrega al **cliente que viene a la sede**:
   - opción A: botón *Proceso ÚNICO CEDIS* en modo directo (control + entrega en
     un clic);
   - opción B: primero control y luego “Entrega al cliente”;
   - opción C: el cliente confirma por **link público**, que se activa **solo
     después del control**.
   Estado final → **ENTREGADA**, **sin evento `entrega_transporte`**.
4. Reglas: no se puede cerrar sin control de bultos (409); no aplica en el flujo
   normal (allí la entrega al cliente exige EN_RUTA).

**Evidencia automatizada:** 6 pruebas en `test_regresion_qa.py`, 2 en
`test_e2e_http.py` y 14 comprobaciones en `.qa/qa_probe.py` (control
obligatorio, cierre sin transporte, unificado y link).

---

### F-04 · Link público de confirmación (flujo normal)

1. Ventas/Administrativo/Admin pueden emitir el link desde el detalle de la
   guía (se reutiliza si ya existe: **1 link por guía**).
2. Se activa cuando la guía está **EN_RUTA**.
3. El cliente abre `/firma/<token>` sin iniciar sesión, revisa datos y confirma
   con firma o foto.
4. Se registra `entrega_cliente` con usuario virtual “público”, la guía pasa a
   **ENTREGADA** y el token se marca como usado. Un segundo intento se rechaza.
5. Expira a los 7 días; `Referrer-Policy: no-referrer` y página sin login.

---

### F-05 · Link público en envío directo

Igual que F-04, con dos diferencias: el link **no se activa antes del control
de bultos de CEDIS** y el cierre se hace desde `EN_CEDIS` (envío directo).
Después del control, el cliente puede confirmar por el link y la guía termina
ENTREGADA sin transporte.

---

### F-06 · Anulación

- Solo **Admin**; exige motivo.
- Permitida en CREADA, RECIBIDA_ADMIN, EN_CEDIS y EN_RUTA.
- **Rechazada** si la guía ya está ENTREGADA o ANULADA (409).
- Registra evento `anular` con motivo, usuario, fecha e IP; la guía pasa a
  ANULADA y deja de ser accionable.

### F-07 · Edición

- **Ventas:** solo guías en CREADA.
- **Administrativo/CEDIS:** antes de que exista entrega a transporte y sin
  estado EN_RUTA/ENTREGADA/ANULADA.
- **Admin:** respaldo, con las mismas protecciones de estados terminales.
- Cada edición registra `edicion_guia` con el diff (antes/después); **no se
  reescribe** el evento `creacion` (se conserva la auditoría original).

---

## 4. Registro de cambios que afectan flujos

| Fecha | ID | Cambio registrado | Flujos afectados | Evidencia |
|---|---|---|---|---|
| 24/10/2026 | PRAC-01 | CEDIS · Practicante / Pasante: al elegirlo se muestran **nombre** y **firma propia** (antes el campo de nombre estaba oculto y no había firma). Ambos obligatorios; se guardan en `control_cedis` y se ven en detalle/acta. | F-01, F-02, F-03 | 6 pruebas nuevas + 6 comprobaciones E2E |
| 24/10/2026 | UX-02 | Rediseño UX/UI del frontend React: tablero “Mi jornada”, detalle con stepper/panel de acción, asistente de nueva guía, login, modo oscuro y navegación móvil. Se retiró el porcentaje de cumplimiento. | Todos | 6 E2E Playwright + capturas reales |
| 24/10/2026 | QA-05b | El envío directo exige `control_cedis` antes de entregar; el link directo no se activa antes del control. | F-03, F-05 | `test_regresion_qa.py` (6 casos) + HTTP + sonda |
| 24/10/2026 | ROL-01 | Se documenta y fija que **solo Ventas crea guías**; admin recibe 403. | Todos | `test_admin_no_puede_crear_guias`, README/informe |
| 24/10/2026 | UX-01 | React redirige a `/tablero` en `/nueva-guia` si el rol no es Ventas (antes mostraba formulario y fallaba al guardar). | F-11, F-08 | `App.jsx` (`SoloVentas`), build OK |
| 24/10/2026 | DOC-01 | Se corrige la redacción “nace en EN_CEDIS” por “se crea con estado inicial EN_CEDIS” en pruebas, sonda e informe. | F-03 | `test_regresion_qa.py`, `.qa/qa_probe.py`, `QA-INFORME.md` |
| 24/10/2026 | QA-01…QA-52 | Correcciones de la QA integral (permisos, tokens, migraciones, frontend, despliegue, etc.). | Todos | [QA-INFORME.md](QA-INFORME.md) §4 |

> Los identificadores QA-xx corresponden al informe de QA integral.

---

## 5. Protocolo de revisión de flujos

Para cada flujo que indique el usuario:

1. **Preparación:** servidor aislado con `COODESCOR_DATA_DIR` temporal y puerto
   de pruebas; usuarios y datos semilla.
2. **Ejecución:** se recorre el flujo tal como lo haría cada rol, usando la API
   real (y la UI cuando aplique).
3. **Evidencia capturada:** peticiones/respuestas HTTP, transiciones de estado,
   eventos generados, permisos aplicados, datos finales y rechazos esperados.
4. **Explicación:** qué hace cada actor en la aplicación, qué valida el sistema,
   qué queda registrado y qué pasa si se intenta un paso inválido.
5. **Registro:** se anota en la bitácora siguiente. Si se detecta un defecto:
   se corrige, se agrega prueba de regresión y se actualiza `QA-INFORME.md`.

**Formato de la explicación:** “Actor → acción en la pantalla → endpoint →
validación → cambio de estado → evento registrado → resultado visible”.

---

## 6. Bitácora de revisiones

| # | Flujo revisado | Fecha | Ejecutado en | Resultado | Observaciones |
|---|---|---|---|---|---|
| 0 | F-03 (envío directo) — revisión inicial | 24/10/2026 | Servidor temporal :8765 | ✅ Conforme | Control obligatorio, cierre sin transporte, unificado y link público |
| 1 | CEDIS · Practicante / Pasante (F-01/F-02/F-03) | 24/10/2026 | Prueba manual del usuario + servidor :8765 | ✅ Defecto corregido | El campo de nombre estaba oculto y no existía firma del practicante. Se agregaron ambos (obligatorios) y se guardan en el evento/acta |
| 2 | Rediseño UX/UI del frontend (todos los flujos) | 24/10/2026 | Navegador real (Chrome/Playwright) | ✅ Implementado | Nueva interfaz responsive, modo oscuro, tablero accionable, detalle y nueva guía en pasos. Flujos de negocio intactos; 6 E2E en verde |
| 3 | _Pendiente de que el usuario indique el flujo_ | — | — | — | — |

---

## 7. Cómo pedir una revisión

Basta indicar el flujo (por ID o con tus palabras), por ejemplo:

- “Revisa F-02, transportador externo de inicio a fin.”
- “Ejecuta el flujo de un cliente que recoge en sede.”
- “Quiero ver qué pasa si CEDIS intenta entregar sin control.”
- “Revisa el flujo del link público y su expiración.”

Con eso ejecuto el escenario, te explico paso a paso cómo funciona en el
aplicativo y dejo la evidencia registrada en la bitácora.
