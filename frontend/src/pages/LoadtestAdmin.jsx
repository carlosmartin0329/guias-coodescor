import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as guiasApi from '../api/guias';
import './LoadtestAdmin.css';

export default function LoadtestAdmin() {
  const { user, logout } = useAuth();
  const [resumen, setResumen] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const cargar = async () => {
      setCargando(true);
      setError(null);
      try {
        const data = await guiasApi.loadtestAdmin();
        setResumen(data);
      } catch (err) {
        setError(err.error || 'Error al cargar el reporte');
      } finally {
        setCargando(false);
      }
    };
    cargar();
  }, []);

  if (cargando) return <div className="container">Cargando…</div>;
  if (error) return <div className="container error">{error}</div>;
  if (!resumen) return <div className="container">Sin datos de load test</div>;

  const { guias_creadas, total_creacion_ms, avg_creacion_ms, p95_creacion_ms, max_creacion_ms,
          eventos_totales, total_eventos_ms, avg_eventos_ms, p95_eventos_ms, max_eventos_ms,
          timestamp, memoria_mb, node_version } = resumen;

  return (
    <div className="loadtest-admin">
      <header className="loadtest-header">
        <div>
          <Link to="/tablero" className="btn-mini">← Volver</Link>
          <h1>Reporte Load Test</h1>
        </div>
        <div className="loadtest-usuario">
          <span>{user?.nombre || user?.usuario}</span>
          <button onClick={logout} className="btn-mini">Salir</button>
        </div>
      </header>

      <section className="card">
        <h2>Resumen</h2>
        <div className="grid">
          <div><strong>Guías creadas:</strong> {guias_creadas}</div>
          <div><strong>Total creación (ms):</strong> {total_creacion_ms}</div>
          <div><strong>Promedio creación (ms):</strong> {avg_creacion_ms}</div>
          <div><strong>P95 creación (ms):</strong> {p95_creacion_ms}</div>
          <div><strong>Máx. creación (ms):</strong> {max_creacion_ms}</div>
          <div><strong>Eventos totales:</strong> {eventos_totales}</div>
          <div><strong>Total eventos (ms):</strong> {total_eventos_ms}</div>
          <div><strong>Promedio eventos (ms):</strong> {avg_eventos_ms}</div>
          <div><strong>P95 eventos (ms):</strong> {p95_eventos_ms}</div>
          <div><strong>Máx. eventos (ms):</strong> {max_eventos_ms}</div>
          <div><strong>Memoria (MB):</strong> {memoria_mb}</div>
          <div><strong>Node.js:</strong> {node_version}</div>
          <div><strong>Timestamp:</strong> {timestamp}</div>
        </div>
      </section>

      <section className="card">
        <h2>Descargas</h2>
        <div className="acciones">
          <button onClick={descargarCSV}>CSV</button>
          <button onClick={descargarXLSX}>XLSX</button>
        </div>
      </section>
    </div>
  );

  function descargarCSV() {
    guiasApi.loadtestCSV()
      .then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `loadtest-${new Date().toISOString().slice(0,10)}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
      })
      .catch((err) => alert(err.error || 'Error al descargar CSV'));
  }

  function descargarXLSX() {
    guiasApi.loadtestXLSX()
      .then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `loadtest-${new Date().toISOString().slice(0,10)}.xlsx`;
        a.click();
        window.URL.revokeObjectURL(url);
      })
      .catch((err) => alert(err.error || 'Error al descargar XLSX'));
  }
}