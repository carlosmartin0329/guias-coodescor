import { useState, useRef, useEffect } from 'react';
import { useNotificaciones } from '../hooks/useNotificaciones';
import { useAuth } from '../contexts/AuthContext';
import './Notificaciones.css';

/**
 * Componente de campana de notificaciones.
 * Muestra el número de guías pendientes y permite ver el listado.
 */
export function CampanaNotificaciones() {
  const { user } = useAuth();
  const rol = user?.rol || '';
  const { hasNew, count, nuevasGuias, markAllAsRead, markGuiaAsRead } = useNotificaciones({ 
    userRol: rol 
  });
  const [showDropdown, setShowDropdown] = useState(false);
  
  const notificationRef = useRef(null);

  // Cerrar dropdown al hacer click fuera
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (notificationRef.current && !notificationRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!rol || ['publico'].includes(rol)) {
    return null; // No mostrar para público
  }

  const toggleDropdown = () => {
    setShowDropdown(prev => !prev);
    if (showDropdown) {
      markAllAsRead();
    }
  };

  const handleGuiaClick = (guia) => {
    markGuiaAsRead(guia.id);
    setShowDropdown(false);
    // Navegar a la guía
    window.location.href = `/guia/${guia.id}`;
  };

  // Determinar qué estados son pendientes para cada rol
  const getPendientesText = () => {
    const pending = {
      'administrativo': 'Guías pendientes de recepción',
      'cedis': 'Guías pendientes en CEDIS',
      'transportador': 'Guías en ruta',
      'ventas': 'Tus guías creadas',
      'admin': 'Todas las guías pendientes',
    };
    return pending[rol] || 'Notificaciones';
  };

  return (
    <div className="notificaciones-container" ref={notificationRef}>
      <button 
        className={`notificaciones-bell ${hasNew ? 'has-new' : ''}`} 
        onClick={toggleDropdown}
        aria-label={`Notificaciones: ${count} pendiente${count !== 1 ? 's' : ''}`}
        title={getPendientesText()}
      >
        🔔
        {count > 0 && (
          <span className="notificaciones-badge">{count}</span>
        )}
      </button>

      {showDropdown && (
        <div className="notificaciones-dropdown">
          <div className="notificaciones-header">
            <h4>{getPendientesText()}</h4>
            {nuevasGuias.length > 0 && (
              <button 
                className="notificaciones-mark-all"
                onClick={(e) => {
                  e.stopPropagation();
                  markAllAsRead();
                }}
              >
                Marcar todas como leídas
              </button>
            )}
          </div>
          
          <div className="notificaciones-list">
            {nuevasGuias.length === 0 ? (
              <div className="notificaciones-empty">
                <p>No hay notificaciones pendientes</p>
              </div>
            ) : (
              nuevasGuias.map((guia) => (
                <div 
                  key={guia.id}
                  className="notificacion-item"
                  onClick={() => handleGuiaClick(guia)}
                >
                  <div className="notificacion-content">
                    <div className="notificacion-title">
                      Guía #{guia.consecutivo}
                    </div>
                    <div className="notificacion-details">
                      <span className="notificacion-cliente">{guia.cliente}</span>
                      <span className={`notificacion-estado estado-${guia.estado?.toLowerCase()}`}>
                        {guia.estado}
                      </span>
                    </div>
                    <div className="notificacion-time">
                      {guia.creada_en}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Componente de alerta toast para notificaciones importantes.
 */
export function NotificacionToast({ message, type = 'info', onClose, duration = 10000, persistent = false }) {
  const [isVisible, setIsVisible] = useState(true);
  const [isClosing, setIsClosing] = useState(false);
  
  useEffect(() => {
    if (!persistent) {
      const timer = setTimeout(() => {
        setIsClosing(true);
        setTimeout(() => {
          setIsVisible(false);
          if (onClose) onClose();
        }, 500); // Esperar animación de cierre
      }, duration);
      
      return () => clearTimeout(timer);
    }
  }, [duration, onClose, persistent]);

  if (!isVisible) return null;

  return (
    <div className={`toast-notification toast-${type} ${isClosing ? 'toast-closing' : 'toast-visible'}`}>
      <div className="toast-content">
        <span className="toast-icon">
          {type === 'success' && '✅'}
          {type === 'error' && '❌'}
          {type === 'warning' && '⚠️'}
          {type === 'info' && '📬'}
        </span>
        <span className="toast-message">{message}</span>
        {persistent && (
          <span className="toast-persistent-badge">NUEVO</span>
        )}
        <button className="toast-close" onClick={() => {
          setIsClosing(true);
          setTimeout(() => {
            setIsVisible(false);
            if (onClose) onClose();
          }, 500);
        }}>
          ×
        </button>
      </div>
    </div>
  );
}

/**
 * Componente que muestra badges de notificación en la barra de navegación.
 */
export function NavbarNotificaciones() {
  const { user } = useAuth();
  const rol = user?.rol || '';
  
  if (!rol || ['publico', 'ventas'].includes(rol)) {
    return null;
  }
  
  return <CampanaNotificaciones />;
}
