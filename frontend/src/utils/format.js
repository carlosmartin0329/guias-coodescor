export function formatInvoiceNumbers(input) {
  if (!input) return '';
  return String(input)
    .split('-')
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => {
      // Manejar prefijos: fv, FV, tb, TB, pd, PD, tr, TR
      // Con o sin separadores entre prefijo y número
      const m = p.match(/^(fv|tb|pd|tr)\s*(\d+)$/i);
      if (m) {
        const prefix = m[1].toUpperCase();
        const number = m[2];
        return `${prefix} ${number}`;
      }
      // Si es solo números, intentar detectar prefijo en el contexto
      // o devolver como está en mayúsculas
      if (/^\d+$/.test(p)) {
        return p;
      }
      // Para otros casos, convertir a mayúsculas
      return p.toUpperCase();
    })
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
  
  return String(input)
    .split('-')
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p, index) => {
      // Verificar si ya tiene prefijo
      const existingPrefixMatch = p.match(/^(fv|tb|pd|tr)/i);
      if (existingPrefixMatch) {
        // Ya tiene prefijo, formatear
        const prefix = existingPrefixMatch[1].toUpperCase();
        const number = p.substring(existingPrefixMatch[1].length).trim();
        if (number) {
          return `${prefix} ${number}`;
        }
        return p.toUpperCase();
      }
      
      // Si es solo números, usar prefijo por defecto
      if (/^\d+$/.test(p)) {
        return `${defaultPrefix} ${p}`;
      }
      
      // Para otros casos (pueden ser prefijos sin números o texto libre)
      // Intentar detectar si el inicio es un prefijo conocido
      const prefixMatch = p.match(/^(fv|tb|pd|tr)/i);
      if (prefixMatch) {
        const prefix = prefixMatch[1].toUpperCase();
        const rest = p.substring(prefixMatch[1].length).trim();
        if (rest) {
          return `${prefix} ${rest}`;
        }
      }
      
      // Devolver en mayúsculas
      return p.toUpperCase();
    })
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
