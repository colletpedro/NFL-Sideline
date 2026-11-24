// Existing Playwright + Chrome only. No installation; synthetic demo server required.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const out = process.argv[2]; if (!out) throw Error('Evidence output directory required');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ executablePath: process.env.CHROME_EXECUTABLE, headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(() => sessionStorage.setItem('metrics-lab-mode', 'observations'));
    await page.goto('http://127.0.0.1:18083/');
    const bundle = page.getByLabel('Bundle', { exact: true });
    const article = page.getByRole('article');
    const choose = async name => { await bundle.selectOption(name); await article.waitFor(); };
    await choose('synthetic');
    assert((await article.innerText()).includes('−<0,001'));
    await page.screenshot({ path: path.join(out, 'desktop-unknown.png'), fullPage: true });
    const details = page.getByText('Contagens, fontes ausentes e motivos', { exact: true });
    await details.focus(); await page.keyboard.press('Enter');
    assert(await details.evaluate(e => e.parentElement.open));
    assert(await details.evaluate(e => e === document.activeElement));
    const focusStyle = await details.evaluate(e => getComputedStyle(e).outlineStyle);
    assert.notEqual(focusStyle, 'none');
    await page.keyboard.press('Space');
    assert(!(await details.evaluate(e => e.parentElement.open)));
    // Freeze an old network response, switch role, then release it.
    let release; const gate = new Promise(r => release = r);
    let captured; const ready = new Promise(r => captured = r); let first = true;
    await page.route('**/__observations/synthetic/*', async route => {
      if (!first) return route.continue(); first = false;
      const response = await route.fetch(); captured(); await gate;
      try { await route.fulfill({ response }); } catch { /* cancelled old request */ }
    });
    await page.getByLabel('Fundamento', { exact: true }).selectOption('classified_pass');
    await ready; await page.getByLabel('Papel', { exact: true }).selectOption('def');
    await page.getByRole('heading', { name: 'EPA permitido', exact: true }).waitFor();
    const selected = await page.getByLabel('Período', { exact: true }).inputValue();
    release(); await page.unrouteAll({ behavior: 'wait' });
    await page.getByText('Identidades para rastreabilidade', { exact: true }).click();
    assert((await article.innerText()).includes(selected));
    assert.equal(await page.getByRole('article').count(), 1);
    await page.getByRole('button', { name: 'Recarregar catálogo da sessão' }).click();
    await page.getByRole('heading', { name: 'EPA permitido', exact: true }).waitFor();
    assert.equal(await page.getByLabel('Período', { exact: true }).inputValue(), selected);
    await page.reload(); await article.waitFor();
    assert.equal(await page.getByLabel('Período', { exact: true }).inputValue(), selected);
    await choose('zero'); assert((await article.innerText()).includes('zero conhecido'));
    await choose('no-epa'); let text = await article.innerText();
    assert(text.includes('Sem denominador') && text.includes('Jogadas observadas') && text.includes('3 / 1'));
    await choose('absent'); text = await article.innerText(); assert(text.includes('Desconhecido') && text.includes('Fonte ausente'));
    await choose('synthetic');
    const options = await page.getByLabel('Período', { exact: true }).locator('option').evaluateAll(es => es.map(e => ({ value: e.value, text: e.textContent })));
    const week3 = options.find(e => /semanas 3 ·/.test(e.text)); assert(week3);
    await page.getByLabel('Período', { exact: true }).selectOption(week3.value);
    await page.getByText(/Observação vazia sustentada:/).waitFor();
    await page.setViewportSize({ width: 390, height: 844 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    await page.screenshot({ path: path.join(out, 'mobile-complete-empty.png'), fullPage: true });
    await choose('history'); await page.getByLabel('Papel', { exact: true }).selectOption('def');
    await page.getByRole('heading', { name: 'EPA permitido', exact: true }).waitFor();
    assert((await article.innerText()).includes('2025 · POST · Referência histórica'));
    await details.focus(); await page.keyboard.press('Enter');
    assert(await details.evaluate(e => e.parentElement.open));
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    await page.screenshot({ path: path.join(out, 'mobile-history.png'), fullPage: true });
    await bundle.selectOption('real-archive'); await page.getByRole('alert').waitFor();
    assert.equal(await article.count(), 0);
    assert((await page.getByRole('alert').innerText()).includes('Nenhum outro bundle foi usado'));
    assert.deepEqual(errors, []);
    const report = { proof: 'CHROME_REAL_HTTP_SYNTHETIC_ONLY', chromeVersion: browser.version(), desktop: '1440x1000', mobile: '390x844', checks: ['five synthetic bundles', 'known zero', 'zero denominator with volume', 'unknown absent source', 'complete empty', 'tiny signed EPA', 'defensive meaning', 'historical POST isolated', 'native keyboard focus and expandable details', 'no horizontal mobile overflow', 'late response discarded', 'reload identity preserved', 'real unavailable without fallback'], humanComprehension: 'NOT_EVALUATED' };
    fs.writeFileSync(path.join(out, 'browser.json'), JSON.stringify(report, null, 2) + '\n'); console.log(report);
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
