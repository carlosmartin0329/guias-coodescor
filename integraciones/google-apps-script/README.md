# Confirmación gratuita de recibido · Google Apps Script

Esta integración crea una página pública de Google para que el cliente confirme
el recibido de una guía. **No requiere firma digital, lugar, dominio ni servidor
adicional.** Solo captura:

- Fecha y hora (la registra Google al enviar).
- Nombre de quien recibe.
- Observaciones.

La página muestra el número de guía y el nombre del cliente. El link es de un
solo uso, vence a los 7 días y el aplicativo local lo procesa automáticamente
cada 5 minutos.

## Archivos

| Archivo | Uso |
|---|---|
| `Codigo.gs` | Lógica de token, página, Google Sheets y API de sincronización. |
| `Pagina.html` | Página pública con el logo y colores de Coodescor. |
| `Logo.gs` | Logo corporativo embebido en base64. |
| `appsscript.json` | Configuración del proyecto y del Web App. |
| `coodescor-logo.png` | Logo original extraído del manual de imagen. |

## Instalación en la cuenta de Google que elijas

> No hay una cuenta fija en este repositorio. Cada desarrollador puede usar su
> propia cuenta. No escribas correos, claves ni URLs reales en archivos que se
> suban a Git. Las instrucciones completas están en
> [`docs/CONFIGURACION-GOOGLE.md`](../../docs/CONFIGURACION-GOOGLE.md).

1. Entrar a <https://sheets.google.com> con la cuenta elegida y crear una hoja nueva
   llamada **Coodescor Confirmaciones**.
2. En la hoja: **Extensiones → Apps Script**.
3. Crear o reemplazar los archivos:
   - `Codigo.gs`
   - `Pagina.html`
   - `Logo.gs`
   - `appsscript.json` (menú **Configuración del proyecto → Mostrar manifiesto**).
4. En **Configuración del proyecto → Propiedades del script**, agregar:

   | Propiedad | Valor |
   |---|---|
   | `TOKEN_SECRET` | Una clave larga y aleatoria, por ejemplo 48 caracteres. |
   | `SYNC_SECRET` | Otra clave larga y aleatoria, distinta a la anterior. |
   | `SHEET_NAME` | `Confirmaciones` |

5. Guardar el proyecto.
6. **Implementar → Nueva implementación → Aplicación web**:
   - Ejecutar como: **Yo**.
   - Quién tiene acceso: **Cualquier persona**.
   - Implementar y copiar la URL del Web App.
7. Verificar que la URL termine en `/exec`.

> Cada vez que se modifique el código hay que crear una **nueva versión** de la
> implementación. La URL del Web App se mantiene si se actualiza la misma
> implementación.

## Configuración del aplicativo local

En el servidor donde corre el aplicativo, definir estas variables de entorno
antes de arrancar:

```powershell
$env:COODESCOR_CONFIRMACION_URL = "https://script.google.com/macros/s/XXXXXXXX/exec"
$env:COODESCOR_CONFIRMACION_TOKEN_SECRET = "la-misma-clave-TOKEN_SECRET"
$env:COODESCOR_CONFIRMACION_SYNC_SECRET = "la-misma-clave-SYNC_SECRET"
$env:COODESCOR_CONFIRMACION_INTERVALO = "300"
```

Luego reiniciar el servidor. El aplicativo consultará Google cada 5 minutos y
cerrará automáticamente las guías **EN_RUTA** del flujo normal.

También se puede usar el archivo de configuración local:

1. Copiar `backend/configuracion_google.env.example` a
   `backend/configuracion_google.env`.
2. Completar URL y claves.
3. Iniciar con `deploy\windows\iniciar_servidor.bat`, que carga ese archivo
   automáticamente.

> El archivo real `configuracion_google.env` está excluido de Git.

> `TOKEN_SECRET` y `SYNC_SECRET` deben coincidir exactamente entre Apps Script
> y el aplicativo. No compartirlas con el cliente.

## Prueba manual

1. Abrir el Web App directamente: debe mostrar una página de error de token
  (es normal).
2. Generar un link desde una guía normal en el aplicativo con Ventas o
   Administrativo.
3. Abrir el link en el navegador: debe mostrar guía y cliente.
4. Confirmar con nombre y observaciones.
5. En el aplicativo, abrir **Administrativo → Confirmaciones** y pulsar
   **Sincronizar ahora**, o esperar el ciclo automático de 5 minutos.
6. La guía debe quedar **ENTREGADA** y la confirmación **Aplicada**.

## Seguridad

- La hoja de Google es privada de la cuenta corporativa.
- La página pública solo muestra guía, cliente y formulario.
- El token está firmado con HMAC SHA-256; no se puede alterar guía/cliente.
- Un token solo se acepta una vez.
- Los endpoints `accion=pendientes` y `accion=marcar` exigen `SYNC_SECRET`.
- El aplicativo no expone las claves en la interfaz.
