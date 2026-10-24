import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import * as guiasApi from '../api/guias';
import { useAuth } from '../contexts/AuthContext';
import { formatInvoiceNumbers } from '../utils/format';

const EVENTOS_CON_FIRMA = new Set([
  'recepcion_admin', 'control_cedis', 'entrega_transporte', 'entrega_cliente',
]);
const TITULOS = {
  recepcion_admin: 'Recepción administrativa',
  control_cedis: 'Control CEDIS',
  entrega_transporte: 'Entrega a transportador',
  entrega_cliente: 'Entrega al cliente',
  anular: 'Anular guía',
  editar_guia: 'Editar datos de la guía',
};

function FirmaCanvas({ canvasRef }) {
  const dibujando = useRef(false);
  const ultimo = useRef({ x: 0, y: 0 });

  const posicion = (evento) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const punto = evento.touches ? evento.touches[0] : evento;
    return {
      x: punto.clientX - rect.left,
      y: punto.clientY - rect.top,
    };
  };

  const iniciar = (evento) => {
    evento.preventDefault();
    dibujando.current = true;
    ultimo.current = posicion(evento);
  };
  const mover = (evento) => {
    if (!dibujando.current || !canvasRef.current) return;
    evento.preventDefault();
    const ctx = canvasRef.current.getContext('2d');
    const p = posicion(evento);
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(ultimo.current.x, ultimo.current.y);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    ultimo.current = p;
  };
  const terminar = () => { dibujando.current = false; };

  return (
    <canvas
      ref={canvasRef}
      width={600}
      height={180}
      style={{ width: '100%', maxWidth: 600, height: 180, border: '1px dashed #94a3b8', borderRadius: 8, background: '#fff', touchAction: 'none' }}
      onMouseDown={iniciar}
      onMouseMove={mover}
      onMouseUp={terminar}
      onMouseLeave={terminar}
      onTouchStart={iniciar}
      onTouchMove={mover}
      onTouchEnd={terminar}
    />
  );
}

export default function DetalleGuia() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [guia, setGuia] = useState(null);
  const [eventos, setEventos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [accion, setAccion] = useState(null);
  const [form, setForm] = useState({});
  const [enviando, setEnviando] = useState(false);
  const canvasRef = useRef(null);
  const firmaPracticanteRef = useRef(null);

  const cargar = async () => {
    const [detalle, evs] = await Promise.all([
      guiasApi.guiasDetalle(id),
      guiasApi.guiasEventos(id),
    ]);
    setGuia(detalle.guia);
    setEventos(evs.eventos || []);
  };

  useEffect(() => {
    let cancelado = false;
    const cargarInicial = async () => {
      setCargando(true);
      setError(null);
      try {
        const [detalle, evs] = await Promise.all([
          guiasApi.guiasDetalle(id),
          guiasApi.guiasEventos(id),
        ]);
        if (!cancelado) {
          setGuia(detalle.guia);
          setEventos(evs.eventos || []);
        }
      } catch (err) {
        if (!cancelado) setError(err.error || 'Error al cargar la guía');
      } finally {
        if (!cancelado) setCargando(false);
      }
    };
    cargarInicial();
    return () => { cancelado = true; };
  }, [id]);

  const abrir = (tipo) => {
    setError(null);
    setForm({});
    setAccion(tipo);
    // Limpia los canvas cuando se monta el panel de firma.
    window.setTimeout(() => {
      const c = canvasRef.current;
      if (c) c.getContext('2d').clearRect(0, 0, c.width, c.height);
      const cp = firmaPracticanteRef.current;
      if (cp) cp.getContext('2d').clearRect(0, 0, cp.width, cp.height);
    }, 0);
  };

  const limpiarFirma = () => {
    const c = canvasRef.current;
    if (c) c.getContext('2d').clearRect(0, 0, c.width, c.height);
  };

  const limpiarFirmaPracticante = () => {
    const c = firmaPracticanteRef.current;
    if (c) c.getContext('2d').clearRect(0, 0, c.width, c.height);
  };

  const firmaActual = () => {
    const c = canvasRef.current;
    if (!c) return '';
    const data = c.toDataURL('image/png');
    // Un canvas vacío produce una imagen casi constante (~1 KB). Se exige que
    // el usuario dibuje algo antes de enviar la firma.
    return data && data.length > 1200 ? data : '';
  };

  const firmaPracticanteActual = () => {
    const c = firmaPracticanteRef.current;
    if (!c) return '';
    const data = c.toDataURL('image/png');
    return data && data.length > 1200 ? data : '';
  };

  const cambiar = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((f) => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
  };

  const enviarAccion = async () => {
    if (!accion) return;
    setEnviando(true);
    setError(null);
    try {
      if (accion === 'editar_guia') {
        await guiasApi.guiasEditar(id, form);
      } else if (accion === 'anular') {
        if (!form.motivo?.trim()) throw { error: 'Indique el motivo de la anulación' };
        await guiasApi.guiasEvento(id, 'anular', { motivo: form.motivo });
      } else {
        const payload = { ...form };
        if (EVENTOS_CON_FIRMA.has(accion)) {
          const firma = firmaActual();
          if (!firma) throw { error: 'Dibuja la firma en el recuadro antes de continuar' };
          payload.firma = firma;
          if (accion === 'control_cedis') {
            payload.cedis_funcionario = form.cedis_funcionario || user?.nombre || user?.usuario;
            if (payload.cedis_funcionario === 'PRACTICANTE_PASANTE') {
              if (!(form.cedis_funcionario_practicante || '').trim()) {
                throw { error: 'Escribe el nombre del practicante / pasante' };
              }
              const firmaPrac = firmaPracticanteActual();
              if (!firmaPrac) {
                throw { error: 'Dibuja la firma del practicante / pasante' };
              }
              payload.cedis_funcionario_practicante = form.cedis_funcionario_practicante.trim();
              payload.firma_practicante = firmaPrac;
            }
            payload.cajas = Number(form.cajas || 0);
            payload.bolsas = Number(form.bolsas || 0);
            payload.cayvas = Number(form.cayvas || 0);
            payload.sobres = Number(form.sobres || 0);
            payload.vehiculo_cumple = form.vehiculo_cumple ? 'si' : 'no';
          }
        }
        await guiasApi.guiasEvento(id, accion, payload);
      }
      await cargar();
      setAccion(null);
      window.alert(`✅ ${TITULOS[accion] || 'Acción'} completada.`);
      if (['recepcion_admin', 'control_cedis', 'entrega_transporte', 'entrega_cliente', 'anular'].includes(accion)) {
        navigate('/tablero');
      }
    } catch (err) {
      setError(err?.error || 'No se pudo ejecutar la acción');
    } finally {
      setEnviando(false);
    }
  };

  if (cargando) return <div className="container">Cargando…</div>;
  if (!guia) return <div className="container error">{error || 'Guía no encontrada'}</div>;

  const estado = guia.estado;
  const esDirecto = Boolean(guia.envio_directo_cedis);
  const rol = user?.rol;
  // En envío directo la guía nace en EN_CEDIS: la entrega final solo se ofrece
  // cuando ya existe el control de bultos de CEDIS.
  const controlRegistrado = eventos.some((e) => e.tipo === 'control_cedis');
  const puede = {
    recepcion_admin: ['administrativo', 'admin'].includes(rol) && estado === 'CREADA',
    control_cedis: ['cedis', 'admin'].includes(rol) && ['RECIBIDA_ADMIN', 'EN_CEDIS'].includes(estado),
    entrega_transporte: ['cedis', 'admin'].includes(rol) && estado === 'EN_CEDIS',
    entrega_cliente:
      (['cedis', 'admin'].includes(rol)
        && (estado === 'EN_RUTA' || (estado === 'EN_CEDIS' && esDirecto && controlRegistrado)))
      || (rol === 'transportador' && estado === 'EN_RUTA'),
    anular: rol === 'admin' && !['ENTREGADA', 'ANULADA'].includes(estado),
    editar_guia:
      (rol === 'ventas' && estado === 'CREADA')
      || (rol === 'admin' && !['EN_RUTA', 'ENTREGADA', 'ANULADA'].includes(estado)),
  };
  const acciones = Object.entries(TITULOS).filter(([tipo]) => puede[tipo]);

  return (
    <div className="detalle">
      <header className="detalle-header">
        <div>
          <Link to="/tablero" className="btn-mini">← Volver</Link>
          <h1>Guía #{guia.consecutivo || guia.id} · {estado}</h1>
        </div>
        <div className="detalle-usuario">
          <span>{user?.nombre || user?.usuario}</span>
          <button onClick={logout} className="btn-mini">Salir</button>
        </div>
      </header>

      {error && <div className="error" role="alert">{error}</div>}

      <section className="card">
        <h2>Datos de la guía</h2>
        <div className="grid">
          <div><strong>Cliente:</strong> {guia.cliente}</div>
          <div><strong>NIT:</strong> {guia.nit || '—'}</div>
          <div><strong>Ciudad:</strong> {guia.ciudad}</div>
          <div><strong>Dirección:</strong> {guia.direccion}</div>
          <div><strong>Documentos:</strong> {formatInvoiceNumbers(guia.documentos)}</div>
          <div><strong>Creada en:</strong> {guia.creada_en}</div>
          {guia.anulada_motivo && <div><strong>Anulada:</strong> {guia.anulada_motivo}</div>}
        </div>
      </section>

      <section className="card">
        <h2>Acciones</h2>
        <div className="acciones">
          {acciones.length === 0 && <p className="nota">No hay acciones disponibles para tu rol en este estado.</p>}
          {acciones.map(([tipo, titulo]) => (
            <button
              key={tipo}
              className={tipo === 'anular' ? 'peligro' : ''}
              onClick={() => abrir(tipo)}
              disabled={enviando}
            >
              {titulo}
            </button>
          ))}
        </div>
      </section>

      {accion && (
        <section className="card">
          <h2>{TITULOS[accion]}</h2>
          {accion === 'editar_guia' && (
            <div className="grid">
              {['cliente', 'ciudad', 'direccion', 'documentos', 'obs_ventas'].map((campo) => (
                <label key={campo}>
                  {campo}
                  <input name={campo} value={form[campo] ?? guia[campo] ?? ''} onChange={cambiar} />
                </label>
              ))}
            </div>
          )}
          {accion === 'anular' && (
            <label>
              Motivo de la anulación
              <input name="motivo" value={form.motivo || ''} onChange={cambiar} />
            </label>
          )}
          {accion === 'recepcion_admin' && (
            <label>
              Nombre de quien recibe en bodega
              <input name="recibe" value={form.recibe || ''} onChange={cambiar} />
            </label>
          )}
          {accion === 'control_cedis' && (
            <div className="grid">
              <label>Cajas<input name="cajas" type="number" min="0" value={form.cajas ?? 0} onChange={cambiar} /></label>
              <label>Bolsas<input name="bolsas" type="number" min="0" value={form.bolsas ?? 0} onChange={cambiar} /></label>
              <label>Cavas<input name="cayvas" type="number" min="0" value={form.cayvas ?? 0} onChange={cambiar} /></label>
              <label>Sobres<input name="sobres" type="number" min="0" value={form.sobres ?? 0} onChange={cambiar} /></label>
              <label>
                Funcionario CEDIS
                <select name="cedis_funcionario" value={form.cedis_funcionario || ''} onChange={cambiar}>
                  <option value="">-- Seleccione funcionario --</option>
                  <option value="Aldair Hoyos">Aldair Hoyos</option>
                  <option value="Nel Guerra">Nel Guerra</option>
                  <option value="Mario Wilchez">Mario Wilchez</option>
                  <option value="Danilo Gomez">Danilo Gomez</option>
                  <option value="Lida Perez">Lida Perez</option>
                  <option value="PRACTICANTE_PASANTE">Practicante / Pasante (escribir nombre)</option>
                </select>
              </label>
              {form.cedis_funcionario === 'PRACTICANTE_PASANTE' && (
                <label>
                  Nombre del practicante / pasante
                  <input
                    name="cedis_funcionario_practicante"
                    value={form.cedis_funcionario_practicante || ''}
                    onChange={cambiar}
                    required
                  />
                </label>
              )}
              <label className="check">
                <input name="vehiculo_cumple" type="checkbox" checked={form.vehiculo_cumple ?? true} onChange={cambiar} />
                El vehículo cumple las condiciones
              </label>
            </div>
          )}
          {accion === 'entrega_transporte' && (
            <div className="grid">
              <label>Nombre transportador<input name="nombre" value={form.nombre || ''} onChange={cambiar} /></label>
              <label>CC<input name="cc" value={form.cc || ''} onChange={cambiar} /></label>
              <label>Teléfono<input name="tel" value={form.tel || ''} onChange={cambiar} /></label>
              <label>Vehículo<input name="vehiculo" value={form.vehiculo || ''} onChange={cambiar} /></label>
              <label>Placa<input name="placa" value={form.placa || ''} onChange={cambiar} /></label>
              <label>Flete<input name="flete" value={form.flete || ''} onChange={cambiar} /></label>
            </div>
          )}
          {accion === 'entrega_cliente' && (
            <label>
              Nombre de quien recibe
              <input name="recibe" value={form.recibe || ''} onChange={cambiar} />
            </label>
          )}
          {EVENTOS_CON_FIRMA.has(accion) && (
            <div style={{ marginTop: 12 }}>
              <p className="nota">Firma en el recuadro (obligatoria):</p>
              <FirmaCanvas canvasRef={canvasRef} />
              <button type="button" className="btn-mini" onClick={limpiarFirma}>Limpiar firma</button>
            </div>
          )}
          {accion === 'control_cedis' && form.cedis_funcionario === 'PRACTICANTE_PASANTE' && (
            <div style={{ marginTop: 12 }}>
              <p className="nota">Firma del practicante / pasante (obligatoria):</p>
              <FirmaCanvas canvasRef={firmaPracticanteRef} />
              <button type="button" className="btn-mini" onClick={limpiarFirmaPracticante}>
                Limpiar firma
              </button>
            </div>
          )}
          <div className="acciones" style={{ marginTop: 12 }}>
            <button onClick={enviarAccion} disabled={enviando}>{enviando ? 'Guardando…' : 'Confirmar'}</button>
            <button className="peligro" onClick={() => setAccion(null)} disabled={enviando}>Cancelar</button>
          </div>
        </section>
      )}

      <section className="card">
        <h2>Historial de eventos ({eventos.length})</h2>
        {eventos.length === 0 && <p className="nota">Sin eventos registrados.</p>}
        {eventos.length > 0 && (
          <table className="tabla">
            <thead>
              <tr><th>Fecha</th><th>Tipo</th><th>Usuario</th><th>Rol</th></tr>
            </thead>
            <tbody>
              {eventos.map((ev) => (
                <tr key={ev.id}>
                  <td>{ev.en}</td>
                  <td>{ev.tipo}</td>
                  <td>{ev.usuario || '—'}</td>
                  <td>{ev.rol || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
