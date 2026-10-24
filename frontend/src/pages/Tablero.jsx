import { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useGuias } from '../contexts/GuiaContext';
import { useAuth } from '../contexts/AuthContext';
import { useNotificaciones } from '../hooks/useNotificaciones';
import * as guiasApi from '../api/guias';
import { CampanaNotificaciones } from '../components/Notificaciones';
import './Tablero.css';

export default function Tablero() {
  const { guias, conteo, error, listarGuias, cargarConteo } = useGuias();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [estado, setEstado] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(null);
  const refreshingRef = useRef(false);
  
  // Hook de notificaciones
  const { getPendientesCount } = useNotificaciones();

  // Función para recargar datos
  const refreshData = useCallback(async () => {
    if (refreshingRef.current) return;
    refreshingRef.current = true;
    try {
      await Promise.all([
        cargarConteo(),
        listarGuias({ q, estado })
      ]);
      setLastRefresh(new Date());
    } catch (err) {
      console.error('Error al refrescar:', err);
    } finally {
      refreshingRef.current = false;
    }
  }, [cargarConteo, listarGuias, q, estado]);

  // Cargar datos iniciales
  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // Actualizar el tablero cada 2 segundos sin solapar solicitudes.
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(() => {
      if (!document.hidden) refreshData();
    }, 2000);

    const handleVisibilityChange = () => {
      if (!document.hidden) refreshData();
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [autoRefresh, refreshData]);

  const buscar = (e) => {
    e.preventDefault();
    listarGuias({ q, estado });
    alert('✅ Ejecutado: búsqueda realizada. Información cargada.');
  };

  const exportarCSV = async () => {
    try {
      const blob = await guiasApi.exportarGuias({ q, estado });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `guias-${new Date().toISOString().slice(0,10)}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
      alert('✅ Ejecutado: exportación completada. Proceso finalizado y enviado.');
    } catch (err) {
      alert(`❌ Error: ${err.error || 'Error al exportar'}`);
    }
  };

  const descargarLoadtest = async () => {
    try {
      const blob = await guiasApi.loadtestCSV();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `loadtest-${new Date().toISOString().slice(0,10)}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
      alert('✅ Ejecutado: descarga de load test completada. Proceso finalizado.');
    } catch (err) {
      alert(`❌ Error: ${err.error || 'Error al descargar load test'}`);
    }
  };

  const irADetalle = (id) => navigate(`/guia/${id}`);

  const toggleAutoRefresh = () => {
    setAutoRefresh(prev => !prev);
    if (!autoRefresh) {
      refreshData(); // Refrescar inmediatamente al activar
    }
  };

  // Obtener badge de notificaciones según rol
  const getPendientesBadge = () => {
    if (!user) return null;
    
    const total = getPendientesCount(user.rol);
    
    if (total === 0) return null;
    
    return (
      <span 
        className="pendientes-badge" 
        title={`Tienes ${total} guía${total !== 1 ? 's' : ''} pendiente${total !== 1 ? 's' : ''}`}
      >
        {total}
      </span>
    );
  };

  return (
    <div className="tablero">
      <header className="tablero-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h1>Guías Coodescor</h1>
          {getPendientesBadge()}
          <button 
            className={`btn-mini ${autoRefresh ? 'primario' : ''}`} 
            onClick={toggleAutoRefresh}
            title={autoRefresh ? 'Auto-refresh activado (2s)' : 'Auto-refresh desactivado'}
          >
            {autoRefresh ? '🔄 Auto · 2 s' : '⏸️ Manual'}
          </button>
        </div>
        
        <div className="tablero-usuario">
          <CampanaNotificaciones />
          <span>{user?.nombre || user?.usuario}</span>
          <button onClick={logout} className="btn-mini">Salir</button>
        </div>
      </header>

      <section className="conteo" aria-label="Guías por estado" aria-live="polite">
        {conteo.map((item) => (
          <div key={item.estado} className="chip-conteo">
            <strong>{item.n ?? item.total ?? 0}</strong> {item.estado}
          </div>
        ))}
        {lastRefresh && (
          <div className="chip-conteo refresh-time">
            <small>Última actualización: {lastRefresh.toLocaleTimeString()}</small>
          </div>
        )}
      </section>

      <form className="filtros" onSubmit={buscar}>
        <input
          type="text"
          placeholder="Buscar por cliente, ciudad, documento…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          <option value="CREADA">Creada</option>
          <option value="EN_CEDIS">En CEDIS</option>
          <option value="EN_RUTA">En ruta</option>
          <option value="ENTREGADA">Entregada</option>
          <option value="ANULADA">Anulada</option>
        </select>
        <button type="submit">Buscar</button>
        {user?.rol === 'ventas' && (
          <Link to="/nueva-guia" className="btn-mini primario">+ Nueva guía</Link>
        )}
        {['admin', 'administrativo'].includes(user?.rol) && (
          <button onClick={exportarCSV} className="btn-mini">Exportar CSV</button>
        )}
        {user?.rol === 'admin' && (
          <button onClick={descargarLoadtest} className="btn-mini">Load Test CSV</button>
        )}
      </form>

      {error && <div className="error">{error}</div>}

      <table className="tabla">
        <thead>
          <tr>
            <th>#</th>
            <th>Cliente</th>
            <th>Ciudad</th>
            <th>Estado</th>
            <th>Creada</th>
          </tr>
        </thead>
        <tbody>
          {guias.map((g) => (
            <tr
              key={g.id}
              onClick={() => irADetalle(g.id)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  irADetalle(g.id);
                }
              }}
              className="clickable"
              tabIndex={0}
              aria-label={`Abrir guía ${g.consecutivo || g.id}`}
            >
              <td data-label="Guía">{g.consecutivo || g.id}</td>
              <td data-label="Cliente">{g.cliente}</td>
              <td data-label="Ciudad">{g.ciudad}</td>
              <td data-label="Estado"><span className={`chip ${g.estado?.toLowerCase()}`}>{g.estado}</span></td>
              <td data-label="Creada">{g.creada_en ? new Date(g.creada_en).toLocaleDateString() : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {user?.rol === 'admin' && (
        <div className="admin-links">
          <Link to="/admin/db">Base de datos</Link>
        </div>
      )}
    </div>
  );
}
