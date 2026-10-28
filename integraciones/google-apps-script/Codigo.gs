/**
 * Coodescor · Confirmación gratuita de recibido
 * Google Apps Script Web App + Google Sheets
 *
 * Variables obligatorias en Configuración del proyecto > Propiedades del script:
 *   TOKEN_SECRET  Clave compartida con el aplicativo local (firma de links).
 *   SYNC_SECRET   Clave compartida con el aplicativo local (consulta de pendientes).
 *   SHEET_NAME    Opcional. Por defecto: Confirmaciones.
 *
 * La hoja puede ser la hoja activa (script vinculado a la hoja) o abrirse por
 * SHEET_ID (script independiente).
 */

const PROPS = PropertiesService.getScriptProperties();
const SHEET_NAME = PROPS.getProperty('SHEET_NAME') || 'Confirmaciones';
const DIAS_VIGENCIA = 7;
const ESTADOS_MARCADOS = ['aplicada', 'duplicada', 'error'];
const ENCABEZADOS = [
  'id', 'token', 'guia_id', 'numero_guia', 'cliente',
  'fecha_confirmacion', 'nombre', 'observaciones',
  'estado', 'fecha_aplicacion', 'detalle',
];

function doGet(e) {
  const p = (e && e.parameter) || {};
  try {
    if (p.accion === 'pendientes') return respuestaJson_(pendientes_(p));
    if (p.accion === 'marcar') return respuestaJson_(marcar_(p));
    return pagina_(p.t || '');
  } catch (err) {
    return paginaError_(err && err.message ? err.message : String(err));
  }
}

function doPost(e) {
  try {
    return confirmar_((e && e.parameter) || {});
  } catch (err) {
    return paginaError_(err && err.message ? err.message : String(err));
  }
}

/* -------------------------------------------------------------------------- */
/* Página pública                                                             */
/* -------------------------------------------------------------------------- */

function pagina_(token) {
  token = String(token || '').trim();
  if (!token) return paginaError_('El enlace no contiene un código de confirmación.');

  const info = validarToken_(token);
  if (info.error) return paginaError_(info.error);
  if (buscarFilaToken_(token)) {
    return paginaError_('Este enlace ya fue utilizado. Si necesitas otra confirmación, solicita un nuevo link.');
  }

  const t = HtmlService.createTemplateFromFile('Pagina');
  t.logoDataUri = LOGO_DATA_URI;
  t.token = token;
  t.guia = String(info.n || '');
  t.cliente = String(info.c || '');
  t.error = '';
  t.exito = false;
  t.nombreRecibe = '';
  t.fechaHora = fechaHoraActual_();
  t.postUrl = ScriptApp.getService().getUrl();
  return t.evaluate()
    .setTitle('Confirmar recibido · Coodescor')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function paginaError_(mensaje) {
  const t = HtmlService.createTemplateFromFile('Pagina');
  t.logoDataUri = LOGO_DATA_URI;
  t.token = '';
  t.guia = '';
  t.cliente = '';
  t.error = String(mensaje || 'No se pudo procesar la confirmación.');
  t.exito = false;
  t.nombreRecibe = '';
  t.fechaHora = fechaHoraActual_();
  t.postUrl = ScriptApp.getService().getUrl();
  return t.evaluate()
    .setTitle('Confirmar recibido · Coodescor')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function confirmar_(p) {
  const token = String(p.token || '').trim();
  const nombre = String(p.nombre || '').trim();
  const observaciones = String(p.observaciones || '').trim();

  if (!token) throw new Error('Falta el código de confirmación.');
  if (!nombre) throw new Error('Escribe el nombre de quien recibe.');
  if (nombre.length > 120) throw new Error('El nombre es demasiado largo.');
  if (observaciones.length > 500) throw new Error('Las observaciones son demasiado largas.');

  const info = validarToken_(token);
  if (info.error) throw new Error(info.error);

  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    if (buscarFilaToken_(token)) {
      throw new Error('Este enlace ya fue utilizado. No se registró dos veces.');
    }
    const hoja = asegurarHoja_();
    const fecha = new Date();
    hoja.appendRow([
      Utilities.getUuid(),
      token,
      Number(info.g || 0),
      String(info.n || ''),
      String(info.c || ''),
      fecha,
      nombre,
      observaciones,
      'pendiente',
      '',
      '',
    ]);

    const t = HtmlService.createTemplateFromFile('Pagina');
    t.logoDataUri = LOGO_DATA_URI;
    t.token = '';
    t.guia = String(info.n || '');
    t.cliente = String(info.c || '');
    t.error = '';
    t.exito = true;
    t.nombreRecibe = nombre;
    t.fechaHora = Utilities.formatDate(fecha, Session.getScriptTimeZone(), 'dd/MM/yyyy HH:mm:ss');
    t.postUrl = ScriptApp.getService().getUrl();
    return t.evaluate()
      .setTitle('Recibido confirmado · Coodescor')
      .addMetaTag('viewport', 'width=device-width, initial-scale=1');
  } finally {
    lock.releaseLock();
  }
}

/* -------------------------------------------------------------------------- */
/* API para el aplicativo local                                               */
/* -------------------------------------------------------------------------- */

function pendientes_(p) {
  exigirSecreto_(p);
  const hoja = asegurarHoja_();
  const filas = filasDatos_(hoja);
  const pendientes = [];
  filas.forEach((fila) => {
    if (String(fila.estado || '') !== 'pendiente') return;
    pendientes.push({
      id: String(fila.id || ''),
      guia_id: Number(fila.guia_id || 0),
      numero_guia: String(fila.numero_guia || ''),
      cliente: String(fila.cliente || ''),
      fecha_confirmacion: fila.fecha_confirmacion instanceof Date
        ? fila.fecha_confirmacion.toISOString()
        : String(fila.fecha_confirmacion || ''),
      nombre: String(fila.nombre || ''),
      observaciones: String(fila.observaciones || ''),
    });
  });
  return { ok: true, pendientes: pendientes, total: pendientes.length };
}

function marcar_(p) {
  exigirSecreto_(p);
  const id = String(p.id || '').trim();
  const estado = String(p.estado || '').trim().toLowerCase();
  const detalle = String(p.detalle || '').trim();
  if (!id) throw new Error('Falta el id de la confirmación.');
  if (ESTADOS_MARCADOS.indexOf(estado) === -1) {
    throw new Error('Estado inválido. Use aplicada, duplicada o error.');
  }
  const hoja = asegurarHoja_();
  const lastRow = hoja.getLastRow();
  if (lastRow < 2) throw new Error('No hay confirmaciones registradas.');
  const rango = hoja.getRange(2, 1, lastRow - 1, ENCABEZADOS.length).getValues();
  for (let i = 0; i < rango.length; i += 1) {
    if (String(rango[i][0]) !== id) continue;
    hoja.getRange(i + 2, 9).setValue(estado);
    hoja.getRange(i + 2, 10).setValue(new Date());
    hoja.getRange(i + 2, 11).setValue(detalle.slice(0, 500));
    return { ok: true, id: id, estado: estado };
  }
  throw new Error('No se encontró la confirmación con ese id.');
}

function exigirSecreto_(p) {
  const esperado = PROPS.getProperty('SYNC_SECRET') || '';
  if (!esperado) throw new Error('Falta configurar SYNC_SECRET en Apps Script.');
  if (String(p.secret || '') !== esperado) throw new Error('No autorizado.');
}

/* -------------------------------------------------------------------------- */
/* Token firmado                                                              */
/* -------------------------------------------------------------------------- */

function validarToken_(token) {
  const partes = String(token || '').split('.');
  if (partes.length !== 2) return { error: 'El enlace de confirmación no es válido.' };
  const payloadB64 = partes[0];
  const firma = partes[1];
  const esperada = hmac_(payloadB64);
  if (!compararSeguro_(firma, esperada)) {
    return { error: 'El enlace de confirmación no es válido.' };
  }
  let payload;
  try {
    payload = JSON.parse(Utilities.newBlob(
      Utilities.base64DecodeWebSafe(payloadB64)
    ).getDataAsString('UTF-8'));
  } catch (err) {
    return { error: 'El enlace de confirmación no es válido.' };
  }
  const ahora = Math.floor(Date.now() / 1000);
  if (!payload || !payload.exp || ahora > Number(payload.exp)) {
    return { error: 'El enlace de confirmación venció. Solicita un nuevo link.' };
  }
  if (!payload.g || !payload.n) {
    return { error: 'El enlace de confirmación está incompleto.' };
  }
  return payload;
}

function hmac_(texto) {
  const secreto = PROPS.getProperty('TOKEN_SECRET') || '';
  if (!secreto) throw new Error('Falta configurar TOKEN_SECRET en Apps Script.');
  const bytes = Utilities.computeHmacSha256Signature(texto, secreto);
  return Utilities.base64EncodeWebSafe(bytes).replace(/=+$/, '');
}

function compararSeguro_(a, b) {
  a = String(a || '');
  b = String(b || '');
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

/* -------------------------------------------------------------------------- */
/* Google Sheets                                                              */
/* -------------------------------------------------------------------------- */

function asegurarHoja_() {
  let libro = SpreadsheetApp.getActiveSpreadsheet();
  if (!libro) {
    const id = PROPS.getProperty('SHEET_ID');
    if (!id) throw new Error('Falta SHEET_ID o vincular el script a una hoja de cálculo.');
    libro = SpreadsheetApp.openById(id);
  }
  let hoja = libro.getSheetByName(SHEET_NAME);
  if (!hoja) hoja = libro.insertSheet(SHEET_NAME);
  if (hoja.getLastRow() === 0) {
    hoja.appendRow(ENCABEZADOS);
    hoja.getRange(1, 1, 1, ENCABEZADOS.length).setFontWeight('bold');
    hoja.freezeRows(1);
    hoja.setColumnWidth(1, 280);
    hoja.setColumnWidth(2, 420);
    hoja.setColumnWidth(7, 160);
    hoja.setColumnWidth(8, 240);
  }
  return hoja;
}

function filasDatos_(hoja) {
  const lastRow = hoja.getLastRow();
  if (lastRow < 2) return [];
  const valores = hoja.getRange(2, 1, lastRow - 1, ENCABEZADOS.length).getValues();
  return valores.map((fila) => {
    const obj = {};
    ENCABEZADOS.forEach((nombre, i) => { obj[nombre] = fila[i]; });
    return obj;
  });
}

function buscarFilaToken_(token) {
  const hoja = asegurarHoja_();
  const lastRow = hoja.getLastRow();
  if (lastRow < 2) return null;
  const valores = hoja.getRange(2, 2, lastRow - 1, 1).getValues();
  for (let i = 0; i < valores.length; i += 1) {
    if (String(valores[i][0]) === String(token)) return i + 2;
  }
  return null;
}

function respuestaJson_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function fechaHoraActual_() {
  return Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'dd/MM/yyyy HH:mm:ss');
}
