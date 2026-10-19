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
├── frontend/         Interfaz web (React + Vite)
├── android_app/      Aplicación Android
├── deploy/
│   ├── docker/       Dockerfiles y docker-compose (dev y producción)
│   └── windows/      Scripts de arranque para Windows
├── docs/             Documentación técnica, bitácora y referencias
├── tools/            Herramientas externas (ngrok)
└── .github/workflows CI/CD
```

## Arranque rápido

### Windows (sin Docker)

```bat
deploy\windows\run.bat
```

El servidor queda en http://localhost:8000.

### Backend manual

```bash
cd backend
pip install -r requirements.txt
python run_app.py
```

### Pruebas

```bash
cd backend
python -m pytest tests
```

### Docker

```bash
cd deploy/docker
docker compose up --build            # desarrollo
docker compose -f docker-compose.prod.yml up -d --build   # producción
```

## Configuración

- Copia `backend/.env.example` y ajusta los valores.
- `backend/config.json` define rutas locales y **no se versiona**.
- Los datos (base de datos, adjuntos, `secretos.json`) viven en el directorio de datos, no en el código.

## Documentación

Ver la carpeta [`docs/`](docs/), en particular `docs/documentacion-tecnica.md`.
