import { test, expect } from '@playwright/test';
import path from 'path';

const TEST_FILE = path.resolve(__dirname, '../../envio_rendimentos/scripts/tmp/test_lgm.xlsx');

test('mostra banner de sessão expirada quando polling retorna 401', async ({ page, context }) => {
  // 1) login
  await page.goto('/accounts/login/');
  await page.fill('input[name=username]', 'testuser');
  await page.fill('input[name=password]', 'testpass');
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle' }),
    page.click('button[type=submit]')
  ]);

  // 2) abrir LGM e subir arquivo
  await page.goto('/lgm/');
  await page.setInputFiles('input[type=file]#arquivo', TEST_FILE);
  // trigger upload via form submit (client JS handles AJAX)
  await page.click('#uploadForm button[type=submit]');

  // esperar pelo card de progresso
  await page.waitForSelector('#progress-card', { timeout: 30000 });

  // 3) simular logout limpando cookies e forçar poll global
  await context.clearCookies();
  // chamar helper global que insere o banner quando receber 401
  await page.evaluate(() => {
    if (window.__lgm_force_poll) return window.__lgm_force_poll();
    if (window._lgm_pollProgress) return window._lgm_pollProgress();
    return null;
  });

  // assert: banner existe
  const banner = page.locator('#auth-banner');
  await expect(banner).toBeVisible({ timeout: 5000 });
});
