import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as guiasApi from '../api/guias';
import api from '../api';
import { GuiaProvider, useGuias } from '../contexts/GuiaContext';
import './NuevaGuia.css';
import { 
  numericMask, 
  phoneMask, 
  cedulaMask, 
  documentosMask,
  formatInvoiceNumbersWithPrefix 
} from '../utils/format';

export default function NuevaGuia() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
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
    cliente_recibe_contacto_id: null, // ID del contacto seleccionado
    cajas: 0,
    bolsas: 0,
    cayvas: 0,
    sobres: 0,
    otros: '',
    generar_link_recibido: false,
  });
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [estados, setEstados] = useState([]);
  const [clienteOpts, setClienteOpts] = useState([]);
  const [contactoOpts, setContactoOpts] = useState([]);
  const [showContactoDropdown, setShowContactoDropdown] = useState(false);
  const [transportadorOpts, setTransportadorOpts] = useState([]);
  const [showTransportadorDropdown, setShowTransportadorDropdown] = useState(false);
  const [guardandoTransportador, setGuardandoTransportador] = useState(false);
  const ultimoTransportadorGuardado = useRef('');

  // Autocompletado de clientes
  useEffect(() => {
    if (!form.cliente || form.cliente.length < 1) { 
      setClienteOpts([]); 
      return; 
    }
    const t = setTimeout(() => {
      fetch(`/api/clientes/buscar?q=${encodeURIComponent(form.cliente)}&limite=10`, { 
        credentials: 'include' 
      })
        .then(r => r.json())
        .then(d => setClienteOpts(d.resultados || []))
        .catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [form.cliente]);

  // Autocompletado de contactos cuando se selecciona un cliente
  useEffect(() => {
    if (!form.nit) { 
      setContactoOpts([]); 
      return; 
    }
    const t = setTimeout(() => {
      fetch(`/api/clientes_contactos/por_cliente?nit_cliente=${encodeURIComponent(form.nit)}&limite=20`, { 
        credentials: 'include' 
      })
        .then(r => r.json())
        .then(d => {
          if (d.ok) {
            setContactoOpts(d.contactos || []);
          }
        })
        .catch(() => {});
    }, 100);
    return () => clearTimeout(t);
  }, [form.nit]);

  // También buscar contactos cuando se busca por nombre
  useEffect(() => {
    if (!form.cliente_recibe_nombre || form.cliente_recibe_nombre.length < 2) { 
      return; 
    }
    const t = setTimeout(() => {
      const nit = form.nit || '';
      const url = nit 
        ? `/api/clientes_contactos/buscar?q=${encodeURIComponent(form.cliente_recibe_nombre)}&nit_cliente=${encodeURIComponent(nit)}&limite=10`
        : `/api/clientes_contactos/buscar?q=${encodeURIComponent(form.cliente_recibe_nombre)}&limite=10`;
      fetch(url, { credentials: 'include' })
        .then(r => r.json())
        .then(d => {
          if (d.ok) {
            setContactoOpts(d.resultados || []);
            setShowContactoDropdown(true);
          }
        })
        .catch(() => {});
    }, 300);
    return () => clearTimeout(t);
  }, [form.cliente_recibe_nombre, form.nit]);

  // Autocompletado para transportadores externos
  useEffect(() => {
    if (!form.transportador_nombre || form.transportador_nombre.length < 2) { 
      setTransportadorOpts([]);
      return; 
    }
    const t = setTimeout(() => {
      fetch(`/api/transportadores_externos/buscar?q=${encodeURIComponent(form.transportador_nombre)}&limite=10`, { 
        credentials: 'include' 
      })
        .then(r => r.json())
        .then(d => {
          if (d.ok) {
            setTransportadorOpts(d.resultados || []);
            setShowTransportadorDropdown(true);
          }
        })
        .catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [form.transportador_nombre]);

  const onChange = (e) => {
    const { name, value, type, checked } = e.target;
    let v = value;
    
    // Aplicar máscaras según el campo
    if (name === 'transportador_tel') {
      v = phoneMask(value);
    } else if (name === 'transportador_cc') {
      v = cedulaMask(value);
    } else if (name === 'documentos') {
      v = documentosMask(value);
    } else if (name === 'nit') {
      // El NIT lleva dígito de verificación ("900123456-1"); no se debe borrar
      // el guion, porque el autocompletado y el maestro de clientes lo usan.
      v = numericMask(value, true);
    } else if (['cajas', 'bolsas', 'cayvas', 'sobres'].includes(name)) {
      v = numericMask(value, false);
    }
    
    setForm((f) => ({
      ...f,
      [name]: type === 'checkbox' ? checked : v,
    }));

    // Autocompletar datos del cliente al escribir/elegir una coincidencia.
    if (name === 'cliente') {
      const texto = String(value || '').trim().toLowerCase();
      const encontrado = clienteOpts.find(
        (c) => String(c.nit || '').toLowerCase() === texto
          || String(c.razon_social || '').toLowerCase() === texto,
      );
      if (encontrado) {
        setForm((f) => ({
          ...f,
          cliente: encontrado.razon_social || f.cliente,
          nit: encontrado.nit || f.nit,
          ciudad: encontrado.ciudad || f.ciudad,
          direccion: encontrado.direccion || f.direccion,
        }));
      }
    }
  };

  // Manejar selección de contacto
  const handleContactoSelect = (contacto) => {
    setForm(prev => ({
      ...prev,
      cliente_recibe_nombre: contacto.nombre,
      cliente_recibe_contacto_id: contacto.id,
    }));
    setShowContactoDropdown(false);
  };

  // Manejar change del campo cliente_recibe_nombre
  const handleClienteRecibeChange = (e) => {
    const value = e.target.value;
    setForm(prev => ({
      ...prev,
      cliente_recibe_nombre: value,
      cliente_recibe_contacto_id: null, // Reset al escribir manualmente
    }));
    setShowContactoDropdown(value.length >= 2);
  };

  // Manejar selección de transportador externo
  const handleTransportadorSelect = (transportador) => {
    setForm(prev => ({
      ...prev,
      transportador_nombre: transportador.nombre,
      transportador_cc: transportador.cc || '',
      transportador_tel: transportador.telefono || '',
      transportador_vehiculo: transportador.vehiculo || '',
      transportador_placa: transportador.placa || '',
      transportador_flete: transportador.flete || '',
    }));
    setShowTransportadorDropdown(false);
  };

  // Manejar change del campo transportador_nombre
  const handleTransportadorChange = (e) => {
    const value = e.target.value;
    setForm(prev => ({
      ...prev,
      transportador_nombre: value,
    }));
    setShowTransportadorDropdown(value.length >= 2);
    // El guardado automático ocurre SOLO en onBlur (handleTransportadorBlur).
    // Antes se guardaba en cada tecla y se duplicaban transportadores.
  };

  // Manejar blur del campo transportador_nombre para guardar (una sola vez)
  const handleTransportadorBlur = async () => {
    if (user?.rol !== 'administrativo') return;
    const nombre = (form.transportador_nombre || '').trim();
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

  // Formatear documentos automáticamente al hacer blur
  const handleDocumentosBlur = (e) => {
    const value = e.target.value;
    const formatted = formatInvoiceNumbersWithPrefix(value, form.prefijo);
    if (value !== formatted) {
      setForm(prev => ({
        ...prev,
        documentos: formatted,
      }));
    }
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setCargando(true);
    setError(null);
    try {
      // Si se seleccionó un contacto existente, incluir su ID para guardarlo
      const datosAGuardar = {
        ...form,
        cajas: Number(form.cajas) || 0,
        bolsas: Number(form.bolsas) || 0,
        cayvas: Number(form.cayvas) || 0,
        sobres: Number(form.sobres) || 0,
      };
      // cliente_recibe_contacto_id se quitó: el backend no lo consume, así que
      // guardarlo daba una falsa sensación de que el contacto quedaba asociado.
      delete datosAGuardar.cliente_recibe_contacto_id;
      
      const data = await guiasApi.guiasCrear(datosAGuardar);
      if (data.ok && data.id) {
        navigate(`/guia/${data.id}`);
      } else {
        setError(data.error || 'No se pudo crear la guía');
      }
    } catch (err) {
      setError(err.error || 'Error al crear la guía');
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="nueva-guia">
      <header className="nueva-guia-header">
        <div>
          <Link to="/tablero" className="btn-mini">← Volver</Link>
          <h1>Nueva guía</h1>
        </div>
        <div className="nueva-guia-usuario">
          <span>{user?.nombre || user?.usuario}</span>
          <button onClick={logout} className="btn-mini">Salir</button>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <form className="card form" onSubmit={onSubmit}>
        <h2>Datos generales</h2>
        <label>
          Cliente
          <input 
            name="cliente" 
            value={form.cliente} 
            onChange={onChange} 
            required 
            maxLength={200} 
            list="cliente-list"
          />
          <datalist id="cliente-list">
            {clienteOpts.map((c, i) => (
              <option key={i} value={c.razon_social || c.nit}>{c.nit} - {c.razon_social}</option>
            ))}
          </datalist>
        </label>
        <label>
          Ciudad
          <input name="ciudad" value={form.ciudad} onChange={onChange} required maxLength={120} />
        </label>
        <label>
          Dirección
          <input name="direccion" value={form.direccion} onChange={onChange} required maxLength={300} />
        </label>
        <label>
          Documentos
          <input 
            name="documentos" 
            value={form.documentos} 
            onChange={onChange} 
            onBlur={handleDocumentosBlur}
            maxLength={200} 
            placeholder="Ej: fv123, fv456 o 123-456"
          />
          <small className="hint">Formato: FV123, TB456 o 123-456 (se auto-formateará)</small>
        </label>
        <label>
          NIT
          <input name="nit" value={form.nit} onChange={onChange} maxLength={60} />
        </label>
        <label>
          Centro de operación
          <input name="centro_operacion" value={form.centro_operacion} onChange={onChange} maxLength={20} />
        </label>
        <label>
          Prefijo
          <select name="prefijo" value={form.prefijo} onChange={onChange}>
            <option value="FV">FV</option>
            <option value="TB">TB</option>
            <option value="PD">PD</option>
            <option value="TR">TR</option>
          </select>
        </label>
        <label>
          Observaciones ventas
          <textarea name="obs_ventas" value={form.obs_ventas} onChange={onChange} maxLength={1000} />
        </label>
        <label className="check">
          <input type="checkbox" name="envio_directo_cedis" checked={form.envio_directo_cedis} onChange={onChange} />
          Envío directo a CEDIS
        </label>
        <label className="check">
          <input type="checkbox" name="generar_link_recibido" checked={form.generar_link_recibido} onChange={onChange} />
          Generar link de recibido
        </label>

        <h2>Transporte</h2>
        <label>
          Transportador
          <input 
            name="transportador_nombre" 
            value={form.transportador_nombre} 
            onChange={handleTransportadorChange}
            onBlur={handleTransportadorBlur}
            onFocus={() => form.transportador_nombre.length >= 2 && setShowTransportadorDropdown(true)}
            maxLength={120} 
            placeholder="Seleccione o escriba el nombre"
            autoComplete="off"
          />
          {showTransportadorDropdown && transportadorOpts.length > 0 && (
            <div className="contacto-dropdown">
              {transportadorOpts.slice(0, 5).map((trans) => (
                <div 
                  key={trans.id} 
                  className="contacto-option"
                  onClick={() => handleTransportadorSelect(trans)}
                >
                  <strong>{trans.nombre}</strong>
                  {trans.cc && <span> - CC: {trans.cc}</span>}
                  {trans.telefono && <span> - Tel: {trans.telefono}</span>}
                  {trans.placa && <span> - Placa: {trans.placa}</span>}
                </div>
              ))}
            </div>
          )}
          {guardandoTransportador && <small className="hint">Guardando transportador...</small>}
        </label>
        <label>
          CC
          <input name="transportador_cc" value={form.transportador_cc} onChange={onChange} maxLength={50} placeholder="Solo números" />
        </label>
        <label>
          Tel
          <input name="transportador_tel" value={form.transportador_tel} onChange={onChange} maxLength={50} placeholder="Solo números" />
        </label>
        <label>
          Vehículo
          <input name="transportador_vehiculo" value={form.transportador_vehiculo} onChange={onChange} maxLength={80} />
        </label>
        <label>
          Placa
          <input name="transportador_placa" value={form.transportador_placa} onChange={onChange} maxLength={20} />
        </label>
        <label>
          Flete
          <input name="transportador_flete" value={form.transportador_flete} onChange={onChange} maxLength={40} />
        </label>
        {user?.rol === 'administrativo' && form.transportador_nombre && (
          <small className="hint">
            Los datos del transportador se guardarán automáticamente para futuras guías
          </small>
        )}

        <h2>Entrega en cliente</h2>
        <label>
          Nombre de quien recibe
          <input 
            name="cliente_recibe_nombre" 
            value={form.cliente_recibe_nombre} 
            onChange={handleClienteRecibeChange}
            onFocus={() => form.cliente_recibe_nombre.length >= 2 && setShowContactoDropdown(true)}
            onBlur={() => setTimeout(() => setShowContactoDropdown(false), 200)}
            maxLength={120} 
            placeholder="Seleccione o escriba el nombre"
            autoComplete="off"
          />
          {showContactoDropdown && contactoOpts.length > 0 && (
            <div className="contacto-dropdown">
              {contactoOpts.slice(0, 5).map((contacto) => (
                <div 
                  key={contacto.id} 
                  className="contacto-option"
                  onClick={() => handleContactoSelect(contacto)}
                >
                  <strong>{contacto.nombre}</strong>
                  {contacto.telefono && <span> - Tel: {contacto.telefono}</span>}
                  {contacto.cedula && <span> - CC: {contacto.cedula}</span>}
                </div>
              ))}
            </div>
          )}
          <small className="hint">
            {form.nit ? `Contactos registrados para ${form.nit}` : 'Seleccione un cliente primero para ver sus contactos'}
          </small>
        </label>

        <h2>Bultos</h2>
        <div className="bultos">
          <label>
            Cajas
            <input type="number" name="cajas" value={form.cajas} onChange={onChange} min={0} />
          </label>
          <label>
            Bolsas
            <input type="number" name="bolsas" value={form.bolsas} onChange={onChange} min={0} />
          </label>
          <label>
            Cayvas
            <input type="number" name="cayvas" value={form.cayvas} onChange={onChange} min={0} />
          </label>
          <label>
            Sobres
            <input type="number" name="sobres" value={form.sobres} onChange={onChange} min={0} />
          </label>
          <label>
            Otros
            <input name="otros" value={form.otros} onChange={onChange} maxLength={200} />
          </label>
        </div>

        <button type="submit" disabled={cargando}>
          {cargando ? 'Creando…' : 'Crear guía'}
        </button>
      </form>
    </div>
  );
}
