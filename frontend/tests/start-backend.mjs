/**
 * Arranca el backend para las pruebas E2E de Playwright.
 *
 * - Usa un COODESCOR_DATA_DIR temporal: nunca toca la base real ni las firmas
 *   del cliente.
 * - Elige el intérprete de Python disponible (py -3 en Windows, python3 en CI).
 *
 * Lo invoca playwright.config.ts como webServer.
 */
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const frontendDir = process.cwd();
const backendDir = path.resolve(frontendDir, '..', 'backend');
const dataDir = path.join(os.tmpdir(), 'coodescor-playwright-data');
fs.mkdirSync(dataDir, { recursive: true });

const env = {
  ...process.env,
  COODESCOR_DATA_DIR: dataDir,
  PORT: '8000',
  HOST: '127.0.0.1',
  ENVIRONMENT: 'development',
};

const esWindows = process.platform === 'win32';
const comando = esWindows ? 'py' : 'python3';
const args = esWindows ? ['-3', 'run_app.py'] : ['run_app.py'];

const hijo = spawn(comando, args, {
  cwd: backendDir,
  env,
  stdio: 'inherit',
});

const cerrar = () => {
  try {
    hijo.kill();
  } catch {
    /* ignore */
  }
  process.exit(0);
};
process.on('SIGINT', cerrar);
process.on('SIGTERM', cerrar);
hijo.on('exit', (codigo) => process.exit(codigo ?? 0));
