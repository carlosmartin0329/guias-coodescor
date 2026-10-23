import { useState, useRef, useEffect } from 'react';
import { useNotificaciones } from '../hooks/useNotificaciones';
import { useAuth } from '../contexts/AuthContext';
import './Notificaciones.css';

export function CampanaNotificaciones() {
  const { user } = useAuth();
  const rol = user?.rol || '';
  const { hasNew, count, nuevasGuias, markAllAsRead, markGuiaAsRead } = useNotificaciones({ 
    userRol: rol 
  });
  const [showDropdown, setShowDropdown] = useState(false);
  const notificationRef = useRef(null);

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
    return null;
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
    window.location.href = `/guia/${guia.id}`;
  };

  const getPendientesText = () => {
    const pending = {
      'administrativo': 'Guias pendientes de recepcion',
      'cedis': 'Guias pendientes en CEDIS',
      'transportador': 'Guias en ruta',
      'ventas': 'Tus guias creadas',
      'admin': 'Todas las guias pendientes',
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
                Marcar todas como leidas
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
                      Guia #{guia.consecutivo}
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

export function NotificacionToast({ message, type = 'info', onClose, duration = 15000 }) {
  const [isVisible, setIsVisible] = useState(true);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      if (onClose) onClose();
    }, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  if (!isVisible) return null;

  return (
    <div className={`toast-notification toast-${type}`}>
      <div className="toast-content">
        <span className="toast-icon">
          {type === 'success' && '✅'}
          {type === 'error' && '❌'}
          {type === 'warning' && '⚠️'}
          {type === 'info' && '📬'}
        </span>
        <span className="toast-message">{message}</span>
        <button className="toast-close" onClick={() => {
          setIsVisible(false);
          if (onClose) onClose();
        }}>
          ×
        </button>
      </div>
    </div>
  );
}

export function NavbarNotificaciones() {
  const { user } = useAuth();
  const rol = user?.rol || '';
  if (!rol || ['publico', 'ventas'].includes(rol)) {
    return null;
  }
  return <CampanaNotificaciones />;
}
