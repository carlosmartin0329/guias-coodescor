#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio de notificaciones en tiempo real.

Implementa:
1. Server-Sent Events (SSE) para conexiones persistentes
2. Polling endpoint para compatibilidad con todos los navegadores

Permite notificar a los clientes cuando:
- Se crea una nueva guía
- Se actualiza el estado de una guía
- Cualquier otro evento relevante
"""

import json
import threading
import time
from typing import Any, Dict, List, Optional, Set

from guias_coodescor.core.logging_config import get_logger
from guias_coodescor.database.connection import db_connection

logger = get_logger("guias_coodescor.sse")


# Almacén de eventos recientes para polling
_event_history = []
_event_history_lock = threading.Lock()
_EVENT_HISTORY_MAX = 50  # Máximo eventos a almacenar


class SSEClient:
    """Representa un cliente conectado via SSE."""
    
    def __init__(self, wfile, user_id: Optional[int] = None, user_rol: Optional[str] = None):
        self.wfile = wfile
        self.user_id = user_id
        self.user_rol = user_rol
        self.connected = True
        self.last_ping = time.time()
    
    def send(self, event_type: str, data: Dict[str, Any], event_id: Optional[str] = None):
        """Envía un evento SSE al cliente."""
        if not self.connected:
            return False
        
        try:
            # Formato SSE: data: <json>\n\n
            if event_id:
                msg = f"id: {event_id}\n"
            else:
                msg = ""
            
            msg += f"event: {event_type}\n"
            msg += f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            
            self.wfile.write(msg.encode('utf-8'))
            self.wfile.flush()
            self.last_ping = time.time()
            return True
        except (BrokenPipeError, ConnectionResetError, ValueError):
            self.connected = False
            return False


class SSEEmitter:
    """
    Emisor de eventos SSE.
    
    Mantiene una lista de clientes conectados y permite enviar eventos a:
    - Todos los clientes
    - Clientes de un rol específico
    - Un cliente específico
    """
    
    _instance: Optional['SSEEmitter'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.clients: Set[SSEClient] = set()
        self.clients_lock = threading.Lock()
        self.event_id = 0
        self._initialized = True
        
        # Thread para limpieza de clientes desconectados
        self.cleanup_thread = threading.Thread(target=self._cleanup_disconnected, daemon=True)
        self.cleanup_thread.start()
    
    def _cleanup_disconnected(self):
        """Limpia clientes desconectados cada 30 segundos."""
        while True:
            time.sleep(30)
            with self.clients_lock:
                disconnected = [c for c in self.clients if not c.connected or 
                             (time.time() - c.last_ping) > 60]
                for c in disconnected:
                    self.clients.discard(c)
                    logger.info(f"SSE: Cliente desconectado (user_id={c.user_id}, rol={c.user_rol})")
                
                # Enviar ping a clientes activos cada 30 segundos
                for c in self.clients:
                    if c.connected:
                        c.send("ping", {"timestamp": time.time()})
    
    def add_client(self, client: SSEClient):
        """Agrega un cliente a la lista de suscriptores."""
        with self.clients_lock:
            self.clients.add(client)
            logger.info(f"SSE: Nuevo cliente conectado (user_id={client.user_id}, rol={client.user_rol})")
    
    def remove_client(self, client: SSEClient):
        """Remueve un cliente de la lista."""
        with self.clients_lock:
            if client in self.clients:
                self.clients.discard(client)
                logger.info(f"SSE: Cliente removido (user_id={client.user_id})")
    
    def emit(self, event_type: str, data: Dict[str, Any], 
             target_rol: Optional[str] = None,
             target_user_id: Optional[int] = None):
        """
        Emite un evento a los clientes.
        
        Args:
            event_type: Tipo de evento (ej: 'nueva_guia', 'estado_actualizado')
            data: Datos del evento
            target_rol: Si se especifica, solo enviar a clientes con este rol
            target_user_id: Si se especifica, solo enviar a este usuario
        """
        self.event_id += 1
        event_id = str(self.event_id)
        
        with self.clients_lock:
            clients_to_notify = []
            for client in self.clients:
                if not client.connected:
                    continue
                
                # Filtrar por usuario específico
                if target_user_id is not None and client.user_id != target_user_id:
                    continue
                
                # Filtrar por rol
                if target_rol is not None and client.user_rol != target_rol:
                    continue
                
                clients_to_notify.append(client)
            
            # Enviar a todos los clientes filtrados
            failed = []
            for client in clients_to_notify:
                if not client.send(event_type, data, event_id):
                    failed.append(client)
            
            # Remover clientes que fallaron
            for client in failed:
                self.clients.discard(client)
            
            logger.info(f"SSE: Evento '{event_type}' emitido a {len(clients_to_notify)} clientes")
    
    def emit_to_all(self, event_type: str, data: Dict[str, Any]):
        """Emite un evento a TODOS los clientes conectados."""
        self.emit(event_type, data)
    
    def emit_to_rol(self, event_type: str, data: Dict[str, Any], rol: str):
        """Emite un evento solo a clientes con un rol específico."""
        self.emit(event_type, data, target_rol=rol)
    
    def get_client_count(self) -> int:
        """Retorna el número de clientes conectados."""
        with self.clients_lock:
            return len([c for c in self.clients if c.connected])


# Instancia global
emitter = SSEEmitter()


def notify_nueva_guia(guia_id: int, guia_data: Dict[str, Any]):
    """
    Notifica a todos los usuarios que se ha creado una nueva guía.
    
    Los usuarios de rol 'ventas' no reciben esta notificación ya que son
    los que crean las guías.
    """
    emitter.emit_to_all("nueva_guia", {
        "guia_id": guia_id,
        "consecutivo": guia_data.get("consecutivo", ""),
        "cliente": guia_data.get("cliente", ""),
        "estado": guia_data.get("estado", ""),
        "creada_en": guia_data.get("creada_en", ""),
        "creada_por": guia_data.get("creada_por", ""),
        "mensaje": "Nueva guía creada y esperando proceso"
    })


def notify_estado_actualizado(guia_id: int, nuevo_estado: str, guia_data: Dict[str, Any]):
    """
    Notifica que el estado de una guía ha sido actualizado.
    """
    emitter.emit_to_all("estado_actualizado", {
        "guia_id": guia_id,
        "consecutivo": guia_data.get("consecutivo", ""),
        "nuevo_estado": nuevo_estado,
        "mensaje": f"Guía {nuevo_estado}"
    })
