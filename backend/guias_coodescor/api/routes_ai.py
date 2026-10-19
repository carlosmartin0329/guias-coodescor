#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rutas API para el servicio de Inteligencia Artificial.
Proporciona endpoints para:
- Generar texto con modelos de IA gratuitos
- Obtener información de proveedores disponibles
- Validar configuración de API Keys
"""

import json
from guias_coodescor.services.ai_service import get_ai_service
from guias_coodescor.config import AI_DEFAULT_PROVIDER


def _handler_generate(qs, user, json_fn):
    """
    GET /api/ai/generate?prompt=<texto>&proveedor=<nombre>&model=<modelo>
    
    Genera texto usando IA. Requiere sesión autenticada.
    
    Parámetros:
    - prompt: Texto de entrada (obligatorio)
    - proveedor: Nombre del proveedor (opcional, default: AI_DEFAULT_PROVIDER)
    - model: Modelo específico (opcional)
    - temperature: Temperatura para la generación (opcional, 0.0-1.0)
    - max_tokens: Máximo de tokens en la respuesta (opcional)
    
    Retorna: {ok: bool, respuesta: str, proveedor: str, error?: str}
    """
    if not user:
        return json_fn({"ok": False, "error": "Sesión inválida o expirada"}, 401)
    
    prompt = (qs.get("prompt") or [""])[0].strip()
    if not prompt:
        return json_fn({"ok": False, "error": "El parámetro 'prompt' es obligatorio"}, 400)
    
    proveedor = (qs.get("proveedor") or [AI_DEFAULT_PROVIDER])[0]
    model = (qs.get("model") or [""])[0] or None
    
    # Parámetros opcionales
    kwargs = {}
    try:
        temp = (qs.get("temperature") or [""])[0]
        if temp:
            kwargs["temperature"] = float(temp)
    except (ValueError, TypeError):
        pass
    
    try:
        tokens = (qs.get("max_tokens") or [""])[0]
        if tokens:
            kwargs["max_tokens"] = int(tokens)
    except (ValueError, TypeError):
        pass
    
    try:
        ai_service = get_ai_service()
        success, response, provider_used = ai_service.generate(
            prompt, proveedor=proveedor, model=model, **kwargs
        )
        
        if success:
            return json_fn({
                "ok": True,
                "respuesta": response,
                "proveedor": provider_used or proveedor,
            })
        else:
            return json_fn({
                "ok": False,
                "error": response,
                "proveedor": provider_used or proveedor,
            }, 500)
    except Exception as e:
        return json_fn({
            "ok": False,
            "error": f"Error al generar respuesta: {str(e)}",
            "proveedor": proveedor,
        }, 500)


def _handler_info(qs, user, json_fn):
    """
    GET /api/ai/info
    
    Obtiene información sobre los proveedores de IA disponibles.
    No requiere autenticación.
    
    Retorna: {
        ok: bool,
        proveedores: [
            {
                nombre: str,
                disponible: bool,
                modelo_por_defecto: str,
                modelos_alternativos: [str],
            },
            ...
        ],
        proveedor_por_defecto: str,
    }
    """
    try:
        ai_service = get_ai_service()
        info = ai_service.get_provider_info()
        
        proveedores = []
        for nombre, datos in info.items():
            proveedores.append({
                "nombre": nombre,
                "disponible": datos.get("available", False),
                "modelo_por_defecto": datos.get("default_model"),
                "modelos_alternativos": datos.get("models", []),
            })
        
        return json_fn({
            "ok": True,
            "proveedores": proveedores,
            "proveedor_por_defecto": AI_DEFAULT_PROVIDER,
        })
    except Exception as e:
        return json_fn({
            "ok": False,
            "error": str(e),
        }, 500)


def _handler_health(qs, user, json_fn):
    """
    GET /api/ai/health
    
    Verifica el estado del servicio de IA.
    No requiere autenticación.
    
    Retorna: {ok: bool, saludable: bool, proveedores_disponibles: [str]}
    """
    try:
        ai_service = get_ai_service()
        disponibles = ai_service.get_available_providers()
        
        return json_fn({
            "ok": True,
            "saludable": len(disponibles) > 0,
            "proveedores_disponibles": disponibles,
        })
    except Exception as e:
        return json_fn({
            "ok": False,
            "error": str(e),
            "saludable": False,
            "proveedores_disponibles": [],
        }, 500)


# POST handlers

def _handler_generate_post(user, body, ip, json_fn):
    """
    POST /api/ai/generate
    
    Genera texto usando IA. Requiere sesión autenticada.
    
    Body JSON:
    {
        "prompt": "Texto de entrada",
        "proveedor": "mistral",  // opcional
        "model": "mistral-tiny", // opcional
        "temperature": 0.7,      // opcional
        "max_tokens": 1024       // opcional
    }
    
    Retorna: {ok: bool, respuesta: str, proveedor: str, error?: str}
    """
    if not user:
        return json_fn({"ok": False, "error": "Sesión inválida o expirada"}, 401)
    
    try:
        prompt = body.get("prompt", "").strip()
        if not prompt:
            return json_fn({"ok": False, "error": "El campo 'prompt' es obligatorio"}, 400)
        
        proveedor = body.get("proveedor", AI_DEFAULT_PROVIDER)
        model = body.get("model") or None
        
        # Parámetros opcionales
        kwargs = {}
        if "temperature" in body:
            kwargs["temperature"] = float(body["temperature"])
        if "max_tokens" in body:
            kwargs["max_tokens"] = int(body["max_tokens"])
        
        ai_service = get_ai_service()
        success, response, provider_used = ai_service.generate(
            prompt, proveedor=proveedor, model=model, **kwargs
        )
        
        if success:
            return json_fn({
                "ok": True,
                "respuesta": response,
                "proveedor": provider_used or proveedor,
            })
        else:
            return json_fn({
                "ok": False,
                "error": response,
                "proveedor": provider_used or proveedor,
            }, 500)
    except Exception as e:
        return json_fn({
            "ok": False,
            "error": f"Error al generar respuesta: {str(e)}",
        }, 500)


# Definición de rutas
RUTAS_AI_GET = [
    (r"^/api/ai/generate$", _handler_generate),
    (r"^/api/ai/info$", _handler_info),
    (r"^/api/ai/health$", _handler_health),
]

RUTAS_AI_POST = [
    (r"^/api/ai/generate$", _handler_generate_post),
]
