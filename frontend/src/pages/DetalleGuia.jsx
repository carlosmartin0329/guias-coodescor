import {
  forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState,
} from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import * as guiasApi from '../api/guias';
import { useAuth } from '../contexts/AuthContext';
import AppShell from '../components/AppShell';
import Icon from '../components/Icon';
import {
  StatusPill, TITULOS_EVENTO, Toast, fechaHora, useToast,
} from '../components/ui';
import { formatInvoiceNumbers } from '../utils/format';

const EVENTOS_CON_FIRMA = new Set([
  'recepcion_admin', 'control_cedis', 'entrega_transporte', 'entrega_cliente', 'captura_reclamo',
]);
const TITULOS = {
  recepcion_admin: 'Recepción administrativa',
  control_cedis: 'Control CEDIS',
  entrega_transporte: 'Entrega a transportador',
  entrega_cliente: 'Entrega al cliente',
  anular: 'Anular guía',
  editar_guia: 'Editar datos de la guía',
  captura_reclamo: 'Capturar datos de quien reclama',
};
const PASOS_NORMAL = [
  { clave: 'CREADA', etiqueta: 'Creada' },
  { clave: 'RECIBIDA_ADMIN', etiqueta: 'Recibida' },
  { clave: 'EN_CEDIS', etiqueta: 'Control CEDIS' },
  { clave: 'EN_RUTA', etiqueta: 'En ruta' },
  { clave: 'ENTREGADA', etiqueta: 'Entregada' },
];
const PASOS_DIRECTO = [
  { clave: 'CREADA', etiqueta: 'Creada' },
  { clave: 'EN_CEDIS', etiqueta: 'Control CEDIS' },
  { clave: 'ENTREGADA', etiqueta: 'Entregada' },
];
const FUNCIONARIOS = [
  'Aldair Hoyos', 'Nel Guerra', 'Mario Wilchez', 'Danilo Gomez', 'Lida Perez',
];

const SignaturePad = forwardRef(function SignaturePad({ label, hint }, ref) {
  const canvasRef = useRef(null);
  const dibujando = useRef(false);
  const ultimo = useRef({ x: 0, y: 0 });
  const [vacio, setVacio] = useState(true);

  const limpiar = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
    setVacio(true);
  }, []);

  useImperativeHandle(ref, () => ({
    getDataURL: () => {
      const canvas = canvasRef.current;
      if (!canvas || vacio) return '';
      return canvas.toDataURL('image/png');
    },
    isEmpty: () => vacio,
    clear: limpiar,
  }), [limpiar, vacio]);

  const posicion = (evento) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const punto = evento.touches ? evento.touches[0] : evento;
    return {
      x: ((punto.clientX - rect.left) / rect.width) * canvas.width,
      y: ((punto.clientY - rect.top) / rect.height) * canvas.height,
    };
  };

  const iniciar = (evento) => {
    evento.preventDefault();
    dibujando.current = true;
    ultimo.current = posicion(evento);
  };
  const mover = (evento) => {
    if (!dibujando.current) return;
    evento.preventDefault();
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const punto = posicion(evento);
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 2.2;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(ultimo.current.x, ultimo.current.y);
    ctx.lineTo(punto.x, punto.y);
    ctx.stroke();
    ultimo.current = punto;
    if (vacio) setVacio(false);
  };
  const terminar = () => { dibujando.current = false; };

  return (
    <div className="sig-box">
      <div className="sig-label">
        <span>{label}</span>
        <button type="button" className="link" onClick={limpiar}>Limpiar</button>
      </div>
      <canvas
        ref={canvasRef}
        className="sig-canvas"
        width={600}
        height={150}
        aria-label={label}
        onPointerDown={iniciar}
        onPointerMove={mover}
        onPointerUp={terminar}
        onPointerLeave={terminar}
      />
      {hint ? <p className="hint">{hint}</p> : null}
    </div>
  );
});

export default function DetalleGuia() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [guia, setGuia] = useState(null);
  const [eventos, setEventos] = useState([]);
  const [prellenado, setPrellenado] = useState({});
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [accion, setAccion] = useState(null);
  const [form, setForm] = useState({});
  const [enviando, setEnviando] = useState(false);
  const firmaRef = useRef(null);
  const firmaPracticanteRef = useRef(null);
  const firmaTransportadorRef = useRef(null);
  const { toast, showToast, closeToast } = useToast();

  const cargar = useCallback(async () => {
    const detalle = await guiasApi.guiasDetalle(id);
    setGuia(detalle.guia);
    setEventos(detalle.eventos || []);
    setPrellenado(detalle.prellenado || {});
  }, [id]);

  useEffect(() => {
    let cancelado = false;
    setCargando(true);
    setError(null);
    cargar()
      .catch((err) => { if (!cancelado) setError(err?.error || 'No se pudo cargar la guía'); })
      .finally(() => { if (!cancelado) setCargando(false); });
    return () => { cancelado = true; };
  }, [cargar]);

  const cambiar = (evento) => {
    const { name, value, type, checked } = evento.target;
    setForm((actual) => ({ ...actual, [name]: type === 'checkbox' ? checked : value }));
  };

  const abrir = (tipo) => {
    setError(null);
    const control = eventos.find((evento) => evento.tipo === 'control_cedis')?.datos || {};
    const reclamo = [...eventos]
      .filter((evento) => evento.tipo === 'captura_reclamo')
      .sort((a, b) => Number(b.id) - Number(a.id))[0]?.datos || {};
    const base = {};
    if (tipo === 'control_cedis') {
      ['cajas', 'bolsas', 'cayvas', 'sobres'].forEach((campo) => {
        base[campo] = control[campo] ?? prellenado[campo] ?? guia?.[campo] ?? 0;
      });
      base.obs = control.obs || '';
      base.funcionario = '';
      base.vehiculo_cumple = true;
    } else if (tipo === 'entrega_transporte') {
      base.nombre = prellenado.transportador_nombre || '';
      base.cc = prellenado.transportador_cc || '';
      base.tel = prellenado.transportador_tel || '';
      base.vehiculo = prellenado.transportador_vehiculo || '';
      base.placa = prellenado.transportador_placa || '';
      base.flete = prellenado.transportador_flete || '';
    } else if (tipo === 'captura_reclamo') {
      base.nombre = reclamo.reclamo_nombre || prellenado.reclamo_nombre || '';
      base.cedula = reclamo.reclamo_cedula || prellenado.reclamo_cedula || '';
      base.telefono = reclamo.reclamo_telefono || prellenado.reclamo_telefono || '';
    } else if (tipo === 'entrega_cliente' || tipo === 'recepcion_admin') {
      base.recibe = tipo === 'entrega_cliente'
        ? (reclamo.reclamo_nombre || prellenado.cliente_recibe_nombre || guia?.cliente_recibe_nombre || '')
        : '';
      if (tipo === 'recepcion_admin') {
        base.transportador_nombre = prellenado.transportador_nombre || '';
        base.transportador_cc = prellenado.transportador_cc || '';
        base.transportador_tel = prellenado.transportador_tel || '';
        base.transportador_vehiculo = prellenado.transportador_vehiculo || '';
        base.transportador_placa = prellenado.transportador_placa || '';
        base.transportador_flete = prellenado.transportador_flete || '';
      }
    } else if (tipo === 'editar_guia') {
      ['cliente', 'ciudad', 'direccion', 'documentos', 'obs_ventas'].forEach((campo) => {
        base[campo] = guia?.[campo] || '';
      });
    }
    setForm(base);
    setAccion(tipo);
  };

  const cerrarAccion = () => {
    if (enviando) return;
    setAccion(null);
    setError(null);
  };

  const firmaVacia = (ref) => !ref.current || ref.current.isEmpty?.() !== false;

  const enviarAccion = async () => {
    if (!accion) return;
    setEnviando(true);
    setError(null);
    try {
      if (accion === 'editar_guia') {
        await guiasApi.guiasEditar(id, form);
      } else if (accion === 'anular') {
        if (!String(form.motivo || '').trim()) throw { error: 'Indica el motivo de la anulación' };
        await guiasApi.guiasEvento(id, 'anular', { motivo: form.motivo.trim() });
      } else if (accion === 'captura_reclamo') {
        if (!String(form.nombre || '').trim()) throw { error: 'Indica el nombre de la persona que reclama' };
        if (!String(form.cedula || '').replace(/\D/g, '')) throw { error: 'Indica la cédula de la persona que reclama' };
        if (!String(form.telefono || '').replace(/\D/g, '')) throw { error: 'Indica el teléfono de la persona que reclama' };
        if (firmaVacia(firmaRef)) throw { error: 'Dibuja la firma de la persona que reclama' };
        await guiasApi.guiasEvento(id, 'captura_reclamo', {
          reclamo_nombre: String(form.nombre).trim(),
          reclamo_cedula: String(form.cedula).trim(),
          reclamo_telefono: String(form.telefono).trim(),
          firma_reclamo: firmaRef.current.getDataURL(),
        });
      } else {
        const payload = { ...form };
        if (EVENTOS_CON_FIRMA.has(accion)) {
          if (firmaVacia(firmaRef)) throw { error: 'Dibuja la firma en el recuadro antes de continuar' };
          payload.firma = firmaRef.current.getDataURL();
          if (accion === 'entrega_cliente' && rol === 'transportador') {
            if (firmaVacia(firmaTransportadorRef)) {
              throw { error: 'Dibuja la firma del transportador que entrega' };
            }
            payload.firma_transportador_entrega = firmaTransportadorRef.current.getDataURL();
          }
          if (accion === 'control_cedis') {
            const funcionario = form.funcionario || user?.nombre || user?.usuario;
            if (!funcionario) throw { error: 'Selecciona el funcionario CEDIS que entrega' };
            payload.cedis_funcionario = funcionario;
            if (funcionario === 'PRACTICANTE_PASANTE') {
              if (!String(form.practicante || '').trim()) {
                throw { error: 'Escribe el nombre del practicante / pasante' };
              }
              if (firmaVacia(firmaPracticanteRef)) {
                throw { error: 'Dibuja la firma del practicante / pasante' };
              }
              payload.cedis_funcionario_practicante = String(form.practicante).trim();
              payload.firma_practicante = firmaPracticanteRef.current.getDataURL();
            }
            ['cajas', 'bolsas', 'cayvas', 'sobres'].forEach((campo) => {
              payload[campo] = Number(form[campo] || 0);
            });
            payload.vehiculo_cumple = form.vehiculo_cumple ? 'si' : 'no';
            payload.obs = form.obs || '';
          }
        }
        await guiasApi.guiasEvento(id, accion, payload);
      }
      await cargar();
      setAccion(null);
      showToast(`${TITULOS[accion]} completada.`);
      if (['recepcion_admin', 'control_cedis', 'entrega_transporte', 'entrega_cliente', 'anular'].includes(accion)) {
        window.setTimeout(() => navigate('/tablero'), 650);
      }
    } catch (err) {
      setError(err?.error || 'No se pudo ejecutar la acción');
    } finally {
      setEnviando(false);
    }
  };

  const estado = guia?.estado;
  const esDirecto = Boolean(guia?.envio_directo_cedis);
  const rol = user?.rol;
  const controlRegistrado = eventos.some((evento) => evento.tipo === 'control_cedis');

  const puede = useMemo(() => ({
    recepcion_admin: ['administrativo', 'admin'].includes(rol) && estado === 'CREADA',
    control_cedis: ['cedis', 'admin'].includes(rol) && ['RECIBIDA_ADMIN', 'EN_CEDIS'].includes(estado),
    entrega_transporte: ['cedis', 'admin'].includes(rol) && estado === 'EN_CEDIS',
    entrega_cliente:
      (['cedis', 'admin'].includes(rol)
        && (estado === 'EN_RUTA' || (estado === 'EN_CEDIS' && esDirecto && controlRegistrado)))
      || (rol === 'transportador' && estado === 'EN_RUTA'),
    anular: rol === 'admin' && !['ENTREGADA', 'ANULADA'].includes(estado),
    captura_reclamo:
      ['cedis', 'admin'].includes(rol) && !['ENTREGADA', 'ANULADA'].includes(estado),
    editar_guia:
      (rol === 'ventas' && estado === 'CREADA')
      || (rol === 'admin' && !['EN_RUTA', 'ENTREGADA', 'ANULADA'].includes(estado)),
  }), [controlRegistrado, esDirecto, estado, rol]);

  const acciones = Object.keys(TITULOS).filter((tipo) => puede[tipo]);
  const accionFlujo = acciones.find(
    (tipo) => !['editar_guia', 'anular', 'captura_reclamo'].includes(tipo),
  );
  const control = eventos.find((evento) => evento.tipo === 'control_cedis')?.datos || {};
  const eventoReclamo = [...eventos]
    .filter((evento) => evento.tipo === 'captura_reclamo')
    .sort((a, b) => Number(b.id) - Number(a.id))[0]?.datos;
  // La captura hecha por Ventas al crear la guía vive en "creacion"; la de
  // CEDIS posterior, en "captura_reclamo". Se muestra la más reciente.
  const reclamo = eventoReclamo || eventos.find((evento) => evento.tipo === 'creacion')?.datos || {};
  const bultos = {
    cajas: control.cajas ?? prellenado.cajas ?? guia?.cajas ?? 0,
    bolsas: control.bolsas ?? prellenado.bolsas ?? guia?.bolsas ?? 0,
    cayvas: control.cayvas ?? prellenado.cayvas ?? guia?.cayvas ?? 0,
    sobres: control.sobres ?? prellenado.sobres ?? guia?.sobres ?? 0,
  };
  const totalBultos = Number(control.totales)
    || (Number(bultos.cajas) + Number(bultos.bolsas) + Number(bultos.cayvas) + Number(bultos.sobres));

  const pasos = esDirecto ? PASOS_DIRECTO : PASOS_NORMAL;
  const indiceActual = pasos.findIndex((paso) => paso.clave === estado);
  const eventoOrdenado = [...eventos].sort((a, b) => Number(b.id) - Number(a.id));

  if (cargando) {
    return (
      <AppShell title="Detalle de guía" breadcrumb="Detalle de guía" sinPageHead>
        <div className="panel"><div className="loading-block"><span className="spinner" /> Cargando guía…</div></div>
      </AppShell>
    );
  }

  if (!guia) {
    return (
      <AppShell title="Detalle de guía" breadcrumb="Detalle de guía" sinPageHead>
        <div className="panel" style={{ padding: 18 }}>
          <div className="inline-alert" role="alert"><Icon name="alert" size={16} /> {error || 'Guía no encontrada'}</div>
          <button type="button" className="btn mt-3" onClick={() => navigate('/tablero')}>Volver al tablero</button>
        </div>
      </AppShell>
    );
  }

  const renderFormulario = () => {
    if (accion === 'editar_guia') {
      return (
        <div className="form-grid">
          {['cliente', 'ciudad', 'direccion', 'documentos', 'obs_ventas'].map((campo) => (
            <label key={campo} className={campo === 'obs_ventas' || campo === 'direccion' ? 'wide' : ''}>
              <span className="lbl" style={{ textTransform: 'capitalize' }}>{campo.replace('_', ' ')}</span>
              <input className="input" name={campo} value={form[campo] ?? ''} onChange={cambiar} />
            </label>
          ))}
        </div>
      );
    }
    if (accion === 'anular') {
      return (
        <label>
          <span className="lbl">Motivo de la anulación</span>
          <textarea className="input" name="motivo" value={form.motivo || ''} onChange={cambiar} />
        </label>
      );
    }
    if (accion === 'captura_reclamo') {
      return (
        <>
          <div className="form-grid">
            <label className="wide">
              <span className="lbl">Nombre completo *</span>
              <input
                className="input"
                name="nombre"
                value={form.nombre || ''}
                onChange={cambiar}
                maxLength={120}
                placeholder="Nombre de la persona que reclama"
              />
            </label>
            <label>
              <span className="lbl">Cédula *</span>
              <input
                className="input"
                name="cedula"
                value={form.cedula || ''}
                onChange={(evento) => setForm((f) => ({ ...f, cedula: evento.target.value.replace(/\D/g, '') }))}
                maxLength={30}
                inputMode="numeric"
                placeholder="Solo números"
              />
            </label>
            <label>
              <span className="lbl">Teléfono *</span>
              <input
                className="input"
                name="telefono"
                value={form.telefono || ''}
                onChange={(evento) => setForm((f) => ({ ...f, telefono: evento.target.value.replace(/\D/g, '') }))}
                maxLength={30}
                inputMode="tel"
                placeholder="Solo números"
              />
            </label>
          </div>
          <SignaturePad
            ref={firmaRef}
            label="Firma de la persona que reclama"
            hint="Solo captura de datos. No cambia el estado ni cierra la entrega."
          />
          <p className="action-note">
            CEDIS seguirá confirmando los datos y firmando el cierre de la entrega cuando corresponda.
          </p>
        </>
      );
    }
    if (accion === 'recepcion_admin') {
      return (
        <>
          <label>
            <span className="lbl">Nombre de quien recibe en bodega</span>
            <input className="input" name="recibe" value={form.recibe || ''} onChange={cambiar} />
          </label>
          <div className="transport-capture">
            <div className="panel-title" style={{ fontSize: 13, marginBottom: 6 }}>
              Datos del transportador
            </div>
            <p className="hint" style={{ marginTop: 0, marginBottom: 8 }}>
              Administrativo los registra aquí; CEDIS los recibirá prellenados al entregar.
            </p>
            <div className="form-grid">
              <label className="wide">
                <span className="lbl">Transportador</span>
                <input
                  className="input"
                  name="transportador_nombre"
                  value={form.transportador_nombre || ''}
                  onChange={cambiar}
                  maxLength={120}
                  placeholder="Nombre del transportador"
                />
              </label>
              <label>
                <span className="lbl">CC</span>
                <input className="input" name="transportador_cc" value={form.transportador_cc || ''} onChange={cambiar} maxLength={50} inputMode="numeric" />
              </label>
              <label>
                <span className="lbl">Teléfono</span>
                <input className="input" name="transportador_tel" value={form.transportador_tel || ''} onChange={cambiar} maxLength={50} inputMode="tel" />
              </label>
              <label>
                <span className="lbl">Vehículo</span>
                <input className="input" name="transportador_vehiculo" value={form.transportador_vehiculo || ''} onChange={cambiar} maxLength={80} />
              </label>
              <label>
                <span className="lbl">Placa</span>
                <input className="input" name="transportador_placa" value={form.transportador_placa || ''} onChange={cambiar} maxLength={20} />
              </label>
              <label>
                <span className="lbl">Flete</span>
                <input className="input" name="transportador_flete" value={form.transportador_flete || ''} onChange={cambiar} maxLength={40} />
              </label>
            </div>
          </div>
          <SignaturePad ref={firmaRef} label="Firma de quien recibe" hint="Obligatoria para registrar la recepción." />
        </>
      );
    }
    if (accion === 'control_cedis') {
      return (
        <>
          <div className="bultos" style={{ marginBottom: 12 }}>
            {[
              ['cajas', 'Cajas'], ['bolsas', 'Bolsas'], ['cayvas', 'Cavas'], ['sobres', 'Sobres'],
            ].map(([campo, etiqueta]) => (
              <div key={campo} className="bulto" style={{ padding: '7px 5px' }}>
                <span style={{ display: 'block', fontSize: 9.5, color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 700 }}>{etiqueta}</span>
                <div className="counter" style={{ justifyContent: 'center', marginTop: 3 }}>
                  <button type="button" onClick={() => setForm((f) => ({ ...f, [campo]: Math.max(0, Number(f[campo] || 0) - 1) }))}>−</button>
                  <b className="num">{form[campo] ?? 0}</b>
                  <button type="button" onClick={() => setForm((f) => ({ ...f, [campo]: Number(f[campo] || 0) + 1 }))}>+</button>
                </div>
              </div>
            ))}
          </div>

          <label>
            <span className="lbl">Funcionario CEDIS que entrega</span>
            <select className="selectbox" name="funcionario" value={form.funcionario || ''} onChange={cambiar}>
              <option value="">-- Seleccione funcionario --</option>
              {FUNCIONARIOS.map((nombre) => <option key={nombre} value={nombre}>{nombre}</option>)}
              <option value="PRACTICANTE_PASANTE">Practicante / Pasante</option>
            </select>
          </label>
          {form.funcionario === 'PRACTICANTE_PASANTE' ? (
            <label>
              <span className="lbl">Nombre del practicante / pasante</span>
              <input className="input" name="practicante" value={form.practicante || ''} onChange={cambiar} />
            </label>
          ) : null}
          <label className="check" style={{ marginTop: 8 }}>
            <input type="checkbox" name="vehiculo_cumple" checked={form.vehiculo_cumple ?? true} onChange={cambiar} />
            El vehículo cumple las condiciones
          </label>
          <label>
            <span className="lbl">Observaciones del control</span>
            <input className="input" name="obs" value={form.obs || ''} onChange={cambiar} />
          </label>
          <SignaturePad ref={firmaRef} label="Firma de quien entrega en CEDIS" hint="Obligatoria." />
          {form.funcionario === 'PRACTICANTE_PASANTE' ? (
            <SignaturePad ref={firmaPracticanteRef} label="Firma del practicante / pasante" hint="Obligatoria cuando entrega un practicante." />
          ) : null}
        </>
      );
    }
    if (accion === 'entrega_transporte') {
      return (
        <>
          <div className="form-grid">
            <label><span className="lbl">Nombre transportador</span><input className="input" name="nombre" value={form.nombre || ''} onChange={cambiar} /></label>
            <label><span className="lbl">CC</span><input className="input" name="cc" value={form.cc || ''} onChange={cambiar} /></label>
            <label><span className="lbl">Teléfono</span><input className="input" name="tel" value={form.tel || ''} onChange={cambiar} /></label>
            <label><span className="lbl">Vehículo</span><input className="input" name="vehiculo" value={form.vehiculo || ''} onChange={cambiar} /></label>
            <label><span className="lbl">Placa</span><input className="input" name="placa" value={form.placa || ''} onChange={cambiar} /></label>
            <label><span className="lbl">Flete</span><input className="input" name="flete" value={form.flete || ''} onChange={cambiar} /></label>
          </div>
          <SignaturePad ref={firmaRef} label="Firma del transportador" hint="Obligatoria para iniciar la ruta." />
        </>
      );
    }
    if (accion === 'entrega_cliente') {
      return (
        <>
          <label>
            <span className="lbl">Nombre de quien recibe</span>
            <input className="input" name="recibe" value={form.recibe || ''} onChange={cambiar} />
          </label>
          {rol === 'transportador' ? (
            <SignaturePad
              ref={firmaTransportadorRef}
              label="Firma del transportador que entrega"
              hint="Obligatoria: el transportador propio entrega la mercancía."
            />
          ) : null}
          <SignaturePad ref={firmaRef} label="Firma del cliente" hint="Obligatoria para cerrar la guía." />
        </>
      );
    }
    return null;
  };

  return (
    <AppShell title="Guías" breadcrumb="Detalle de guía" sinPageHead>
      <section className="panel" style={{ marginBottom: 14 }}>
        <div className="detail-header">
          <button type="button" className="back-btn" onClick={() => navigate('/tablero')} aria-label="Volver al tablero">
            <Icon name="arrowLeft" size={17} />
          </button>
          <div className="grow">
            <div className="detail-title-row">
              <h1 className="detail-title">Guía #{guia.consecutivo || guia.id}</h1>
              <StatusPill estado={estado} />
              {esDirecto ? <span className="tag directo">Envío directo</span> : null}
            </div>
            <div className="detail-sub">
              {guia.cliente} · {guia.ciudad || '—'} · creada {fechaHora(guia.creada_en)}
            </div>
          </div>
          <div className="detail-actions">
            {puede.editar_guia ? (
              <button type="button" className="btn btn-sm" onClick={() => abrir('editar_guia')} disabled={enviando}>
                <Icon name="edit" size={14} /> Editar
              </button>
            ) : null}
            {puede.anular ? (
              <button type="button" className="btn btn-sm btn-danger" onClick={() => abrir('anular')} disabled={enviando}>
                <Icon name="trash" size={14} /> Anular
              </button>
            ) : null}
          </div>
        </div>

        {estado !== 'ANULADA' ? (
          <div className="stepper" aria-label="Estado del proceso">
            {pasos.map((paso, indice) => {
              const hecho = indiceActual > indice || estado === 'ENTREGADA';
              const actual = indiceActual === indice && estado !== 'ENTREGADA';
              return (
                <div className="step-cluster" key={paso.clave} style={{ display: 'inline-flex', alignItems: 'center', flex: 'none' }}>
                  <div className={`step ${hecho ? 'done' : ''} ${actual ? 'current' : ''}`.trim()}>
                    <span className="step-dot">
                      {hecho ? <Icon name="check" size={13} /> : indice + 1}
                    </span>
                    <span className="step-label">{paso.etiqueta}</span>
                  </div>
                  {indice < pasos.length - 1 ? <span className={`step-line ${hecho ? 'done' : ''}`.trim()} /> : null}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="inline-alert" style={{ margin: 14 }} role="alert">
            <Icon name="alert" size={16} /> Esta guía fue anulada{guia.anulada_motivo ? `: ${guia.anulada_motivo}` : '.'}
          </div>
        )}
      </section>

      {error ? <div className="inline-alert" role="alert" style={{ marginBottom: 12 }}><Icon name="alert" size={16} /> {error}</div> : null}

      <div className="detail-grid">
        <div className="detail-main">
          <section className="panel">
            <div className="panel-head">
              <div className="panel-title">Datos de la guía</div>
              <span className="tag" style={{ marginLeft: 'auto' }}>Acta digital</span>
            </div>
            <div className="panel-body">
              <div className="grid-2">
                <dl className="kv"><dt>Cliente</dt><dd>{guia.cliente}</dd></dl>
                <dl className="kv"><dt>NIT</dt><dd className="mono">{guia.nit || '—'}</dd></dl>
                <dl className="kv"><dt>Ciudad</dt><dd>{guia.ciudad || '—'}</dd></dl>
                <dl className="kv"><dt>Dirección</dt><dd>{guia.direccion || '—'}</dd></dl>
                <dl className="kv"><dt>Documentos</dt><dd>{formatInvoiceNumbers(guia.documentos) || '—'}</dd></dl>
                <dl className="kv"><dt>Centro de operación</dt><dd>{guia.centro_operacion || '—'}</dd></dl>
                <dl className="kv"><dt>Persona que recibe</dt><dd>{prellenado.cliente_recibe_nombre || guia.cliente_recibe_nombre || '—'}</dd></dl>
                <dl className="kv"><dt>Tipo de flujo</dt><dd>{esDirecto ? 'Envío directo a CEDIS' : 'Flujo normal'}</dd></dl>
              </div>
              {prellenado.obs_ventas || guia.obs_ventas ? (
                <div className="inline-info" style={{ marginTop: 10 }}>
                  <Icon name="file" size={15} />
                  <span><strong>Observaciones de Ventas:</strong> {prellenado.obs_ventas || guia.obs_ventas}</span>
                </div>
              ) : null}
            </div>
          </section>

          <section className="panel">
            <div className="panel-head">
              <div className="panel-title">Control de bultos</div>
              <span className="panel-sub" style={{ marginLeft: 'auto' }}>
                {control.cajas != null ? 'Verificado por CEDIS' : 'Informado por Ventas'}
              </span>
            </div>
            <div className="panel-body">
              <div className="bultos">
                <div className="bulto"><b>{bultos.cajas}</b><span>Cajas</span></div>
                <div className="bulto"><b>{bultos.bolsas}</b><span>Bolsas</span></div>
                <div className="bulto"><b>{bultos.cayvas}</b><span>Cavas</span></div>
                <div className="bulto"><b>{bultos.sobres}</b><span>Sobres</span></div>
              </div>
              <div className="bulto-total"><span>Total unidades</span><strong className="num">{totalBultos}</strong></div>
            </div>
          </section>

          {reclamo.reclamo_nombre || reclamo.firma_reclamo_archivo ? (
            <section className="panel">
              <div className="panel-head">
                <div className="panel-title">Persona que reclama (capturada)</div>
                <span className="tag" style={{ marginLeft: 'auto' }}>Solo captura</span>
              </div>
              <div className="panel-body">
                <div className="grid-2">
                  <dl className="kv"><dt>Nombre</dt><dd>{reclamo.reclamo_nombre || '—'}</dd></dl>
                  <dl className="kv"><dt>Cédula</dt><dd className="mono">{reclamo.reclamo_cedula || '—'}</dd></dl>
                  <dl className="kv"><dt>Teléfono</dt><dd>{reclamo.reclamo_telefono || '—'}</dd></dl>
                </div>
                {reclamo.firma_reclamo_archivo ? (
                  <div className="sig-wrap">
                    <span className="sig-label">Firma capturada</span>
                    <img
                      src={`/static_file/${reclamo.firma_reclamo_archivo}`}
                      alt="Firma de la persona que reclama"
                      style={{ maxWidth: 360, width: '100%', border: '1px solid var(--border)', borderRadius: 8, background: '#fff' }}
                    />
                  </div>
                ) : null}
                <p className="action-note">Estos datos no cierran la guía; CEDIS confirma y firma la entrega.</p>
              </div>
            </section>
          ) : null}

          <section className="panel">
            <div className="panel-head">
              <div className="panel-title">Historial de la guía</div>
              <span className="panel-sub" style={{ marginLeft: 'auto' }}>{eventos.length} eventos</span>
            </div>
            <div className="panel-body">
              {eventoOrdenado.length === 0 ? (
                <p className="nota">Sin eventos registrados.</p>
              ) : (
                <div className="event-list">
                  {eventoOrdenado.map((evento) => (
                    <div className="event-item" key={evento.id}>
                      <span className={`event-ico ${evento.tipo === 'control_cedis' || evento.tipo === 'entrega_cliente' ? 'done' : ''}`.trim()}>
                        <Icon name={evento.tipo === 'entrega_cliente' ? 'check' : evento.tipo === 'entrega_transporte' ? 'truck' : 'file'} size={13} />
                      </span>
                      <span className="event-body">
                        <span className="event-title">{TITULOS_EVENTO[evento.tipo] || evento.tipo}</span>
                        <span className="event-meta">{evento.usuario || 'Sistema'} · {evento.rol || '—'}</span>
                      </span>
                      <span className="event-time">{fechaHora(evento.en)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        </div>

        <aside className="detail-rail">
          <section className="panel action-card">
            {accion ? (
              <>
                <div className="action-hero">
                  <h3>{TITULOS[accion]}</h3>
                  <p>Completa los datos y confirma para registrar el paso.</p>
                </div>
                <div className="action-body">
                  {renderFormulario()}
                  <div className="form-actions">
                    <button type="button" className="btn btn-primary" onClick={enviarAccion} disabled={enviando}>
                      {enviando ? 'Guardando…' : 'Confirmar'}
                    </button>
                    <button type="button" className="btn" onClick={cerrarAccion} disabled={enviando}>Cancelar</button>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="action-hero">
                  <h3>{accionFlujo ? `Siguiente paso: ${TITULOS[accionFlujo]}` : 'Guía sin acciones pendientes'}</h3>
                  <p>
                    {accionFlujo
                      ? 'Este es el paso que corresponde a tu rol en este momento.'
                      : 'No hay pasos disponibles para tu rol en el estado actual.'}
                  </p>
                </div>
                <div className="action-body">
                  <div className="action-list">
                    {acciones.length === 0 ? (
                      <p className="nota">No hay acciones disponibles para tu rol en este estado.</p>
                    ) : (
                      acciones.map((tipo) => (
                        <button
                          key={tipo}
                          type="button"
                          className={`btn ${tipo === accionFlujo ? 'btn-primary' : ''} ${tipo === 'anular' ? 'btn-danger' : ''}`.trim()}
                          onClick={() => abrir(tipo)}
                          disabled={enviando}
                        >
                          {TITULOS[tipo]}
                          <Icon name="chevronRight" size={14} style={{ marginLeft: 'auto' }} />
                        </button>
                      ))
                    )}
                  </div>
                  <p className="action-note">
                    Las firmas y evidencias quedan guardadas en el historial de la guía y en el acta.
                  </p>
                </div>
              </>
            )}
          </section>

          <section className="panel">
            <div className="panel-body">
              <div className="panel-title" style={{ marginBottom: 6 }}>Resumen del proceso</div>
              <div className="summary-row"><span>Estado</span><StatusPill estado={estado} /></div>
              <div className="summary-row"><span>Bultos</span><b className="num">{totalBultos}</b></div>
              <div className="summary-row"><span>Eventos</span><b className="num">{eventos.length}</b></div>
              <div className="summary-row"><span>Flujo</span><b>{esDirecto ? 'Directo' : 'Normal'}</b></div>
            </div>
          </section>
        </aside>
      </div>
      <Toast toast={toast} onClose={closeToast} />
    </AppShell>
  );
}
