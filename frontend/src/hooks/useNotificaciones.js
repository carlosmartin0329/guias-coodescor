import { createContext, createElement, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

const NotificacionesContext = createContext(null);

const ESTADOS_PENDIENTES = {
  administrativo: ['CREADA'],
  cedis: ['RECIBIDA_ADMIN', 'EN_CEDIS'],
  transportador: ['EN_CEDIS', 'EN_RUTA'],
  ventas: ['CREADA', 'RECIBIDA_ADMIN', 'EN_CEDIS', 'EN_RUTA'],
  admin: ['CREADA', 'RECIBIDA_ADMIN', 'EN_CEDIS', 'EN_RUTA'],
};

function leerNotificacionesLeidas(storageKey) {
  if (!storageKey || typeof window === 'undefined') return new Set();
  try {
    return new Set(JSON.parse(window.localStorage.getItem(storageKey) || '[]'));
  } catch (error) {
    console.warn('No se pudieron leer notificaciones guardadas:', error);
    return new Set();
  }
}

function guardarNotificacionesLeidas(storageKey, ids) {
  if (!storageKey || typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(storageKey, JSON.stringify([...ids].slice(-300)));
  } catch (error) {
    console.warn('No se pudieron guardar notificaciones leídas:', error);
  }
}

function useNotificacionesState({ userId, userRol, pollingInterval = 2000 }) {
  const [nuevasGuias, setNuevasGuias] = useState([]);
  const [conteoEstados, setConteoEstados] = useState({});
  const [hasNew, setHasNew] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const [toastNotification, setToastNotification] = useState(null);
  const lastSeenIdsRef = useRef(new Set());
  const currentNotificationsRef = useRef([]);
  const readIdsRef = useRef(new Set());
  const initializedRef = useRef(false);
  const pollingTimeoutRef = useRef(null);
  const pollingActiveRef = useRef(false);
  const storageKey = userId && userRol
    ? `guias.notificaciones.leidas:${userId}:${userRol}`
    : '';

  const playNotificationSound = useCallback(() => {
    try {
      const AudioContextApi = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextApi) return;
      const audioContext = new AudioContextApi();
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      oscillator.connect(gain);
      gain.connect(audioContext.destination);
      oscillator.frequency.value = 880;
      gain.gain.value = 0.12;
      oscillator.start();
      oscillator.stop(audioContext.currentTime + 0.18);
      oscillator.onended = () => audioContext.close();
    } catch (error) {
      console.warn('Web Audio API no disponible:', error);
    }
  }, []);

  const showBrowserNotification = useCallback((title, body, notificationId) => {
    try {
      if (!('Notification' in window) || Notification.permission !== 'granted') return;
      new Notification(title, {
        body,
        icon: '/static/icons/icon-192x192.png',
        tag: notificationId,
      });
    } catch (error) {
      console.warn('No se pudo mostrar la notificación del navegador:', error);
    }
  }, []);

  useEffect(() => {
    readIdsRef.current = leerNotificacionesLeidas(storageKey);
  }, [storageKey]);

  useEffect(() => {
    if (!userId || !userRol || !('Notification' in window)) return;
    if (Notification.permission === 'default') {
      Notification.requestPermission().catch((permissionError) => {
        console.warn('No se pudo solicitar permiso de notificaciones:', permissionError);
      });
    }
  }, [userId, userRol]);

  const fetchNuevasGuias = useCallback(async () => {
    if (!userId || !userRol) return 0;
    try {
      const response = await fetch('/api/notificaciones/pendientes', {
        credentials: 'include',
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!data.ok) throw new Error(data.error || 'Respuesta de notificaciones inválida');

      const recibidas = data.notificaciones || [];
      const nuevas = recibidas.filter((item) => !readIdsRef.current.has(item.id));
      const recienLlegadas = nuevas.filter((item) => !lastSeenIdsRef.current.has(item.id));

      if (initializedRef.current && recienLlegadas.length > 0) {
        const primera = recienLlegadas[0];
        const titulo = `Guía #${primera.consecutivo || primera.guia_id} pendiente`;
        const detalle = `${primera.estado} · ${primera.cliente || 'Sin cliente'}`;
        setToastNotification(primera);
        playNotificationSound();
        showBrowserNotification(titulo, detalle, primera.id);
      }

      lastSeenIdsRef.current = new Set(recibidas.map((item) => item.id));
      initializedRef.current = true;
      currentNotificationsRef.current = nuevas;
      setNuevasGuias(nuevas);
      setHasNew(nuevas.length > 0);
      setConteoEstados(data.estados || {});
      setError(null);
      setIsConnected(true);
      return nuevas.length;
    } catch (fetchError) {
      setError(fetchError.message);
      setIsConnected(false);
      console.error('Error al actualizar notificaciones:', fetchError);
      return 0;
    }
  }, [userId, userRol, playNotificationSound, showBrowserNotification]);

  const stopPolling = useCallback(() => {
    pollingActiveRef.current = false;
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    stopPolling();
    if (!userId || !userRol) return;
    pollingActiveRef.current = true;
    const poll = async () => {
      await fetchNuevasGuias();
      if (pollingActiveRef.current) {
        pollingTimeoutRef.current = setTimeout(poll, pollingInterval);
      }
    };
    void poll();
  }, [fetchNuevasGuias, pollingInterval, stopPolling, userId, userRol]);

  useEffect(() => {
    startPolling();
    return stopPolling;
  }, [startPolling, stopPolling]);

  const markAllAsRead = useCallback(() => {
    const ids = new Set(readIdsRef.current);
    currentNotificationsRef.current.forEach((item) => ids.add(item.id));
    readIdsRef.current = ids;
    guardarNotificacionesLeidas(storageKey, ids);
    currentNotificationsRef.current = [];
    setNuevasGuias([]);
    setHasNew(false);
    setToastNotification(null);
  }, [storageKey]);

  const markGuiaAsRead = useCallback((notificationId) => {
    const ids = new Set(readIdsRef.current);
    ids.add(notificationId);
    readIdsRef.current = ids;
    guardarNotificacionesLeidas(storageKey, ids);
    const remaining = currentNotificationsRef.current.filter(
      (item) => item.id !== notificationId,
    );
    currentNotificationsRef.current = remaining;
    setNuevasGuias(remaining);
    setHasNew(remaining.length > 0);
    setToastNotification((current) => (
      current?.id === notificationId ? null : current
    ));
  }, [storageKey]);

  const getPendientesCount = useCallback((rol) => (
    (ESTADOS_PENDIENTES[rol] || []).reduce(
      (total, estado) => total + (conteoEstados[estado] || 0),
      0,
    )
  ), [conteoEstados]);
  const dismissToast = useCallback(() => setToastNotification(null), []);

  const value = {
    nuevasGuias,
    conteoEstados,
    hasNew,
    count: nuevasGuias.length,
    isConnected,
    error,
    toastNotification,
    dismissToast,
    startPolling,
    stopPolling,
    markAllAsRead,
    markGuiaAsRead,
    getPendientesCount,
    fetchNuevasGuias,
  };

  return value;
}

export function NotificacionesProvider({ children }) {
  const { user } = useAuth();
  const userId = user?.id;
  const userRol = user?.rol || '';
  const key = userId && userRol ? `${userId}:${userRol}` : 'sin-sesion';

  return createElement(
    NotificacionesSession,
    { key, userId, userRol },
    children,
  );
}

function NotificacionesSession({ children, userId, userRol }) {
  const notifications = useNotificacionesState({
    userId,
    userRol,
  });

  return createElement(NotificacionesContext.Provider, { value: notifications }, children);
}

export function useNotificaciones() {
  const context = useContext(NotificacionesContext);
  if (!context) {
    throw new Error('useNotificaciones debe usarse dentro de NotificacionesProvider');
  }
  return context;
}

export function useNotificacionesBadge(rol) {
  const { hasNew, getPendientesCount } = useNotificaciones();
  return { hasNew, count: getPendientesCount(rol) };
}
