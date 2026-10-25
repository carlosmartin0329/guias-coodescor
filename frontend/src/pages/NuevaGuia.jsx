import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as guiasApi from '../api/guias';
import AppShell from '../components/AppShell';
import Icon from '../components/Icon';
import { Toast, useToast } from '../components/ui';
import {
  numericMask, phoneMask, cedulaMask, documentosMask,
  formatInvoiceNumbersWithPrefix,
} from '../utils/format';

const DRAFT_KEY = 'guias.borrador.nueva-guia';
const PASOS = [
  { numero: 1, titulo: 'Cliente y documentos' },
  { numero: 2, titulo: 'Bultos y flujo' },
  { numero: 3, titulo: 'Transporte y confirmación' },
];
const FORM_INICIAL = {
  cliente: '',
  ciudad: '',
  direccion: '',
  documentos: '',
  obs_ventas: '',
  nit: '',
  centro_operacion: '-',
  prefijo: 'FV',
  envio_directo_cedis: false,
  transportador_nombre: '',
  transportador_cc: '',
  transportador_tel: '',
  transportador_vehiculo: '',
  transportador_placa: '',
  transportador_flete: '',
  cliente_recibe_nombre: '',
  cliente_recibe_contacto_id: null,
  cajas: 0,
  bolsas: 0,
  cayvas: 0,
  sobres: 0,
  otros: '',
  generar_link_recibido: false,
};

export default function NuevaGuia() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toast, showToast, closeToast } = useToast();
  const [form, setForm] = useState(FORM_INICIAL);
  const [paso, setPaso] = useState(1);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [clienteOpts, setClienteOpts] = useState([]);
  const [contactoOpts, setContactoOpts] = useState([]);
  const [showContactoDropdown, setShowContactoDropdown] = useState(false);
  const [transportadorOpts, setTransportadorOpts] = useState([]);
  const [showTransportadorDropdown, setShowTransportadorDropdown] = useState(false);
  const [guardandoTransportador, setGuardandoTransportador] = useState(false);
  const [guardado, setGuardado] = useState(false);
  const [mostrarClientes, setMostrarClientes] = useState(false);
  const [clienteCargado, setClienteCargado] = useState('');
  const ultimoTransportadorGuardado = useRef('');

  const aplicarCliente = (cliente) => {
    const nombre = cliente.razon_social || '';
    setForm((actual) => {
      const siguiente = {
        ...actual,
        cliente: nombre || actual.cliente,
        nit: cliente.nit || actual.nit,
        ciudad: cliente.ciudad || actual.ciudad,
        direccion: cliente.direccion || actual.direccion,
      };
      const igual = siguiente.cliente === actual.cliente
        && siguiente.nit === actual.nit
        && siguiente.ciudad === actual.ciudad
        && siguiente.direccion === actual.direccion;
      return igual ? actual : siguiente;
    });
    if (nombre) setClienteCargado(nombre);
    setMostrarClientes(false);
  };

  // Borrador local: evita perder el trabajo si se recarga la página.
  useEffect(() => {
    try {
      const crudo = window.localStorage.getItem(DRAFT_KEY);
      if (crudo) {
        const guardadoPrevio = JSON.parse(crudo);
        if (guardadoPrevio && typeof guardadoPrevio === 'object') {
          setForm((actual) => ({ ...actual, ...guardadoPrevio }));
        }
      }
    } catch {
      /* borrador ilegible: se ignora */
    }
  }, []);

  useEffect(() => {
    const temporizador = window.setTimeout(() => {
      try {
        window.localStorage.setItem(DRAFT_KEY, JSON.stringify(form));
        setGuardado(true);
        window.setTimeout(() => setGuardado(false), 1200);
      } catch {
        /* sin almacenamiento disponible */
      }
    }, 700);
    return () => window.clearTimeout(temporizador);
  }, [form]);

  useEffect(() => {
    if (!form.cliente || form.cliente.length < 1) { setClienteOpts([]); return undefined; }
    const temporizador = window.setTimeout(() => {
      fetch(`/api/clientes/buscar?q=${encodeURIComponent(form.cliente)}&limite=10`, { credentials: 'include' })
        .then((r) => r.json())
        .then((data) => setClienteOpts(data.resultados || []))
        .catch(() => {});
    }, 250);
    return () => window.clearTimeout(temporizador);
  }, [form.cliente]);

  // Autocompletado por NIT: al escribir un NIT registrado se completan razón
  // social, ciudad y dirección sin tener que elegir de una lista.
  useEffect(() => {
    const consulta = String(form.nit || '').trim();
    const soloDigitos = consulta.replace(/\D/g, '');
    if (soloDigitos.length < 3) return undefined;
    let cancelado = false;
    const temporizador = window.setTimeout(() => {
      fetch(`/api/clientes/buscar?q=${encodeURIComponent(consulta)}&limite=10`, { credentials: 'include' })
        .then((r) => r.json())
        .then((data) => {
          if (cancelado) return;
          const encontrado = (data.resultados || []).find(
            (c) => String(c.nit || '').replace(/\D/g, '') === soloDigitos,
          );
          if (encontrado) aplicarCliente(encontrado);
        })
        .catch(() => {});
    }, 400);
    return () => { cancelado = true; window.clearTimeout(temporizador); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.nit]);

  useEffect(() => {
    if (!form.nit) { setContactoOpts([]); return undefined; }
    const temporizador = window.setTimeout(() => {
      fetch(`/api/clientes_contactos/por_cliente?nit_cliente=${encodeURIComponent(form.nit)}&limite=20`, { credentials: 'include' })
        .then((r) => r.json())
        .then((data) => { if (data.ok) setContactoOpts(data.contactos || []); })
        .catch(() => {});
    }, 100);
    return () => window.clearTimeout(temporizador);
  }, [form.nit]);

  useEffect(() => {
    if (!form.cliente_recibe_nombre || form.cliente_recibe_nombre.length < 2) return undefined;
    const temporizador = window.setTimeout(() => {
      const nit = form.nit || '';
      const url = nit
        ? `/api/clientes_contactos/buscar?q=${encodeURIComponent(form.cliente_recibe_nombre)}&nit_cliente=${encodeURIComponent(nit)}&limite=10`
        : `/api/clientes_contactos/buscar?q=${encodeURIComponent(form.cliente_recibe_nombre)}&limite=10`;
      fetch(url, { credentials: 'include' })
        .then((r) => r.json())
        .then((data) => {
          if (data.ok) {
            setContactoOpts(data.resultados || []);
            setShowContactoDropdown(true);
          }
        })
        .catch(() => {});
    }, 300);
    return () => window.clearTimeout(temporizador);
  }, [form.cliente_recibe_nombre, form.nit]);

  useEffect(() => {
    if (!form.transportador_nombre || form.transportador_nombre.length < 2) { setTransportadorOpts([]); return undefined; }
    const temporizador = window.setTimeout(() => {
      fetch(`/api/transportadores_externos/buscar?q=${encodeURIComponent(form.transportador_nombre)}&limite=10`, { credentials: 'include' })
        .then((r) => r.json())
        .then((data) => {
          if (data.ok) {
            setTransportadorOpts(data.resultados || []);
            setShowTransportadorDropdown(true);
          }
        })
        .catch(() => {});
    }, 250);
    return () => window.clearTimeout(temporizador);
  }, [form.transportador_nombre]);

  const onChange = (evento) => {
    const { name, value, type, checked } = evento.target;
    let nuevo = value;
    if (name === 'transportador_tel') nuevo = phoneMask(value);
    else if (name === 'transportador_cc') nuevo = cedulaMask(value);
    else if (name === 'documentos') nuevo = documentosMask(value);
    else if (name === 'nit') {
      nuevo = numericMask(value, true);
      setClienteCargado('');
    }
    else if (['cajas', 'bolsas', 'cayvas', 'sobres'].includes(name)) nuevo = numericMask(value, false);

    // Si el texto ya coincide exactamente con un cliente sugerido, completa
    // NIT/ciudad/dirección sin obligar a hacer clic en la lista.
    if (name === 'cliente') {
      const texto = String(nuevo || '').trim().toLowerCase();
      const digitos = String(nuevo || '').replace(/\D/g, '');
      const encontrado = clienteOpts.find((c) => (
        String(c.razon_social || '').trim().toLowerCase() === texto
        || (digitos.length >= 3 && String(c.nit || '').replace(/\D/g, '') === digitos)
      ));
      if (encontrado) {
        aplicarCliente(encontrado);
        return;
      }
    }

    setForm((actual) => ({ ...actual, [name]: type === 'checkbox' ? checked : nuevo }));
  };

  const seleccionarCliente = (cliente) => {
    aplicarCliente(cliente);
    setClienteOpts([]);
  };

  const autocompletarClientePorTexto = async (textoCrudo) => {
    const texto = String(textoCrudo || '').trim();
    if (!texto) return;
    const digitos = texto.replace(/\D/g, '');
    try {
      const respuesta = await fetch(
        `/api/clientes/buscar?q=${encodeURIComponent(texto)}&limite=10`,
        { credentials: 'include' },
      );
      const data = await respuesta.json();
      const resultados = data.resultados || [];
      setClienteOpts(resultados);
      const exacto = resultados.find((c) => (
        String(c.razon_social || '').trim().toLowerCase() === texto.toLowerCase()
        || (digitos.length >= 3 && String(c.nit || '').replace(/\D/g, '') === digitos)
      ));
      if (exacto) aplicarCliente(exacto);
    } catch {
      /* sin conexión: se mantiene lo escrito */
    }
  };

  const handleClienteBlur = () => {
    window.setTimeout(() => setMostrarClientes(false), 160);
    autocompletarClientePorTexto(form.cliente);
  };

  const handleClienteKeyDown = (evento) => {
    if (evento.key === 'Enter' && clienteOpts.length > 0) {
      evento.preventDefault();
      seleccionarCliente(clienteOpts[0]);
    }
  };

  const handleContactoSelect = (contacto) => {
    setForm((actual) => ({
      ...actual,
      cliente_recibe_nombre: contacto.nombre,
      cliente_recibe_contacto_id: contacto.id,
    }));
    setShowContactoDropdown(false);
  };

  const handleClienteRecibeChange = (evento) => {
    const value = evento.target.value;
    setForm((actual) => ({ ...actual, cliente_recibe_nombre: value, cliente_recibe_contacto_id: null }));
    setShowContactoDropdown(value.length >= 2);
  };

  const handleTransportadorSelect = (transportador) => {
    setForm((actual) => ({
      ...actual,
      transportador_nombre: transportador.nombre,
      transportador_cc: transportador.cc || '',
      transportador_tel: transportador.telefono || '',
      transportador_vehiculo: transportador.vehiculo || '',
      transportador_placa: transportador.placa || '',
      transportador_flete: transportador.flete || '',
    }));
    setShowTransportadorDropdown(false);
  };

  const handleTransportadorChange = (evento) => {
    const value = evento.target.value;
    setForm((actual) => ({ ...actual, transportador_nombre: value }));
    setShowTransportadorDropdown(value.length >= 2);
  };

  const handleTransportadorBlur = async () => {
    if (user?.rol !== 'administrativo') return;
    const nombre = String(form.transportador_nombre || '').trim();
    if (nombre.length < 2) return;
    if (guardandoTransportador || ultimoTransportadorGuardado.current === nombre) return;
    try {
      setGuardandoTransportador(true);
      const response = await fetch('/api/transportadores_externos/guardar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nombre,
          cc: form.transportador_cc || '',
          telefono: form.transportador_tel || '',
          vehiculo: form.transportador_vehiculo || '',
          placa: form.transportador_placa || '',
          flete: form.transportador_flete || '',
        }),
        credentials: 'include',
      });
      const data = await response.json();
      if (data.ok) ultimoTransportadorGuardado.current = nombre;
      setShowTransportadorDropdown(false);
    } catch (err) {
      console.warn('No se pudo guardar el transportador externo:', err);
    } finally {
      setGuardandoTransportador(false);
    }
  };

  const handleDocumentosBlur = () => {
    const formateado = formatInvoiceNumbersWithPrefix(form.documentos, form.prefijo);
    if (formateado !== form.documentos) setForm((actual) => ({ ...actual, documentos: formateado }));
  };

  const ajustarBulto = (campo, delta) => {
    setForm((actual) => ({ ...actual, [campo]: Math.max(0, Number(actual[campo] || 0) + delta) }));
  };

  const totalBultos = useMemo(() => (
    Number(form.cajas || 0) + Number(form.bolsas || 0) + Number(form.cayvas || 0) + Number(form.sobres || 0)
  ), [form.cajas, form.bolsas, form.cayvas, form.sobres]);

  const validarPaso = (numero) => {
    if (numero >= 2 && (!form.cliente.trim() || !form.ciudad.trim() || !form.direccion.trim())) {
      setError('Completa el cliente, la ciudad y la dirección antes de continuar.');
      setPaso(1);
      return false;
    }
    setError(null);
    return true;
  };

  const continuar = () => {
    if (!validarPaso(paso + 1)) return;
    setPaso((actual) => Math.min(3, actual + 1));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const retroceder = () => {
    setPaso((actual) => Math.max(1, actual - 1));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const onSubmit = async (evento) => {
    evento.preventDefault();
    if (!validarPaso(2)) return;
    setCargando(true);
    setError(null);
    try {
      const datosAGuardar = {
        ...form,
        cajas: Number(form.cajas) || 0,
        bolsas: Number(form.bolsas) || 0,
        cayvas: Number(form.cayvas) || 0,
        sobres: Number(form.sobres) || 0,
      };
      delete datosAGuardar.cliente_recibe_contacto_id;
      const data = await guiasApi.guiasCrear(datosAGuardar);
      if (data.ok && data.id) {
        try { window.localStorage.removeItem(DRAFT_KEY); } catch { /* ignora */ }
        showToast('Guía creada correctamente.');
        window.setTimeout(() => navigate(`/guia/${data.id}`), 250);
      } else {
        setError(data.error || 'No se pudo crear la guía');
      }
    } catch (err) {
      setError(err.error || 'Error al crear la guía');
    } finally {
      setCargando(false);
    }
  };

  const irAPaso = (numero) => {
    if (numero > paso && !validarPaso(numero)) return;
    setPaso(numero);
  };

  return (
    <AppShell
      title="Nueva guía"
      subtitle="Creas la guía como Ventas; CEDIS confirmará los bultos antes de entregar."
      breadcrumb="Nueva guía"
      actions={(
        <>
          <span className="autosave"><span className="punto" /> {guardado ? 'Borrador guardado' : 'Guardado automático'}</span>
          <button type="button" className="btn" onClick={() => navigate('/tablero')}>
            <Icon name="arrowLeft" size={15} /> Volver
          </button>
        </>
      )}
    >
      {error ? <div className="inline-alert" role="alert" style={{ marginBottom: 12 }}><Icon name="alert" size={16} /> {error}</div> : null}

      <form onSubmit={onSubmit} noValidate>
        <section className="panel" style={{ marginBottom: 14 }}>
          <div className="wizard-steps">
            {PASOS.map((item) => (
              <button
                key={item.numero}
                type="button"
                className={`wstep ${paso === item.numero ? 'active' : ''} ${paso > item.numero ? 'done' : ''}`.trim()}
                onClick={() => irAPaso(item.numero)}
              >
                <span className="n">{paso > item.numero ? <Icon name="check" size={11} /> : item.numero}</span>
                {item.titulo}
              </button>
            ))}
            <span className="updated-at" style={{ marginLeft: 'auto' }}>Paso {paso} de 3</span>
          </div>
        </section>

        <div className="wizard-body">
          <div className="wizard-main">
            {paso === 1 ? (
              <section className="panel">
                <div className="panel-head">
                  <div className="panel-title">Datos del cliente</div>
                  <span className="panel-sub" style={{ marginLeft: 'auto' }}>El NIT autocompleta los datos</span>
                </div>
                <div className="panel-body">
                  <div className="form-grid">
                    <label className="wide relative">
                      <span className="lbl">Cliente *</span>
                      <input
                        className="input"
                        name="cliente"
                        value={form.cliente}
                        onChange={onChange}
                        onFocus={() => setMostrarClientes(true)}
                        onBlur={handleClienteBlur}
                        onKeyDown={handleClienteKeyDown}
                        required
                        maxLength={200}
                        autoComplete="off"
                        placeholder="Nombre o NIT del cliente"
                      />
                      {mostrarClientes && clienteOpts.length > 0 ? (
                        <div className="dropdown">
                          {clienteOpts.slice(0, 6).map((cliente) => (
                            <div
                              key={`${cliente.nit}-${cliente.razon_social}`}
                              role="button"
                              tabIndex={0}
                              className="dropdown-option"
                              onMouseDown={() => seleccionarCliente(cliente)}
                            >
                              <strong>{cliente.razon_social}</strong>
                              <span>{cliente.nit} · {cliente.ciudad || 'Sin ciudad'}</span>
                            </div>
                          ))}
                        </div>
                      ) : null}
                      <span className="hint">
                        Escribe el nombre y elige una sugerencia (o pulsa Enter). Se llenan NIT, ciudad y dirección.
                      </span>
                    </label>
                    <label>
                      <span className="lbl">NIT</span>
                      <input className="input" name="nit" value={form.nit} onChange={onChange} maxLength={60} placeholder="900123456-1" />
                      <span className="hint">
                        Si el NIT existe, se completan el cliente, la ciudad y la dirección.
                      </span>
                      {clienteCargado ? (
                        <span className="hint" style={{ color: 'var(--success)', fontWeight: 600 }}>
                          Datos cargados desde el maestro: {clienteCargado}
                        </span>
                      ) : null}
                    </label>
                    <label>
                      <span className="lbl">Centro de operación</span>
                      <input className="input" name="centro_operacion" value={form.centro_operacion} onChange={onChange} maxLength={20} />
                    </label>
                    <label>
                      <span className="lbl">Ciudad *</span>
                      <input className="input" name="ciudad" value={form.ciudad} onChange={onChange} required maxLength={120} />
                    </label>
                    <label>
                      <span className="lbl">Dirección *</span>
                      <input className="input" name="direccion" value={form.direccion} onChange={onChange} required maxLength={300} />
                    </label>
                    <label>
                      <span className="lbl">Prefijo</span>
                      <select className="selectbox" name="prefijo" value={form.prefijo} onChange={onChange}>
                        <option value="FV">FV</option>
                        <option value="TB">TB</option>
                        <option value="PD">PD</option>
                        <option value="TR">TR</option>
                      </select>
                    </label>
                    <label>
                      <span className="lbl">Documentos</span>
                      <input
                        className="input"
                        name="documentos"
                        value={form.documentos}
                        onChange={onChange}
                        onBlur={handleDocumentosBlur}
                        maxLength={200}
                        placeholder="Ej: 123, 456 o FV123-FV456"
                      />
                      <span className="hint">Se normaliza como FV 123, TB 456, etc.</span>
                    </label>
                    <label className="wide">
                      <span className="lbl">Observaciones para CEDIS</span>
                      <textarea className="input" name="obs_ventas" value={form.obs_ventas} onChange={onChange} maxLength={1000} placeholder="Ej: mercancía refrigerada, entregar antes de las 5 p. m." />
                    </label>
                  </div>
                </div>
              </section>
            ) : null}

            {paso === 2 ? (
              <>
                <section className="panel">
                  <div className="panel-head">
                    <div className="panel-title">Bultos informados a CEDIS</div>
                    <span className="panel-sub" style={{ marginLeft: 'auto' }}>CEDIS los confirmará</span>
                  </div>
                  <div className="panel-body">
                    <div className="bultos-grid">
                      {[['cajas', 'Cajas'], ['bolsas', 'Bolsas'], ['cayvas', 'Cavas'], ['sobres', 'Sobres']].map(([campo, etiqueta]) => (
                        <div key={campo}>
                          <span className="lbl">{etiqueta}</span>
                          <div className="counter">
                            <button type="button" onClick={() => ajustarBulto(campo, -1)} aria-label={`Quitar ${etiqueta}`}>−</button>
                            <b className="num">{form[campo] ?? 0}</b>
                            <button type="button" onClick={() => ajustarBulto(campo, 1)} aria-label={`Agregar ${etiqueta}`}>+</button>
                          </div>
                        </div>
                      ))}
                      <label className="wide">
                        <span className="lbl">Otros (descripción)</span>
                        <input className="input" name="otros" value={form.otros} onChange={onChange} maxLength={200} />
                      </label>
                    </div>
                    <div className="total-bultos"><span>Total unidades</span><strong className="num">{totalBultos}</strong></div>
                  </div>
                </section>

                <section className="panel">
                  <div className="panel-head"><div className="panel-title">Flujo de la guía</div></div>
                  <div className="panel-body" style={{ display: 'grid', gap: 8 }}>
                    <label className={`flujo-card ${!form.envio_directo_cedis ? 'activo' : ''}`.trim()}>
                      <input
                        type="radio"
                        name="flujo"
                        checked={!form.envio_directo_cedis}
                        onChange={() => setForm((actual) => ({ ...actual, envio_directo_cedis: false }))}
                      />
                      <span className="grow">
                        <span className="flujo-title">Flujo normal (recomendado)</span>
                        <span className="flujo-sub">Bodega recibe → CEDIS controla → transportador entrega</span>
                      </span>
                    </label>
                    <label className={`flujo-card ${form.envio_directo_cedis ? 'activo' : ''}`.trim()}>
                      <input
                        type="radio"
                        name="flujo"
                        checked={form.envio_directo_cedis}
                        onChange={() => setForm((actual) => ({ ...actual, envio_directo_cedis: true }))}
                      />
                      <span className="grow">
                        <span className="flujo-title">Envío directo a CEDIS</span>
                        <span className="flujo-sub">El cliente recoge en sede; la guía se cierra en CEDIS</span>
                      </span>
                    </label>
                    <label className="check">
                      <input type="checkbox" name="generar_link_recibido" checked={form.generar_link_recibido} onChange={onChange} />
                      Generar link de recibido para el cliente
                    </label>
                  </div>
                </section>
              </>
            ) : null}

            {paso === 3 ? (
              <>
                <section className="panel">
                  <div className="panel-head">
                    <div className="panel-title">Transporte</div>
                    <span className="panel-sub" style={{ marginLeft: 'auto' }}>Datos del transportador (si aplica)</span>
                  </div>
                  <div className="panel-body">
                    <div className="form-grid">
                      <label className="wide relative">
                        <span className="lbl">Transportador</span>
                        <input
                          className="input"
                          name="transportador_nombre"
                          value={form.transportador_nombre}
                          onChange={handleTransportadorChange}
                          onBlur={handleTransportadorBlur}
                          onFocus={() => form.transportador_nombre.length >= 2 && setShowTransportadorDropdown(true)}
                          maxLength={120}
                          placeholder="Seleccione o escriba el nombre"
                          autoComplete="off"
                        />
                        {showTransportadorDropdown && transportadorOpts.length > 0 ? (
                          <div className="dropdown">
                            {transportadorOpts.slice(0, 5).map((transportador) => (
                              <div
                                key={transportador.id}
                                role="button"
                                tabIndex={0}
                                className="dropdown-option"
                                onMouseDown={() => handleTransportadorSelect(transportador)}
                              >
                                <strong>{transportador.nombre}</strong>
                                <span>
                                  {transportador.cc ? `CC ${transportador.cc}` : ''}
                                  {transportador.telefono ? ` · Tel ${transportador.telefono}` : ''}
                                  {transportador.placa ? ` · ${transportador.placa}` : ''}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : null}
                        {guardandoTransportador ? <span className="hint">Guardando transportador…</span> : null}
                      </label>
                      <label><span className="lbl">CC</span><input className="input" name="transportador_cc" value={form.transportador_cc} onChange={onChange} maxLength={50} /></label>
                      <label><span className="lbl">Teléfono</span><input className="input" name="transportador_tel" value={form.transportador_tel} onChange={onChange} maxLength={50} /></label>
                      <label><span className="lbl">Vehículo</span><input className="input" name="transportador_vehiculo" value={form.transportador_vehiculo} onChange={onChange} maxLength={80} /></label>
                      <label><span className="lbl">Placa</span><input className="input" name="transportador_placa" value={form.transportador_placa} onChange={onChange} maxLength={20} /></label>
                      <label><span className="lbl">Flete</span><input className="input" name="transportador_flete" value={form.transportador_flete} onChange={onChange} maxLength={40} /></label>
                    </div>
                    {user?.rol === 'administrativo' && form.transportador_nombre ? (
                      <p className="hint">Los datos del transportador se guardan para futuras guías.</p>
                    ) : null}
                  </div>
                </section>

                <section className="panel">
                  <div className="panel-head">
                    <div className="panel-title">Entrega en cliente</div>
                    <span className="panel-sub" style={{ marginLeft: 'auto' }}>Persona que recibe</span>
                  </div>
                  <div className="panel-body">
                    <label className="relative" style={{ display: 'block' }}>
                      <span className="lbl">Nombre de quien recibe</span>
                      <input
                        className="input"
                        name="cliente_recibe_nombre"
                        value={form.cliente_recibe_nombre}
                        onChange={handleClienteRecibeChange}
                        onFocus={() => form.cliente_recibe_nombre.length >= 2 && setShowContactoDropdown(true)}
                        onBlur={() => window.setTimeout(() => setShowContactoDropdown(false), 200)}
                        maxLength={120}
                        placeholder="Seleccione o escriba el nombre"
                        autoComplete="off"
                      />
                      {showContactoDropdown && contactoOpts.length > 0 ? (
                        <div className="dropdown">
                          {contactoOpts.slice(0, 5).map((contacto) => (
                            <div
                              key={contacto.id}
                              role="button"
                              tabIndex={0}
                              className="dropdown-option"
                              onMouseDown={() => handleContactoSelect(contacto)}
                            >
                              <strong>{contacto.nombre}</strong>
                              <span>{contacto.telefono ? `Tel ${contacto.telefono}` : ''}{contacto.cedula ? ` · CC ${contacto.cedula}` : ''}</span>
                            </div>
                          ))}
                        </div>
                      ) : null}
                      <span className="hint">
                        {form.nit ? `Contactos registrados para ${form.nit}` : 'Selecciona un cliente para ver sus contactos'}
                      </span>
                    </label>
                  </div>
                </section>
              </>
            ) : null}
          </div>

          <aside className="wizard-rail">
            <section className="panel summary">
              <div className="panel-head"><div className="panel-title">Resumen de la guía</div></div>
              <div className="panel-body">
                <div className="summary-row"><span>Cliente</span><b>{form.cliente || '—'}</b></div>
                <div className="summary-row"><span>NIT</span><b className="mono">{form.nit || '—'}</b></div>
                <div className="summary-row"><span>Ciudad</span><b>{form.ciudad || '—'}</b></div>
                <div className="summary-row"><span>Documentos</span><b>{form.documentos || '—'}</b></div>
                <div className="summary-row"><span>Flujo</span><b>{form.envio_directo_cedis ? 'Envío directo' : 'Normal'}</b></div>
                <div className="summary-total"><span>Total bultos</span><span className="num">{totalBultos}</span></div>

                {paso < 3 ? (
                  <>
                    <button type="button" className="btn btn-primary btn-block mt-3" onClick={continuar}>
                      Continuar <Icon name="arrowRight" size={15} />
                    </button>
                    <button type="submit" className="btn btn-block mt-2" disabled={cargando}>
                      {cargando ? 'Creando…' : 'Crear guía ahora'}
                    </button>
                  </>
                ) : (
                  <>
                    <button type="submit" className="btn btn-primary btn-block mt-3" disabled={cargando}>
                      {cargando ? 'Creando…' : 'Crear guía'}
                    </button>
                    <button type="button" className="btn btn-block mt-2" onClick={retroceder} disabled={cargando}>
                      Atrás
                    </button>
                  </>
                )}
                <p className="action-note" style={{ textAlign: 'center' }}>
                  Podrás revisar el acta después de crearla.
                </p>
              </div>
            </section>

            <section className="panel">
              <div className="panel-body">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 7 }}>
                  <span className="kpi-icon green"><Icon name="shield" size={15} /></span>
                  <div className="panel-title">Validación en línea</div>
                </div>
                <p className="nota">Los datos del cliente se autocompletan por NIT, el documento se normaliza y los bultos se validan en CEDIS.</p>
              </div>
            </section>

            <button type="button" className="btn btn-ghost btn-block" onClick={retroceder} disabled={paso === 1 || cargando}>
              <Icon name="chevronLeft" size={14} /> Paso anterior
            </button>
          </aside>
        </div>
      </form>
      <Toast toast={toast} onClose={closeToast} />
    </AppShell>
  );
}
