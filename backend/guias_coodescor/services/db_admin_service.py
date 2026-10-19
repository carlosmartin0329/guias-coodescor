#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Administración de la base de datos desde la aplicación.

Permite al administrador del sistema explorar el esquema real, ver y editar filas,
ejecutar consultas, generar y restaurar respaldos y revisar las migraciones, sin
salir del aplicativo y sin tocar archivos con un editor externo.

Criterios de diseño que aplica este módulo:

1. Identificadores Fighters  → los nombres de tabla y columna NUNCA se
   interpolan desde la entrada del usuario: se resuelven contra la
   introspección real (PRAGMA) y se citan con comillas dobles. Los valores
   viajan siempre como parámetros vinculados.
2. Allowlist           → solo se pueden modificar tablas que el sistema
   reconoce como editables. Las internas del motor y las de datos cifrados se
   niegan con un motivo legible.
3. Respaldo antes de destruir → eliminar filas o restaurar un archivo crea
   primero un respaldo íntegro verificado.
4. Auditoría inmutable → cada operación escribe quién, qué, cuándo, desde qué
   IP y los valores anteriores y posteriores en admin_auditoria.
5. Límites             → tiempo máximo de ejecución, tope de filas devueltas y
   tamaño máximo de archivo, para que un descuido no deje el servidor sin
   respuesta.
6. Fallos explícitos    → las excepciones de este módulo llevan un mensaje
   accionable; nunca se filtra SQL ni traceback al cliente.
"""
import json
import os
import re
import shutil
import sqlite3
import time

import guias_coodescor.config as _cfg
from guias_coodescor.core.logging_config import get_logger
from guias_coodescor.core.utils import ahora_txt
from guias_coodescor.database.connection import (
    get_connection,
    get_db_lock,
    get_receptores_connection,
)

logger = get_logger("guias_coodescor.db_admin")

MASCARADO = "••••••"

# Columnas que nunca se muestran ni se editan desde este módulo.
#   - pass_hash / sal: cambiar un hash a mano deja al usuario sin poder entrar
#     y rompe la verificación. La gestión de claves va por Admin → Usuarios.
#   - columnas _cif: son datos cifrados con una clave que NO está en la base de
#     datos (está en DATA_DIR/secretos.json). Editar el texto cifrado produce
#     basura irrecuperable.
COLUMNAS_SENSIBLES = {
    "usuarios": {"pass_hash", "sal"},
    "receptores": {
        "nombres_apellidos_cif",
        "numero_doc_cif",
        "telefono_cif",
        "email_cif",
    },
}

# Sentencias permitidas en el editor cuando el modo es solo lectura.
_SQL_SOLO_LECTURA = ("select", "with", "explain")
# Palabras que rompen el aislamiento de datos aunque la frase empiece por SELECT.
_SQL_PROHIBIDO = (
    "attach",
    "detach",
    "pragma",
    "vacuum",
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "reindex",
    "begin",
    "commit",
    "rollback",
    "savepoint",
    "release",
)
# Verbos que el editor de SQL no ejecuta NUNCA, ni siquiera en modo escritura.
# Un DELETE/UPDATE accidental es el peor daño posible en este módulo, y el
# CRUD parametrizado es la única vía para cambiar datos: audita fila a fila y
# valida tipos. ATTACH además permitiría leer o escribir archivos del servidor.
_SQL_NUNCA = (
    "attach",
    "detach",
    "drop",
    "alter",
    "create",
    "replace",
    "reindex",
    "pragma",
    "begin",
    "commit",
    "rollback",
    "savepoint",
    "release",
    "vacuum",
)
_IDENTIFICADOR_SQL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# Verbos de escritura admitidos en el editor: solo cambio de filas, nunca de esquema.
_SQL_ESCRITURA_ADMITIDA = ("update", "insert", "delete", "with")
# Columnas cuyo valor nunca debe salir por el editor de SQL, ni siquiera filtrado.
_COLUMNAS_SENSIBLES_TODAS = frozenset(
    c for cols in COLUMNAS_SENSIBLES.values() for c in cols
)
_RE_TABLA_SENSIBLE = re.compile(
    r"\b(?:from|join|into|update|table)\s+[\"'`]?"
    r"(usuarios|receptores)\b",
    re.IGNORECASE,
)
_RE_ESTRELLA = re.compile(r"(?:select|,)\s*\*|,\s*\*", re.IGNORECASE)


class DbAdminError(Exception):
    """Error funcional del módulo de base de datos (mensaje para el usuario)."""


class TablaNoPermitida(DbAdminError):
    pass


class ColumnaNoPermitida(DbAdminError):
    pass


class ConsultaNoPermitida(DbAdminError):
    pass


class RespaldoNoValido(DbAdminError):
    pass


# ---------------------------------------------------------------------------
# Conexiones
# ---------------------------------------------------------------------------

BASES = ("guias", "receptores")


def _ruta_base(base: str) -> str:
    base = (base or "guias").strip().lower()
    if base == "guias":
        return _cfg.DB_PATH
    if base == "receptores":
        return _cfg.RECEPTORES_DB_PATH
    raise DbAdminError(f"Base de datos desconocida: {base}")


def _conectar(base: str, solo_lectura: bool = False) -> sqlite3.Connection:
    if (base or "guias").lower() == "receptores":
        conn = get_receptores_connection()
    else:
        conn = get_connection()
    if solo_lectura:
        # Blindaje del motor: impide cualquier escritura en la conexión aunque
        # una consulta maliceversa se cuele por un hueco del filtro.
        conn.execute("PRAGMA query_only=ON")
    return conn


def _conectar_cualquiera(solo_lectura: bool = False) -> sqlite3.Connection:
    return _conectar("guias", solo_lectura)


# ---------------------------------------------------------------------------
# Introspección
# ---------------------------------------------------------------------------

def listar_bases() -> list:
    """Archivos de base de datos conocidos, con tamaño y conteo de filas."""
    salida = []
    for base in BASES:
        ruta = _ruta_base(base)
        existe = os.path.isfile(ruta)
        info = {
            "base": base,
            "ruta": ruta,
            "bytes": os.path.getsize(ruta) if existe else 0,
            "existe": existe,
            "editable": base == "guias",
            "motivo_edicion": (
                "Base principal del sistema."
                if base == "guias"
                else "Contiene datos personales cifrados: solo lectura desde aquí."
            ),
        }
        if existe:
            try:
                conn = _conectar(base, solo_lectura=True)
                try:
                    info["integridad"] = (
                        conn.execute("PRAGMA integrity_check").fetchone()[0]
                    )
                    info["paginas"] = conn.execute("PRAGMA page_count").fetchone()[0]
                    info["tamano_pagina"] = conn.execute("PRAGMA page_size").fetchone()[0]
                    info["journal"] = conn.execute("PRAGMA journal_mode").fetchone()[0]
                finally:
                    conn.close()
            except sqlite3.Error as ex:
                info["integridad"] = f"ERROR: {ex}"
        salida.append(info)
    return salida


def listar_tablas(base: str = "guias") -> list:
    """Tablas del esquema real con su conteo de filas y permisos de edición."""
    conn = _conectar(base, solo_lectura=True)
    try:
        nombres = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        salida = []
        for nombre in nombres:
            filas = conn.execute(f'SELECT COUNT(*) FROM "{nombre}"').fetchone()[0]
            editable, motivo = _permisos_tabla(base, nombre)
            salida.append(
                {
                    "nombre": nombre,
                    "filas": filas,
                    "editable": editable,
                    "motivo": motivo,
                }
            )
        return salida
    finally:
        conn.close()


def _permisos_tabla(base: str, tabla: str) -> tuple:
    """Devuelve (editable, motivo) según las reglas de la tabla."""
    if tabla in _cfg.DB_TABLAS_SOLO_LECTURA:
        return False, "Tabla interna del sistema: se modifica sola, no de forma manual."
    if tabla in _cfg.DB_TABLAS_CIFRADAS:
        return False, (
            "Contiene datos cifrados con una clave externa: editar el texto "
            "cifrado los haría irrecuperables."
        )
    if base != "guias":
        return False, "Base secundaria de solo lectura."
    if tabla == "config":
        return True, (
            "Configuración del sistema. Las claves de cifrado y de IA no están "
            "aquí: viven en DATA_DIR/secretos.json, fuera de la base de datos."
        )
    if tabla == "usuarios":
        return True, "Usuarios del sistema. No edites pass_hash ni sal aquí."
    return True, "Tabla de negocio: edición permitida."


def describir_tabla(base: str, tabla: str) -> dict:
    """Esquema completo de una tabla: columnas, índices y claves foráneas."""
    _exigir_tabla(base, tabla)
    conn = _conectar(base, solo_lectura=True)
    try:
        columnas = []
        for fila in conn.execute(f'PRAGMA table_info("{tabla}")').fetchall():
            nombre = fila[1]
            # PRAGMA table_info devuelve 6 columnas; la 7ª (secuencia) no siempre
            # viene presente según la versión de SQLite.
            secuencia = str(fila[6]) if len(fila) > 6 else ""
            columnas.append(
                {
                    "nombre": nombre,
                    "tipo": fila[2] or "TEXT",
                    "no_nulo": bool(fila[3]),
                    "por_defecto": fila[4],
                    "pk": bool(fila[5]),
                    "autoincremento": secuencia.upper() == "TRUE",
                    "sensible": nombre in COLUMNAS_SENSIBLES.get(tabla, set()),
                    "editable": nombre not in COLUMNAS_SENSIBLES.get(tabla, set()),
                }
            )

        indices = []
        for fila in conn.execute(f'PRAGMA index_list("{tabla}")').fetchall():
            nombre_indice = fila[1]
            cols_indice = [
                c[2]
                for c in conn.execute(f'PRAGMA index_info("{nombre_indice}")').fetchall()
            ]
            indices.append(
                {"nombre": nombre_indice, "unico": bool(fila[2]), "columnas": cols_indice}
            )

        foraneas = []
        for fila in conn.execute(f'PRAGMA foreign_key_list("{tabla}")').fetchall():
            foraneas.append(
                {
                    "columna": fila[3],
                    "tabla": fila[2],
                    "referencia": fila[4],
                    "on_delete": fila[6],
                    "on_update": fila[7],
                }
            )

        editable, motivo = _permisos_tabla(base, tabla)
        total = conn.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0]
        return {
            "base": base,
            "tabla": tabla,
            "filas": total,
            "editable": editable,
            "motivo": motivo,
            "columnas": columnas,
            "indices": indices,
            "foraneas": foraneas,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Validación de identificadores
# ---------------------------------------------------------------------------

def _exigir_tabla(base: str, tabla: str) -> str:
    """
    Resuelve el nombre real de la tabla contra la introspección y devuelve el
    nombre canónico. Nunca devuelve algo que venga directamente del usuario.
    """
    if not tabla or not _IDENTIFICADOR_SQL.match(str(tabla)):
        raise TablaNoPermitida("Nombre de tabla no válido.")
    base_norm = (base or "guias").strip().lower()
    if base_norm not in BASES:
        raise TablaNoPermitida(f"Base de datos desconocida: {base}")
    conn = _conectar(base_norm, solo_lectura=True)
    try:
        existe = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?", (tabla,)
        ).fetchone()
    finally:
        conn.close()
    if not existe:
        raise TablaNoPermitida(f"La tabla '{tabla}' no existe en la base '{base_norm}'.")
    return tabla


def _columnas_reales(base: str, tabla: str) -> list:
    conn = _conectar(base, solo_lectura=True)
    try:
        return [f[1] for f in conn.execute(f'PRAGMA table_info("{tabla}")').fetchall()]
    finally:
        conn.close()


def _exigir_editable(base: str, tabla: str) -> None:
    _exigir_tabla(base, tabla)
    editable, motivo = _permisos_tabla(base, tabla)
    if not editable:
        raise TablaNoPermitida(motivo)


def _validar_columnas(base: str, tabla: str, columnas: dict, solo_lectura: bool = False) -> dict:
    """
    Descarta cualquier clave que no sea una columna real y rechaza las sensibles
    cuando se intenta escribir. Devuelve el diccionario ya saneado.
    """
    reales = set(_columnas_reales(base, tabla))
    sensibles = COLUMNAS_SENSIBLES.get(tabla, set())
    limpio = {}
    for nombre, valor in (columnas or {}).items():
        if nombre not in reales:
            raise ColumnaNoPermitida(f"'{nombre}' no es una columna de '{tabla}'.")
        if nombre in sensibles and not solo_lectura:
            raise ColumnaNoPermitida(
                f"La columna '{nombre}' no se puede editar desde aquí: "
                "gestiónala desde el módulo de usuarios o con la herramienta oficial."
            )
        limpio[nombre] = valor
    return limpio


def _clave_primaria(base: str, tabla: str) -> str:
    conn = _conectar(base, solo_lectura=True)
    try:
        for fila in conn.execute(f'PRAGMA table_info("{tabla}")').fetchall():
            if fila[5]:
                return fila[1]
    finally:
        conn.close()
    raise DbAdminError(
        f"La tabla '{tabla}' no tiene clave primaria: no se pueden editar filas de forma segura."
    )


def _escapar_like(texto: str) -> str:
    """Escapa los comodines de LIKE para que la búsqueda sea literal."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _mascarar_si_sensible(tabla: str, columna: str, valor):
    if columna in COLUMNAS_SENSIBLES.get(tabla, set()) and valor not in (None, ""):
        return MASCARADO
    return valor


def _serializable(valor):
    """Convierte tipos de SQLite a algo que json.dumps acepte."""
    if isinstance(valor, bytes):
        return f"<binario {len(valor)} bytes>"
    return valor


# ---------------------------------------------------------------------------
# Lectura de filas
# ---------------------------------------------------------------------------

def listar_filas(
    base: str,
    tabla: str,
    q: str = "",
    pagina: int = 1,
    page_size: int = 50,
    orden: str = "",
    direccion: str = "asc",
) -> dict:
    """Pagina las filas de una tabla, con búsqueda de texto y orden validados."""
    _exigir_tabla(base, tabla)
    columnas = _columnas_reales(base, tabla)
    try:
        pagina = max(1, int(pagina))
    except (TypeError, ValueError):
        pagina = 1
    try:
        page_size = int(page_size)
    except (TypeError, ValueError):
        page_size = 50
    page_size = max(1, min(page_size, _cfg.DB_PAGE_SIZE_MAX))

    where = ""
    params = []
    if q:
        texto = f"%{_escapar_like(str(q))}%"
        partes = [
            f'CAST("{c}" AS TEXT) LIKE ? ESCAPE \'\\\'' for c in columnas
        ]
        where = " WHERE " + " OR ".join(partes)
        params = [texto] * len(columnas)

    if orden and orden in columnas:
        flecha = "DESC" if str(direccion).lower() == "desc" else "ASC"
        clause_order = f' ORDER BY "{orden}" {flecha}'
    else:
        clause_order = ""

    conn = _conectar(base, solo_lectura=True)
    try:
        total = conn.execute(f'SELECT COUNT(*) FROM "{tabla}"{where}', params).fetchone()[0]
        limite = page_size
        desplazamiento = (pagina - 1) * page_size
        filas_sql = conn.execute(
            f'SELECT * FROM "{tabla}"{where}{clause_order} LIMIT ? OFFSET ?',
            [*params, limite, desplazamiento],
        ).fetchall()
    finally:
        conn.close()

    filas = [
        {k: _mascarar_si_sensible(tabla, k, _serializable(f[k])) for k in f.keys()}
        for f in filas_sql
    ]
    paginas = max(1, (total + page_size - 1) // page_size)
    return {
        "base": base,
        "tabla": tabla,
        "columnas": columnas,
        "filas": filas,
        "total": total,
        "pagina": min(pagina, paginas),
        "paginas": paginas,
        "page_size": page_size,
    }


# ---------------------------------------------------------------------------
# Escritura de filas
# ---------------------------------------------------------------------------

def _validar_tipos(columnas: dict, definidos: dict) -> dict:
    """
    Coacciona los valores al tipo declarado de la columna. SQLite es flexible y
    una coerción incorrecta se descubre tarde y como bug silencioso.
    """
    salida = {}
    for nombre, valor in columnas.items():
        tipo = (definidos.get(nombre) or "").upper()
        if valor is None:
            salida[nombre] = None
            continue
        try:
            if "INT" in tipo:
                salida[nombre] = int(valor)
            elif any(p in tipo for p in ("REAL", "FLOA", "DOUB")):
                salida[nombre] = float(valor)
            elif "BOOL" in tipo:
                salida[nombre] = 1 if str(valor).strip().lower() in ("1", "true", "si", "sí") else 0
            else:
                salida[nombre] = str(valor)
        except (TypeError, ValueError):
            raise ColumnaNoPermitida(
                f"El valor '{valor}' no es válido para la columna '{nombre}' de tipo {tipo or 'TEXT'}."
            )
    return salida


def insertar_fila(base: str, tabla: str, valores: dict, admin: dict, ip: str = "") -> dict:
    """Inserta una fila. Los identificadores se resuelven contra el esquema."""
    _exigir_editable(base, tabla)
    conn = _conectar(base)
    try:
        definidos = {
            f[1]: f[2] for f in conn.execute(f'PRAGMA table_info("{tabla}")').fetchall()
        }
        limpios = _validar_columnas(base, tabla, valores)
        if not limpios:
            raise ColumnaNoPermitida("No se indicó ningún campo a guardar.")
        limpios = _validar_tipos(limpios, definidos)
        nombres = ", ".join(f'"{c}"' for c in limpios)
        marcadores = ", ".join("?" for _ in limpios)
        with get_db_lock():
            cursor = conn.execute(
                f'INSERT INTO "{tabla}" ({nombres}) VALUES ({marcadores})',
                list(limpios.values()),
            )
            nuevo_id = cursor.lastrowid
            conn.commit()
    except sqlite3.IntegrityError as ex:
        raise DbAdminError(
            f"No se pudo guardar: {ex}. Revisa los campos obligatorios, los valores "
            "únicos y las referencias."
        ) from ex
    except sqlite3.Error as ex:
        raise DbAdminError(f"No se pudo guardar la fila: {ex}") from ex
    finally:
        conn.close()

    _auditar(
        admin,
        ip,
        accion="insertar",
        tabla=tabla,
        clave=str(nuevo_id),
        resumen=f"Fila insertada en {tabla}",
        detalle=limpios,
        filas=1,
    )
    return {"id": nuevo_id}


def actualizar_fila(
    base: str, tabla: str, clave, valores: dict, admin: dict, ip: str = ""
) -> dict:
    """Actualiza una fila y registra el antes y el después de cada campo."""
    _exigir_editable(base, tabla)
    pk = _clave_primaria(base, tabla)
    conn = _conectar(base)
    try:
        definidos = {
            f[1]: f[2] for f in conn.execute(f'PRAGMA table_info("{tabla}")').fetchall()
        }
        if pk not in definidos:
            raise DbAdminError("No se identificó la clave primaria.")

        limpio = _validar_columnas(base, tabla, valores)
        limpio.pop(pk, None)
        if not limpio:
            raise ColumnaNoPermitida("No se indicó ningún campo a modificar.")
        limpio = _validar_tipos(limpio, definidos)

        anterior = conn.execute(
            f'SELECT * FROM "{tabla}" WHERE "{pk}" = ?', (clave,)
        ).fetchone()
        if anterior is None:
            raise DbAdminError(f"No existe la fila '{clave}' en la tabla '{tabla}'.")
        antes = {k: _serializable(anterior[k]) for k in anterior.keys()}
        nombres = ", ".join(f'"{c}" = ?' for c in limpio)
        with get_db_lock():
            conn.execute(
                f'UPDATE "{tabla}" SET {nombres} WHERE "{pk}" = ?',
                [*limpio.values(), clave],
            )
            conn.commit()
    except sqlite3.IntegrityError as ex:
        raise DbAdminError(
            f"No se pudo actualizar: {ex}. Revisa los valores únicos y las referencias."
        ) from ex
    except sqlite3.Error as ex:
        raise DbAdminError(f"No se pudo actualizar la fila: {ex}") from ex
    finally:
        conn.close()

    _auditar(
        admin,
        ip,
        accion="actualizar",
        tabla=tabla,
        clave=str(clave),
        resumen=f"Fila actualizada en {tabla}",
        detalle={"antes": antes, "cambios": limpio},
        filas=1,
    )
    return {"clave": str(clave), "campos": list(limpio.keys())}


def eliminar_fila(base: str, tabla: str, clave, admin: dict, ip: str = "") -> dict:
    """
    Elimina una fila. Crea un respaldo verificado antes de borrar: es la única
    forma de recuperar datos si el borrado fue un error.
    """
    _exigir_editable(base, tabla)
    pk = _clave_primaria(base, tabla)

    anterior = None
    conn = _conectar(base)
    try:
        fila = conn.execute(
            f'SELECT * FROM "{tabla}" WHERE "{pk}" = ?', (clave,)
        ).fetchone()
        if fila is None:
            raise DbAdminError(f"No existe la fila '{clave}' en la tabla '{tabla}'.")
        anterior = {k: _serializable(fila[k]) for k in fila.keys()}
    finally:
        conn.close()

    respaldo = crear_respaldo(motivo=f"antes-de-borrar-en-{tabla}", base=base)

    conn = _conectar(base)
    try:
        with get_db_lock():
            conn.execute(f'DELETE FROM "{tabla}" WHERE "{pk}" = ?', (clave,))
            conn.commit()
    except sqlite3.IntegrityError as ex:
        raise DbAdminError(
            f"No se pudo eliminar: la fila está referenciada por otra tabla ({ex})."
        ) from ex
    except sqlite3.Error as ex:
        raise DbAdminError(f"No se pudo eliminar la fila: {ex}") from ex
    finally:
        conn.close()

    _auditar(
        admin,
        ip,
        accion="eliminar",
        tabla=tabla,
        clave=str(clave),
        resumen=f"Fila eliminada de {tabla}",
        detalle={"fila_eliminada": anterior, "respaldo": respaldo.get("archivo")},
        filas=1,
    )
    return {"clave": str(clave), "respaldo": respaldo.get("archivo")}


# ---------------------------------------------------------------------------
# Editor de consultas
# ---------------------------------------------------------------------------

def _validar_consulta(sql: str, escritura: bool, confirmado: bool = False) -> str:
    """
    Valida la sentencia antes de tocar la base de datos.

    El modo escritura exige `confirmado=True` y queda limitado a verbs que solo
    cambian filas. El esquema y los datos sensibles quedan fuera del editor.
    """
    texto = (sql or "").strip().rstrip(";").strip()
    if not texto:
        raise ConsultaNoPermitida("La consulta está vacía.")
    if len(texto) > 20000:
        raise ConsultaNoPermitida("La consulta es demasiado larga (máximo 20000 caracteres).")

    # Una sola sentencia: el API no acepta lotes.
    if ";" in texto:
        raise ConsultaNoPermitida(
            "Ejecuta una sola sentencia a la vez: no se admiten varias separadas por ';'."
        )

    limpio = _sin_comentarios(texto)
    comentario = limpio.lower().lstrip()
    if not comentario:
        raise ConsultaNoPermitida("La consulta no contiene ninguna sentencia.")

    # Datos sensibles: no se leen ni escriben por SQL en ningún modo. El editor de
    # filas los enmascara y la gestión de usuarios va por Admin → Usuarios.
    for columna in _COLUMNAS_SENSIBLES_TODAS:
        if re.search(r"\b{}\b".format(re.escape(columna)), limpio, re.IGNORECASE):
            raise ConsultaNoPermitida(
                f"La columna '{columna}' está protegida: no se puede leer ni escribir "
                "desde el editor de SQL."
            )
    # SELECT * sobre una tabla con columnas sensibles las arrastraría igualmente.
    if _RE_ESTRELLA.search(limpio) and _RE_TABLA_SENSIBLE.search(limpio):
        raise ConsultaNoPermitida(
            "No se admite SELECT * sobre tablas con datos protegidos. "
            "Indica las columnas una por una."
        )

    palabras = set(re.findall(r"[a-z_]+", comentario))
    prohibidas = palabras & set(_SQL_NUNCA)
    if prohibidas:
        raise ConsultaNoPermitida(
            "El editor de SQL no ejecuta {} por seguridad. Usa el módulo de filas, "
            "los respaldos o el mantenimiento.".format(", ".join(sorted(prohibidas)).upper())
        )

    if not escritura:
        if not comentario.startswith(_SQL_SOLO_LECTURA):
            raise ConsultaNoPermitida(
                "El modo de lectura solo admite SELECT, WITH o EXPLAIN. "
                "Cambia a modo escritura para modificar datos."
            )
        if _contiene_prohibida(comentario):
            raise ConsultaNoPermitida(
                "La consulta de solo lectura no puede escribir ni cambiar la configuración "
                "de la base de datos."
            )
    else:
        if not confirmado:
            raise ConsultaNoPermitida(
                "El modo escritura exige confirmación explícita. Vuelve a marcar la "
                "casilla de confirmación para ejecutar la sentencia."
            )
        verbo = comentario.split(None, 1)[0]
        if verbo in ("select", "explain"):
            raise ConsultaNoPermitida(
                "Esta consulta no modifica datos. Ejecútala en modo lectura."
            )
        if verbo == "with":
            # Un WITH puede esconder un DELETE: se exige que la sentencia principal
            # sea de escritura y se rechaza si el CTE termina en una lectura.
            if not _contiene_escritura(limpio):
                raise ConsultaNoPermitida(
                    "Esta consulta no modifica datos. Ejecútala en modo lectura."
                )
        elif verbo not in _SQL_ESCRITURA_ADMITIDA:
            raise ConsultaNoPermitida(
                "El modo escritura solo admite INSERT, UPDATE y DELETE. "
                "Para el esquema usa una migración."
            )
    return texto


def _contiene_escritura(texto: str) -> bool:
    """True si el texto contiene un verbo de cambio de filas."""
    palabras = set(re.findall(r"[a-z_]+", texto.lower()))
    return bool(palabras & {"insert", "update", "delete"})


def _sin_comentarios(sql: str) -> str:
    """Quita comentarios de línea y de bloque antes de analizar la sentencia."""
    texto = re.sub(r"--[^\n]*", " ", sql)
    return re.sub(r"/\*.*?\*/", " ", texto, flags=re.S)


def _contiene_prohibida(texto: str) -> bool:
    palabras = set(re.findall(r"[a-z_]+", texto))
    return bool(palabras & set(_SQL_PROHIBIDO))


def ejecutar_consulta(
    base: str,
    sql: str,
    escritura: bool = False,
    admin: dict = None,
    ip: str = "",
    confirmado: bool = False,
) -> dict:
    """
    Ejecuta una sentencia y devuelve columnas y filas.

    El modo lectura activa PRAGMA query_only en la conexión, así que el motor
    rechaza cualquier escritura aunque el filtro de texto se hubiera evitado.
    El modo escritura exige confirmación explícita del operador, crea un respaldo
    previo y se audita.
    """
    sentencia = _validar_consulta(sql, escritura, confirmado=confirmado)
    base_norm = (base or "guias").strip().lower()
    _ruta_base(base_norm)

    # Red de seguridad: si la sentencia borra filas, el respaldo existe antes.
    respaldo_previo = crear_respaldo(motivo="antes-de-consulta") if escritura else None

    inicio = time.monotonic()
    conn = _conectar(base_norm, solo_lectura=not escritura)
    try:
        limite_ms = _cfg.DB_QUERY_TIMEOUT_MS

        def _corte():
            return 1 if (time.monotonic() - inicio) * 1000 > limite_ms else 0

        conn.set_progress_handler(_corte, 2000)
        try:
            cursor = conn.execute(sentencia)
        except sqlite3.OperationalError as ex:
            if "interrupted" in str(ex).lower():
                raise ConsultaNoPermitida(
                    f"La consulta superó el máximo de {limite_ms} ms y fue cancelada."
                ) from ex
            raise ConsultaNoPermitida(f"Error de SQLite: {ex}") from ex
        finally:
            conn.set_progress_handler(None, 0)

        columnas = [d[0] for d in (cursor.description or [])]
        filas = cursor.fetchmany(_cfg.DB_QUERY_MAX_ROWS + 1)
        truncado = len(filas) > _cfg.DB_QUERY_MAX_ROWS
        filas = filas[: _cfg.DB_QUERY_MAX_ROWS]
        afectadas = cursor.rowcount if escritura and cursor.rowcount and cursor.rowcount > 0 else 0

        if escritura:
            with get_db_lock():
                conn.commit()
    finally:
        conn.close()

    duracion_ms = int((time.monotonic() - inicio) * 1000)
    resultado = {
        "base": base_norm,
        "columnas": columnas,
        "filas": [[_serializable(v) for v in fila] for fila in filas],
        "truncado": truncado,
        "filas_afectadas": afectadas,
        "duracion_ms": duracion_ms,
        "escritura": bool(escritura),
    }
    if respaldo_previo:
        resultado["respaldo_previo"] = respaldo_previo.get("archivo")
    if escritura:
        _auditar(
            admin,
            ip,
            accion="consulta_escritura",
            tabla=None,
            clave=None,
            resumen=f"Consulta de escritura ({duracion_ms} ms)",
            detalle={
                "sql": sentencia[:4000],
                "filas_afectadas": afectadas,
                "respaldo_previo": (respaldo_previo or {}).get("archivo"),
            },
            filas=afectadas,
        )
    return resultado


# ---------------------------------------------------------------------------
# Respaldos
# ---------------------------------------------------------------------------

def _nombre_respaldo(base: str, motivo: str) -> str:
    """
    Nombre único del respaldo. Incluye milisegundos y un contador porque dos
    operaciones en el mismo segundo (borrar dos filas seguidas) no pueden
    sobrescribirse: perder un respaldo es perder la única red de seguridad.
    """
    marca = time.strftime("%Y%m%d_%H%M%S")
    seguro = re.sub(r"[^A-Za-z0-9_-]+", "-", str(motivo or "manual")).strip("-")[:40]
    prefijo = "guias" if (base or "guias").lower() == "guias" else "receptores"
    directorio = _directorio_respaldos(base)
    base_nombre = f"{prefijo}_{marca}_{seguro or 'manual'}"
    candidato = f"{base_nombre}_{time.time_ns() % 1_000_000:06d}.db"
    intento = 1
    while os.path.exists(os.path.join(directorio, candidato)):
        intento += 1
        candidato = f"{base_nombre}_{time.time_ns() % 1_000_000:06d}_{intento}.db"
    return candidato


def _prune_respaldos() -> None:
    """Conserva solo los respaldos más recientes según BACKUP_RETENTION."""
    for base in BASES:
        directorio = _directorio_respaldos(base)
        if not os.path.isdir(directorio):
            continue
        archivos = sorted(
            (f for f in os.listdir(directorio) if f.endswith(".db")),
            reverse=True,
        )
        for sobrante in archivos[_cfg.BACKUP_RETENTION :]:
            try:
                os.remove(os.path.join(directorio, sobrante))
            except OSError:
                logger.warning("No se pudo eliminar el respaldo antiguo %s", sobrante)


def _directorio_respaldos(_base: str = "guias") -> str:
    directorio = os.path.join(_cfg.DATA_DIR, "respaldos")
    os.makedirs(directorio, exist_ok=True)
    return directorio


def crear_respaldo(motivo: str = "manual", base: str = "guias") -> dict:
    """
    Copia consistente de la base usando la API de respaldo de SQLite, que es
    segura con el archivo en uso y con el modo WAL activo.
    """
    base_norm = (base or "guias").strip().lower()
    ruta = _ruta_base(base_norm)
    if not os.path.isfile(ruta):
        raise DbAdminError(f"No existe el archivo de la base '{base_norm}'.")

    directorio = _directorio_respaldos(base_norm)
    destino = os.path.join(directorio, _nombre_respaldo(base_norm, motivo))

    origen = sqlite3.connect(ruta, timeout=30)
    try:
        destino_conn = sqlite3.connect(destino)
        try:
            with origen:
                origen.backup(destino_conn)
        finally:
            destino_conn.close()
    except sqlite3.Error as ex:
        raise DbAdminError(f"No se pudo crear el respaldo: {ex}") from ex
    finally:
        origen.close()

    # Verificación: un respaldo que no abre no sirve de nada.
    verificador = sqlite3.connect(destino)
    try:
        integridad = verificador.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        verificador.close()
    if integridad != "ok":
        raise RespaldoNoValido(
            f"El respaldo creado no pasó la verificación de integridad ({integridad})."
        )

    _prune_respaldos()
    logger.info("Respaldo creado: %s (%s)", destino, motivo)
    return {
        "archivo": os.path.basename(destino),
        "ruta": destino,
        "bytes": os.path.getsize(destino),
        "fecha": ahora_txt(),
    }


def listar_respaldos(base: str = "guias") -> list:
    directorio = _directorio_respaldos(base or "guias")
    salida = []
    for nombre in sorted(os.listdir(directorio), reverse=True):
        if not nombre.endswith(".db"):
            continue
        completa = os.path.join(directorio, nombre)
        stat = os.stat(completa)
        salida.append(
            {
                "archivo": nombre,
                "bytes": stat.st_size,
                "fecha": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            }
        )
    return salida


def _verificar_respaldo(ruta: str) -> None:
    if not os.path.isfile(ruta):
        raise RespaldoNoValido("El archivo de respaldo no existe.")
    tamano = os.path.getsize(ruta)
    if tamano == 0:
        raise RespaldoNoValido("El archivo de respaldo está vacío.")
    if tamano > _cfg.MAX_DB_BACKUP_SIZE:
        raise RespaldoNoValido("El archivo de respaldo supera el tamaño máximo admitido.")
    conn = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    try:
        resultado = conn.execute("PRAGMA integrity_check").fetchone()[0]
    except sqlite3.Error as ex:
        raise RespaldoNoValido(f"El archivo no es una base de datos válida: {ex}") from ex
    finally:
        conn.close()
    if resultado != "ok":
        raise RespaldoNoValido(f"El respaldo está dañado: {resultado}.")


def leer_respaldo(archivo: str, admin: dict, ip: str = "") -> tuple:
    """
    Devuelve (contenido, nombre_sugerido) para descargar un respaldo.

    Solo admite un nombre plano dentro del directorio de respaldos, y queda
    auditado: sacar una copia de la base es una operación sensible.
    """
    directorio = _directorio_respaldos("guias")
    nombre = os.path.basename((archivo or "").strip())
    if not nombre.endswith(".db"):
        raise RespaldoNoValido("El nombre del respaldo no es válido.")
    completa = os.path.join(directorio, nombre)
    if os.path.abspath(completa) != os.path.abspath(os.path.join(directorio, nombre)):
        raise RespaldoNoValido("La ruta del respaldo no es válida.")
    if not os.path.isfile(completa):
        raise RespaldoNoValido("El archivo de respaldo no existe.")

    tamano = os.path.getsize(completa)
    if tamano == 0:
        raise RespaldoNoValido("El archivo de respaldo está vacío.")
    if tamano > _cfg.MAX_DB_BACKUP_SIZE:
        raise RespaldoNoValido("El archivo de respaldo supera el tamaño máximo admitido.")
    with open(completa, "rb") as f:
        contenido = f.read()

    _auditar(
        admin,
        ip,
        accion="descargar_respaldo",
        tabla=None,
        clave=None,
        resumen=f"Descarga del respaldo {nombre}",
        detalle={"archivo": nombre, "bytes": tamano},
        filas=0,
    )
    return contenido, nombre


def restaurar_respaldo(archivo: str, admin: dict, ip: str = "") -> dict:
    """
    Sustituye la base activa por un respaldo verificado.

    Siempre guarda el estado actual antes de sobrescribir, de modo que volver
    atrás sea posible. Tras restaurar hay que reiniciar el servidor para que
    todas las conexiones vuelvan a abrir el archivo nuevo.
    """
    base_norm = "guias"
    directorio = _directorio_respaldos(base_norm)
    origen = os.path.join(directorio, os.path.basename(archivo or ""))
    _verificar_respaldo(origen)

    seguridad = crear_respaldo(motivo="antes-de-restaurar", base=base_norm)
    destino = _ruta_base(base_norm)

    with get_db_lock():
        for sufijo in ("-wal", "-shm"):
            try:
                os.remove(destino + sufijo)
            except OSError:
                pass
        shutil.copy2(origen, destino + ".restaurando")
        os.replace(destino + ".restaurando", destino)

    _auditar(
        admin,
        ip,
        accion="restaurar_respaldo",
        tabla=None,
        clave=None,
        resumen="Base de datos restaurada desde respaldo",
        detalle={
            "respalto": os.path.basename(origen),
            "seguridad_previa": seguridad.get("archivo"),
        },
        filas=0,
    )
    logger.warning("Base restaurada desde %s. Reinicie el servidor.", origen)
    return {
        "ok": True,
        "respalto": os.path.basename(origen),
        "seguridad_previa": seguridad.get("archivo"),
        "aviso": "Reinicie el servidor para que todos los hilos abran el archivo nuevo.",
    }


def eliminar_respaldo(archivo: str, admin: dict, ip: str = "") -> dict:
    nombre = os.path.basename(archivo or "")
    if not nombre.endswith(".db"):
        raise RespaldoNoValido("Nombre de respaldo no válido.")
    ruta = os.path.join(_directorio_respaldos("guias"), nombre)
    if not os.path.isfile(ruta):
        raise RespaldoNoValido("El respaldo indicado no existe.")
    try:
        os.remove(ruta)
    except OSError as ex:
        raise DbAdminError(f"No se pudo eliminar el respaldo: {ex}") from ex
    _auditar(
        admin,
        ip,
        accion="eliminar_respaldo",
        tabla=None,
        clave=None,
        resumen="Respaldo eliminado",
        detalle={"archivo": nombre},
        filas=0,
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Mantenimiento y migraciones
# ---------------------------------------------------------------------------

_MANTENIMIENTOS = {
    "vacuum": "Reconstruye el archivo y recupera el espacio libre. Cierra la base un instante.",
    "wal_checkpoint": "Vuelca el registro WAL a la base y lo trunca.",
    "optimize": "Actualiza las estadísticas del planificador de consultas.",
    "analyze": "Recalcula los índices para acelerar las consultas.",
}


def ejecutar_mantenimiento(operacion: str, admin: dict, ip: str = "") -> dict:
    """Ejecuta una operación de mantenimiento y audita el resultado."""
    operacion = (operacion or "").strip().lower()
    if operacion not in _MANTENIMIENTO_DISPONIBLE():
        raise DbAdminError(
            "Operación no válida. Disponibles: " + ", ".join(sorted(_MANTENIMIENTO_DISPONIBLE()))
        )
    conn = _conectar("guias")
    inicio = time.monotonic()
    try:
        with get_db_lock():
            if operacion == "wal_checkpoint":
                fila = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                detalle = {"busy": fila[0], "paginas": fila[1], "movidas": fila[2]}
            else:
                conn.execute(f"PRAGMA {operacion.upper()}")
                conn.commit()
                detalle = {}
    except sqlite3.Error as ex:
        raise DbAdminError(f"No se pudo ejecutar '{operacion}': {ex}") from ex
    finally:
        conn.close()

    _auditar(
        admin,
        ip,
        accion="mantenimiento",
        tabla=None,
        clave=None,
        resumen=f"Mantenimiento: {operacion}",
        detalle=detalle,
        filas=0,
    )
    return {"operacion": operacion, "duracion_ms": int((time.monotonic() - inicio) * 1000)}


def _MANTENIMIENTO_DISPONIBLE() -> set:
    return {"vacuum", "wal_checkpoint", "optimize", "analyze"}


def listar_migraciones() -> list:
    """Migraciones declaradas en disco y cuáles están aplicadas."""
    aplicadas = {}
    conn = _conectar("guias", solo_lectura=True)
    try:
        for fila in conn.execute("SELECT version, nombre, aplicada_en FROM schema_migrations").fetchall():
            aplicadas[fila["version"]] = {"nombre": fila["nombre"], "aplicada_en": fila["aplicada_en"]}
    except sqlite3.Error:
        aplicadas = {}
    finally:
        conn.close()

    salida = []
    if os.path.isdir(_cfg.MIGRATIONS_DIR):
        for nombre in sorted(os.listdir(_cfg.MIGRATIONS_DIR)):
            if not (nombre.startswith("V") and nombre.endswith(".sql")):
                continue
            try:
                version = int(nombre.split("_", 1)[0][1:])
            except (ValueError, IndexError):
                continue
            info = aplicadas.get(version)
            salida.append(
                {
                    "version": version,
                    "archivo": nombre,
                    "aplicada": info is not None,
                    "aplicada_en": (info or {}).get("aplicada_en"),
                }
            )
    salida.sort(key=lambda m: m["version"])
    return salida


def aplicar_migraciones(admin: dict, ip: str = "") -> dict:
    """
    Aplica las migraciones pendientes. Crea un respaldo previo: una migración
    que falla a mitad puede dejar el esquema inconsistente.
    """
    from guias_coodescor.database.models import _aplicar_migraciones_pendientes

    seguridad = crear_respaldo(motivo="antes-de-migrar")
    antes = {m["version"] for m in listar_migraciones() if m["aplicada"]}
    try:
        _aplicar_migraciones_pendientes()
    except sqlite3.Error as ex:
        raise DbAdminError(
            f"La migración falló: {ex}. Se conserva el respaldo "
            f"'{seguridad.get('archivo')}' para revertir."
        ) from ex
    despues = {m["version"] for m in listar_migraciones() if m["aplicada"]}
    nuevas = sorted(despues - antes)
    _auditar(
        admin,
        ip,
        accion="aplicar_migraciones",
        tabla=None,
        clave=None,
        resumen=f"Migraciones aplicadas: {nuevas or 'ninguna pendiente'}",
        detalle={"versiones": nuevas, "respaldo": seguridad.get("archivo")},
        filas=0,
    )
    return {"versiones_nuevas": nuevas, "respaldo": seguridad.get("archivo")}


# ---------------------------------------------------------------------------
# Auditoría
# ---------------------------------------------------------------------------

def _auditar(
    admin: dict,
    ip: str,
    accion: str,
    tabla: str = None,
    clave: str = None,
    resumen: str = "",
    detalle=None,
    filas: int = 0,
) -> None:
    """Escribe una entrada de auditoría. Nunca debe romper la operación principal."""
    try:
        conn = _conectar_cualquiera()
        try:
            conn.execute(
                """
                INSERT INTO admin_auditoria(
                    en, usuario_id, usuario, rol, ip, accion,
                    tabla, clave, resumen, detalle, filas_afectadas
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ahora_txt(),
                    (admin or {}).get("id"),
                    (admin or {}).get("usuario"),
                    (admin or {}).get("rol"),
                    ip or "",
                    accion,
                    tabla,
                    clave,
                    resumen,
                    json.dumps(detalle, ensure_ascii=False, default=str)[:20000] if detalle else "",
                    filas,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as ex:  # pragma: no cover - la auditoría nunca debe fallar la operación
        logger.warning("No se pudo registrar la auditoría de '%s': %s", accion, ex)


def listar_auditoria(limite: int = 100, offset: int = 0, accion: str = "", usuario: str = "") -> dict:
    """Historial de operaciones de base de datos, del más reciente al más viejo."""
    try:
        limite = max(1, min(int(limite), 500))
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        limite, offset = 100, 0

    where = ""
    params = []
    filtros = []
    if accion:
        filtros.append("accion = ?")
        params.append(accion)
    if usuario:
        filtros.append("usuario = ?")
        params.append(usuario)
    if filtros:
        where = " WHERE " + " AND ".join(filtros)

    conn = _conectar_cualquiera()
    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM admin_auditoria{where}", params
        ).fetchone()[0]
        filas = conn.execute(
            f"SELECT * FROM admin_auditoria{where} ORDER BY id DESC LIMIT ? OFFSET ?",
            [*params, limite, offset],
        ).fetchall()
    finally:
        conn.close()

    salida = []
    for f in filas:
        detalle = None
        try:
            detalle = json.loads(f["detalle"]) if f["detalle"] else None
        except (ValueError, TypeError):
            detalle = {"crudo": f["detalle"]}
        salida.append(
            {
                "id": f["id"],
                "en": f["en"],
                "usuario": f["usuario"],
                "rol": f["rol"],
                "ip": f["ip"],
                "accion": f["accion"],
                "tabla": f["tabla"],
                "clave": f["clave"],
                "resumen": f["resumen"],
                "filas_afectadas": f["filas_afectadas"],
                "detalle": detalle,
            }
        )
    return {"total": total, "limite": limite, "offset": offset, "registros": salida}


def acciones_auditadas() -> list:
    """Acciones distintas presentes en el historial, para poblar el filtro."""
    conn = _conectar_cualquiera()
    try:
        return [
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT accion FROM admin_auditoria ORDER BY accion"
            ).fetchall()
        ]
    finally:
        conn.close()