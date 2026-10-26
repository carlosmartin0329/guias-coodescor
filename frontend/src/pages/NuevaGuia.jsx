import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as guiasApi from '../api/guias';
import AppShell from '../components/AppShell';
import Icon from '../components/Icon';
import SignaturePad from '../components/SignaturePad';
import { Toast, useToast } from '../components/ui';
import { numericMask, phoneMask, cedulaMask, documentosMask } from '../utils/format';

const DRAFT_KEY = 'guias.borrador.nueva-guia';
const PASOS = [
  { numero: 1, titulo: 'Cliente y documentos' },
  { numero: 2, titulo: 'Bultos y flujo' },
  { numero: 3, titulo: 'Confirmación y entrega' },
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
  cliente_recibe_nombre: '',
  cliente_recibe_contacto_id: null,
  cajas: 0,
  bolsas: 0,
  cayvas: 0,
  sobres: 0,
  otros: '',
  generar_link_recibido: false,
  captura_reclamo: false,
  reclamo_nombre: '',
  reclamo_cedula: '',
  reclamo_telefono: '',
};

export default function NuevaGuia() {
  const navigate = useNavigate();
  const { toast, showToast, closeToast } = useToast();
  const [form, setForm] = useState(FORM_INICIAL);
  const [paso, setPaso] = useState(1);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [clienteOpts, setClienteOpts] = useState([]);
  const [contactoOpts, setContactoOpts] = useState([]);
  const [showContactoDropdown, setShowContactoDropdown] = useState(false);
  const [guardado, setGuardado] = useState(false);
  const [mostrarClientes, setMostrarClientes] = useState(false);
  const [clienteCargado, setClienteCargado] = useState('');
  const [documentosFilas, setDocumentosFilas] = useState([{ prefijo: 'FV', numero: '' }]);
  const firmaReclamoRef = useRef(null);

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
          const filas = Array.isArray(guardadoPrevio._documentosFilas)
            ? guardadoPrevio._documentosFilas
            : null;
          const datosForm = { ...guardadoPrevio };
          delete datosForm._documentosFilas;
          setForm((actual) => ({ ...actual, ...datosForm }));
          if (filas && filas.length) setDocumentosFilas(filas);
        }
      }
    } catch {
      /* borrador ilegible: se ignora */
    }
  }, []);

  useEffect(() => {
    const temporizador = window.setTimeout(() => {
      try {
        window.localStorage.setItem(
          DRAFT_KEY,
          JSON.stringify({ ...form, _documentosFilas: documentosFilas }),
        );
        setGuardado(true);
        window.setTimeout(() => setGuardado(false), 1200);
      } catch {
        /* sin almacenamiento disponible */
      }
    }, 700);
    return () => window.clearTimeout(temporizador);
  }, [form, documentosFilas]);

  const sincronizarDocumentos = (filas) => {
    setDocumentosFilas(filas);
    setForm((actual) => ({
      ...actual,
      prefijo: filas[0]?.prefijo || actual.prefijo || 'FV',
      documentos: filas
        .filter((fila) => fila.numero.trim())
        .map((fila) => `${fila.prefijo} ${fila.numero.trim()}`)
        .join(' - '),
    }));
  };

  const cambiarDocumento = (indice, campo, valor) => {
    const filas = documentosFilas.map((fila, i) => (
      i === indice ? { ...fila, [campo]: valor } : fila
    ));
    sincronizarDocumentos(filas);
  };

  const agregarDocumento = () => {
    if (documentosFilas.length >= 50) return;
    sincronizarDocumentos([...documentosFilas, { prefijo: 'FV', numero: '' }]);
  };

  const quitarDocumento = (indice) => {
    const filas = documentosFilas.filter((_, i) => i !== indice);
    sincronizarDocumentos(filas.length ? filas : [{ prefijo: 'FV', numero: '' }]);
  };

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

  const onChange = (evento) => {
    const { name, value, type, checked } = evento.target;
    let nuevo = value;
    if (name === 'reclamo_cedula') nuevo = cedulaMask(value);
    else if (name === 'reclamo_telefono') nuevo = phoneMask(value);
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

  const continuar = (evento) => {
    // Evita que el navegador reutilice el botón como submit al cambiar de paso.
    evento?.preventDefault();
    if (!validarPaso(paso + 1)) return;
    setPaso((actual) => Math.min(3, actual + 1));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const retroceder = (evento) => {
    evento?.preventDefault();
    setPaso((actual) => Math.max(1, actual - 1));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const onSubmit = async (evento) => {
    evento.preventDefault();
    if (!validarPaso(2)) return;

    const filasDocumentos = documentosFilas.filter((fila) => fila.numero.trim());
    if (form.captura_reclamo) {
      if (!form.reclamo_nombre.trim()) {
        setError('Escribe el nombre de la persona que reclama.');
        setPaso(3);
        return;
      }
      if (!String(form.reclamo_cedula).replace(/\D/g, '')) {
        setError('Escribe la cédula de la persona que reclama.');
        setPaso(3);
        return;
      }
      if (!String(form.reclamo_telefono).replace(/\D/g, '')) {
        setError('Escribe el teléfono de la persona que reclama.');
        setPaso(3);
        return;
      }
      if (!firmaReclamoRef.current || firmaReclamoRef.current.isEmpty()) {
        setError('Falta la firma de la persona que reclama.');
        setPaso(3);
        return;
      }
    }

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
      // Ventas no captura datos del transportador: se asignan luego desde CEDIS.
      // Se limpian también si venían de un borrador antiguo.
      [
        'transportador_nombre', 'transportador_cc', 'transportador_tel',
        'transportador_vehiculo', 'transportador_placa', 'transportador_flete',
      ].forEach((campo) => delete datosAGuardar[campo]);
      if (filasDocumentos.length) {
        datosAGuardar.documentos_json = JSON.stringify(
          filasDocumentos.map((fila) => ({
            prefijo: fila.prefijo,
            numero: fila.numero.trim(),
          })),
        );
      }
      if (form.captura_reclamo) {
        datosAGuardar.firma_reclamo = firmaReclamoRef.current.getDataURL();
      } else {
        delete datosAGuardar.reclamo_nombre;
        delete datosAGuardar.reclamo_cedula;
        delete datosAGuardar.reclamo_telefono;
        delete datosAGuardar.firma_reclamo;
      }
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
                    <div className="wide">
                      <span className="lbl">Documentos y prefijos</span>
                      <div className="doc-editor">
                        {documentosFilas.map((fila, indice) => (
                          <div className="doc-row" key={`doc-${indice}`}>
                            <select
                              className="selectbox doc-prefix"
                              value={fila.prefijo}
                              aria-label={`Prefijo del documento ${indice + 1}`}
                              onChange={(evento) => cambiarDocumento(indice, 'prefijo', evento.target.value)}
                            >
                              <option value="FV">FV</option>
                              <option value="TB">TB</option>
                              <option value="PD">PD</option>
                              <option value="TR">TR</option>
                            </select>
                            <input
                              className="input"
                              name={indice === 0 ? 'documentos' : `documento_${indice + 1}`}
                              value={fila.numero}
                              aria-label={`Número del documento ${indice + 1}`}
                              onChange={(evento) => cambiarDocumento(indice, 'numero', documentosMask(evento.target.value))}
                              maxLength={40}
                              placeholder="Número del documento"
                            />
                            <button
                              type="button"
                              className="btn btn-sm"
                              onClick={() => quitarDocumento(indice)}
                              disabled={documentosFilas.length === 1 && !fila.numero}
                              title="Quitar documento"
                              aria-label={`Quitar documento ${indice + 1}`}
                            >
                              <Icon name="trash" size={14} />
                            </button>
                          </div>
                        ))}
                        <button type="button" className="btn btn-sm" onClick={agregarDocumento} disabled={documentosFilas.length >= 50}>
                          <Icon name="plus" size={14} /> Agregar documento
                        </button>
                      </div>
                      <span className="hint">Cada documento guarda su propio prefijo (FV, TB, PD, TR). Máximo 50.</span>
                    </div>
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

                    <div className="captura-reclamo">
                      <label className="check">
                        <input
                          type="checkbox"
                          name="captura_reclamo"
                          checked={form.captura_reclamo}
                          onChange={(evento) => {
                            const activo = evento.target.checked;
                            setForm((actual) => ({
                              ...actual,
                              captura_reclamo: activo,
                              ...(activo ? {} : {
                                reclamo_nombre: '',
                                reclamo_cedula: '',
                                reclamo_telefono: '',
                              }),
                            }));
                            if (!activo) firmaReclamoRef.current?.clear();
                          }}
                        />
                        Registrar datos de la persona que reclama en sede
                      </label>
                      {form.captura_reclamo ? (
                        <div className="captura-reclamo-form">
                          <div className="form-grid">
                            <label>
                              <span className="lbl">Nombre completo *</span>
                              <input
                                className="input"
                                name="reclamo_nombre"
                                value={form.reclamo_nombre}
                                onChange={onChange}
                                maxLength={120}
                                placeholder="Nombre de quien reclama"
                              />
                            </label>
                            <label>
                              <span className="lbl">Cédula *</span>
                              <input
                                className="input"
                                name="reclamo_cedula"
                                value={form.reclamo_cedula}
                                onChange={onChange}
                                maxLength={30}
                                inputMode="numeric"
                                placeholder="Solo números"
                              />
                            </label>
                            <label>
                              <span className="lbl">Teléfono *</span>
                              <input
                                className="input"
                                name="reclamo_telefono"
                                value={form.reclamo_telefono}
                                onChange={onChange}
                                maxLength={30}
                                inputMode="tel"
                                placeholder="Solo números"
                              />
                            </label>
                          </div>
                          <SignaturePad
                            ref={firmaReclamoRef}
                            label="Firma de la persona que reclama"
                            hint="Solo se guarda como captura de datos; CEDIS seguirá confirmando y cerrando la entrega."
                          />
                        </div>
                      ) : null}
                    </div>
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
                    <button key="btn-continuar" type="button" className="btn btn-primary btn-block mt-3" onClick={continuar}>
                      Continuar <Icon name="arrowRight" size={15} />
                    </button>
                    <button key="btn-crear-ahora" type="submit" className="btn btn-block mt-2" disabled={cargando}>
                      {cargando ? 'Creando…' : 'Crear guía ahora'}
                    </button>
                  </>
                ) : (
                  <>
                    <button key="btn-crear" type="submit" className="btn btn-primary btn-block mt-3" disabled={cargando}>
                      {cargando ? 'Creando…' : 'Crear guía'}
                    </button>
                    <button key="btn-atras" type="button" className="btn btn-block mt-2" onClick={retroceder} disabled={cargando}>
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
