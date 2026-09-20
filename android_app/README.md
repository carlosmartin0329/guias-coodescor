# 📱 Guías Coodescor - App Android para Operarios CEDIS y Transportadores

## 📋 Descripción

Esta aplicación Android permite a los operarios de **CEDIS** y **Transportadores** acceder al sistema **Guías Coodescor** desde sus dispositivos móviles Android de manera nativa.

### ✨ Características

- ✅ **Interfaz nativa Android** con WebView
- ✅ **Configuración sencilla** de la IP del servidor
- ✅ **Detección automática** de conexión a Internet
- ✅ **Captura de firmas** desde el dispositivo móvil
- ✅ **Carga de fotos** desde la cámara o galería
- ✅ **Notificaciones** de estado de conexión
- ✅ **Soporte para Android 7.0+** (API 24+)
- ✅ **Diseño responsive** adaptado a móviles

---

## 🚀 Instalación

### Opción 1: Compilar desde Android Studio (Recomendado)

1. **Abrir el proyecto en Android Studio**
   - Abre Android Studio
   - Selecciona "Open an Existing Project"
   - Navega a `android_app/CoodescorGuias` y selecciona la carpeta

2. **Sincronizar Gradle**
   - Android Studio descargará automáticamente las dependencias
   - Espera a que finalice la sincronización

3. **Configurar el JDK**
   - Asegúrate de tener JDK 17 instalado
   - En `File > Project Structure > SDK Location`, configura el JDK

4. **Ejecutar en un dispositivo o emulador**
   - Conecta tu dispositivo Android (con modo desarrollador activado)
   - O usa un emulador (recomendado: Pixel 5, Android 13)
   - Haz clic en el botón ▶️ Run

5. **Generar APK para distribución**
   - `Build > Build Bundle(s) / APK(s) > Build APK`
   - El APK se generará en `android_app/CoodescorGuias/app/build/outputs/apk/debug/`

---

### Opción 2: Usar la PWA directamente (Sin instalar app)

El sistema web ya está configurado como **Progressive Web App (PWA)**, por lo que puedes:

1. Abrir Chrome en tu dispositivo Android
2. Navegar a `http://[IP-DEL-SERVIDOR]:8000`
3. Chrome mostrará una opción para **"Instalar app"** o **"Añadir a pantalla de inicio"**
4. Aceptar para instalar como aplicación nativa

**Ventajas:**
- No requiere compilar código Android
- Se actualiza automáticamente cuando el servidor se actualiza
- Funciona con cache offline básico

---

## 📱 Configuración de la App

Al abrir la aplicación por primera vez, se mostrará un diálogo de configuración:

```
┌─────────────────────────────────┐
│     Configuración Inicial         │
│                                 │
│  Ingrese la dirección IP del     │
│  servidor Guías Coodescor        │
│                                 │
│  ┌───────────────────────┐      │
│  │ 192.168.1.100         │      │
│  └───────────────────────┘      │
│                                 │
│  [Cancelar]         [Guardar]    │
└─────────────────────────────────┘
```

### Datos a ingresar:

| Campo | Valor | Ejemplo |
|-------|-------|---------|
| **IP del Servidor** | La IP de la PC donde corre el servidor | `192.168.1.100` |
| **Puerto** | Puerto del servidor (por defecto: 8000) | `8000` |

> ⚠️ **IMPORTANTE:** La PC con el servidor y el dispositivo Android **deben estar en la misma red Wi-Fi**

---

## 🎯 Uso para Operarios

### Para CEDIS:

1. **Recepción en Bodega** (Admin):
   - Abre la app
   - Inicia sesión con usuario `administrativo`
   - Ve al tablero y verás las guías pendientes
   - Selecciona una guía y firma la recepción

2. **Control CEDIS**:
   - Usa usuario `cedis`
   - En el tablero verás las guías en estado "RECIBIDA_ADMIN"
   - Abre una guía y completa:
     - Número de cajas, bolsas, cayvas, sobres
     - Condiciones del vehículo
     - Firma digital
   - Guarda el control

3. **Entrega al Transportador**:
   - Después del control, la guía pasará a "EN_CEDIS"
   - Completa los datos del transportador
   - Firma digital
   - Guarda la entrega

4. **Entrega al Cliente**:
   - Cuando la guía está "EN_RUTA"
   - Completa:
     - Nombre de quien recibe
     - Firma del cliente o foto como evidencia
     - Observaciones
   - Guarda la entrega final

### Para Transportadores:

El transportador **no necesita instalar la app**. El operario de CEDIS:

1. Registra los datos del transportador en el sistema web
2. El transportador solo necesita:
   - Firmar en la tablet/celular de CEDIS al recibir la guía
   - Firmar al entregar al cliente

---

## 📁 Estructura del Proyecto Android

```
android_app/
└── CoodescorGuias/
    ├── app/
    │   ├── src/
    │   │   └── main/
    │   │       ├── java/com/coodescor/guias/
    │   │       │   ├── MainActivity.java   # Actividad principal
    │   │       │   └── MainApp.java        # Configuración de la app
    │   │       ├── res/
    │   │       │   ├── layout/
    │   │       │   │   └── activity_main.xml  # Diseño de la interfaz
    │   │       │   ├── values/
    │   │       │   │   ├── strings.xml        # Textos de la app
    │   │       │   │   ├── colors.xml        # Colores
    │   │       │   │   └── styles.xml        # Estilos
    │   │       │   └── drawable/
    │   │       │       ├── btn_primary_background.xml
    │   │       │       ├── btn_secondary_background.xml
    │   │       │       └── ic_refresh.xml
    │   │       └── AndroidManifest.xml      # Manifest de Android
    │   ├── build.gradle      # Configuración de Gradle
    │   └── proguard-rules.pro
    ├── build.gradle                         # Build del proyecto
    ├── settings.gradle                      # Configuración de Gradle
    └── gradle.properties                    # Propiedades de Gradle
```

---

## ⚙️ Configuración Adicional

### Cambiar la IP por defecto

En `MainApp.java`, línea 17-18:
```java
private static final String DEFAULT_SERVER_IP = "192.168.1.100";
private static final String DEFAULT_SERVER_PORT = "8000";
```

### Cambiar el nombre y ícono de la app

En `AndroidManifest.xml`:
```xml
<application
    android:label="Guías Coodescor"
    android:icon="@mipmap/ic_launcher">
```

Los íconos se encuentran en las carpetas:
- `app/src/main/res/mipmap-hdpi/`
- `app/src/main/res/mipmap-mdpi/`
- `app/src/main/res/mipmap-xhdpi/`
- etc.

### Cambiar el tema de colores

En `res/values/colors.xml`:
```xml
<color name="azul_primary">#1d4ed8</color>
<color name="azul_secondary">#2563eb</color>
```

---

## 🐞 Solución de Problemas

### La app no carga la página

1. **Verifica la IP del servidor**
   - Asegúrate de que la IP sea correcta
   - Prueba ping desde el dispositivo: `ping 192.168.1.100`

2. **Verifica el puerto**
   - El servidor debe estar escuchando en el puerto 8000
   - Prueba acceder desde Chrome: `http://[IP]:8000`

3. **Verifica el firewall**
   - En Windows: Permite el puerto 8000 en el firewall
   - En el router: No bloquear el puerto

4. **Verifica que estén en la misma red**
   - Ambos dispositivos deben estar conectados a la misma Wi-Fi

### La cámara no funciona

1. **Verifica permisos**
   - La app solicita permisos al iniciar
   - Asegúrate de conceder todos los permisos

2. **Limpia caché de la app**
   - Ve a Configuración > Aplicaciones > Guías Coodescor
   - Limpia caché y datos

### La app se cierra inesperadamente

1. **Verifica la versión de Android**
   - Requiere Android 7.0+ (API 24+)

2. **Revisa Logcat**
   - Conecta el dispositivo a Android Studio
   - Ve a `View > Tool Windows > Logcat`
   - Busca errores marcados en rojo

---

## 📊 Requisitos del Sistema

### Servidor:
- Python 3.7+
- Sistema operativo: Windows, Linux o macOS
- Memoria RAM: 2GB mínimo
- Espacio en disco: 100MB

### Cliente Android:
- Android 7.0 (Nougat) o superior
- Conexión Wi-Fi
- Cámara (opcional, para fotos)
- Navegador Chrome (para PWA)

---

## 🔒 Seguridad

### Permisos requeridos:

| Permiso | Uso | ¿Obligatorio? |
|---------|-----|---------------|
| INTERNET | Conexión al servidor | ✅ Sí |
| ACCESS_NETWORK_STATE | Verificar conexión | ✅ Sí |
| CAMERA | Tomar fotos para firmas | ❌ No (opcional) |
| WRITE_EXTERNAL_STORAGE | Guardar fotos temporalmente | ❌ No (opcional) |
| READ_EXTERNAL_STORAGE | Cargar fotos desde galería | ❌ No (opcional) |

### Recomendaciones para producción:

1. **Usa HTTPS en producción**
   - Configura un proxy reverso con nginx/Caddy
   - Modifica `config.py` para usar cookies seguras

2. **Protege la red Wi-Fi**
   - Usa contraseña fuerte
   - No uses redes públicas abiertas

3. **Cambia las contraseñas por defecto**
   - Desde el panel admin: `/admin`
   - Cambia todas las contraseñas de usuarios

---

## 📞 Soporte

Si tienes problemas, revisa:

1. Este README
2. El `README.md` en la carpeta raíz del proyecto
3. Los logs de Android Studio (Logcat)
4. Los logs del servidor (en `guias_coodescor/data/guias_coodescor.log`)

---

## 🎨 Personalización

Puedes personalizar:

- **Colores**: Modifica `android_app/CoodescorGuias/app/src/main/res/values/colors.xml`
- **Textos**: Modifica `android_app/CoodescorGuias/app/src/main/res/values/strings.xml`
- **Estilos**: Modifica `android_app/CoodescorGuias/app/src/main/res/values/styles.xml`
- **Lógica**: Modifica `MainActivity.java` y `MainApp.java`

---

*Desarrollado para Guías Coodescor - Sistema de actas de entrega digitales*
