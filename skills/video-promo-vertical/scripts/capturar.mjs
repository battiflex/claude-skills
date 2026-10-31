// Capturas de pantallas reales en formato celular, con emulacion movil REAL (DevTools Protocol):
// viewport 390x844, densidad 2.7692 (-> 1080 px de ancho), touch y user agent de Android.
// Chrome headless comun NO aplica el viewport movil de la pagina y el contenido sale cortado.
//
// Uso: node capturar.mjs <proyecto.json>
//   proyecto.capturas = [{ "nombre": "01_calendario", "url": "https://...", "espera": 6000 }, ...]
//   opcional por captura: "js" (se evalua en la pagina antes de capturar) y "espera_js" (ms, 1500)
//   proyecto.capturas_dir (relativo al json, default "capturas")
// Deja <nombre>.png (una pantalla) y <nombre>_largo.png (hasta 2400 px CSS, para hacer scroll).
// Oculta avisos de Google (AdSense) e iframes: no son parte del producto que se promociona.
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, mkdtempSync, readFileSync, existsSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { tmpdir } from 'node:os';

const proyectoPath = resolve(process.argv[2] || 'proyecto.json');
const P = JSON.parse(readFileSync(proyectoPath, 'utf8'));
const BASE = dirname(proyectoPath);
const OUT = resolve(BASE, P.capturas_dir || 'capturas');
mkdirSync(OUT, { recursive: true });

const CANDIDATOS = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
];
const CHROME = P.chrome || CANDIDATOS.find(existsSync);
if (!CHROME) { console.error('No encontre Chrome/Edge: poner "chrome" en el proyecto'); process.exit(1); }
const UA = 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36';
const PORT = 9300 + Math.floor(Math.random() * 500);
const perfil = mkdtempSync(join(tmpdir(), 'cap-'));
const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${perfil}`, 'about:blank'], { stdio: 'ignore' });
const dormir = ms => new Promise(r => setTimeout(r, ms));

async function destino() {
  for (let i = 0; i < 60; i++) {
    try {
      const l = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
      const p = l.find(x => x.type === 'page');
      if (p) return p.webSocketDebuggerUrl;
    } catch (e) {}
    await dormir(250);
  }
  throw new Error('Chrome no respondio');
}

const ws = new WebSocket(await destino());
await new Promise(r => ws.addEventListener('open', r, { once: true }));
let id = 0; const pend = new Map();
ws.addEventListener('message', ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
  // Un confirm()/alert() de la pagina frena todo (Runtime.evaluate no vuelve nunca): se acepta solo.
  // Paso con la promo del Super 8: "¿Reemplazar el que tenés en este celular?" colgaba las capturas.
  if (m.method === 'Page.javascriptDialogOpening') {
    ws.send(JSON.stringify({ id: ++id, method: 'Page.handleJavaScriptDialog', params: { accept: true } }));
  }
});
const cdp = (method, params = {}) => new Promise(r => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });

await cdp('Page.enable');
await cdp('Emulation.setUserAgentOverride', { userAgent: UA, platform: 'Android' });
await cdp('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2.7692, mobile: true });
await cdp('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });

const cssExtra = (P.ocultar_css || '').replace(/`/g, '');
const ocultar = `(() => { const s = document.createElement('style');
  s.textContent = 'ins, ins.adsbygoogle, iframe, [id^="google_ads"], [id^="aswift"], .adsbygoogle, [data-ad-client], [data-ad-slot] { display:none !important; height:0 !important; } ${cssExtra}';
  document.head.appendChild(s); document.querySelectorAll('ins, iframe').forEach(e => e.remove()); })()`;

for (const c of P.capturas) {
  await cdp('Page.navigate', { url: c.url });
  await dormir(c.espera || 6000);
  // "js" opcional: se corre en la pagina antes de capturar, para lo que un clic haria
  // (sacar un filtro, cerrar un cartel, abrir una pestaña). "espera_js" ms despues (1500).
  if (c.js) { await cdp('Runtime.evaluate', { expression: c.js }); await dormir(c.espera_js || 1500); }
  await cdp('Runtime.evaluate', { expression: ocultar }); await dormir(600);
  let r = await cdp('Page.captureScreenshot', { format: 'png' });
  writeFileSync(join(OUT, c.nombre + '.png'), Buffer.from(r.result.data, 'base64'));
  // larga: scroll por toda la pagina para disparar lo diferido (lazy), despues captura entera
  const alto = (await cdp('Runtime.evaluate', { expression: 'Math.min(document.documentElement.scrollHeight, 2400)', returnByValue: true })).result.result.value;
  for (let y = 0; y < alto; y += 600) { await cdp('Runtime.evaluate', { expression: `scrollTo(0, ${y})` }); await dormir(700); }
  await cdp('Runtime.evaluate', { expression: ocultar });
  await cdp('Runtime.evaluate', { expression: 'scrollTo(0, 0)' }); await dormir(800);
  r = await cdp('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: 0, y: 0, width: 390, height: alto, scale: 1 } });
  writeFileSync(join(OUT, c.nombre + '_largo.png'), Buffer.from(r.result.data, 'base64'));
  const ancho = (await cdp('Runtime.evaluate', { expression: 'document.documentElement.scrollWidth', returnByValue: true })).result.result.value;
  console.log(c.nombre.padEnd(20), 'ok  alto', alto, ' ancho contenido', ancho, ancho > 390 ? '(desborda: revisar)' : '');
}
ws.close(); chrome.kill();
