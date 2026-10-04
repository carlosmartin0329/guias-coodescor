import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import './AdminDB.css';

export default function AdminDB() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [bases, setBases] = useState([]);
  const [base, setBase] = useState('guias');
  const [tablas, setTablas] = useState([]);
  const [tabla, setTabla] = useState('');
  const [filas, setFilas] = useState([]);
  const [esquema, setEsquema] = useState([]);
  const [pagina, setPagina] = useState(1);
  const [totalPaginas, setTotalPaginas] = useState(1);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);
  const [respaldos, setRespaldos] = useState([]);
  const [sql, setSql] = useState('');
  const [sqlModo, setSqlModo] = useState('0');
  const [sqlConfirmar, setSqlConfirmar] = useState(false);
  const [sqlResultado, setSqlResultado] = useState(null);
  const [nuevaFila, setNuevaFila] = useState({});
  const [editarFila, setEditarFila] = useState(null);

  useEffect(() => {
    cargarBases();
  }, []);

  const cargarBases = async () => {
    setCargando(true);
    setError(null);
    try {
      const data = await api.get('/admin/db/bases');
      setBases(data.bases || []);
    } catch (err) {
      setError(err.error);
    } finally {
      setCargando(false);
    }
  };

  const cargarTablas = async (b) => {
    setBase(b);
    setTabla('');
    setFilas([]);
    setEsquema([]);
    setCargando(true);
    setError(null);
    try {
      const [t, r] = await Promise.all([
        api.get(`/admin/db/tablas?base=${b}`),
        api.get(`/admin/db/respaldos?base=${b}`),
      ]);
      setTablas(t.tablas || []);
      setRespaldos(r.respaldos || []);
    } catch (err) {
      setError(err.error);
    } finally {
      setCargando(false);
    }
  };

  const cargarFilas = async (t, pag = 1) => {
    setTabla(t);
    setFilas([]);
    setEsquema([]);
    setPagina(pag);
    setCargando(true);
    setError(null);
    try {
      const [f, e] = await Promise.all([
        api.get(`/admin/db/filas?base=${base}&tabla=${t}&pagina=${pag}&page_size=50`),
        api.get(`/admin/db/esquema?base=${base}&tabla=${t}`),
      ]);
      setFilas(f.datos?.filas || []);
      setEsquema(e.esquema?.columnas || []);
      setTotalPaginas(f.datos?.total_paginas || 1);
    } catch (err) {
      setError(err.error);
    } finally {
      setCargando(false);
    }
  };

  const crearFila = async () => {
    try {
      await api.post(`/admin/db/filas?base=${base}&tabla=${tabla}`, { datos: nuevaFila });
      setNuevaFila({});
      cargarFilas(tabla, pagina);
    } catch (err) {
      setError(err.error);
    }
  };

  const actualizarFila = async (pkValor) => {
    try {
      await api.post(`/admin/db/actualizar?base=${base}&tabla=${tabla}`, {
        pk: esquema.find((c) => c.pk)?.nombre,
        pk_valor: pkValor,
        datos: editarFila,
      });
      setEditarFila(null);
      cargarFilas(tabla, pagina);
    } catch (err) {
      setError(err.error);
    }
  };

  const eliminarFila = async (pkValor) => {
    if (!confirm('¿Eliminar esta fila?')) return;
    try {
      await api.delete(`/admin/db/filas?base=${base}&tabla=${tabla}`, {
        data: { pk: esquema.find((c) => c.pk)?.nombre, pk_valor: pkValor },
      });
      cargarFilas(tabla, pagina);
    } catch (err) {
      setError(err.error);
    }
  };

  const ejecutarSQL = async () => {
    setError(null);
    try {
      const res = await api.post('/admin/db/consulta', {
        base,
        sql,
        escritura: sqlModo === '1',
        confirmar: sqlModo === '1' && sqlConfirmar,
      });
      setSqlResultado(res);
    } catch (err) {
      setError(err.error);
    }
  };

  const crearRespaldo = async () => {
    try {
      await api.post('/admin/db/respaldo/crear', { base, motivo: 'manual' });
      cargarRespaldos();
    } catch (err) {
      setError(err.error);
    }
  };

  const restaurarRespaldo = async (archivo) => {
    if (!confirm('¿Restaurar este respaldo? Se guardará el estado actual.')) return;
    try {
      await api.post('/admin/db/respaldo/restaurar', { base, archivo });
      alert('Respaldo restaurado. Reinicia el servidor.');
    } catch (err) {
      setError(err.error);
    }
  };

  const eliminarRespaldo = async (archivo) => {
    if (!confirm('¿Eliminar este respaldo?')) return;
    try {
      await api.delete(`/admin/db/respaldo?base=${base}&archivo=${encodeURIComponent(archivo)}`);
      cargarRespaldos();
    } catch (err) {
      setError(err.error);
    }
  };

  return (
    <div className="admin-db">
      <header className="admin-db-header">
        <div>
          <Link to="/tablero" className="btn-mini">← Volver</Link>
          <h1>Base de datos</h1>
        </div>
        <div className="admin-db-usuario">
          <span>{user?.nombre || user?.usuario}</span>
          <button onClick={logout} className="btn-mini">Salir</button>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <section className="card">
        <h2>Bases de datos</h2>
        <div className="bases">
          {bases.map((b) => (
            <button key={b.nombre} className={`btn ${base === b.nombre ? 'primario' : ''}`} onClick={() => cargarTablas(b.nombre)}>
              {b.nombre}
            </button>
          ))}
        </div>
      </section>

      {tablas.length > 0 && (
        <section className="card">
          <h2>Tablas</h2>
          <div className="tablas">
            {tablas.map((t) => (
              <button key={t.nombre} className={`btn ${tabla === t.nombre ? 'primario' : ''}`} onClick={() => cargarFilas(t.nombre)}>
                {t.nombre} ({t.filas})
              </button>
            ))}
          </div>
        </section>
      )}

      {esquema.length > 0 && (
        <section className="card">
          <h2>Esquema: {tabla}</h2>
          <table className="tabla">
            <thead>
              <tr>
                <th>Columna</th>
                <th>Tipo</th>
                <th>Nulo</th>
                <th>PK</th>
                <th>Sensible</th>
              </tr>
            </thead>
            <tbody>
              {esquema.map((col) => (
                <tr key={col.nombre}>
                  <td>{col.nombre}</td>
                  <td>{col.tipo}</td>
                  <td>{col.no_nulo ? 'NO' : 'Sí'}</td>
                  <td>{col.pk ? '✓' : ''}</td>
                  <td>{col.sensible ? '🔒' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {filas.length > 0 && (
        <section className="card">
          <h2>Filas: {tabla}</h2>
          <div className="tbl-wrap">
            <table className="tabla">
              <thead>
                <tr>
                  {esquema.map((col) => (
                    <th key={col.nombre}>{col.nombre}</th>
                  ))}
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filas.map((fila, i) => (
                  <tr key={i}>
                    {esquema.map((col) => (
                      <td key={col.nombre}>{col.sensible ? '••••••' : String(fila[col.nombre] ?? '')}</td>
                    ))}
                    <td>
                      <button className="btn-mini" onClick={() => setEditarFila(fila)}>Editar</button>
                      <button className="btn-mini peligro" onClick={() => eliminarFila(fila[esquema.find((c) => c.pk)?.nombre])}>Eliminar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="paginacion">
            <button disabled={pagina <= 1} onClick={() => cargarFilas(tabla, pagina - 1)}>← Anterior</button>
            <span>Página {pagina} de {totalPaginas}</span>
            <button disabled={pagina >= totalPaginas} onClick={() => cargarFilas(tabla, pagina + 1)}>Siguiente →</button>
          </div>
        </section>
      )}

      {editarFila && (
        <section className="card">
          <h2>Editar fila</h2>
          {esquema.map((col) => (
            <label key={col.nombre}>
              {col.nombre}
              <input
                disabled={col.pk || col.sensible}
                value={editarFila[col.nombre] ?? ''}
                onChange={(e) => setEditarFila({ ...editarFila, [col.nombre]: e.target.value })}
              />
            </label>
          ))}
          <div className="acciones">
            <button onClick={() => actualizarFila(editarFila[esquema.find((c) => c.pk)?.nombre])}>Guardar</button>
            <button className="peligro" onClick={() => setEditarFila(null)}>Cancelar</button>
          </div>
        </section>
      )}

      {tabla && (
        <section className="card">
          <h2>Nueva fila en {tabla}</h2>
          {esquema.filter((c) => !c.pk && !c.sensible).map((col) => (
            <label key={col.nombre}>
              {col.nombre}
              <input
                value={nuevaFila[col.nombre] ?? ''}
                onChange={(e) => setNuevaFila({ ...nuevaFila, [col.nombre]: e.target.value })}
              />
            </label>
          ))}
          <button onClick={crearFila}>Insertar</button>
        </section>
      )}

      <section className="card">
        <h2>Consulta SQL</h2>
        <textarea
          value={sql}
          onChange={(e) => setSql(e.target.value)}
          placeholder="SELECT * FROM guias WHERE estado = 'CREADA'"
          rows={4}
        />
        <div className="sql-controls">
          <select value={sqlModo} onChange={(e) => setSqlModo(e.target.value)}>
            <option value="0">Solo lectura</option>
            <option value="1">Escritura</option>
          </select>
          {sqlModo === '1' && (
            <label className="check">
              <input type="checkbox" checked={sqlConfirmar} onChange={(e) => setSqlConfirmar(e.target.checked)} />
              Confirmo que esta consulta modifica la base
            </label>
          )}
          <button onClick={ejecutarSQL}>Ejecutar</button>
        </div>
        {sqlResultado && (
          <div className="sql-result">
            <pre>{JSON.stringify(sqlResultado, null, 2)}</pre>
          </div>
        )}
      </section>

      <section className="card">
        <h2>Respaldos</h2>
        <button onClick={crearRespaldo}>Crear respaldo</button>
        <div className="respaldos-lista">
          {respaldos.map((r) => (
            <div key={r.archivo} className="respaldo-item">
              <span>{r.archivo}</span>
              <button onClick={() => window.open(`/api/admin/db/respaldo/descargar?archivo=${encodeURIComponent(r.archivo)}`)}>Descargar</button>
              <button onClick={() => restaurarRespaldo(r.archivo)}>Restaurar</button>
              <button className="peligro" onClick={() => eliminarRespaldo(r.archivo)}>Eliminar</button>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <h2>Mantenimiento</h2>
        <div className="mantenimiento">
          <button onClick={async () => { await api.post('/admin/db/mantenimiento', { base, accion: 'vacuum' }); alert('VACUUM ejecutado'); }}>VACUUM</button>
          <button onClick={async () => { await api.post('/admin/db/mantenimiento', { base, accion: 'analyze' }); alert('ANALYZE ejecutado'); }}>ANALYZE</button>
          <button onClick={async () => { await api.post('/admin/db/mantenimiento', { base, accion: 'optimize' }); alert('OPTIMIZE ejecutado'); }}>OPTIMIZE</button>
        </div>
      </section>

      <section className="card">
        <h2>Migraciones</h2>
        <button onClick={async () => { await api.post('/admin/db/migraciones/aplicar'); alert('Migraciones aplicadas'); cargarBases(); }}>Aplicar migraciones pendientes</button>
      </section>
    </div>
  );
}
