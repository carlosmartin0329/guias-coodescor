# Guías Coodescor

Aplicación para la gestión de guías, clientes y receptores.

## Estructura

```
guias coodescor/
├── backend/          API y lógica de negocio (Python)
│   ├── guias_coodescor/  Paquete: api, services, database, core, web
│   ├── tests/            Pruebas automatizadas (pytest)
│   ├── scripts/          Utilidades (importación de Excel, etc.)
│   ├── run_app.py        Punto de entrada del servidor
│   └── requirements.txt
├── frontend/         Interfaz web React + Vite (rediseño UX 2026)
├── android_app/      Aplicación Android
├── deploy/
│   ├── docker/       Dockerfiles y docker-compose (dev y producción)
│   └── windows/      Scripts de arranque para Windows
├── docs/             Documentación técnica, bitácora y referencias
├── ngrok.exe         Túnel externo opcional (o tools/ngrok.exe)
└── .github/workflows CI/CD
```

## Arranque rápido

### Windows (sin Docker)

```bat
deploy\windows\run.bat
```

El servidor queda en **http://localhost:8000** y ya sirve la **interfaz React
nueva** (login, tablero, detalle, nueva guía y administración). Si el build no
existe, el script lo compila automáticamente la primera vez (requiere Node.js).

### Backend manual

```bash
cd frontend && npm install && npm run build   # una vez (o tras cambiar el frontend)
cd ../backend
pip install -r requirements.txt
python run_app.py
```

Abre **http://localhost:8000**. El backend sirve el build de `frontend/dist`, así
que no se necesita Vite en producción ni en el acceso por ngrok.

### Frontend en desarrollo (opcional)

```bash
cd backend && python run_app.py              # API en http://localhost:8000
cd frontend && npm install && npm run dev    # SPA con recarga en http://localhost:5173
```

La SPA incluye el rediseño UX/UI: tablero “Mi jornada”, vistas de Guías y En ruta,
detalle por pasos, asistente de nueva guía, modo claro/oscuro, navegación móvil y
notificaciones. El puerto 8000 siempre muestra el build compilado.

### Pruebas

```bash
cd backend
python -m pytest tests          # backend (incluye E2E HTTP)
cd ../frontend
npm run lint && npm run build
npx playwright test             # E2E navegador (requiere navegadores instalados)
# Si no descargaste los navegadores de Playwright, usa el Chrome del sistema:
# PowerShell:  $env:PLAYWRIGHT_CHANNEL="chrome"; npx playwright test
```

### Docker

```bash
cd deploy/docker
docker compose up --build            # desarrollo
docker compose -f docker-compose.prod.yml up -d --build   # producción
```

## Configuración

- Copia `.env.example` (raíz del repositorio) a `.env` y ajusta los valores.
  Todas las variables usan el prefijo `COODESCOR_` (p. ej. `COODESCOR_PORT`,
  `COODESCOR_DATA_DIR`, `COODESCOR_CORS_ORIGINS`).
- `backend/config.json` define rutas locales y **no se versiona**.
- Los datos (base de datos, adjuntos, `secretos.json`) viven en el directorio de datos, no en el código.
- El detalle del control de calidad, defectos corregidos y evidencia está en
  [`docs/QA-INFORME.md`](docs/QA-INFORME.md).
- La integración gratuita de confirmaciones con Google Apps Script está
  documentada en [`docs/CONFIGURACION-GOOGLE.md`](docs/CONFIGURACION-GOOGLE.md).
  Cada desarrollador puede usar su propia cuenta de Google; las claves locales
  no se versionan.

## Documentación

Ver la carpeta [`docs/`](docs/), en particular:

- [`docs/documentacion-tecnica.md`](docs/documentacion-tecnica.md): arquitectura y operación.
- [`docs/FLUJOS-FUNCIONALES.md`](docs/FLUJOS-FUNCIONALES.md): flujos del aplicativo, reglas y bitácora de revisión.
- [`docs/QA-INFORME.md`](docs/QA-INFORME.md): informe de QA integral, defectos corregidos y checklist de entrega.
- [`docs/UX-PROPUESTA-MODERNA.md`](docs/UX-PROPUESTA-MODERNA.md): rediseño UX/UI implementado, maquetas y capturas reales (galería en [`docs/ux-preview/index.html`](docs/ux-preview/index.html)).
