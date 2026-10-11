# Base44 Dev Environment

## Project Overview
Guías Coodescor — local digital delivery-guide system for merchandise transport.
Python stdlib HTTP server backend (ThreadingHTTPServer + SQLite) + React/Vite frontend.

## Architecture
- **Backend**: `guias_coodescor/` package, entry point `run_app.py` → `guias_coodescor.app.main()`. No web framework — plain `http.server.ThreadingHTTPServer` on port 8000. Uses pydantic/pydantic-settings for config validation. SQLite database auto-created on first run.
- **Frontend**: `frontend/` — React 19 + Vite 8 SPA. Uses relative `/api` URLs via axios; Vite dev proxy routes `/api`, `/static`, `/login`, `/tablero`, `/admin`, `/static_file`, `/firma` to the backend.
- **Data dir**: resolved by `COODESCOR_DATA_DIR` env var (highest priority). Set to `/data` (named volume) in the Base44 compose.
- **No external credentials needed** — fully local system with SQLite. AI provider keys (HuggingFace, Mistral, Groq, Google Gemini) are optional and only used if set.

## Dev Setup (docker-compose.base44.yml)
- `backend`: `python:3.11-slim`, source bind-mounted read-only, `pip install` on startup, runs `python run_app.py`. No hot-reload (plain HTTP server) — restart the service after backend edits.
- `frontend`: `node:20-slim`, `frontend/` bind-mounted, `npm install` on startup, runs `vite --host 0.0.0.0`. HMR active. Port 3000 → 5173.
- The Vite proxy target is configurable via `API_PROXY_TARGET` env var (defaults to `http://127.0.0.1:8000` for local dev; set to `http://backend:8000` in compose).
- `__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS` is passed through for the preview proxy hostname.

## Default Users (change passwords in Admin panel after first login)
- `admin / admin123` — system admin
- `administrativo / adminbod123` — warehouse admin
- `ventas / ventas123` — sales
- `cedis / cedis123` — CEDIS operator

## Verification
- Backend health: `curl http://localhost:8000/api/captcha/nuevo`
- Frontend: `curl http://localhost:3000/` — should return the Vite SPA HTML
- Login at `/login` with default credentials above
