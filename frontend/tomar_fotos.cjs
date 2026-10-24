const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  
  // 1. Frontend (React/Vite)
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'frontend-react.png', fullPage: true });
  console.log('1. Frontend React guardado: frontend-react.png');
  
  // 2. Maqueta UX (HTML estático)
  await page.goto('http://localhost:8000/ux-propuesta-preview.html', { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'ux-maqueta.png', fullPage: true });
  console.log('2. Maqueta UX guardada: ux-maqueta.png');
  
  // 3. Login backend
  await page.goto('http://localhost:8000/login', { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'backend-login.png', fullPage: true });
  console.log('3. Login backend guardada: backend-login.png');
  
  await browser.close();
  console.log('Completado');
})();