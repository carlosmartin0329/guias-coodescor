# Guía de implementación incremental: UX por perfil

## Objetivo aprobado

Mejorar la experiencia de Ventas, Administrativo, CEDIS, Transportador y Admin
sin quitar acciones existentes:

- Notificaciones por tareas pendientes del perfil en campana, aviso emergente y
  navegador.
- Actualización automática del tablero cada 2 segundos, sin refrescar toda la
  página ni interrumpir al usuario.
- Tarjetas/listas compactas, legibles y adaptables a móvil.
- Mantener búsqueda, filtros, exportación, impresión, acciones de guías,
  permisos y herramientas administrativas.

La maqueta aprobada está en [ux-propuesta-preview.html](./ux-propuesta-preview.html).
Sus datos son ficticios; no se conecta a la base de datos.

## Estado al pausar

- Rama: `feature/ux-perfiles-notificaciones`.
- Hay cambios de código sin commit en esa rama. Antes de continuar, ejecutar
  `git status --short` y revisar el diff; **no volver a aplicar a ciegas** los
  bloques que ya aparezcan modificados.
- Ya están en el árbol, de forma preliminar, el centro de notificaciones por
  perfil, el polling de 2 segundos para ambos tableros, la presentación
  compacta y las pruebas focalizadas.
- Verificaciones que ya pasaron:
  - `npm run build` en `frontend/`.
  - `py -m pytest backend\tests\test_notificaciones.py backend\tests\test_api_guias.py -q`
    (19 pruebas y 4 subcasos).
  - `node --check backend\guias_coodescor\static\live-dashboard.js`.
  - `py -m py_compile` sobre los módulos backend tocados.
  - `git diff --check`.
- `npm run lint` terminó con advertencias. Revisar y resolver las advertencias
  introducidas en los archivos modificados; no corregir advertencias ajenas a
  esta tarea.
- Falta comprobar la interfaz con una sesión real para los cinco perfiles,
  probar canales de navegador en un navegador real y ejecutar la suite completa
  si las pruebas focalizadas pasan. No se hizo commit ni despliegue.

## Cómo trabajar con poco presupuesto de uso

1. Ejecutar **un bloque por conversación**; no pedir a un agente que implemente
   todos los bloques a la vez.
2. Antes de cada bloque, pedir que inspeccione `git status --short` y
   `git diff`. Debe continuar el trabajo existente sin duplicarlo.
3. Dar al asistente solo el prompt del bloque y los archivos que ese bloque
   requiere.
4. Pedir cambios quirúrgicos y pruebas focalizadas. No instalar paquetes,
   cambiar dependencias, alterar credenciales, datos ni la base de datos.
5. Revisar la aceptación de cada bloque antes de iniciar el siguiente.
6. No hacer commit, push ni despliegue salvo que se solicite expresamente.

## Bloque 1 — Notificaciones seguras y por perfil

### Archivos

- `backend/guias_coodescor/api/routes_notificaciones.py`
- `backend/guias_coodescor/api/routes_guias_api.py`
- `backend/tests/test_notificaciones.py`
- `backend/tests/test_api_guias.py`

### Reglas del perfil

| Perfil | Estados que requieren atención |
|---|---|
| Ventas | `CREADA`, `RECIBIDA_ADMIN`, `EN_CEDIS`, `EN_RUTA` |
| Administrativo | `CREADA` |
| CEDIS | `RECIBIDA_ADMIN`, `EN_CEDIS` |
| Transportador | `EN_CEDIS`, `EN_RUTA`, únicamente guías asignadas a su usuario |
| Admin | `CREADA`, `RECIBIDA_ADMIN`, `EN_CEDIS`, `EN_RUTA` |

Las guías finalizadas (`ENTREGADA` y `ANULADA`) permanecen en el tablero e
historial, pero no son alertas accionables.

### Prompt para ejecutar el bloque

> Continúa en la rama existente. Inspecciona primero `git status --short` y el
> diff. Implementa o completa únicamente el Bloque 1 de
> `GUIA-IMPLEMENTACION-UX-POR-PARTES.md`: notificaciones pendientes filtradas
> por rol, filtrado obligatorio de guías asignadas al Transportador y respuesta
> con campos mínimos (sin firmas ni fotos). Mantén compatibilidad de las rutas
> existentes. Añade/ajusta pruebas de sesión, roles, asignación y sanitización.
> No cambies frontend ni estilos. Ejecuta solo las pruebas backend focalizadas
> de notificaciones y listado de guías, y reporta los archivos y resultados.

### Aceptación

- Sin sesión: endpoint responde `401`; perfiles no operativos no reciben datos.
- Transportador nunca puede consultar notificaciones o guías de otro usuario,
  incluso enviando otro ID como parámetro.
- Respuestas de listado y notificaciones no contienen firmas, fotos ni datos
  internos que el tablero no necesita.
- Se preservan las rutas existentes y su respuesta documentada.

## Bloque 2 — Centro de notificaciones React

### Archivos

- `frontend/src/hooks/useNotificaciones.js`
- `frontend/src/App.jsx`
- `frontend/src/components/Notificaciones.jsx`
- `frontend/src/components/Notificaciones.css`

### Prompt para ejecutar el bloque

> Revisa el diff y completa únicamente el Bloque 2 de
> `GUIA-IMPLEMENTACION-UX-POR-PARTES.md`. Deja una sola instancia del polling de
> notificaciones compartida por campana y avisos emergentes. Usa el endpoint
> filtrado del Bloque 1, deduplica por guía y estado, y conserva las leídas por
> usuario/perfil. La campana debe permitir abrir la guía y marcar una o todas
> como leídas; el toast debe desaparecer sin reiniciar su temporizador en cada
> polling. Solicita permiso del navegador de forma comprensible y solo una vez.
> Mantén los tres canales sin duplicar campanas ni alertas. No cambies aún el
> tablero. Ejecuta el build y lint del frontend; resuelve únicamente problemas
> relacionados con este bloque.

### Aceptación

- Solo existe una suscripción/polling compartida por página.
- Una tarea nueva produce campana, toast y notificación de navegador cuando el
  permiso está concedido; no repite alertas en cada consulta.
- Marcar como leída se mantiene al navegar o recargar con el mismo usuario.
- Ningún aviso aparece en login sin sesión; todos los perfiles operativos
  pueden usar la campana.

## Bloque 3 — Tablero React y tarjetas compactas

### Archivos

- `frontend/src/pages/Tablero.jsx`
- `frontend/src/pages/Tablero.css`
- `frontend/src/contexts/GuiaContext.jsx` (solo si es necesario para evitar
  solicitudes solapadas o estados inconsistentes)

### Prompt para ejecutar el bloque

> Continúa desde el diff existente y completa solo el Bloque 3 de
> `GUIA-IMPLEMENTACION-UX-POR-PARTES.md`. Conserva búsqueda, filtros, clic en
> guía, CSV, nueva guía, Base de datos y Load Test. Actualiza datos del tablero
> cada 2 segundos, pausa consultas de tablero en pestañas ocultas, refresca al
> volver y evita solapar solicitudes. Reorganiza filas como tarjetas compactas
> responsivas, manteniendo semántica accesible y los selectores necesarios de
> pruebas existentes. Usa correctamente el campo de conteo que devuelve el
> backend. No modifiques las rutas de negocio.

### Aceptación

- Los conteos y la lista cambian sin recargar la página y muestran hora/estado
  de actualización.
- La búsqueda, los filtros, navegación y acciones siguen funcionando.
- En móvil las tarjetas no desbordan y siguen mostrando guía, cliente, ciudad,
  estado y fecha.
- No se generan consultas simultáneas cada 2 segundos.

## Bloque 4 — Tablero HTML y navegación de la aplicación

### Archivos

- `backend/guias_coodescor/web/views/base.py`
- `backend/guias_coodescor/web/views/auth_views.py`
- `backend/guias_coodescor/web/views/base.py` (helper `lista_guias`)
- `backend/guias_coodescor/static/live-dashboard.js`
- `backend/guias_coodescor/static/style.css`

### Prompt para ejecutar el bloque

> Revisa primero el estado actual del diff. Completa solamente el Bloque 4 de
> `GUIA-IMPLEMENTACION-UX-POR-PARTES.md` para la interfaz HTML del backend:
> campana disponible en todos los perfiles autenticados, notificaciones
> filtradas en servidor y refresco parcial de conteos/listas cada 2 segundos.
> Actualiza solo las tarjetas cuyo contenido cambió; no recargues la página ni
> cierres acordeones. Usa nodos DOM y `textContent` para valores de guías,
> conserva impresión donde esté permitida y limita transportador a sus guías
> asignadas. Mantén existentes los formularios, vínculos y acciones. Valida
> sintaxis JS/Python y pruebas backend focalizadas.

### Aceptación

- El tablero HTML por perfil actualiza conteos y listas sin perder acordeones ni
  navegación.
- Campana, toast y notificación de navegador funcionan sin inyectar HTML con
  datos de usuario.
- Los cinco perfiles conservan sus secciones y permisos, incluidos historial,
  exportación e impresión.
- Si hay un error temporal de red, se informa y se reintenta sin dejar el
  tablero bloqueado.

## Bloque 5 — Revisión final

### Prompt para ejecutar el bloque

> Haz una revisión final del diff del Bloque 1 al 4. No añadas funcionalidades
> nuevas ni hagas refactors ajenos. Comprueba preservación de acciones y
> permisos para Ventas, Administrativo, CEDIS, Transportador y Admin; revisa
> polling de 2 segundos, deduplicación, estado de lectura, responsive y
> accesibilidad básica. Ejecuta build frontend, lint, pruebas focalizadas
> backend y pruebas frontend existentes pertinentes. Corrige solo defectos
> demostrados y entrega un resumen de pruebas, advertencias pendientes y
> archivos cambiados. No hagas commit ni despliegue.

### Matriz manual de aceptación

| Perfil | Pendientes/notificaciones | Funciones que deben seguir disponibles |
|---|---|---|
| Ventas | Guías de su flujo y pendientes de confirmación | Crear/editar guías, buscar, ver estados e imprimir |
| Administrativo | Guías `CREADA` y confirmaciones aplicables | Recibir, exportar auditoría CSV, buscar |
| CEDIS | `RECIBIDA_ADMIN` y `EN_CEDIS` | Control, entrega a transporte/cliente, imprimir |
| Transportador | Solo `EN_CEDIS`/`EN_RUTA` asignadas | Ver sus entregas y cerrar con firmas requeridas; sin imprimir |
| Admin | Estados abiertos de todos los flujos | Panel, anulación permitida, base de datos, load test y exportaciones |

## Referencias de diseño

- [Ant Design Pro — Workplace dashboard](https://github.com/ant-design/ant-design-pro/tree/52506486ea134486937043c5fb677d89bbcd07f2/src/pages/dashboard/workplace):
  encabezado por usuario, actividad y accesos frecuentes.
- [MUI — Dashboard template](https://mui.com/material-ui/getting-started/templates/dashboard/):
  resumen compacto, distribución adaptable y notificación en encabezado.
- [Ant Design — Card](https://ant.design/components/card/) y
  [Notification](https://ant.design/components/notification/): patrones de
  tarjetas pequeñas y avisos apilables.
- [Refine — Access Control Provider](https://refine.dev/core/docs/authorization/access-control-provider/)
  y [Live Provider](https://refine.dev/core/docs/realtime/live-provider/):
  ejemplos de controles por recurso y actualización de datos ante eventos.
