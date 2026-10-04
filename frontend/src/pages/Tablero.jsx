import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useGuias } from '../contexts/GuiaContext';
import { useAuth } from '../contexts/AuthContext';
import * as guiasApi from '../api/guias';
import api from '../api';
import './Tablero.css';

export default function Tablero() {
  const { guias, conteo, cargando, error, listarGuias, cargarConteo } = useGuias();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [estado, setEstado] = useState('');

  useEffect(() => {
    cargarConteo();
    listarGuias();
  }, [cargarConteo, listarGuias]);

  const buscar = (e) => {
    e.preventDefault();
    listarGuias({ q, estado });
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
    } catch (err) {
      alert(err.error || 'Error al descargar load test');
    }
  };

  const irADetalle = (id) => navigate(`/guia/${id}`);

  return (
    <div className="tablero">
      <header className="tablero-header">
        <h1>Guías Coodescor</h1>
        <div className="tablero-usuario">
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
            <tr key={g.id} onClick={() => irADetalle(g.id)} className="clickable">
              <td>{g.id}</td>
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
