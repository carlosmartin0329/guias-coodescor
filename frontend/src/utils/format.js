export function formatInvoiceNumbers(input) {
  if (!input) return '';
  return String(input)
    .split('-')
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => {
      const m = p.match(/^fv\s*(\d+)$/i);
      return m ? `FV ${m[1]}` : p.toUpperCase();
    })
    .join(', ');
}

export function numericMask(value, allowDash = false) {
  const re = allowDash ? /[^0-9-]/g : /[^0-9]/g;
  return String(value || '').replace(re, '');
}
