#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resolución de rutas de datos, archivo de configuración externo y secretos.

Regla de diseño: los DATOS (base de datos, adjuntos, logs, respaldos) NUNCA deben
vivir dentro de la carpeta del código. Así se puede actualizar, reinstalar o
versionar el programa sin tocar la información, y se puede desplegar como
servicio en un equipo distinto sin reconfigurar nada.

Orden de resolución del directorio de datos (gana el primero que exista):
    1. Variable de entorno COODESCOR_DATA_DIR   → despliegues como servicio
    2. Clave "data_dir" del config.json externo  → editable sin tocar código
    3. Ubicación de datos del sistema            → %ProgramData% en Windows,
                                                    ~/.local/share en Linux

El archivo de configuración externo es <BASE_DIR>/config.json y puede moverse con
la variable COODESCOR_CONFIG_FILE.
"""
import json
import os
import shutil
import sys
import time

BASE_DIR_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Carpeta del proyecto (donde vive run_app.py). El config.json va aquí porque es
# la ubicación que el usuario abre a diario; la carpeta del paquete es código.
PROJECT_DIR = os.path.dirname(BASE_DIR_PKG)

NOMBRE_ARCHIVO_CONFIG = "config.json"
NOMBRE_ARCHIVO_SECRETOS = "secretos.json"
NOMBRE_ARCHIVO_MIGRACION = ".migrado_desde_legado"
NOMBRE_DIRECTORIO_APP = "Coodescor"
NOMBRE_SUBDIRECTORIO_APP = "Guias"

ENV_DATA_DIR = "COODESCOR_DATA_DIR"
ENV_CONFIG_FILE = "COODESCOR_CONFIG_FILE"

ARCHIVOS_DATOS = ("guias.db", "receptores.db")
DIRECTORIO_LEGADO = "data"


def ruta_config_externo() -> str:
    """Ruta del config.json externo. Respeta COODESCOR_CONFIG_FILE."""
    return os.environ.get(ENV_CONFIG_FILE) or os.path.join(
        PROJECT_DIR, NOMBRE_ARCHIVO_CONFIG
    )


def leer_json(ruta: str) -> dict:
    """Lee un JSON devolviendo {} si no existe o está corrupto."""
    try:
        with open(ruta, "r", encoding="utf-8") as fh:
            datos = json.load(fh)
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def escribir_json_atomico(ruta: str, datos: dict) -> None:
    """
    Escribe un JSON de forma atómica (archivo temporal + replace) para que una
    interrupción no deje un archivo de configuración a medio escribir.
    """
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    tmp = f"{ruta}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, ruta)
    if os.name != "nt":
        try:
            os.chmod(ruta, 0o600)
        except OSError:
            pass


def _writable(directorio: str) -> bool:
    try:
        os.makedirs(directorio, exist_ok=True)
        return os.access(directorio, os.W_OK)
    except OSError:
        return False


def data_dir_por_defecto() -> str:
    """
    Ubicación de datos propia del sistema operativo, pensada para que la
    aplicación funcione como servicio y no choque con la carpeta de programas.
    """
    if sys.platform == "win32":
        base = os.environ.get("ProgramData") or r"C:\ProgramData"
        candidate = os.path.join(base, NOMBRE_DIRECTORIO_APP, NOMBRE_SUBDIRECTORIO_APP)
        if _writable(candidate):
            return candidate
        fallback = os.path.join(
            os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
            NOMBRE_DIRECTORIO_APP,
            NOMBRE_SUBDIRECTORIO_APP,
        )
        return fallback
    if sys.platform == "darwin":
        return os.path.join(
            os.path.expanduser("~"),
            "Library",
            "Application Support",
            NOMBRE_DIRECTORIO_APP,
            NOMBRE_SUBDIRECTORIO_APP,
        )
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    return os.path.join(base, "coodescor", "guias")


def resolver_data_dir() -> tuple:
    """
    Devuelve (ruta_absoluta, origen) del directorio de datos.
    origen ∈ {"entorno", "config", "sistema"}.

    Una instalación anterior con los datos dentro de la carpeta del código NO
    tiene atajo: resuelve a la ubicación del sistema y migrar_datos_legados()
    traslada los archivos. Así la base deja de depender de la carpeta del
    programa, que es lo que se pidió.
    """
    desde_entorno = os.environ.get(ENV_DATA_DIR)
    if desde_entorno:
        return os.path.abspath(desde_entorno), "entorno"

    desde_config = leer_json(ruta_config_externo()).get("data_dir")
    if desde_config:
        return os.path.abspath(str(desde_config)), "config"

    return os.path.abspath(data_dir_por_defecto()), "sistema"


def contiene_datos(directorio: str) -> bool:
    """Indica si el directorio ya tiene una base de datos principal."""
    return os.path.isfile(os.path.join(directorio, ARCHIVOS_DATOS[0]))


def _copiar_arbol(origen: str, destino: str, saltar: set) -> None:
    os.makedirs(destino, exist_ok=True)
    for raiz, directorios, archivos in os.walk(origen):
        relative = os.path.relpath(raiz, origen)
        destino_raiz = destino if relative == "." else os.path.join(destino, relative)
        os.makedirs(destino_raiz, exist_ok=True)
        for nombre in archivos:
            if relative == "." and nombre in saltar:
                continue
            if nombre.endswith(("-wal", "-shm")) or nombre.startswith(NOMBRE_ARCHIVO_CONFIG + ".tmp"):
                continue
            origen_archivo = os.path.join(raiz, nombre)
            destino_archivo = os.path.join(destino_raiz, nombre)
            try:
                shutil.copy2(origen_archivo, destino_archivo)
            except OSError:
                continue


def migrar_datos_legados(destino: str) -> str:
    """
    Si los datos seguían dentro de la carpeta del código (comportamiento de las
    versiones anteriores) y el destino está vacío, los copia al destino.

    Nunca borra el origen: queda como respaldo de seguridad y se informa por
    log. Devuelve una descripción de lo que hizo, o cadena vacía si no hizo nada.
    """
    legado = os.path.join(BASE_DIR_PKG, DIRECTORIO_LEGADO)
    if os.path.abspath(legado) == os.path.abspath(destino):
        return ""
    # No se migra si el destino ya tiene base: es una instalación en marcha.
    if not contiene_datos(legado) or contiene_datos(destino):
        return ""
    _copiar_arbol(legado, destino, saltar={NOMBRE_ARCHIVO_CONFIG})
    marca = os.path.join(destino, NOMBRE_ARCHIVO_MIGRACION)
    try:
        with open(marca, "w", encoding="utf-8") as fh:
            fh.write(
                f"Migrado el {time.strftime('%Y-%m-%d %H:%M:%S')} desde {legado}\n"
                "El origen NO se eliminó; bórralo manualmente cuando confirmes que todo funciona.\n"
            )
    except OSError:
        pass
    return (
        f"Datos migrados de la carpeta del código ({legado}) a {destino}. "
        f"El respaldo original se conservó en {legado}."
    )


def ruta_secretos(data_dir: str) -> str:
    return os.path.join(data_dir, NOMBRE_ARCHIVO_SECRETOS)


def leer_secretos(data_dir: str) -> dict:
    """
    Lee el almacén de secretos (archivo fuera de la base de datos).
    Los secretos NO deben vivir en la BD: si alguien copia el archivo de datos
    no debe poder descifrar los datos personales cifrados.
    """
    return leer_json(ruta_secretos(data_dir))


def escribir_secretos(data_dir: str, secretos: dict) -> None:
    escribir_json_atomico(ruta_secretos(data_dir), secretos)


def asegurar_secreto(data_dir: str, nombre: str, generador) -> str:
    """
    Devuelve el secreto persistido. Lo crea una sola vez si no existe.
    Semántica idéntica a la que se usaba cuando vivía en la tabla config.
    """
    secretos = leer_secretos(data_dir)
    valor = secretos.get(nombre)
    if valor:
        return str(valor)
    valor = generador()
    secretos[nombre] = valor
    escribir_secretos(data_dir, secretos)
    return valor


def preparar() -> dict:
    """
    Punto de entrada usado por config.py. Crea la estructura de directorios,
    migra datos legados si corresponde y devuelve un resumen del destino.
    """
    data_dir, origen = resolver_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, "adjuntos"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "respaldos"), exist_ok=True)

    resumen_migracion = migrar_datos_legados(data_dir)

    ruta_config = ruta_config_externo()
    cfg = leer_json(ruta_config)
    # Se registra la ubicación solo cuando viene del valor por defecto del
    # sistema: si viene de una variable de entorno no se persiste, para que
    # quitarla del entorno no quede anulada por el archivo.
    if origen in ("sistema",) and not cfg.get("data_dir"):
        cfg["data_dir"] = data_dir
        escribir_json_atomico(ruta_config, cfg)

    return {
        "data_dir": data_dir,
        "origen": origen,
        "config_file": ruta_config,
        "migracion": resumen_migracion,
    }