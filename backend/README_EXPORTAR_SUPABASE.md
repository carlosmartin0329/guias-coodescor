# Exportador a Supabase - Guías Coodescor

Este módulo replica datos de la base SQLite local a Supabase (PostgreSQL)
cada 15 minutos, manteniendo la app local como motor operativo y Supabase
como respaldo externo y para reportes.

## Arquitectura

```
SQLite local (guias.db)  -->  exportar_a_supabase.py  -->  Supabase (PostgreSQL)
      (motor operativo)           (cada 15 min)            (respaldo / reportes)
```

La aplicación sigue funcionando 100% local y sin internet. Supabase es solo
una copia de seguridad externa accesible desde cualquier lugar.

## Tablas sincronizadas

| Tabla SQLite | Clave primaria | Filas aprox. |
|--------------|----------------|--------------|
| usuarios     | id             | 12           |
| clientes     | nit            | 154          |
| guias        | id             | 106          |
| eventos      | id             | 179          |
| config       | clave          | 9            |
| admin_auditoria | id          | 2            |
| entrega_tokens | id          | 1            |
| sesiones     | sid            | 4            |
| schema_migrations | version    | 8            |

## Pasos para configurar

### 1. Crear proyecto en Supabase

1. Ve a https://supabase.com y crea una cuenta (gratis).
2. Crea un nuevo proyecto.
3. Anota la **URL del proyecto** (ej: `https://abcdefghijklmnop.supabase.co`).
4. Ve a **Settings > API** y copia la **anon public key** o la **service_role key**.

### 2. Crear las tablas en Supabase

Ejecuta este SQL en el **SQL Editor** de Supabase para crear las tablas con el
esquema correcto:

```sql
-- Habilitar extensión uuid-ossp si se necesita
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabla usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY,
    usuario TEXT,
    nombre TEXT,
    pass_hash TEXT,
    sal TEXT,
    rol TEXT,
    activo INTEGER,
    creado TEXT,
    ultima_sesion TEXT,
    intentos_fallidos INTEGER,
    bloqueado_hasta TEXT
);

-- Tabla clientes
CREATE TABLE IF NOT EXISTS clientes (
    nit TEXT PRIMARY KEY,
    razon_social TEXT,
    direccion TEXT,
    ciudad TEXT,
    telefono TEXT,
    email TEXT,
    contacto TEXT,
    forma_pago_default TEXT,
    observaciones TEXT,
    metadata TEXT,
    cliente_descubierto INTEGER,
    creado_en TEXT,
    actualizado_en TEXT
);

-- Tabla guias
CREATE TABLE IF NOT EXISTS guias (
    id INTEGER PRIMARY KEY,
    consecutivo INTEGER,
    cliente TEXT,
    ciudad TEXT,
    direccion TEXT,
    documentos TEXT,
    obs_ventas TEXT,
    envio_directo_cedis INTEGER,
    creada_por INTEGER,
    creada_en TEXT,
    estado TEXT,
    anulada_motivo TEXT,
    anulada_por INTEGER,
    anulada_en TEXT,
    tipo_transportador TEXT,
    transportador_asignado_id INTEGER,
    nit TEXT,
    centro_operacion TEXT,
    prefijo TEXT
);

-- Tabla eventos
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY,
    guia_id INTEGER,
    tipo TEXT,
    usuario_id INTEGER,
    usuario TEXT,
    rol TEXT,
    en TEXT,
    dispositivo TEXT,
    ip TEXT,
    datos TEXT
);

-- Tabla config
CREATE TABLE IF NOT EXISTS config (
    clave TEXT PRIMARY KEY,
    valor TEXT
);

-- Tabla admin_auditoria
CREATE TABLE IF NOT EXISTS admin_auditoria (
    id INTEGER PRIMARY KEY,
    en TEXT,
    usuario_id INTEGER,
    usuario TEXT,
    rol TEXT,
    ip TEXT,
    accion TEXT,
    tabla TEXT,
    clave TEXT,
    resumen TEXT,
    detalle TEXT,
    filas_afectadas INTEGER
);

-- Tabla entrega_tokens
CREATE TABLE IF NOT EXISTS entrega_tokens (
    id INTEGER PRIMARY KEY,
    guia_id INTEGER,
    token TEXT,
    creado_por INTEGER,
    creado_rol TEXT,
    creado_en TEXT,
    expira TEXT,
    usado_en TEXT,
    usado_ip TEXT,
    usado_ua TEXT
);

-- Tabla sesiones
CREATE TABLE IF NOT EXISTS sesiones (
    sid TEXT PRIMARY KEY,
    usuario_id INTEGER,
    creada TEXT,
    expira TEXT,
    ip TEXT,
    user_agent TEXT
);

-- Tabla schema_migrations
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    nombre TEXT,
    aplicada_en TEXT
);
```

### 3. Configurar variables de entorno

Copia `.env.example` a `.env` y completa los valores:

```powershell
Copy-Item .env.example .env
```

Edita `.env` con tu URL y clave de Supabase:

```
SUPABASE_URL=https://TU_PROYECTO.supabase.co
SUPABASE_KEY=TU_CLAVE_API_AQUI
SQLITE_PATH=C:\ProgramData\Coodescor\Guias\guias.db
SUPABASE_BATCH=100
```

### 4. Ejecutar la exportación

**Una sola vez:**
```powershell
py exportar_a_supabase.py
```

**Cada 15 minutos (bucle interno):**
```powershell
py exportar_a_supabase.py --loop --interval 900
```

**Como tarea programada de Windows (recomendado):**

Ejecuta como Administrador:
```powershell
.\configurar_tarea_programada.ps1
```

Esto crea una tarea en el Programador de Tareas de Windows que ejecuta
`exportar_a_supabase.py` cada 15 minutos.

### 5. Verificar que funcionó

En el panel de Supabase, ve a **Table Editor** y confirma que las tablas
tienen datos replicados desde SQLite.

## Notas importantes

- **Sincronización incremental**: el script solo envía filas nuevas (basado en la clave primaria máxima ya en Supabase). No duplica registros.
- **Upsert**: si una fila ya existe en Supabase con la misma PK, se actualiza (merge-duplicates).
- **No se borra nada**: el script nunca elimina filas de Supabase, solo inserta/actualiza.
- **Primera ejecución**: envía todas las filas existentes. Ejecuciones siguientes solo envían las nuevas.
- **Conexión**: requiere acceso a internet para llegar a Supabase. Si no hay conexión, el script registra el error y continúa en el próximo ciclo.

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `exportar_a_supabase.py` | Script principal de exportación |
| `.env.example` | Plantilla de variables de entorno |
| `exportar_a_supabase.bat` | Ejecutar una vez desde Windows |
| `configurar_tarea_programada.ps1` | Crear tarea programada cada 15 min |
