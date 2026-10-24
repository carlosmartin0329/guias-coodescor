import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
  const { hasNew, count, nuevasGuias, markAllAsRead, markGuiaAsRead, error } = useNotificaciones();
  const [showDropdown, setShowDropdown] = useState(false);
  const navigate = useNavigate();
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
  };

  const handleGuiaClick = (guia) => {
    markGuiaAsRead(guia.id);
    setShowDropdown(false);
    navigate(`/guia/${guia.guia_id}`);
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
        aria-expanded={showDropdown}
        aria-controls="notificaciones-dropdown"
        aria-label={`Notificaciones: ${count} pendiente${count !== 1 ? 's' : ''}`}
        title={getPendientesText()}
      >
        🔔
        {count > 0 && (
          <span className="notificaciones-badge">{count}</span>
        )}
      </button>

      {showDropdown && (
        <div className="notificaciones-dropdown" id="notificaciones-dropdown">
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
                <button
                  key={guia.id}
                  className="notificacion-item"
                  onClick={() => handleGuiaClick(guia)}
                >
                  <div className="notificacion-content">
                    <div className="notificacion-title">
                      Guía #{guia.consecutivo || guia.guia_id}
                    </div>
                    <div className="notificacion-details">
                      <span className="notificacion-cliente">{guia.cliente}</span>
                      <span className={`notificacion-estado ${guia.estado?.toLowerCase()}`}>
                        {guia.estado}
                      </span>
                    </div>
                    <div className="notificacion-time">{guia.mensaje} · {guia.ciudad}</div>
                  </div>
                </button>
              ))
            )}
          </div>
          {error && <div className="notificaciones-error">Sin conexión: no se pudo actualizar la lista.</div>}
        </div>
      )}
    </div>
  );
}

/**
 * Componente de alerta toast para notificaciones importantes.
 */
export function NotificacionToast({ message, type = 'info', onClose, duration = 5000 }) {
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
          {type === 'info' && 'ℹ️'}
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

/**
 * Componente que muestra badges de notificación en la barra de navegación.
 */
export function NavbarNotificaciones() {
  const { user } = useAuth();
  const rol = user?.rol || '';
  
  if (!rol || ['publico'].includes(rol)) {
    return null;
  }
  
  return <CampanaNotificaciones />;
}
