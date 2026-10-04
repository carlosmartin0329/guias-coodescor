# Guías Coodescor · Sistema Local (reestructurado)

Sistema web **local** de actas de entrega digitales para transporte de mercancías.
Funciona 100% sin internet, **sin dependencias externas** (solo Python 3 estándar + SQLite)
y se accede desde el navegador del PC o celular conectado a la misma red Wi‑Fi.

---

## 1) Estructura modular del proyecto

```
guias coodescor/
├── run_app.py                      # Lanzador desde la raíz (recomendado)
├── run.bat / run.ps1               # Scripts de arranque (Windows)
├── requirements.txt                # Sin dependencias obligatorias (solo opcional: segno para QR)
├── guias_coodescor/
│   ├── app.py                      # Entry point del paquete (iniciliza DB + servidor HTTP)
│   ├── config.py                   # Configuración centralizada (rutas, puertos, seguridad, roles)
│   ├── database/
│   │   ├── connection.py           # Conexiones SQLite (WAL, FKs, context managers)
│   │   ├── models.py               # Esquema, índices, seed data, migraciones, limpieza
│   │   └── migrations/             # Migraciones SQL (archivos V{version}_{nombre}.sql)
│   │       ├── V2_campos_auditoria.sql
│   │       └── V3_envio_directo_rol_administrativo.sql
│   ├── core/
│   │   ├── utils.py                # Funciones puras: fechas, hashing, adjuntos, rutas seguras
│   │   ├── security.py             # Sesiones con expiración, rate limit login, cookies HttpOnly
│   │   ├── validators.py           # Validación de entradas (usuarios, guías, números)
│   │   └── logging_config.py       # Logging rotativo (archivo + consola)
│   ├── services/
│   │   ├── auth_service.py         # Login/logout, gestión de usuarios, permisos por rol
│   │   ├── guias_service.py        # CRUD, búsqueda y transiciones de estado de guías
│   │   ├── eventos_service.py      # Registro de eventos + firma digital / fotos en disco
│   │   └── export_service.py       # Exportación CSV para Excel
│   ├── api/
│   │   └── router.py               # Servidor HTTP (ThreadingHTTPServer) + routing GET/POST
│   ├── web/views/
│   │   ├── base.py                 # Layouts, chips, stepper, componentes HTML
│   │   ├── auth_views.py           # Login y tablero principal
│   │   ├── guias_views.py          # Nueva guía, listado, detalle, imprimir
│   │   └── admin_views.py          # Panel admin (usuarios + configuración)
│   ├── static/                     # CSS y JS (sin cambios, ya existían)
│   │   ├── style.css
│   │   └── app.js
│   └── data/
│       ├── guias.db                # Base de datos SQLite (creada al iniciar)
│       ├── guias_coodescor.log     # Logs rotativos
│       └── adjuntos/               # Firmas y fotos de las guías
└── uploads/                        # (sin uso en la versión modular)
```

---

## 2) Forma de ejecución

En Windows, desde la carpeta raíz del proyecto (`d:\Users\57323\Downloads\guias coodescor`):

### Opción A · Scripts (doble clic o PowerShell)
```powershell
# PowerShell
.\run.ps1
```
```cmd
:: CMD (doble clic sobre run.bat)
run.bat
```

### Opción B · Lanzador directo
```powershell
py -3 run_app.py
```
O si `python` está en el PATH:
```powershell
python run_app.py
```

### Qué esperar
- La **primera ejecución** crea `guias_coodescor/data/guias.db`, la carpeta `adjuntos/`
  y los usuarios iniciales.
- Servidor en: **http://localhost:8000**  (y `http://<IP-PC>:8000` en la red local).
- Usuarios iniciales (**CAMBIE LAS CLAVES EN EL PANEL ADMIN**):
  - `admin / admin123`              · Admin. del SISTEMA (total: usuarios, anular, config)
  - `administrativo / admin123`     · Administrativo BODEGA (solo recepción, NO crea usuarios)
  - `ventas / ventas123`            · Ventas 1
  - `ventas2 / ventas123`           · Ventas 2
  - `ventas3 / ventas123`           · Ventas 3
  - `ventas4 / ventas123`           · Ventas 4
  - `cedis / cedis123`              · CEDIS (control, entrega transportador, entrega cliente)

---

## 2.5) Roles y flujo del proceso

**4 roles con permisos diferenciados:**

| Rol | Acciones permitidas |
|-----|-------------------|
| 🛒 **Ventas** (usuarios ventas, ventas2-4: 4 simultáneos) | Crear guías, marcar **"Envío DIRECTO a CEDIS"**, pre-llenar datos de transportador y quién recibe en cliente. Firma opcional (no obligatoria). |
| 📦 **Administrativo / Bodega** (usuario `administrativo`) | Solo **recepción Bodega** (firma recepción de guías creadas). NO puede anular ni crear usuarios. |
| 🚚 **CEDIS** | Control de bultos (cajas/bolsas/cayvas/sobres), entrega al transportador, entrega final al cliente (firma + foto). |
| 🔑 **Admin. del Sistema** (usuario `admin`) | **TODOS** los permisos: crear usuarios, editar consecutivo, configuración, exportar CSV, **anular guías**, hacer de respaldo en recepción. |

**Flujo normal (con paso por Bodega):**
```
VENTAS crea guía (estado CREADA)
   ↓
ADMINISTRATIVO BODEGA firma recepción (RECIBIDA_ADMIN)
   ↓
CEDIS controla bultos → (EN_CEDIS)
   ↓
CEDIS entrega al transportador → (EN_RUTA)
   ↓
CEDIS entrega al cliente → (ENTREGADA) ✓
```

**Flujo DIRECTO (salta Bodega):**
```
VENTAS crea guía MARCANDO ☑ Envío DIRECTO a CEDIS
  → la guía queda EN_CEDIS automáticamente
  → se registra evento envio_directo_cedis
  → paso ADMINISTRACIÓN se muestra como "saltado"
   ↓
CEDIS controla bultos → entrega transportador → entrega cliente ✓
```

**Datos pre-cargados desde Ventas (ahorra trabajo a CEDIS):**
- Transportador: **nombre, CC, teléfono, vehículo, placa, valor flete**
- Cliente recibe: **nombre de la persona que recibe en la farmacia**
- Estos campos aparecen **autocompletados pero editables** en los formularios de CEDIS
- También se muestran en detalle, en la hoja de imprimir y en el CSV exportado.

**Consecutivos atómicos (4 ventas concurrentes):**
- Cada creación de guía usa `get_db_lock()` + transacción atómica sobre `config.siguiente`
- Los consecutivos no se repiten aunque 4 usuarios de ventas creen guías al mismo tiempo.

---

## 3) Mejoras de desarrollo (arquitectura limpia)

| Principio | Cómo se cumple en esta reestructuración |
|-----------|----------------------------------------|
| **Separación de responsabilidades** | Capas claras: `config`, `database`, `core`, `services`, `api/router`, `web/views`. Ningún módulo hace de todo. |
| **Inversión de dependencias** | `database/models.py` NO depende de `security.py`; el hashing puro vive en `core/utils.py` (sin ciclo de imports). |
| **Single Responsibility** | `auth_service.py` solo autenticación/usuarios, `guias_service.py` solo negocio de guías, `router.py` solo HTTP. |
| **DRY** | Validadores centralizados en `core/validators.py`. Helpers HTML en `web/views/base.py`. |
| **Configuración externa** | Todas las constantes (puertos, límites, duración sesión, roles) en `config.py`. |
| **Migraciones versionadas** | Carpeta `database/migrations/` con `V{version}_{nombre}.sql` + tabla `schema_migrations` en BD. |
| **Índices de rendimiento** | Índices creados sobre `guias.estado`, `guias.creada_en`, `eventos.guia_id`, `sesiones.expira`, etc. |

---

## 4) Mejoras de seguridad

| Riesgo | Mitigación aplicada |
|--------|--------------------|
| Contraseñas en texto plano | Hash `PBKDF2-HMAC-SHA256`, 120 000 iteraciones, sal aleatoria por usuario, comparación en tiempo constante. |
| Sesiones robadas | Cookies `HttpOnly; SameSite=Lax`, sesiones con **expiración** (8h), limpieza periódica de sesiones expiradas. |
| Fuerza bruta en login | **Rate limiting**: 5 intentos fallidos → bloqueo de 5 min por cuenta (persistido en BD). |
| Inyección SQL | Todas las consultas con `?` y parámetros vinculados (sqlite3 placeholders). Sin concatenación de SQL. |
| Path traversal (adjuntos) | `ruta_adjunto_segura()` normaliza y verifica que el archivo esté dentro de `DATA_DIR` antes de servir. |
| XSS | Todas las variables interpoladas en HTML pasan por `html.escape()` (helpers en `web/views/base.py`). |
| Subida de archivos maliciosos | Solo se aceptan `data:image/png|jpeg|gif`, extensión validada y nombre basename() antes de guardar. |
| Tamaño de payload abusivo | `MAX_REQUEST_BODY = 30 MB` y validación de Content-Length antes de leer el cuerpo. |
| Clickjacking / MIME sniff | Cabeceras `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`. |
| Errores con info sensible | El router captura excepciones y devuelve páginas 400/403/500 genéricas; los detalles van **solo** al log. |
| Permisos por rol | `requerir_rol()` + `PERMISO` config validan el rol antes de cada acción crítica. |
| Transiciones inválidas de estado | `ESTADO_ESPERADO_POR_EVENTO` evita aplicar eventos sobre una guía en estado incorrecto (409 Conflict). |

---

## 5) Base de datos · Tablas actualizadas

**usuarios** — Id, usuario (único), nombre, pass_hash, sal, rol
(CHECK: `ventas` | `administrativo` | `cedis` | `admin`),
activo, creado, ultima_sesion, intentos_fallidos, bloqueado_hasta.

**sesiones** — sid (PK), usuario_id (FK→usuarios ON DELETE CASCADE), creada, expira, ip, user_agent.

**guias** — Id, consecutivo (único), cliente, ciudad, direccion, documentos, obs_ventas,
creada_por (FK), creada_en, estado (CHECK en 7 estados), **envio_directo_cedis INTEGER (0/1)**,
anulada_motivo, anulada_por, anulada_en.

**eventos** — Id, guia_id (FK→guias ON DELETE CASCADE), tipo (CHECK de 7+ tipos: creacion, recepcion_admin,
control_cedis, entrega_transporte, entrega_cliente, anulacion, **envio_directo_cedis**),
usuario_id (FK), usuario, rol, en, dispositivo, ip, datos (JSON con rutas a firma/foto + prellenados).

**config** — clave/valor (consecutivo, empresa, pie).

**schema_migrations** — version/nombre/aplicada_en para control de migraciones.

Todos los FKs se ejecutan con `PRAGMA foreign_keys=ON` y la BD usa `journal_mode=WAL`
para permitir múltiples lectores concurrentes desde varios celulares/PCs.

---

## 6) Logs y auditoría

Todas las acciones relevantes quedan registradas en:
- `guias_coodescor/data/guias_coodescor.log` (rotativo, 5 MB × 3 archivos).
- Tabla `eventos` de la BD (cada cambio de estado con usuario, rol, IP, dispositivo y fecha).

Eventos que se auditan: login exitoso/fallido, logout, creación de usuario, creación/anulación
de guía, recepción admin, control CEDIS, entrega transportador, entrega cliente.

---

## 8) Adaptación para Android - Operarios CEDIS y Transportadores

El sistema ha sido adaptado para funcionar en **dispositivos Android** de dos formas:

### 📱 Opción A: Progressive Web App (PWA) - Recomendado para prueba rápida

**Sin necesidad de instalar nada.** El sistema web ya está configurado como PWA:

1. En tu dispositivo Android, abre **Chrome**
2. Navega a: `http://[IP-DE-TU-PC]:8000`
3. Chrome mostrará un mensaje: **"Instalar app"** o **"Añadir a pantalla de inicio"**
4. Acepta y la app se instalará como una aplicación nativa
5. Puedes abrirla desde el menú de aplicaciones

**Ventajas:**
- No requiere compilar código
- Se actualiza automáticamente
- Funciona con cache offline básico
- Acceso rápido desde el launched de Android

### 🤖 Opción B: App Nativa Android con WebView - Para producción

Para una experiencia más profesional, se ha creado un **proyecto Android completo** en la carpeta:
```
android_app/CoodescorGuias/
```

**Características:**
- App nativa con icono propio
- Configuración de IP al primer inicio
- Detección de conexión a Internet
- Soporta carga de fotos desde cámara/galería
- Notificaciones de estado
- Compatible con Android 7.0+ (API 24+)

**Instrucciones detalladas en:** `android_app/README.md`

### Configuración para Operarios Móviles

1. **En el servidor (PC):**
   - Ejecuta `python run_app.py` como siempre
   - Anota la **IP de tu PC** en la red local (ej: 192.168.1.100)

2. **En el dispositivo Android:**
   - Instala la app (PWA o nativa)
   - Ingresa la **IP del servidor** al abrir la app por primera vez
   - Inicia sesión con tus credenciales (cedis/cedis123, etc.)

3. **Funcionamiento:**
   - Firmas táctiles en la pantalla
   - Captura de fotos con la cámara
   - Navegación optimizada para touch
   - Diseño responsive

### Mejoras para Dispositivos Móviles

**En CSS:**
- Botones más grandes (≥44px para touch)
- Checkbox y radio buttons estilo táctil
- Inputs de cámara optimizados
- Diseño responsive para todas las pantallas

**En JavaScript:**
- Firma táctil mejorada
- Compresión de imágenes antes de subir
- Soporte para camera API

**Nuevos archivos:**
- `static/manifest.json` - Configuración PWA
- `static/service-worker.js` - Cache offline
- `static/style.css` - Mejorado para móviles
- `android_app/CoodescorGuias/` - Proyecto Android completo

---

## 7) Advertencias de producción local

1. **CAMBIE LAS CLAVES POR DEFECTO** de admin/ventas/cedis en `/admin` tras el primer inicio.
2. El sistema está pensado para **red LAN de confianza**. Si lo expone a internet,
   coloque un proxy reverso (nginx/Caddy) con **HTTPS** y establezca `Secure` en las cookies
   editando `core/security.py → cookie_set_sid(..., secure=True)`.
3. Haga copias periódicas de `guias_coodescor/data/guias.db` y la carpeta `adjuntos/`.


---

## 9) Ubicacion de los datos (fuera de la aplicacion)

Las bases, adjuntos, logs y respaldos **ya no viven dentro de la carpeta del
proyecto**. Se resuelven en este orden y el primero que exista gana:

1. Variable de entorno COODESCOR_DATA_DIR
2. config.json en la raiz del proyecto
3. Ruta del sistema: %ProgramData%\\Coodescor\\Guias en Windows,
   ~/Library/Application Support/Coodescor/Guias en macOS,
   /var/lib/coodescor/guias en Linux

En esta instalacion quedo en C:\\ProgramData\\Coodescor\\Guias, con
guias.db, 
eceptores.db, djuntos/, 
espaldos/ y secretos.json.

La primera vez, si existia la carpeta antigua guias_coodescor/data, se copia
al destino nuevo y **la original no se borra** (queda como respaldo). Para
retirarla despues de validar, borrala a mano.

### Secretos

secretos.json vive en el directorio de datos, nunca en el repositorio:

- 
eceptores_secret_key: cifra los datos de receptores
- captcha_hmac_secret_key: firma los desafios del CAPTCHA

Se generan solas la primera vez. Si venian guardadas en la tabla config de una
instalacion anterior, se migran al archivo y de alli no se vuelven a leer.

---

## 10) Modulo de base de datos (Admin -> Base de datos)

Solo para el rol **admin**. Sirve para operar los datos sin entrar a un gestor
externo.

- **Resumen**: bases, tamano, integridad y version de esquema.
- **Explorador**: ver, buscar, paginar, agregar, editar y eliminar filas.
  Las columnas sensibles (usuarios.pass_hash, usuarios.sal y las columnas
  *_cif de receptores) salen enmascaradas y no son editables.
- **Consultas SQL**: modo lectura o modo escritura. El escritura exige marcar
  una casilla de confirmacion y crea un respaldo automatico antes de ejecutar.
  El editor **nunca** ejecuta DROP, ALTER, CREATE, PRAGMA, ATTACH,
  VACUUM ni REINDEX, ni toca columnas protegidas.
- **Respaldos**: crear, descargar, restaurar y eliminar. Todos se verifican con
  PRAGMA integrity_check antes de confiar en ellos; restaurar guarda primero el
  estado actual y pide reiniciar el servidor.
- **Mantenimiento**: VACUUM, OPTIMIZE, ANALYZE, checkpoint del WAL y
  aplicacion de migraciones pendientes.
- **Auditoria**: todo lo que se modifica queda registrado con usuario, rol, IP,
  sentencia o fila afectada.


eceptores.db es siempre de solo lectura: se modifica por el flujo normal de
clientes y receptores, no desde aqui.

---

## 11) API REST de guías (contrato para el frontend)

Todos los endpoints devuelven JSON. Los errores de dominio (`ValidationError`,
`AuthError`, `ForbiddenError`) se transforman en respuestas JSON con el código
HTTP correspondiente.

### Autenticación

Toda petición a `/api/guias` requiere sesión activa (cookie `session_id`).
El flujo es:

1. `GET /api/captcha/nuevo` → `{ "ok": true, "svg": "...", "token": "..." }`
2. `POST /api/login` con `usuario`, `clave`, `captcha_token`, `captcha_respuesta`
   → `{ "ok": true, "redirect": "/tablero" }`

### Catálogo

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/guias?q=&estado=&limite=&transportador=` | Búsqueda paginada de guías |
| GET | `/api/guias/conteo` | Conteo por estado para el tablero |
| GET | `/api/guias/estados` | Catálogo de estados con etiqueta y color |

`/api/guias` acepta `q` (texto libre), `estado` (CREADA, EN_CEDIS, …),
`limite` (máx. 500) y `transportador` (id numérico). La respuesta incluye
`guias`, `total` y `conteo_por_estado`.

### Detalle

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/guias/<id>` | Guía, eventos, prellenado y estado_info |
| GET | `/api/guias/<id>/eventos` | Historial de eventos (últimos N, por defecto 100) |
| GET | `/api/guias/<id>/transicion/<tipo>` | ¿Puede el usuario actual ejecutar el paso? |

`estado_info` devuelve `{ estado, etiqueta, clase }` para que el frontend
no tenga que conocer las constantes del backend.

### Mutaciones

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/guias` | Crear guía (solo rol ventas) |
| PUT / PATCH | `/api/guias/<id>` | Editar cabecera (solo antes de que otro rol la procese) |
| POST | `/api/guias/<id>/evento/<tipo>` | Ejecutar paso: `recepcion_admin`, `control_cedis`, `entrega_transporte`, `entrega_cliente`, `anular`, `edicion_guia` |

Crear devuelve `{ ok, id, redirect }`. Editar y eventos devuelven `{ ok,
mensaje, guia, eventos, evento_id?, ... }`.

### Permisos por rol

| Rol | Puede |
|-----|-------|
| ventas | crear, editar, listar |
| administrativo | recepcion_admin, listar |
| cedis | control_cedis, entrega_transporte, entrega_cliente, listar |
| admin | todo lo anterior + anular, base de datos |
| transportador | listar (si está asignado) |

### Códigos HTTP

- `200` éxito
- `400` solicitud inválida o validación fallida
- `401` sesión inválida o expirada
- `403` rol insuficiente
- `404` guía no encontrada
- `409` estado de la guía no permite la operación
- `500` error interno

`receptores.db` es solo lectura desde este módulo: se gestiona por el flujo
normal de clientes y receptores.

---

## 12) Próxima fase: frontend React + Vite

La API REST anterior es el contrato estable. El frontend futuro puede
consumirla sin tocar el backend. Mientras tanto, el HTML renderizado por
Python sigue funcionando como antes.

---

## 13) Frontend React + Vite

El frontend vive en `frontend/` y se ejecuta de forma independiente del backend.
En desarrollo, Vite hace proxy de `/api`, `/static`, `/login`, `/tablero` y
`/admin` al backend Python en `http://127.0.0.1:8000`.

### Requisitos

- Node.js 18+
- npm 9+

### Puesta en marcha

```powershell
# 1) Backend (terminal 1)
py -3 run_app.py

# 2) Frontend (terminal 2)
cd frontend
npm install
npm run dev
```

Abrir `http://localhost:5173` en el navegador.

### Build de producción

```powershell
cd frontend
npm run build
npm run preview
```

El build se despliega en `frontend/dist/`. Para producción, sirve esa carpeta
con cualquier servidor estático y mantén el backend Python en `/api`.

### Estructura

```
frontend/
├── src/
│   ├── api/               # Cliente HTTP (axios) + endpoints
│   ├── components/        # Componentes reutilizables
│   ├── contexts/          # AuthContext + GuiaContext
│   ├── pages/             # LoginPage, Tablero, DetalleGuia, AdminDB
│   ├── styles/            # CSS global + específicos
│   ├── App.jsx            # Rutas (react-router-dom)
│   └── main.jsx           # Punto de entrada
├── index.html
├── package.json
└── vite.config.js         # Proxy al backend + puerto 5173
```
