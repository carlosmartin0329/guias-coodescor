import { useEffect, useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useGuias } from '../contexts/GuiaContext';
import { useAuth } from '../contexts/AuthContext';
import { useNotificaciones } from '../hooks/useNotificaciones';
import * as guiasApi from '../api/guias';
import api from '../api';
import { CampanaNotificaciones } from '../components/Notificaciones';
import './Tablero.css';

export default function Tablero() {
  const { guias, conteo, cargando, error, listarGuias, cargarConteo } = useGuias();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [estado, setEstado] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(null);
  
  const { hasNew, count: notificationCount, fetchNuevasGuias, markAllAsRead } = useNotificaciones({
    userRol: user?.rol || '',
    pollingInterval: 5000
  });

  const refreshData = useCallback(async () => {
    try {
      await Promise.all([
        cargarConteo(),
        listarGuias({ q, estado }),
        fetchNuevasGuias()
      ]);
      setLastRefresh(new Date());
    } catch (err) {
      console.error('Error al refrescar:', err);
    }
  }, [cargarConteo, listarGuias, q, estado, fetchNuevasGuias]);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      refreshData();
    }, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshData]);

  useEffect(() => {
    if (hasNew) {
      refreshData();
    }
  }, [hasNew, refreshData]);

  const buscar = (e) => {
    e.preventDefault();
    listarGuias({ q, estado });
    alert('Ejecutado: busqueda realizada. Informacion cargada.');
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
      alert('Ejecutado: exportacion completada. Proceso finalizado y enviado.');
    } catch (err) {
      alert(err.error || 'Error al exportar');
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
      alert('Ejecutado: descarga de load test completada. Proceso finalizado.');
    } catch (err) {
      alert(err.error || 'Error al descargar load test');
    }
  };

  const irADetalle = (id) => navigate(`/guia/${id}`);

  const toggleAutoRefresh = () => {
    setAutoRefresh(prev => !prev);
    if (!autoRefresh) {
      refreshData();
    }
  };

  const getPendientesBadge = () => {
    if (!user) return null;
    const pendingStates = {
      'administrativo': ['CREADA'],
      'cedis': ['RECIBIDA_ADMIN', 'EN_CEDIS'],
      'transportador': ['EN_RUTA'],
      'ventas': ['CREADA', 'RECIBIDA_ADMIN', 'EN_CEDIS', 'EN_RUTA'],
      'admin': ['CREADA', 'RECIBIDA_ADMIN', 'EN_CEDIS', 'EN_RUTA'],
    };
    const states = pendingStates[user.rol] || [];
    const count = states.reduce((sum, state) => {
      const c = conteo.find(item => item.estado === state);
      return sum + (c?.total || 0);
    }, 0);
    const total = count + (hasNew ? 1 : 0);
    if (total === 0) return null;
    return (
      <span className="pendientes-badge" title={`Tienes ${total} guias pendientes`}>
        {total}
      </span>
    );
  };

  return (
    <div className="tablero">
      <header className="tablero-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h1>Guias Coodescor</h1>
          {getPendientesBadge()}
          <button 
            className={`btn-mini ${autoRefresh ? 'primario' : ''}`} 
            onClick={toggleAutoRefresh}
            title={autoRefresh ? 'Auto-refresh cada 5 segundos' : 'Auto-refresh desactivado'}
          >
            {autoRefresh ? 'Auto (5s)' : 'Manual'}
          </button>
        </div>
        
        <div className="tablero-usuario">
          <CampanaNotificaciones />
          <span>{user?.nombre || user?.usuario}</span>
          <button onClick={logout} className="btn-mini">Salir</button>
        </div>
      </header>

      <section className="conteo">
        {conteo.map((item) => (
          <div key={item.estado} className="chip-conteo">
            <strong>{item.total}</strong> {item.estado}
          </div>
        ))}
        {lastRefresh && (
          <div className="chip-conteo refresh-time">
            <small>Actualizado: {lastRefresh.toLocaleTimeString()}</small>
          </div>
        )}
      </section>

      <form className="filtros" onSubmit={buscar}>
        <input
          type="text"
          placeholder="Buscar por cliente, ciudad, documento..."
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
          <Link to="/nueva-guia" className="btn-mini primario">+ Nueva guia</Link>
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
            <tr key={g.id} onClick={() => irADetalle(g.id)} className="clickable">
              <td>{g.consecutivo || g.id}</td>
              <td>{g.cliente}</td>
              <td>{g.ciudad}</td>
              <td><span className={`chip ${g.estado?.toLowerCase()}`}>{g.estado}</span></td>
              <td>{g.creada_en ? new Date(g.creada_en).toLocaleDateString() : '-'}</td>
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
