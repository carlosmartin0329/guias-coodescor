#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Settings validados con Pydantic.

- Lee .env, variables de entorno y config.json (en ese orden de prioridad).
- Valida tipos al arrancar: falla rápido si hay typos.
- Compatible con el config.py actual: expone las mismas constantes.
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from guias_coodescor.core.paths import (
    BASE_DIR_PKG,
    leer_json,
    preparar,
    ruta_config_externo,
    ruta_secretos,
)


class Settings(BaseSettings):
    """Configuración tipada y validada."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Entorno --------------------------------------------------------------
    environment: str = Field(default="development", description="development|staging|production")

    # --- Red ------------------------------------------------------------------
    host: str = Field(default="0.0.0.0", description="Bind address")
    port: int = Field(default=8000, ge=1, le=65535, description="Puerto HTTP")

    # --- Datos (resueltos por core/paths.py) ---------------------------------
    data_dir: Optional[str] = Field(default=None, description="Override de COODESCOR_DATA_DIR")

    # --- CORS -----------------------------------------------------------------
    cors_origins: str = Field(default="", description="Orígenes permitidos, separados por coma")

    # --- Proxies de confianza -------------------------------------------------
    trusted_proxies: str = Field(default="127.0.0.1,::1", description="Proxies de confianza para X-Forwarded-For")

    # --- Límites --------------------------------------------------------------
    max_request_body: int = Field(default=30 * 1024 * 1024, ge=1024)
    max_adjunto_size: int = Field(default=10 * 1024 * 1024, ge=1024)

    # --- Logging --------------------------------------------------------------
    log_level: str = Field(default="INFO", description="DEBUG|INFO|WARNING|ERROR")
    log_format: str = Field(default="json", description="json|text")

    # --- Rate limiting --------------------------------------------------------
    rate_limit_requests: int = Field(default=100, ge=1)
    rate_limit_window: int = Field(default=60, ge=1)

    # --- SSL (producción) -----------------------------------------------------
    ssl_cert_path: Optional[str] = Field(default=None)
    ssl_key_path: Optional[str] = Field(default=None)

    # --- Validadores ----------------------------------------------------------
    @field_validator("environment")
    @classmethod
    def _valid_env(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("development", "staging", "production"):
            raise ValueError("environment debe ser development|staging|production")
        return v

    @field_validator("log_level")
    @classmethod
    def _valid_log_level(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            raise ValueError("log_level debe ser DEBUG|INFO|WARNING|ERROR")
        return v

    @field_validator("log_format")
    @classmethod
    def _valid_log_format(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("json", "text"):
            raise ValueError("log_format debe ser json|text")
        return v

    @field_validator("cors_origins")
    @classmethod
    def _parse_cors(cls, v: str) -> str:
        return v.strip()

    @field_validator("trusted_proxies")
    @classmethod
    def _parse_proxies(cls, v: str) -> str:
        return v.strip()


@lru_cache
def get_settings() -> Settings:
    """
    Instancia singleton de settings.

    Prioridad de carga (mayor a menor):
    1. Variables de entorno (COODESCOR_*, etc.)
    2. .env file
    3. config.json externo (leído por core/paths.py)
    4. Valores por defecto de la clase
    """
    # Pre-carga config.json para que Pydantic lo vea como fallback
    _preparado = preparar()
    config_json = leer_json(ruta_config_externo()) or {}

    # Sobrescribe defaults con config.json antes de instanciar
    defaults = {}
    if config_json.get("host"):
        defaults["host"] = config_json["host"]
    if config_json.get("port"):
        defaults["port"] = config_json["port"]
    if config_json.get("cors_origins"):
        defaults["cors_origins"] = config_json["cors_origins"]
    if config_json.get("trusted_proxies"):
        defaults["trusted_proxies"] = config_json["trusted_proxies"]

    return Settings(**defaults)


# Instancia global (se usa en config.py)
settings = get_settings()