# 📦 Sistema de Guías Coodescor

**Sistema web local para gestión de actas de entrega digitales en transporte de mercancías**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-3.0-orange.svg)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-Proprietary-green.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

---

## 📋 Tabla de Contenidos

1. [Descripción General](#-descripción-general)
2. [Características Principales](#-características-principales)
3. [Arquitectura del Sistema](#-arquitectura-del-sistema)
4. [Requisitos](#-requisitos)
5. [Instalación y Configuración](#-instalación-y-configuración)
6. [Primeros Pasos](#-primeros-pasos)
7. [Roles y Permisos](#-roles-y-permisos)
8. [Flujo de Trabajo](#-flujo-de-trabajo)
9. [API y Endpoints](#-api-y-endpoints)
10. [Seguridad](#-seguridad)
11. [Soporte Móvil (Android)](#-soporte-móvil-android)
12. [Base de Datos](#-base-de-datos)
13. [Mantenimiento](#-mantenimiento)
14. [Solución de Problemas](#-solución-de-problemas)
15. [Créditos](#-créditos)

---

## 🎯 Descripción General

El **Sistema de Guías Coodescor** es una solución empresarial diseñada para digitalizar el proceso de seguimiento y entrega de mercancías en operaciones logísticas. Permite la creación, tracking y validación de guías de transporte mediante firmas digitales y evidencia fotográfica, eliminando el uso de papel y mejorando la trazabilidad del proceso.

### Ventajas Clave

- ✅ **100% Offline**: Funciona sin conexión a internet en red local (LAN)
- ✅ **Multi-dispositivo**: Acceso desde PC, tablets y smartphones Android
- ✅ **Sin dependencias externas**: Solo requiere Python 3 estándar + SQLite
- ✅ **Auditoría completa**: Registro detallado de cada acción con usuario, IP y timestamp
- ✅ **PWA Ready**: Instalable como aplicación nativa en dispositivos móviles

---

## ✨ Características Principales

| Característica | Descripción |
|---------------|-------------|
| 📝 **Guías Digitales** | Creación de actas de entrega con consecutivo automático |
| ✍️ **Firma Táctil** | Captura de firma digital en canvas HTML5 |
| 📸 **Evidencia Fotográfica** | Adjuntar fotos de entrega con compresión automática |
| 🔄 **Workflow Multi-etapa** | 5 pasos: Ventas → Administración → CEDIS → Transportador → Cliente |
| 👥 **Multi-rol** | 5 roles con permisos diferenciados (Admin, Ventas, Administrativo, CEDIS, Transportador) |
| 📊 **Tablero de Control** | Vista personalizada por rol con guías pendientes |
| 🔍 **Búsqueda Avanzada** | Filtrado por cliente, ciudad, estado, rango de fechas |
| 📤 **Exportación CSV** | Reportes compatibles con Excel para análisis |
| 🔐 **Seguridad Empresarial** | Hash PBKDF2, sesiones con expiración, rate limiting |
| 📱 **Mobile First** | Interfaz optimizada para touch (Android/iOS) |
| 🖨️ **Impresión PDF** | Formato de impresión listo para actas físicas |

---

## 🏗️ Arquitectura del Sistema

### Estructura de Directorios

```
guias_coodescor/
├── run_app.py                      # Punto de entrada principal
├── run.bat / run.ps1               # Scripts de arranque (Windows)
├── requirements.txt                # Dependencias opcionales
├── README.md                       # Documentación técnica
├── README_PROFESSIONAL.md          # Esta documentación
│
└── guias_coodescor/
    ├── app.py                      # Entry point (inicializa DB + servidor)
    ├── config.py                   # Configuración centralizada
    │
    ├── database/
    │   ├── connection.py           # Conexiones SQLite (WAL, context managers)
    │   ├── models.py               # Schema, índices, seed data, migraciones
    │   └── migrations/             # Migraciones versionadas (V{version}_*.sql)
    │
    ├── core/
    │   ├── utils.py                # Funciones utilitarias (fechas, hashing, rutas)
    │   ├── security.py             # Gestión de sesiones, cookies, rate limit
    │   ├── validators.py           # Validación de entradas
    │   └── logging_config.py       # Logging rotativo
    │
    ├── services/
    │   ├── auth_service.py         # Autenticación, usuarios, permisos
    │   ├── guias_service.py        # Lógica de negocio de guías
    │   ├── eventos_service.py      # Eventos, firmas, fotos
    │   └── export_service.py       # Exportación CSV
    │
    ├── api/
    │   └── router.py               # Servidor HTTP + routing GET/POST
    │
    ├── web/views/
    │   ├── base.py                 # Layouts, componentes HTML reutilizables
    │   ├── auth_views.py           # Login, tablero
    │   ├── guias_views.py          # CRUD guías, detalle, imprimir
    │   └── admin_views.py          # Panel administrativo
    │
    ├── static/
    │   ├── style.css               # Estilos responsive (mobile-first)
    │   ├── app.js                  # JavaScript (firma táctil, PWA)
    │   ├── manifest.json           # Configuración PWA
    │   ├── service-worker.js       # Cache offline
    │   └── icons/                  # Iconos para PWA
    │
    └── data/
        ├── guias.db                # Base de datos SQLite
        ├── guias_coodescor.log     # Logs rotativos
        └── adjuntos/               # Firmas y fotos (organizados por fecha)
```

### Diagrama de Flujo

```
┌─────────────┐
│   VENTAS    │ ──→ Crea guía (CREADA)
└──────┬──────┘
       │
       ├──────────────────────┐
       │                      ↓
       │              ¿Envío Directo? ──→ [EN_CEDIS] (salta bodega)
       ↓                                      │
[RECIBIDA_ADMIN] ←────────────────────────────┘
       │
       ↓
  [EN_CEDIS] ──→ Control bultos
       │
       ↓
  [EN_RUTA] ──→ Entrega al transportador (firma + foto)
       │
       ↓
 [ENTREGADA] ─→ Entrega al cliente (firma + foto) ✓
```

---

## 🛠️ Requisitos

### Mínimos

| Componente | Versión Mínima | Recomendada |
|-----------|----------------|-------------|
| Python | 3.8+ | 3.10+ |
| RAM | 512 MB | 2 GB+ |
| Almacenamiento | 100 MB | 1 GB+ |
| Navegador | Chrome 80+, Firefox 75+, Edge 80+ | Última versión |

### Red Local

- Todos los dispositivos deben estar en la **misma red Wi-Fi/Ethernet**
- El equipo servidor debe tener **IP fija** o reserva DHCP
- Puerto **8000** disponible (configurable en `config.py`)

---

## 📥 Instalación y Configuración

### Paso 1: Descargar e Instalar Python

1. Descargue Python desde [python.org](https://www.python.org/downloads/)
2. Durante la instalación, marque **"Add Python to PATH"**
3. Verifique la instalación:
   ```bash
   python --version
   ```

### Paso 2: Clonar/Descargar el Proyecto

```bash
# Si usa Git
git clone <URL_DEL_REPOSITORIO>
cd guias_coodescor

# O extraiga el archivo ZIP descargado
```

### Paso 3: Configurar Variables (Opcional)

Edite `guias_coodescor/config.py` si necesita cambiar:

```python
HOST = "0.0.0.0"          # Escuchar en todas las interfaces
PORT = 8000               # Puerto del servidor
SESSION_DURATION_SECONDS = 8 * 60 * 60  # Duración de sesión (8 horas)
```

### Paso 4: Ejecutar por Primera Vez

#### Windows (Recomendado)

```powershell
# Opción A: Doble clic en run.bat
run.bat

# Opción B: PowerShell
.\run.ps1

# Opción C: Línea de comandos
py -3 run_app.py
```

#### Linux / macOS

```bash
python3 run_app.py
```

### Paso 5: Acceder al Sistema

1. Abra su navegador y vaya a: **http://localhost:8000**
2. La primera ejecución creará automáticamente:
   - Base de datos `guias.db`
   - Carpeta `adjuntos/`
   - Usuarios iniciales

---

## 🚀 Primeros Pasos

### Usuarios Iniciales (CAMBIAR CONTRASEÑAS INMEDIATAMENTE)

| Usuario | Contraseña | Rol | Descripción |
|---------|------------|-----|-------------|
| `admin` | `admin123` | Admin del Sistema | Control total del sistema |
| `administrativo` | `adminbod123` | Administrativo (Bodega) | Recepción de guías |
| `ventas` | `ventas123` | Ventas 1 | Creación de guías |
| `ventas2` | `ventas123` | Ventas 2 | Creación de guías |
| `ventas3` | `ventas123` | Ventas 3 | Creación de guías |
| `ventas4` | `ventas123` | Ventas 4 | Creación de guías |
| `cedis` | `cedis123` | CEDIS | Control y entrega |
| `transportador` | `trans123` | Transportador | Recogida y entrega |

### ⚠️ Seguridad Inicial

**IMPORTANTE:** Cambie las contraseñas por defecto inmediatamente después del primer inicio:

1. Inicie sesión como `admin`
2. Vaya a **Admin → Usuarios**
3. Edite cada usuario y establezca una contraseña segura
4. Guarde los cambios

---

## 👥 Roles y Permisos

### Matriz de Permisos

| Acción / Rol | Admin | Ventas | Administrativo | CEDIS | Transportador |
|-------------|-------|--------|----------------|-------|---------------|
| Crear guías | ✅ | ✅ | ❌ | ❌ | ❌ |
| Editar guías propias | ✅ | ✅ | ❌ | ❌ | ❌ |
| Recepción administrativa | ✅ | ❌ | ✅ | ❌ | ❌ |
| Control CEDIS | ✅ | ❌ | ❌ | ✅ | ❌ |
| Entrega al transportador | ✅ | ❌ | ❌ | ✅ | ✅ (recibir) |
| Entrega al cliente | ✅ | ❌ | ❌ | ✅ | ✅ (entregar) |
| Anular guías | ✅ | ❌ | ❌ | ❌ | ❌ |
| Crear usuarios | ✅ | ❌ | ❌ | ❌ | ❌ |
| Ver reportes | ✅ | Parcial | ❌ | Parcial | Parcial |
| Exportar CSV | ✅ | ❌ | ❌ | ❌ | ❌ |

### Descripción de Roles

#### 🔑 Admin del Sistema
- **Responsable:** Administrador TI / Supervisor general
- **Acceso completo:** Todas las funciones del sistema
- **Exclusivo:** Crear/editar usuarios, anular guías, configuración global

#### 🛒 Ventas
- **Responsable:** Asistentes comerciales (hasta 4 simultáneos)
- **Funciones:** Crear guías, marcar envío directo, pre-llenar datos
- **Limitaciones:** No puede anular ni modificar guías de otros usuarios

#### 📦 Administrativo (Bodega)
- **Responsable:** Personal de recepción en bodega
- **Funciones:** Confirmar recepción física de guías creadas por ventas
- **Limitaciones:** Solo ve guías en estado `CREADA`, no crea usuarios

#### 🚚 CEDIS
- **Responsable:** Operarios de centro de distribución
- **Funciones:** Control de bultos, entrega a transportador, entrega final
- **Exclusivo:** Registro de peso/volumen, validación de vehículo

#### 🚛 Transportador
- **Responsable:** Conductores / repartidores externos
- **Funciones:** Recoger mercancía en CEDIS, entregar al cliente final
- **Limitaciones:** Solo ve guías asignadas a su nombre, NO tiene acceso administrativo
- **Evidencia:** Debe capturar firma y foto en ambas etapas (recogida y entrega)

---

## 🔄 Flujo de Trabajo

### Flujo Normal (con paso por Bodega)

```
1. VENTAS crea guía
   └─→ Estado: CREADA
   └─→ Consecutivo automático
   └─→ Datos: cliente, ciudad, dirección, documentos, observaciones

2. ADMINISTRATIVO recibe en bodega
   └─→ Estado: RECIBIDA_ADMIN
   └─→ Firma digital de recepción
   └─→ Timestamp y IP registrados

3. CEDIS controla bultos
   └─→ Estado: EN_CEDIS
   └─→ Registra: cajas, bolsas, cayvas, sobres
   └─→ Valida coincidencia con guía

4. CEDIS entrega al TRANSPORTADOR
   └─→ Estado: EN_RUTA
   └─→ Firma del transportador
   └─→ Foto de la mercancía cargada
   └─→ Datos: nombre, CC, teléfono, vehículo, placa, flete

5. TRANSPORTADOR entrega al CLIENTE
   └─→ Estado: ENTREGADA ✓
   └─→ Firma del receptor
   └─→ Foto de entrega (fachada/persona)
   └─→ Nombre de quien recibe
```

### Flujo Directo (sin paso por Bodega)

```
1. VENTAS crea guía marcando ☑ "Envío DIRECTO a CEDIS"
   └─→ Estado: EN_CEDIS (automático)
   └─→ Evento: envio_directo_cedis registrado
   └─→ Paso "Administración" marcado como saltado

2. CEDIS controla bultos → Transportador → Cliente
   (mismo flujo desde paso 3 del flujo normal)
```

### Concurrencia

- **4 usuarios de ventas** pueden crear guías simultáneamente
- Los consecutivos son **atómicos** (no hay duplicados)
- Implementado con `get_db_lock()` + transacciones SQLite

---

## 🔌 API y Endpoints

### Endpoints Públicos (requieren autenticación)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/` | Redirect al tablero o login |
| `GET` | `/login` | Formulario de inicio de sesión |
| `POST` | `/api/login` | Autenticación (devuelve cookie de sesión) |
| `POST` | `/api/logout` | Cerrar sesión |
| `GET` | `/tablero` | Dashboard personalizado por rol |
| `GET` | `/guias` | Listado de guías con filtros |
| `GET` | `/guia/nueva` | Formulario nueva guía (solo Ventas/Admin) |
| `POST` | `/api/guia/crear` | Crear nueva guía |
| `GET` | `/guia/<id>` | Detalle de guía específica |
| `POST` | `/api/guia/evento` | Registrar evento (firma/foto) |
| `GET` | `/guia/<id>/imprimir` | Vista de impresión (PDF-ready) |
| `GET` | `/admin` | Panel administrativo (solo Admin) |
| `POST` | `/api/admin/usuario/crear` | Crear usuario (solo Admin) |
| `POST` | `/api/admin/usuario/editar` | Editar usuario (solo Admin) |
| `GET` | `/export/csv` | Descargar reporte CSV (solo Admin) |
| `GET` | `/static_file/<ruta>` | Servir archivos estáticos (firmas/fotos) |

### Códigos de Respuesta

| Código | Significado |
|--------|-------------|
| `200 OK` | Petición exitosa |
| `302 Found` | Redirect (login requerido) |
| `400 Bad Request` | Datos inválidos |
| `403 Forbidden` | Permiso insuficiente |
| `404 Not Found` | Recurso no existe |
| `409 Conflict` | Estado inválido para transición |
| `500 Internal Server Error` | Error del servidor (ver logs) |

---

## 🔐 Seguridad

### Medidas Implementadas

| Riesgo | Mitigación |
|--------|------------|
| **Contraseñas débiles** | Hash PBKDF2-HMAC-SHA256 (120,000 iteraciones) + sal única |
| **Robo de sesión** | Cookies `HttpOnly; SameSite=Lax`, expiración 8h, limpieza automática |
| **Fuerza bruta** | Rate limiting: 5 intentos fallidos → bloqueo 5 min por cuenta |
| **Inyección SQL** | Consultas parametrizadas (`?` placeholders), sin concatenación |
| **Path traversal** | Validación estricta de rutas de adjuntos con `ruta_adjunto_segura()` |
| **XSS (Cross-Site Scripting)** | Escape automático con `html.escape()` en todas las variables |
| **Archivos maliciosos** | Solo imágenes PNG/JPEG/GIF, validación de MIME type |
| **DoS por payload grande** | Límite 30 MB por request, 10 MB por adjunto |
| **Clickjacking** | Header `X-Frame-Options: SAMEORIGIN` |
| **MIME sniffing** | Header `X-Content-Type-Options: nosniff` |
| **Información sensible en errores** | Páginas de error genéricas, detalles solo en logs |

### Mejores Prácticas Recomendadas

1. **Cambiar contraseñas por defecto** inmediatamente
2. **Usar HTTPS** si se expone fuera de la LAN (proxy reverso nginx/Caddy)
3. **Firewall**: Restringir acceso al puerto 8000 solo a IPs de confianza
4. **Backups diarios** de `guias_coodescor/data/`
5. **Rotación de logs**: Configurar retención según política de la empresa

---

## 📱 Soporte Móvil (Android)

### Opción A: Progressive Web App (PWA) - Recomendado

**Ventajas:**
- Sin instalación compleja
- Actualización automática
- Funciona offline básico
- Acceso desde cualquier navegador

**Instrucciones:**

1. En el dispositivo Android, abra **Chrome**
2. Navegue a: `http://[IP-DEL-SERVIDOR]:8000`
3. Toque el menú (⋮) → **"Instalar aplicación"** o **"Agregar a pantalla de inicio"**
4. Confirme la instalación
5. La app aparecerá en el launcher como una aplicación nativa

### Opción B: App Nativa Android

El proyecto incluye un **proyecto Android completo** en:
```
android_app/CoodescorGuias/
```

**Características:**
- WebView nativa con barra de navegación configurable
- Soporte para cámara y galería
- Gestión de permisos Android
- Compatible con Android 7.0+ (API 24+)

**Compilación:**

1. Abra el proyecto en **Android Studio**
2. Configure la IP del servidor en `MainActivity.java`
3. Compile: **Build → Build Bundle(s) / APK(s) → Build APK(s)**
4. Instale el APK en los dispositivos de los transportadores

Ver `android_app/README.md` para instrucciones detalladas.

### Optimizaciones Mobile

- ✅ Botones ≥ 44px (touch-friendly)
- ✅ Inputs grandes con teclado numérico automático
- ✅ Firma táctil optimizada para dedos
- ✅ Compresión de imágenes antes de subir
- ✅ Diseño responsive (adaptable a cualquier pantalla)
- ✅ Safe area para iPhones (notch)
- ✅ Prevención de zoom accidental

---

## 💾 Base de Datos

### Esquema Principal

#### Tabla: `usuarios`
| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | INTEGER PK | Identificador único |
| `usuario` | TEXT UNIQUE | Nombre de usuario (case-insensitive) |
| `nombre` | TEXT | Nombre completo |
| `pass_hash` | TEXT | Hash de contraseña (PBKDF2) |
| `sal` | TEXT | Sal aleatoria |
| `rol` | TEXT | `ventas` \| `administrativo` \| `cedis` \| `transportador` \| `admin` |
| `activo` | INTEGER | `1` activo, `0` inactivo |
| `creado` | TEXT | Fecha de creación (ISO 8601) |
| `ultima_sesion` | TEXT | Último inicio de sesión |
| `intentos_fallidos` | INTEGER | Intentos fallidos de login |
| `bloqueado_hasta` | TEXT | Fecha de desbloqueo (si aplica) |

#### Tabla: `guias`
| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | INTEGER PK | Identificador único |
| `consecutivo` | INTEGER UNIQUE | Número de guía (autoincremental) |
| `cliente` | TEXT | Nombre del cliente |
| `ciudad` | TEXT | Ciudad de destino |
| `direccion` | TEXT | Dirección de entrega |
| `documentos` | TEXT | Documentos adjuntos (descripción) |
| `obs_ventas` | TEXT | Observaciones de ventas |
| `envio_directo_cedis` | INTEGER | `1` si salta bodega, `0` normal |
| `creada_por` | INTEGER FK | Usuario que creó la guía |
| `creada_en` | TEXT | Fecha de creación |
| `estado` | TEXT | `CREADA` \| `RECIBIDA_ADMIN` \| `EN_CEDIS` \| `EN_RUTA` \| `ENTREGADA` \| `ANULADA` |
| `anulada_motivo` | TEXT | Motivo de anulación (si aplica) |
| `anulada_por` | INTEGER FK | Usuario que anuló |
| `anulada_en` | TEXT | Fecha de anulación |

#### Tabla: `eventos`
| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | INTEGER PK | Identificador único |
| `guia_id` | INTEGER FK | Guía asociada |
| `tipo` | TEXT | Tipo de evento |
| `usuario_id` | INTEGER FK | Usuario que realizó la acción |
| `usuario` | TEXT | Nombre de usuario (denormalizado) |
| `rol` | TEXT | Rol del usuario |
| `en` | TEXT | Fecha/hora del evento |
| `dispositivo` | TEXT | User-Agent del navegador |
| `ip` | TEXT | IP del cliente |
| `datos` | TEXT (JSON) | Datos adicionales (rutas firma/foto, prellenados) |

#### Tabla: `config`
| Columna | Tipo | Descripción |
|---------|------|-------------|
| `clave` | TEXT PK | Clave de configuración |
| `valor` | TEXT | Valor almacenado |

**Claves disponibles:**
- `siguiente`: Próximo consecutivo
- `empresa`: Nombre de la empresa
- `pie`: Pie de página para impresiones
- `lista_clientes_json`: Lista de clientes frecuente (JSON)

### Índices de Rendimiento

```sql
CREATE INDEX idx_guias_estado ON guias(estado);
CREATE INDEX idx_guias_creada_en ON guias(creada_en);
CREATE INDEX idx_guias_cliente ON guias(cliente);
CREATE INDEX idx_guias_consecutivo ON guias(consecutivo);
CREATE INDEX idx_eventos_guia_id ON eventos(guia_id);
CREATE INDEX idx_eventos_tipo ON eventos(tipo);
CREATE INDEX idx_eventos_en ON eventos(en);
CREATE INDEX idx_sesiones_usuario_id ON sesiones(usuario_id);
CREATE INDEX idx_sesiones_expira ON sesiones(expira);
CREATE INDEX idx_usuarios_usuario ON usuarios(usuario);
```

### Modo WAL (Write-Ahead Logging)

La base de datos utiliza **WAL** para permitir:
- Múltiples lectores concurrentes
- Escrituras no bloqueantes
- Mejor rendimiento en red local

---

## 🛠️ Mantenimiento

### Backups

**Recomendado:** Backup diario automático

```bash
# Script de ejemplo (Linux/macOS)
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp guias_coodescor/data/guias.db backups/guias_$DATE.db
tar -czf backups/guias_$DATE.tar.gz guias_coodescor/data/adjuntos/
```

**Windows (PowerShell):**
```powershell
$Date = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item "guias_coodescor\data\guias.db" "backups\guias_$Date.db"
Compress-Archive -Path "guias_coodescor\data\adjuntos\*" -DestinationPath "backups\adjuntos_$Date.zip"
```

### Limpieza de Sesiones Expiradas

El sistema limpia automáticamente sesiones expiradas al iniciar. Para forzar limpieza manual:

```python
from guias_coodescor.database.models import limpiar_sesiones_expiradas
limpiar_sesiones_expiradas()
```

### Rotación de Logs

Los logs rotan automáticamente cada **5 MB**, manteniendo **3 archivos** históricos. Ubicados en:
```
guias_coodescor/data/guias_coodescor.log
guias_coodescor/data/guias_coodescor.log.1
guias_coodescor/data/guias_coodescor.log.2
guias_coodescor/data/guias_coodescor.log.3
```

### Migraciones de Base de Datos

El sistema maneja migraciones versionadas automáticamente. Para crear una nueva migración:

1. Cree un archivo en `database/migrations/` con el formato:
   ```
   V{versión}_{descripcion}.sql
   ```
   Ejemplo: `V4_agrega_columna_costo.sql`

2. El SQL debe ser idempotente (ejecutable múltiples veces sin error)

3. El sistema aplicará la migración automáticamente al reiniciar

---

## 🔧 Solución de Problemas

### El servidor no inicia

**Posibles causas:**
- Puerto 8000 ya está en uso
- Python no está en el PATH
- Permisos insuficientes

**Soluciones:**
```bash
# Verificar si el puerto está ocupado (Windows)
netstat -ano | findstr :8000

# Verificar si el puerto está ocupado (Linux/macOS)
lsof -i :8000

# Cambiar puerto en config.py
PORT = 8080
```

### No puedo acceder desde otros dispositivos

**Verifique:**
1. El firewall permite conexiones entrantes al puerto 8000
2. Todos los dispositivos están en la misma red Wi-Fi
3. Está usando la IP correcta del servidor (no localhost)

**Configurar Firewall (Windows):**
```powershell
New-NetFirewallRule -DisplayName "Guías Coodescor" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

### Las fotos no se guardan

**Verifique:**
1. La carpeta `guias_coodescor/data/adjuntos/` existe y tiene permisos de escritura
2. El tamaño de la imagen no excede 10 MB
3. El formato es PNG, JPEG o GIF

### Olvidé la contraseña de admin

**Solución rápida (reset manual):**

1. Detenga el servidor
2. Ejecute este script Python:

```python
import sqlite3
from guias_coodescor.core.utils import hash_password_puro

conn = sqlite3.connect('guias_coodescor/data/guias.db')
pass_hash, sal = hash_password_puro('nueva_clave_123')
conn.execute(
    "UPDATE usuarios SET pass_hash=?, sal=? WHERE usuario='admin'",
    (pass_hash, sal)
)
conn.commit()
conn.close()
print("Contraseña restablecida a: nueva_clave_123")
```

3. Reinicie el servidor e inicie sesión con la nueva contraseña

### Errores 500 en el navegador

**Revise los logs:**
```
guias_coodescor/data/guias_coodescor.log
```

Busque líneas con `ERROR` para identificar la causa raíz.

---

## 📞 Soporte y Contacto

Para soporte técnico, actualizaciones o personalizaciones, contacte al equipo de desarrollo.

---

## 📄 Licencia

Este software es propiedad exclusiva de **Coodescor**. Su uso está restringido a personal autorizado.

---

## 🙏 Créditos

**Desarrollado por:** Equipo de Desarrollo Coodescor  
**Versión:** 2.0  
**Última actualización:** 2024  

---

*Documentación creada con fines informativos y de capacitación interna.*
