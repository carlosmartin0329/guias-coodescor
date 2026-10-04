import { test, expect } from '@playwright/test';

test.describe('Flujo completo: login → tablero → nueva guía → detalle → acciones', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('h1')).toContainText('Guías Coodescor');
  });

  test('Login admin + CAPTCHA', async ({ page }) => {
    // El CAPTCHA se resuelve automáticamente en test (backend devuelve token con respuesta conocida)
    await page.fill('input[name="usuario"]', 'admin');
    await page.fill('input[name="clave"]', 'admin123');

    // Obtener el token y respuesta del CAPTCHA desde la respuesta del backend
    const [captchaResponse] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/captcha/nuevo')),
      page.goto('/login'),
    ]);
    const captchaData = await captchaResponse.json();
    const reto = captchaData.token.split('|')[3];
    await page.fill('input[name="captcha"]', reto);

    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/tablero');
  });

  test('Tablero: listado, búsqueda y conteo', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="usuario"]', 'admin');
    await page.fill('input[name="clave"]', 'admin123');
    const [captchaResponse] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/captcha/nuevo')),
      page.goto('/login'),
    ]);
    const captchaData = await captchaResponse.json();
    const reto = captchaData.token.split('|')[3];
    await page.fill('input[name="captcha"]', reto);
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/tablero');

    // Verificar conteo
    await expect(page.locator('.conteo .chip-conteo')).toHaveCount(5);

    // Buscar
    await page.fill('input[placeholder*="Buscar"]', 'Cliente');
    await page.click('button[type="submit"]');
    await expect(page.locator('table tbody tr')).toHaveCount(0); // no hay coincidencias

    await page.fill('input[placeholder*="Buscar"]', '');
    await page.click('button[type="submit"]');
  });

  test('Nueva guía (rol ventas)', async ({ page }) => {
    // Login como ventas
    await page.goto('/login');
    await page.fill('input[name="usuario"]', 'ventas');
    await page.fill('input[name="clave"]', 'ventas123');
    const [captchaResponse] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/captcha/nuevo')),
      page.goto('/login'),
    ]);
    const captchaData = await captchaResponse.json();
    const reto = captchaData.token.split('|')[3];
    await page.fill('input[name="captcha"]', reto);
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/tablero');

    // Ir a nueva guía
    await page.click('text=+ Nueva guía');
    await expect(page).toHaveURL('/nueva-guia');

    // Llenar formulario
    await page.fill('input[name="cliente"]', 'Cliente Playwright');
    await page.fill('input[name="ciudad"]', 'Bogotá');
    await page.fill('input[name="direccion"]', 'Calle 123 # 45-67');
    await page.fill('input[name="documentos"]', 'FV 001');
    await page.fill('input[name="nit"]', '900123456-1');

    // Transporte
    await page.fill('input[name="transportador_nombre"]', 'Transporte Test');
    await page.fill('input[name="transportador_cc"]', '123456789');
    await page.fill('input[name="transportador_tel"]', '3001234567');
    await page.fill('input[name="transportador_vehiculo"]', 'Camión');
    await page.fill('input[name="transportador_placa"]', 'ABC123');
    await page.fill('input[name="transportador_flete"]', '50000');

    // Bultos
    await page.fill('input[name="cajas"]', '10');
    await page.fill('input[name="bolsas"]', '5');

    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/guia\/\d+/);
  });

  test('Detalle guía + acciones por rol', async ({ page }) => {
    // Login admin
    await page.goto('/login');
    await page.fill('input[name="usuario"]', 'admin');
    await page.fill('input[name="clave"]', 'admin123');
    const [captchaResponse] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/captcha/nuevo')),
      page.goto('/login'),
    ]);
    const captchaData = await captchaResponse.json();
    const reto = captchaData.token.split('|')[3];
    await page.fill('input[name="captcha"]', reto);
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/tablero');

    // Ir a la primera guía
    await page.click('table tbody tr:first-child');
    await expect(page).toHaveURL(/\/guia\/\d+/);

    // Verificar que hay botones de acción para admin
    await expect(page.locator('button:has-text("Anular guía")')).toBeVisible();
  });
});

test.describe('Admin DB', () => {
  test('Acceso solo admin', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="usuario"]', 'ventas');
    await page.fill('input[name="clave"]', 'ventas123');
    const [captchaResponse] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/captcha/nuevo')),
      page.goto('/login'),
    ]);
    const captchaData = await captchaResponse.json();
    const reto = captchaData.token.split('|')[3];
    await page.fill('input[name="captcha"]', reto);
    await page.click('button[type="submit"]');

    // Intentar acceder a /admin/db como ventas -> debe redirigir a /tablero
    await page.goto('/admin/db');
    await expect(page).toHaveURL('/tablero');
  });

  test('Admin ve el módulo de BD', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="usuario"]', 'admin');
    await page.fill('input[name="clave"]', 'admin123');
    const [captchaResponse] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/captcha/nuevo')),
      page.goto('/login'),
    ]);
    const captchaData = await captchaResponse.json();
    const reto = captchaData.token.split('|')[3];
    await page.fill('input[name="captcha"]', reto);
    await page.click('button[type="submit"]');

    await page.goto('/admin/db');
    await expect(page.locator('h1')).toContainText('Base de datos');
    await expect(page.locator('button:has-text("guias")')).toBeVisible();
  });
});