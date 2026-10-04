#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio de IA multi-proveedor para Guías Coodescor.

Soporta múltiples proveedores de modelos de lenguaje GRATUITOS:
- Hugging Face Inference API (sin API Key, sin límite estricto)
- Mistral AI (API Key gratuita, 32K tokens/mes)
- Groq (API Key gratuita, ~200 req/día)
- Google Gemini (API Key gratuita, 1000 req/día)

Uso:
    from guias_coodescor.services.ai_service import AIService
    ai = AIService()
    respuesta = ai.generate("Explica este texto: ...")

Configuración:
    Establece las API Keys como variables de entorno:
    - HUGGINGFACE_API_KEY (opcional para más solicitudes)
    - MISTRAL_API_KEY
    - GROQ_API_KEY
    - GOOGLE_GEMINI_API_KEY
    
    O en config.py:
    - AI_HUGGINGFACE_KEY
    - AI_MISTRAL_KEY
    - AI_GROQ_KEY
    - AI_GOOGLE_KEY
"""

import json
import os
import ssl
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)


# ============================================================================
# Configuración
# ============================================================================

class AIConfig:
    """Configuración centralizada para el servicio de IA."""
    
    # Prioridad de proveedores (se prueba en este orden)
    PROVEEDOR_PRIORIDAD = [
        "huggingface",  # Gratis sin API Key
        "mistral",     # Gratis con API Key
        "groq",        # Gratis con API Key
        "google",      # Gratis con API Key
    ]
    
    # Configuración de modelos por proveedor
    MODELOS = {
        "huggingface": {
            "default": "mistralai/Mistral-7B-instruct",
            "alternativos": [
                "meta-llama/Llama-3-8B-instruct",
                "google/gemma-7b-it",
                "microsoft/Phi-3-mini-4k-instruct",
                "Qwen/Qwen2-7B-instruct",
            ]
        },
        "mistral": {
            "default": "mistral-tiny",
            "alternativos": ["mistral-small", "mistral-medium"]
        },
        "groq": {
            "default": "llama3-8b-8192",
            "alternativos": [
                "mixtral-8x7b-32768",
                "gemma-7b-it",
                "llama3-70b-8192",
            ]
        },
        "google": {
            "default": "gemini-1.5-flash",
            "alternativos": ["gemini-1.5-pro"]
        }
    }
    
    # Timeouts (segundos)
    TIMEOUT = 30
    
    # Headers comunes
    HEADERS_JSON = {"Content-Type": "application/json"}
    
    @classmethod
    def get_api_key(cls, proveedor: str) -> Optional[str]:
        """Obtiene la API Key desde variables de entorno o config."""
        env_var = {
            "huggingface": "HUGGINGFACE_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "groq": "GROQ_API_KEY",
            "google": "GOOGLE_GEMINI_API_KEY",
        }
        return os.environ.get(env_var.get(proveedor))


# ============================================================================
# Proveedores individuales
# ============================================================================

class AIProvider(ABC):
    """Interfaz base para todos los proveedores de IA."""
    
    @abstractmethod
    def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> Tuple[bool, str]:
        """
        Genera una respuesta a partir de un prompt.
        
        Args:
            prompt: Texto de entrada
            model: Modelo específico a usar (opcional)
            **kwargs: Argumentos adicionales según el proveedor
            
        Returns:
            Tuple[bool, str]: (éxito, respuesta o error)
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica si el proveedor está disponible (tiene API Key si es necesario)."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre del proveedor."""
        pass


class HuggingFaceProvider(AIProvider):
    """Proveedor para Hugging Face Inference API."""
    
    BASE_URL = "https://api-inference.huggingface.co/models/{model}"
    
    def __init__(self):
        self.api_key = AIConfig.get_api_key("huggingface")
    
    @property
    def name(self) -> str:
        return "huggingface"
    
    def is_available(self) -> bool:
        return True  # Funciona sin API Key
    
    def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> Tuple[bool, str]:
        model = model or AIConfig.MODELOS["huggingface"]["default"]
        url = self.BASE_URL.format(model=model)
        
        headers = dict(AIConfig.HEADERS_JSON)
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "inputs": prompt,
            "options": {"wait_for_model": True},
            **kwargs
        }
        
        try:
            req = Request(
                url=url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            
            context = ssl.create_default_context()
            with urlopen(req, timeout=AIConfig.TIMEOUT, context=context) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                # Hugging Face devuelve la respuesta en formato específico
                if isinstance(data, list):
                    # Si es lista, tomar el primer elemento
                    text = data[0].get("generated_text", str(data))
                elif isinstance(data, dict):
                    # Algunos modelos devuelven directamente
                    text = data.get("generated_text", data.get("output", str(data)))
                else:
                    text = str(data)
                
                return True, text
                
        except HTTPError as e:
            error_msg = f"HuggingFace HTTP {e.code}: {e.read().decode() if e.read() else str(e)}"
            logger.warning(f"HuggingFace error: {error_msg}")
            return False, error_msg
        except URLError as e:
            error_msg = f"HuggingFace connection error: {str(e)}"
            logger.warning(f"HuggingFace connection error: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"HuggingFace unexpected error: {str(e)}"
            logger.error(f"HuggingFace unexpected error: {error_msg}")
            return False, error_msg


class MistralProvider(AIProvider):
    """Proveedor para Mistral AI API."""
    
    BASE_URL = "https://api.mistral.ai/v1/chat/completions"
    
    def __init__(self):
        self.api_key = AIConfig.get_api_key("mistral")
    
    @property
    def name(self) -> str:
        return "mistral"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "Mistral API Key no configurada"
        
        model = model or AIConfig.MODELOS["mistral"]["default"]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024),
        }
        
        try:
            req = Request(
                url=self.BASE_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            
            context = ssl.create_default_context()
            with urlopen(req, timeout=AIConfig.TIMEOUT, context=context) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                if "choices" in data and len(data["choices"]) > 0:
                    text = data["choices"][0]["message"]["content"]
                    return True, text
                else:
                    return False, f"Respuesta inesperada de Mistral: {json.dumps(data)}"
                    
        except HTTPError as e:
            error_data = e.read().decode() if e.read() else ""
            try:
                error_json = json.loads(error_data)
                error_msg = error_json.get("message", error_data)
            except:
                error_msg = error_data
            return False, f"Mistral API error: {error_msg}"
        except Exception as e:
            return False, f"Mistral error: {str(e)}"


class GroqProvider(AIProvider):
    """Proveedor para Groq API."""
    
    BASE_URL = "https://api.groq.com/v1/chat/completions"
    
    def __init__(self):
        self.api_key = AIConfig.get_api_key("groq")
    
    @property
    def name(self) -> str:
        return "groq"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "Groq API Key no configurada"
        
        model = model or AIConfig.MODELOS["groq"]["default"]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024),
        }
        
        try:
            req = Request(
                url=self.BASE_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            
            context = ssl.create_default_context()
            with urlopen(req, timeout=AIConfig.TIMEOUT, context=context) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                if "choices" in data and len(data["choices"]) > 0:
                    text = data["choices"][0]["message"]["content"]
                    return True, text
                else:
                    return False, f"Respuesta inesperada de Groq: {json.dumps(data)}"
                    
        except HTTPError as e:
            error_data = e.read().decode() if e.read() else ""
            try:
                error_json = json.loads(error_data)
                error_msg = error_json.get("message", error_data)
            except:
                error_msg = error_data
            return False, f"Groq API error: {error_msg}"
        except Exception as e:
            return False, f"Groq error: {str(e)}"


class GoogleGeminiProvider(AIProvider):
    """Proveedor para Google Gemini API."""
    
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    def __init__(self):
        self.api_key = AIConfig.get_api_key("google")
    
    @property
    def name(self) -> str:
        return "google"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "Google API Key no configurada"
        
        model = model or AIConfig.MODELOS["google"]["default"]
        url = self.BASE_URL.format(model=model, api_key=self.api_key)
        
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxOutputTokens": kwargs.get("max_tokens", 1024),
            }
        }
        
        try:
            req = Request(
                url=url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            
            context = ssl.create_default_context()
            with urlopen(req, timeout=AIConfig.TIMEOUT, context=context) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                if "candidates" in data and len(data["candidates"]) > 0:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return True, text
                else:
                    return False, f"Respuesta inesperada de Google: {json.dumps(data)}"
                    
        except HTTPError as e:
            error_data = e.read().decode() if e.read() else ""
            try:
                error_json = json.loads(error_data)
                error_msg = error_json.get("error", {}).get("message", error_data)
            except:
                error_msg = error_data
            return False, f"Google API error: {error_msg}"
        except Exception as e:
            return False, f"Google error: {str(e)}"


# ============================================================================
# Fábrica de proveedores
# ============================================================================

class AIProviderFactory:
    """Fábrica para crear instancias de proveedores."""
    
    _providers: Dict[str, AIProvider] = {}
    
    @classmethod
    def get_provider(cls, nombre: str) -> Optional[AIProvider]:
        """Obtiene una instancia de un proveedor."""
        if nombre not in cls._providers:
            proveedor_class = {
                "huggingface": HuggingFaceProvider,
                "mistral": MistralProvider,
                "groq": GroqProvider,
                "google": GoogleGeminiProvider,
            }.get(nombre)
            
            if proveedor_class:
                cls._providers[nombre] = proveedor_class()
        
        return cls._providers.get(nombre)
    
    @classmethod
    def get_available_providers(cls) -> List[AIProvider]:
        """Obtiene todos los proveedores disponibles y configurados."""
        proveedores = []
        for nombre in AIConfig.PROVEEDOR_PRIORIDAD:
            provider = cls.get_provider(nombre)
            if provider and provider.is_available():
                proveedores.append(provider)
        return proveedores


# ============================================================================
# Servicio principal de IA
# ============================================================================

class AIService:
    """
    Servicio principal de IA con soporte multi-proveedor y fallback automático.
    
    Uso:
        ai = AIService()
        respuesta = ai.generate("Explica la inteligencia artificial")
        
        # Con opciones
        respuesta = ai.generate(
            "Escribe un poema",
            proveedor="mistral",
            model="mistral-tiny",
            temperature=0.9
        )
    """
    
    def __init__(self):
        self._providers = None
    
    def _get_providers(self) -> List[AIProvider]:
        """Obtiene los proveedores disponibles (cacheado)."""
        if self._providers is None:
            self._providers = AIProviderFactory.get_available_providers()
        return self._providers
    
    def generate(
        self,
        prompt: str,
        proveedor: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Genera una respuesta usando IA.
        
        Args:
            prompt: Texto de entrada
            proveedor: Proveedor específico a usar (None = usar prioridad)
            model: Modelo específico a usar
            **kwargs: Argumentos adicionales para el proveedor
            
        Returns:
            Tuple[bool, str, str]: (éxito, respuesta, nombre_del_proveedor_usado)
        """
        if proveedor:
            # Usar proveedor específico
            provider = AIProviderFactory.get_provider(proveedor)
            if not provider:
                return False, f"Proveedor '{proveedor}' no soportado", None
            if not provider.is_available():
                return False, f"Proveedor '{proveedor}' no está configurado", None
            
            success, response = provider.generate(prompt, model, **kwargs)
            return success, response, provider.name
        
        # Usar prioridad con fallback
        providers = self._get_providers()
        
        if not providers:
            return False, "Ningún proveedor de IA está configurado. Configura al menos una API Key.", None
        
        errors = []
        for provider in providers:
            try:
                success, response = provider.generate(prompt, model, **kwargs)
                if success:
                    logger.info(f"IA: Proveedor '{provider.name}' usado para la solicitud")
                    return True, response, provider.name
                else:
                    errors.append(f"{provider.name}: {response}")
            except Exception as e:
                errors.append(f"{provider.name}: {str(e)}")
        
        error_msg = "Todos los proveedores fallaron. " + " | ".join(errors)
        logger.error(f"IA: Todos los proveedores fallaron: {error_msg}")
        return False, error_msg, None
    
    def get_available_providers(self) -> List[str]:
        """Obtiene la lista de nombres de proveedores disponibles."""
        return [p.name for p in self._get_providers()]
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Obtiene información de todos los proveedores."""
        info = {}
        for nombre in AIConfig.PROVEEDOR_PRIORIDAD:
            provider = AIProviderFactory.get_provider(nombre)
            if provider:
                info[nombre] = {
                    "available": provider.is_available(),
                    "models": AIConfig.MODELOS.get(nombre, {}).get("alternativos", []),
                    "default_model": AIConfig.MODELOS.get(nombre, {}).get("default"),
                }
        return info


# ============================================================================
# Funciones de conveniencia
# ============================================================================

# Instancia global (singleton)
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Obtiene la instancia global del servicio de IA."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service


def generate_text(prompt: str, **kwargs) -> Tuple[bool, str]:
    """
    Función de conveniencia para generar texto.
    
    Args:
        prompt: Texto de entrada
        **kwargs: Argumentos adicionales para el servicio de IA
        
    Returns:
        Tuple[bool, str]: (éxito, respuesta)
    """
    success, response, provider = get_ai_service().generate(prompt, **kwargs)
    return success, response


# ============================================================================
# Inicialización
# ============================================================================

def init_ai_service():
    """Inicializa el servicio de IA (opcional, se inicializa automáticamente)."""
    # Verifica que al menos un proveedor esté configurado
    providers = get_ai_service().get_available_providers()
    if not providers:
        logger.warning(
            "Servicio de IA: Ningún proveedor configurado. "
            "Configura API Keys para Mistral, Groq, Google o HuggingFace."
        )
    else:
        logger.info(f"Servicio de IA: Proveedores disponibles: {', '.join(providers)}")
