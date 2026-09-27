# Sprint 03 · CAPTCHA · LOADTEST 500 · REPORTES ADMIN

## Resumen Ejecutivo

Sprint 03 del proyecto **Guías Coodescor** implementa 4 requerimientos funcionales + 1 tarea de regresión solicitados por el cliente, sobre la base SPEC v1.0 intacta (sin retrocesos, solo adiciones):

| Req | Descripción | Estimado | Cumplimiento |
|---|---|---:|---|
| 1 | CAPTCHA verificación humana login (SVG server-side stdlib) | 22 ACs | ✅ 22/22 PASS |
| 2 | Prueba de carga/concurrencia 500 guías (5 ventas + 2 cedis concurrentes) | 1 métrica umbral ≥95% OK | ✅ 100% (sin DB locked) |
| 3 | Reporte resultados loadtest (Excel CSV BOM + HTML imprimible PDF A4) | 17 ACs | ✅ 17/17 PASS |
| 4 | Usuarios prueba adicionales (ventas5 rol ventas + cedis2 rol cedis) | 4 ACs | ✅ 4/4 PASS |
| 5 | Suites regresión + consolidación review.md | 5 suites obligatorias | ✅ TODAS PASS |

---

## Tabla TR Gates Totalizados (Tareas 1-4 + Regresión 5)

| Componente | Reglas / Tests | Pass | Fail | Estado |
|---|---:|---:|---:|---|
| **TASK 1 · Usuarios extra** (ventas5 + cedis2) · seed idempotente | 4 reglas TR | 4 | 0 | ✅ Aprobado |
| **TASK 2 · CAPTCHA login SVG distorsionado + HMAC nonce 1-solo-uso** | 22 reglas TR HTTP | 22 | 0 | ✅ Aprobado |
| **TASK 3 · Load Test 500 guías VENTAS+CEDIS concurrente** (ThreadPoolExecutor 50 workers) | 1 umbral (≥95% OK, 0 DB locked) | 1 | 0 | ✅ Aprobado |
| **TASK 4 · Reportes admin Excel (CSV UTF8 BOM) + PDF (HTML print A4)** | 17 reglas TR HTTP | 17 | 0 | ✅ Aprobado |
| **REGRESIÓN 5.1 · py_compile (13 Python files targets)** | 13 Syntax | 13 | 0 | ✅ OK EXIT 0 |
| **REGRESIÓN 5.2 · test_clientes_receptores.py (unittest)** | 27 tests | 27 | 0 | ✅ Ran 27 in 6.448s |
| **REGRESIÓN 5.3 · test_sistema.py (unittest core/services)** | 34 tests | 34 | 0 | ✅ Ran 34 in 2.301s |
| **REGRESIÓN 5.4 · diag_nuevo_panel_ventas.py (E2E HTTP real)** | 6 checks | 6 | 0 | ✅ PANEL_EXIT=0 |
| **REGRESIÓN 5.5 · diag_e2e_autocompletar_receptores.py (E2E HTTP real)** | 8 tests | 8 | 0 | ✅ Ran 8 in 43.014s |

---

## Lista de Cambios de Código Aplicados

Solo modificaciones **aditivas** (ningún retroceso, ninguna columna/rol/carpeta intacta eliminada).

| Archivo (path relativo) | Rango líneas | Funcionalidad cubierta |
|---|---|---|
| [guias_coodescor/config.py](file:///D:/Users/57323/Downloads/guias%20coodescor/guias_coodescor/config.py#L139-L153) | L139-L153 | `DEFAULT_USERS` append idempotente 2 usuarios loadtest: `ventas5` (uid=11 rol=ventas pw=ventas123) + `cedis2` (uid=12 rol=cedis pw=cedis123) `activo=1` |
| [crear_usuarios_loadtest.py](file:///D:/Users/57323/Downloads/guias%20coodescor/crear_usuarios_loadtest.py#L1-L85) | L1-L85 | Script CLI idempotente (SELECT OR IGNORE / UPDATE) reinserta subset `{ventas5, cedis2}` reutilizando `hash_password_puro` + `init_db()`; exit 0 siempre |
| [guias_coodescor/services/captcha_service.py](file:///D:/Users/57323/Downloads/guias%20coodescor/guias_coodescor/services/captcha_service.py#L1-L270) | L1-L270 | ✅ Servicio CAPTCHA stdlib (sin externos): SVG 260×80 distorsionado (rotaciones ±22°, 7 líneas ruido, 40 puntos); ALFABETO `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` sin ambigüos; secreto persistido `captcha_hmac_secret_key` en tabla config; token base64url firmado HMAC SHA256 (ip/ua/exp/nonce/resp_hash); nonce 1-solo-uso + TTL lazy purge 360s Lock; bypass seguro doble-factor `COODESCOR_CAPTCHA_BYPASS_KEY` (env+header `compare_digest`); 300s expiración; APIs públicas: `generar_captcha()` + `validar_captcha()` |
| [guias_coodescor/web/views/auth_views.py](file:///D:/Users/57323/Downloads/guias%20coodescor/guias_coodescor/web/views/auth_views.py#L24-L69) | L24-L69 | Inyección bloque CAPTCHA dentro `<form data-api="/api/login">`: render SVG, `<input captcha_respuesta>` aria-label, `<input hidden captcha_token> escape()`, botón 🔄 Nuevo `btn-refresh-captcha` focus-outline var(--azul) |
| [guias_coodescor/api/router.py](file:///D:/Users/57323/Downloads/guias%20coodescor/guias_coodescor/api/router.py#L288-L662) | L288-291, L310-313, L337-350, L364-369, L640-662 | (1) Endpoints sin auth: `GET/POST /api/captcha/nuevo` → JSON `{svg,token}`. (2) **Paso 0 en `_api_login()`** valida CAPTCHA ANTES de `svc_login()` → 400 `{captcha_error:true}` **SIN incrementar `intentos_fallidos`** (anti-credential stuffing). (3) Aplica bypass seguro `X-CAPTCHA-Bypass` env+header. (4) Vista `GET /admin/loadtest/ultimo` admin-only. (5) `GET /api/loadtest/ultimo.csv|.xlsx` attachment UTF8 BOM sep `;` rol admin 403 non-admin |
| [guias_coodescor/static/style.css](file:///D:/Users/57323/Downloads/guias%20coodescor/guias_coodescor/static/style.css#L195-L243) | L195-L243 | (A) `.captcha-wrapper/.captcha-image/.btn-refresh-captcha` responsive min-height 70px focus sr-only. (B) Bloque `@media print @page A4 margin 14mm portrait`, helpers `.no-print / .only-print`, tablas bordes, KPI grid 3 cols impresión reporte |
| [guias_coodescor/static/app.js](file:///D:/Users/57323/Downloads/guias%20coodescor/guias_coodescor/static/app.js#L630-L707) | L630-L707 | `refreshCaptcha(scope)` + `initCaptcha()` async `POST /api/captcha/nuevo` JSON body; actualiza SVG + `#captcha-token` + limpia input foco respuesta; loading/disabled; attach DOMContentLoaded + click + Space/Enter |
| [loadtest_500_ventas_cedis.py](file:///D:/Users/57323/Downloads/guias%20coodescor/loadtest_500_ventas_cedis.py#L1-L422) | L1-L422 | Script CLI `--guias=500 --workers=50 --mezclar_fases`. Pool sesiones 5 ventas + 2 cedis. **MetricasStore thread-safe** `threading.Lock` + JSONL append streaming. Percentiles robustos p50/p95/p99 `rank = min(n-1, round((p/100)*(n-1)))`. **FASE A**: 500 `crear_guia` concurrente `envio_directo_cedis=True` multi-docs 1..4 mixto FV/TB/PD/TR. **FASE B**: 500 `proceso_unificado_cedis` 1-click concurrente firma PNG dummy datauri ≥128B. Persiste `resumen.json` + `loadtest_LAST.txt`. Exit 0 si success≥95% y 0 "database locked" |
| [guias_coodescor/services/loadtest_report_service.py](file:///D:/Users/57323/Downloads/guias%20coodescor/guias_coodescor/services/loadtest_report_service.py#L1-L300) | L1-L300 | `leer_ultimo_resumen()` apuntador `loadtest_LAST.txt`; `rows_para_csv()` 1002 filas `(header + 1001 eventos)`; `generar_csv_bytes()` BOM UTF8 sep `;` `Content-Disposition` attachment; `vista_reporte_admin(user)` grid KPIs semáforo color (verde/amarillo/rojo) + tabla por rol + tabla operación p95/p99 + top errores + only-print encabezado A4 + empty-state mensaje sin ejecución |
| [guias_coodescor/web/views/admin_views.py](file:///D:/Users/57323/Downloads/guias%20coodescor/guias_coodescor/web/views/admin_views.py#L54-L64) | L54-L64 | Tarjeta `📊 Resultados Load Test` panel admin: links `/admin/loadtest/ultimo` (ver/imprimir PDF) y `/api/loadtest/ultimo.csv` (descargar Excel) + instrucción comando CLI |
| **[diag_nuevo_panel_ventas.py](file:///D:/Users/57323/Downloads/guias%20coodescor/diag_nuevo_panel_ventas.py#L19-L38)** (mantenimiento E2E) | L19-L38 | `new_opener()` envía header `X-CAPTCHA-Bypass` si existe `COODESCOR_CAPTCHA_BYPASS_KEY` ENV. `postj` timeout ↑60s. `export_csv_http` timeout ↑180s (soporta 500+ guías) |
| **[diag_e2e_autocompletar_receptores.py](file:///D:/Users/57323/Downloads/guias%20coodescor/diag_e2e_autocompletar_receptores.py#L95-L111)** (mantenimiento E2E) | L95-L111 | `Client.post()` injecta header `X-CAPTCHA-Bypass` automáticamente cuando `path=="/api/login"` si ENV bypass existe |

---

## 🔬 Evidencia TASK 3 · Load Test 500 Concurrente (TAG `20260927_135825`)

**Ficheros persistidos** (ruta `guias_coodescor/data/`):
- `loadtest_LAST.txt` — apuntador puntero a última ejecución
- `loadtest_20260927_135825_metricas_raw.jsonl` — 1.001 eventos JSONL uno por línea
- `loadtest_20260927_135825_resumen.json` — métricas agregadas percentiles
- `loadtest_20260927_135825_resultados.csv` — export admin CSV UTF8 BOM (1.002 filas)

| Parámetro ejecución | Valor |
|---|---|
| TAG lote | `20260927_135825` |
| Guías objetivo | 500 |
| Workers ThreadPoolExecutor | 50 |
| Usuarios VENTAS pool | `ventas`, `ventas2`, `ventas3`, `ventas4`, `ventas5` (5) |
| Usuarios CEDIS pool | `cedis`, `cedis2` (2) |
| Fases | SEPARADAS (A=crear, B=proceso) ✅ |
| Duración total | **69.54 s** (1 min 9.5 s) |
| Throughput efectivo | **7.19 guías / segundo** |
| Eventos totales | 1.001 |
| Eventos OK | 1.001 |
| Eventos fallidos | **0** |
| **Tasa de éxito** | **100.00 %** (≥95% requerido ✅) |
| Database locked / deadlocks | **0** (WAL/SQLite thread-safe probado) ✅ |

### Percentiles por operación (milisegundos)

| Operación | count | avg | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|
| `crear_guia` (VENTAS) | 500 | 4.285 ms | 4.542 ms | **6.962 ms** | 7.840 ms | 10.203 ms |
| `proceso_unificado_cedis` (CEDIS 1-click) | 500 | 2.389 ms | 2.456 ms | **3.288 ms** | 3.616 ms | 4.347 ms |
| `loadtest` overhead (evento único) | 1 | 69.535 ms | 69.535 ms | 69.535 ms | 69.535 ms | 69.535 ms |

### Distribución por Rol

| Rol | Eventos OK | Eventos Total | Errores | Tasa éxito |
|---|---:|---:|---:|---:|
| `ventas` (crear_guia) | 500 | 500 | 0 | 100.0% |
| `cedis` (proceso_unificado) | 500 | 500 | 0 | 100.0% |
| `NA` (loadtest overhead) | 1 | 1 | 0 | 100.0% |

---

## 📊 Evidencia TASK 4 · Reportes Admin

**Rutas y formatos disponibles** (rol requerido: `admin` — 403 Forbidden para ventas/cedis/transportador/administrativo):

| Ruta | Formato | Cómo abrir / PDF | Tamaño típico |
|---|---|---|---|
| `GET /admin/loadtest/ultimo` | HTML imprimible | Abrir navegador → **Ctrl+P → Guardar como PDF** (tamaño hoja A4 portrait 14mm margin; clase `.only-print` encabezado hoja `.no-print` oculta botones acción) | 1.100 líneas / 9 KB |
| `GET /api/loadtest/ultimo.csv` | **Excel** (CSV UTF8 BOM sep `;`) | Doble click Windows → abre MS Excel directamente (BOM + `;` son soportados nativo Excel). `Content-Disposition: attachment; filename="loadtest_20260927_135825_resultados.csv"` | 1.002 filas (1 header + 1.001 eventos) |
| `GET /api/loadtest/ultimo.xlsx` | alias CSV | Mismo contenido CSV para compatibilidad UI link texto "Excel" | ~ |

**KPIs visibles** en vista `/admin/loadtest/ultimo`:
1. Tarjeta cabecera: TAG lote · guías objetivo/OK · workers · duración · throughput · **Tasa éxito semáforo** (verde ≥95, amarillo 85-95, rojo <85) · errores totales
2. Tabla resumen **por rol** (ventas / cedis / admin)
3. Tabla percentiles **por operación** (p50/p95/p99/avg/count/max)
4. Tabla **Top errores frecuentes** (empty-state si 0 errores ✅)
5. Barra acciones no-print: 🔙 Volver Admin · ⬇ Descargar Excel (CSV) · 🖨 Imprimir (PDF via Ctrl+P)
6. Empty-state: Si `loadtest_LAST.txt` no existe o el resumen.json no se lee → mensaje "⚠️ Aún no se ha ejecutado ninguna prueba de carga" sin romper UI (probado con backup temporal + restore finally)

---

## ✅ Constancia SPEC v1.0 Intacta — Sin Retrocesos

Cumplimiento **FEEDBACK PERMANENTE USUARIO** *"recuerda esto es una adicion ene la estructura asi que esto es solo una mejora no retraaigas o desarmes la estructura y su finalidad"*:

1. **6 roles canónicos NO MODIFICADOS**: `ventas` (crea) → `administrativo` (asigna) → `cedis` (proceso_unificado control+entrega) → `transportador` (login propio) → `admin` (super) → `publico` (link virtual). Usuarios `ventas5` / `cedis2` son **instancias adicionales de roles existentes**, NO son roles nuevos.
2. **Carpetas invariables NUNCA BORRADAS/MODIFICADAS**: `[referencias/]` y `[android_app/]` intactas 100% check por diff.
3. **Permisos UI T7 DOBLE-CAPA INTACTOS**: Imprimir guía = `{ventas, administrativo, cedis, admin}`; Export CSV = `{administrativo, admin}`. CAPTCHA solo agrega capa HTTP; no toca permisos.
4. **DECISIONES SPRINTS ANTERIORES CONSERVADAS**:
   - NIT PK/FK blanda `ON DELETE SET NULL ON UPDATE CASCADE`
   - Cifrado reposo PBKDF2 120k + XOR + HMAC receptores
   - TTR purga física receptores: 7d post-entrega / 30d natural
   - WCAG AA modo claro/oscuro variables CSS `--surface-elevada`
   - Benchmark 10k guías p95 ≤200ms servicio interno (validado suites previas ✅)
5. **Bug 1 multidoc + Bug 2 KPI oscuro PERMANECEN CERRADOS** (regresión test_clientes 27/27 + test_sistema 34/34 + panel 6/6 + e2e 8/8 PASS lo confirma).
6. **Dependencias EXTERNAS CERO**: Todo CAPTCHA / SVG / HMAC / ThreadPoolExecutor / CSV BOM / PDF print media usa **Python stdlib** 3.11 + **JS vanilla** (no reportlab, no openpyxl, no PIL, no requests). `requirements.txt` intacto.
7. **Base SQLite principal `guias.db` y receptores `receptores.db`**: Sin migraciones destructivas; solo agregaron 2 filas `users` (ventas5, cedis2) + 1 clave `config.captcha_hmac_secret_key`.
8. **CAPTCHA bypass es seguro (no producción)**: Solo aplica si `COODESCOR_CAPTCHA_BYPASS_KEY` EXISTE en ENV del server + Header HTTP matchea `compare_digest`. OFF por default; solo activa en CI/E2E local.

---

## 🔐 Resumen Seguridad CAPTCHA (TASK 2)

Cumplimiento estándares OWASP Automated Threats (OAT-001 Brute Force / OAT-003 Credential Stuffing):

| Propiedad Seguridad | Implementación |
|---|---|
| **No almacena respuesta texto plano** | Token contiene SHA256(respuesta) dentro de HMAC |
| **Nonce 1-solo-uso** | `nonces_usados` Lock + TTL 360s lazy purge ≥2000 items |
| **Firma HMAC SHA256** | Secreto persistido tabla `config.captcha_hmac_secret_key` (no hardcodeado) |
| **Binding IP + UA** | Token incluye `ip` y `user_agent` en payload firmado; verificado en validación |
| **Comparación tiempo constante** | `hmac.compare_digest` en HMAC + bypass |
| **Tasa fallos separada** | Errores CAPTCHA NO incrementan `intentos_fallidos` cuenta (anti amplificación) |
| **Expiración corta** | 300 segundos (5 min) |
| **Distorsión SVG** | Rot ±22°, 7 líneas random, 40 puntos ruido, `Arial` con `font-weight:bold` aleatorio |
| **Alfabeto sin ambigüos** | Sin `0/O/1/I/l` (6 caracteres desafío) |
| **Bypass seguro** | `COODESCOR_CAPTCHA_BYPASS_KEY` (ENV) + `X-CAPTCHA-Bypass` (header) — BOTH requeridos |

---

*Documento generado automáticamente al cierre Sprint 03. SPEC v1.0 aprobada previamente por usuario — SIN RETROCESOS.*
