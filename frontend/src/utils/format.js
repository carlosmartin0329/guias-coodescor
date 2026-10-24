const _PREFIJOS_DOC = 'fv|tb|pd|tr';
const _RE_DOC = new RegExp(`(?:${_PREFIJOS_DOC})\\s*-?\\s*\\d+|\\d+`, 'gi');

function _documentosEnTexto(input) {
  const texto = String(input || '').trim();
  if (!texto) return [];
  const tokens = texto.match(_RE_DOC) || [];
  if (!tokens.length) return [texto];
  return tokens;
}

function _formatearDocumento(token, defaultPrefix) {
  const conPrefijo = token.match(new RegExp(`^(${_PREFIJOS_DOC})\\s*-?\\s*(\\d+)$`, 'i'));
  if (conPrefijo) {
    return `${conPrefijo[1].toUpperCase()} ${conPrefijo[2]}`;
  }
  if (/^\d+$/.test(token)) {
    return defaultPrefix ? `${defaultPrefix} ${token}` : token;
  }
  return token.toUpperCase();
}

export function formatInvoiceNumbers(input) {
  if (!input) return '';
  // Antes se separaba SIEMPRE por guiones, así que "FV-123" se convertía en
  // "FV, FV 123" y corrompía el número de documento. Ahora se reconocen los
  // documentos con o sin prefijo y los separadores solo entre ellos.
  return _documentosEnTexto(input)
    .map((token) => _formatearDocumento(token, ''))
    .join(', ');
}

/**
 * Formatea múltiples números de factura con prefijo automático FV
 * Ejemplo: "fv123-fv456" o "123-456" con prefijo FV → "FV 123, FV 456"
 * 
 * @param {string} input - Cadena con números separados por guión
 * @param {string} defaultPrefix - Prefijo por defecto (ej: 'FV')
 * @returns {string} Cadena formateada
 */
export function formatInvoiceNumbersWithPrefix(input, defaultPrefix = 'FV') {
  if (!input) return '';
  return _documentosEnTexto(input)
    .map((token) => _formatearDocumento(token, defaultPrefix))
    .join(', ');
}

export function numericMask(value, allowDash = false) {
  const re = allowDash ? /[^0-9-]/g : /[^0-9]/g;
  return String(value || '').replace(re, '');
}

/**
 * Máscara para campos que aceptan solo números y guiones
 * Útil para documentos múltiples como "fv123-fv456"
 * 
 * @param {string} value - Valor a filtrar
 * @returns {string} Valor con solo dígitos y guiones
 */
export function numericWithDashMask(value) {
  return String(value || '').replace(/[^0-9-]/g, '');
}

/**
 * Máscara para números de teléfono
 * Acepta solo dígitos
 * 
 * @param {string} value - Valor a filtrar
 * @returns {string} Valor con solo dígitos
 */
export function phoneMask(value) {
  return String(value || '').replace(/[^0-9]/g, '');
}

/**
 * Máscara para cédula/número de documento
 * Acepta solo dígitos
 * 
 * @param {string} value - Valor a filtrar
 * @returns {string} Valor con solo dígitos
 */
export function cedulaMask(value) {
  return String(value || '').replace(/[^0-9]/g, '');
}

/**
 * Máscara para el campo de documentos (facturas, notas crédito, etc.)
 * Acepta dígitos, guiones y letras para prefijos (FV, TB, PD, TR)
 * 
 * @param {string} value - Valor a filtrar
 * @returns {string} Valor con solo caracteres válidos
 */
export function documentosMask(value) {
  // Permitir dígitos, guiones, y letras de prefijos
  return String(value || '').replace(/[^0-9a-zA-Z\s-]/g, '').toUpperCase();
}
