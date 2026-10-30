# Configuración de Google para desarrollo

Este proyecto puede usar **cualquier cuenta de Google** que tenga acceso a
Google Sheets y Google Apps Script. No hay un correo corporativo fijo y no se
deben guardar credenciales reales en Git.

Cada desarrollador debe crear su propio Web App y usar sus propias claves.

## Qué se necesita

- Una cuenta de Google.
- Una hoja de cálculo nueva para las confirmaciones.
- Un proyecto de Google Apps Script vinculado a esa hoja.
- Dos claves aleatorias distintas:
  - `TOKEN_SECRET`: firma los links de confirmación.
  - `SYNC_SECRET`: protege la consulta y marcación de confirmaciones.

## 1. Crear el proyecto en Google

1. Entra a <https://sheets.google.com> con la cuenta que elijas.
2. Crea una hoja llamada `Coodescor Confirmaciones` (o el nombre que prefieras).
3. En la hoja: **Extensiones → Apps Script**.
4. Crea o pega los archivos de `integraciones/google-apps-script/`:
   - `Codigo.gs`
   - `Pagina.html`
   - `Logo.gs`
   - `appsscript.json`
5. En **Configuración del proyecto → Propiedades del script**, agrega:

| Propiedad | Contenido |
|---|---|
| `TOKEN_SECRET` | Clave larga y aleatoria |
| `SYNC_SECRET` | Otra clave larga y aleatoria, distinta |
| `SHEET_NAME` | `Confirmaciones` |

Puedes generar las claves en PowerShell, ejecutando dos veces:

```powershell
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$b = New-Object byte[] 36
$rng.GetBytes($b)
[Convert]::ToBase64String($b)
```

6. Publica el proyecto como **Aplicación web**:
   - Ejecutar como: **Yo**.
   - Acceso: **Cualquier persona**.
   - Copia la URL que termina en `/exec`.

> Cada vez que cambies el código, crea una **nueva versión** desde
> **Implementar → Administrar implementaciones**.

## 2. Crear la configuración local

Cada desarrollador crea su archivo local, que **no se versiona**:

```powershell
Copy-Item backend\configuracion_google.env.example backend\configuracion_google.env
notepad backend\configuracion_google.env
```

Completa:

```env
COODESCOR_CONFIRMACION_URL=https://script.google.com/macros/s/TU_ID/exec
COODESCOR_CONFIRMACION_TOKEN_SECRET=LA_CLAVE_DE_TOKEN_SECRET
COODESCOR_CONFIRMACION_SYNC_SECRET=LA_CLAVE_DE_SYNC_SECRET
COODESCOR_CONFIRMACION_INTERVALO=300
```

El archivo real `backend/configuracion_google.env` está excluido de Git.

## 3. Reiniciar y probar

```powershell
cd deploy\windows
.\iniciar_servidor.bat
```

Prueba:

1. Entra como Ventas o Administrativo.
2. Abre una guía normal.
3. Genera el link de confirmación.
4. Ábrelo en una ventana privada.
5. Confirma con un nombre.
6. Espera 5 minutos o abre **Tokens clientes** y pulsa **Sincronizar ahora**.

## 4. Compartir el proyecto por un medio privado

Si necesitas entregar el proyecto ya configurado:

- Copia la **carpeta completa** del proyecto, no un `git clone`.
- Incluye `backend/configuracion_google.env`.
- Envía el paquete por un canal privado: correo cifrado, unidad compartida
  privada, USB u otro medio controlado.
- No subas ese archivo a un repositorio público.
- Si el repositorio se vuelve público por error, rota `TOKEN_SECRET` y
  `SYNC_SECRET` en Google y en la configuración local.

## 5. Reglas para Git

- Nunca versionar `backend/configuracion_google.env`.
- Nunca versionar `.env` ni `secretos.json`.
- No incluir URLs de implementación reales en documentación pública.
- Usar únicamente los archivos `.example` como plantillas.
- Si se cambia una clave, los links emitidos antes dejan de ser válidos; hay
  que generar links nuevos.

## Archivos relacionados

- `backend/configuracion_google.env.example`: plantilla sin secretos.
- `integraciones/google-apps-script/README.md`: instalación del Web App.
- `deploy/windows/iniciar_servidor.bat`: carga la configuración local al arrancar.
