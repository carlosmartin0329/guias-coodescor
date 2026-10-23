"""REPRO BUG E2E: VENTAS -> ADMIN -> PROCESO EXTERNO -> ¿LLEGA A RECIBIDA_ADMIN?"""
import os, urllib.request, urllib.error, http.cookiejar, json, sqlite3, sys

BASE = "http://localhost:8000"
# BD usada por el backend (DATA_DIR = %ProgramData%\Coodescor\Guias)
DB = os.environ.get(
    "COODESCOR_DATA_DIR",
    r"C:\ProgramData\Coodescor\Guias\guias.db"
)
if not os.path.isfile(DB):
    # Fallback: usar la BD local del proyecto si existe
    DB = r"d:\Users\57323\Downloads\guias coodescor\guias_coodescor\data\guias.db"
FIRMA_DUMMY = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)
# CAPTCHA bypass key (debe coincidir con la variable de entorno COODESCOR_CAPTCHA_BYPASS_KEY)
CAPTCHA_BYPASS = os.environ.get("COODESCOR_CAPTCHA_BYPASS_KEY", "test-bypass-key")

def do(method, path, body=None, cookie=None, bypass=False):
    """Petición HTTP JSON (con cookie jar persistente). Retorna (status_code, obj_dict/str_body)."""
    url = BASE + path
    data = None
    hdrs = {
        "User-Agent": "BugReproE2E/1.0",
        "Accept": "application/json, text/plain, */*",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    if bypass:
        hdrs["X-CAPTCHA-Bypass"] = CAPTCHA_BYPASS
    opener_cookie = cookie
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with opener_cookie.open(req, timeout=30) as r:
            rb = r.read().decode("utf-8", errors="replace")
            try:
                return r.status, json.loads(rb)
            except Exception:
                return r.status, rb
    except urllib.error.HTTPError as e:
        rb = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(rb)
        except Exception:
            return e.code, rb

def db_state(gid):
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    g = dict(conn.execute("SELECT * FROM guias WHERE id=?", (gid,)).fetchone())
    evs = conn.execute(
        "SELECT id, tipo, en, substr(json(datos),1,260) AS datos_s "
        "FROM eventos WHERE guia_id=? ORDER BY id ASC", (gid,)
    ).fetchall()
    conn.close()
    return g, evs

print("=" * 78)
print("BUG REPRO: flujo administrativo -> transportador EXTERNO")
print("=" * 78)

# ---------- SESION 1: VENTAS ----------
cj_v = http.cookiejar.CookieJar()
op_v = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_v))

st, r = do("POST", "/api/login", {"usuario":"ventas","clave":"ventas123"}, cookie=op_v, bypass=True)
print(f"[Ventas] login: HTTP {st} -> {r}")
assert st == 200 and r.get("ok"), "Login ventas fallo"

gdata = {
    "cliente": "PRUEBA BUG EXTERNO #"+str(__import__('random').randint(100,9999)),
    "ciudad": "Bogota / Cali",
    "direccion": "Calle 123, Prueba, Ciudad",
    "documentos": "FAC-001, GUIA-002",
    "obs_ventas": "REPRO BUG FLUJO EXTERNO",
    "cajas": 2, "bolsas": 0, "cayvas": 0, "sobres": 0,
    "entrega_nombre": "Cliente Recibe Test",
    "envio_directo_cedis": 0,
}
st, r = do("POST", "/api/guias", gdata, cookie=op_v)
print(f"[Ventas] crear guia HTTP {st}: {r}")
assert st == 200 and r.get("ok"), "_crear guia fallo"
# Usar el ID retornado por la respuesta HTTP (no el último de la BD, que puede ser de sesiones anteriores)
gid = r.get("id")
assert gid, "No se obtuvo id de la respuesta"
g, evs = db_state(gid)
print(f"\n[BD] Guia id={gid} creada estado={g['estado']} envio_directo={g.get('envio_directo_cedis')}")

# ---------- SESION 2: ADMINISTRATIVO ----------
cj_a = http.cookiejar.CookieJar()
op_a = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj_a))

st, r = do("POST","/api/login",{"usuario":"administrativo","clave":"adminbod123"}, cookie=op_a, bypass=True)
print(f"[AdminBod] login: HTTP {st} ok={r.get('ok')}")

body_proc = {
    "tipo_transportador": "externo",
    "transportador_nombre": "Juan Perez Externo",
    "transportador_cc": "CC123456789",
    "transportador_tel": "3101234567",
    "transportador_vehiculo": "Camion Isuzu",
    "transportador_placa": "ABC123",
    "transportador_flete": "100000",
    "firma_transportador": FIRMA_DUMMY,
    "recibe": "Administrativo Test",
    "firma_recibido": FIRMA_DUMMY,
}
path = f"/api/guias/{gid}/proceso_administrativo_unificado"
print(f"\n[AdminBod] POST {path}")
print(f"    Body: {json.dumps(body_proc, indent=2)[:500]}")
st, r = do("POST", path, body_proc, cookie=op_a)
print(f"\n[AdminBod] RESPUESTA HTTP {st}  →  ", end="")
print(json.dumps(r, indent=2, ensure_ascii=False)[:1500])

# ---------- VERIFICAR BD POST-PROCESO ----------
g, evs = db_state(gid)
print("\n" + "=" * 78)
print("POST-PROCESO: VERIFICACIÓN FINAL BD")
print("=" * 78)
print(f"  Guia id={gid}")
print(f"  📌 ESTADO ACTUAL:       {g.get('estado')}")
print(f"  tipo_transportador:     {g.get('tipo_transportador')}")
print(f"  transportador_asignad:  {g.get('transportador_asignado_id')}")
print(f"  envio_directo_cedis:    {g.get('envio_directo_cedis')}")
print(f"\n  Eventos relacionados (n={len(evs)}):")
for i, e in enumerate(evs, 1):
    print(f"    {i}. [#{e[0]}] {e[1]:20s} @ {e[2][:19]}  datos=…{str(e[3])[:220]}")

print("\n  🎯 ¿CEDIS LA VERÁ EN '1️⃣ RECIBIDA_ADMIN'? (tiene que estar estado=RECIBIDA_ADMIN)")
if g.get("estado") == "RECIBIDA_ADMIN":
    print("     ✅ SÍ. CEDIS RECIBIRÁ LA GUÍA CORRECTAMENTE.")
    sys.exit(0)
else:
    print(f"     ❌ NO. Estado es '{g.get('estado')}' → BUSCAMOS ROOT CAUSE")
    # Mostrar qué evento pudo haber fallado en cambiar el estado: revisar procesar_evento(recepcion_admin)
    print("\n  🔍 Buscando recepcion_admin si realmente cambió estado:")
    conn2 = sqlite3.connect(DB); conn2.row_factory = sqlite3.Row
    for e in conn2.execute("SELECT * FROM eventos WHERE guia_id=? ORDER BY id ASC", (gid,)).fetchall():
        ed = dict(e)
        datos = json.loads(ed["datos"]) if ed["datos"] else {}
        print(f"    [{ed['id']}] {ed['tipo']:20s} usuario_id={ed['usuario_id']} pre_estado={datos.get('_estado_previo','')} post_estado={datos.get('_estado_siguiente','')}")
    conn2.close()
    sys.exit(2)
