import { test, expect } from '@playwright/test';

/**
 * E2E del flujo real de la aplicación React contra el backend.
 *
 * El CAPTCHA se resuelve leyendo los glifos que el backend dibuja en el SVG
 * (antes el test intentaba `token.split('|')[3]`, pero el token es base64 y la
 * respuesta ya no viaja en él).
 */
async function resolverCaptcha(page) {
  const imagen = page.locator('.captcha-img');
  await expect(imagen).toBeVisible();
  await expect(page.locator('.captcha-img text').first()).toBeAttached({ timeout: 15000 });
  const caracteres = await page.locator('.captcha-img text').allTextContents();
  const codigo = caracteres.join('').replace(/\s/g, '').toUpperCase();
  expect(codigo.length).toBeGreaterThanOrEqual(4);
  return codigo;
}

async function login(page, usuario, clave) {
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: /Guías Coodescor/i })).toBeVisible();
  const codigo = await resolverCaptcha(page);
  await page.getByLabel('Usuario', { exact: false }).fill(usuario);
  await page.getByLabel('Contraseña', { exact: false }).fill(clave);
  await page.getByLabel('Código CAPTCHA', { exact: false }).fill(codigo);
  await page.getByRole('button', { name: /^Entrar$/ }).click();
  await expect(page).toHaveURL(/\/tablero/, { timeout: 15000 });
  await expect(page.getByRole('heading', { name: 'Guías Coodescor' })).toBeVisible();
}

async function logout(page) {
  await page.getByRole('button', { name: 'Salir' }).click();
  await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
}

test.describe('Autenticación y sesión', () => {
  test('el login de admin funciona y la sesión sobrevive a una recarga', async ({ page }) => {
    await login(page, 'admin', 'admin123');
    await page.reload();
    // Antes la recarga expulsaba al usuario porque no se consultaba la sesión.
    await expect(page).toHaveURL(/\/tablero/);
    await expect(page.getByRole('heading', { name: 'Guías Coodescor' })).toBeVisible();
    await logout(page);
  });

  test('credenciales incorrectas muestran error y no navegan', async ({ page }) => {
    await page.goto('/login');
    const codigo = await resolverCaptcha(page);
    await page.getByLabel('Usuario', { exact: false }).fill('admin');
    await page.getByLabel('Contraseña', { exact: false }).fill('clave-incorrecta');
    await page.getByLabel('Código CAPTCHA', { exact: false }).fill(codigo);
    await page.getByRole('button', { name: /^Entrar$/ }).click();
    await expect(page.getByRole('alert')).toContainText(/inválid|incorrect|bloquead/i);
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe('Tablero y guías', () => {
  test('el tablero lista guías y permite buscar', async ({ page }) => {
    await login(page, 'admin', 'admin123');
    await expect(page.locator('.tablero table')).toBeVisible();
    const buscador = page.getByPlaceholder(/Buscar por cliente/i);
    await buscador.fill('Cliente-inexistente-xyz');
    await page.getByRole('button', { name: 'Buscar' }).click();
    await expect(page.locator('.tablero tbody tr')).toHaveCount(0);
    await buscador.fill('');
    await page.getByRole('button', { name: 'Buscar' }).click();
    await logout(page);
  });

  test('ventas crea una guía y llega al detalle', async ({ page }) => {
    await login(page, 'ventas', 'ventas123');
    await page.getByRole('link', { name: /Nueva guía/i }).click();
    await expect(page).toHaveURL(/\/nueva-guia/);

    const sufijo = Date.now();
    await page.locator('input[name="cliente"]').fill(`Cliente Playwright ${sufijo}`);
    await page.locator('input[name="ciudad"]').fill('Bogotá');
    await page.locator('input[name="direccion"]').fill('Calle 123 # 45-67');
    await page.locator('input[name="nit"]').fill('900123456-1');
    await page.locator('input[name="documentos"]').fill('FV 001');
    await page.getByRole('button', { name: /Crear guía|Guardar guía|Registrar guía/i }).click();

    await expect(page).toHaveURL(/\/guia\/\d+/, { timeout: 15000 });
    await expect(page.getByRole('heading', { name: /Guía #/i })).toBeVisible();
    await logout(page);
  });
});

test.describe('Administración', () => {
  test('el módulo de base de datos carga para admin', async ({ page }) => {
    await login(page, 'admin', 'admin123');
    await page.getByRole('link', { name: /Base de datos/i }).click();
    await expect(page).toHaveURL(/\/admin\/db/);
    await expect(page.getByRole('heading', { name: 'Base de datos' })).toBeVisible();
    // La lista de bases dejó de renderizarse vacía: usa la clave "base".
    await expect(page.getByRole('button', { name: /^guias/ })).toBeVisible();
    await logout(page);
  });

  test('ventas no puede entrar a /admin/db', async ({ page }) => {
    await login(page, 'ventas', 'ventas123');
    await page.goto('/admin/db');
    await expect(page).toHaveURL(/\/tablero/);
    await logout(page);
  });
});
