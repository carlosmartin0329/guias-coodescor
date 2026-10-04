import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as guiasApi from '../api/guias';
import * as estadosApi from '../api/guias';
import api from '../api';
import { GuiaProvider, useGuias } from '../contexts/GuiaContext';
import './NuevaGuia.css';

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
  const [conteo, setConteo] = useState([]);

  useEffect(() => {
    estadosApi.guiasEstados()
      .then((data) => setEstados(data.estados || []))
      .catch(() => {});
    guiasApi.guiasConteo()
      .then((data) => setConteo(data.conteo || []))
      .catch(() => {});
  }, []);

  const onChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((f) => ({
      ...f,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setCargando(true);
    setError(null);
    try {
      const data = await guiasApi.guiasCrear({
        ...form,
        cajas: Number(form.cajas) || 0,
        bolsas: Number(form.bolsas) || 0,
        cayvas: Number(form.cayvas) || 0,
        sobres: Number(form.sobres) || 0,
      });
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
          <input name="cliente" value={form.cliente} onChange={onChange} required maxLength={200} />
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
          <input name="documentos" value={form.documentos} onChange={onChange} maxLength={200} />
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
          <input name="transportador_nombre" value={form.transportador_nombre} onChange={onChange} maxLength={120} />
        </label>
        <label>
          CC
          <input name="transportador_cc" value={form.transportador_cc} onChange={onChange} maxLength={50} />
        </label>
        <label>
          Tel
          <input name="transportador_tel" value={form.transportador_tel} onChange={onChange} maxLength={50} />
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

        <h2>Entrega en cliente</h2>
        <label>
          Nombre de quien recibe
          <input name="cliente_recibe_nombre" value={form.cliente_recibe_nombre} onChange={onChange} maxLength={120} />
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
