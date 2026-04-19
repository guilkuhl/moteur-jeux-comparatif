const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = path.join(__dirname, 'benchmark-results');
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR);

// Cherche des pixels rouges dans la zone HUD (haut gauche) en capturant le canvas via screenshot
// Plus fiable que de lire les pixels WebGL directement
const CHECK_RED_HUD_JS = `async () => {
  const canvas = document.querySelector('canvas');
  if (!canvas) return { found: false, reason: 'no canvas' };

  // Créer un canvas 2D pour lire les pixels du canvas principal
  const w = Math.min(canvas.width, 400);
  const h = Math.min(canvas.height, 80);
  const tmp = document.createElement('canvas');
  tmp.width = w;
  tmp.height = h;
  const ctx = tmp.getContext('2d');

  // Essayer via drawImage (fonctionne si canvas 2D)
  try {
    ctx.drawImage(canvas, 0, 0, w, h, 0, 0, w, h);
    const data = ctx.getImageData(0, 0, w, h).data;
    let redPixels = 0;
    for (let i = 0; i < data.length; i += 4) {
      if (data[i] > 180 && data[i+1] < 60 && data[i+2] < 60 && data[i+3] > 100) {
        redPixels++;
      }
    }
    return { found: redPixels > 5, redPixels, source: '2d-copy' };
  } catch(e) {}

  // Fallback WebGL readPixels
  const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
  if (!gl) return { found: false, reason: 'no gl' };
  let redPixels = 0;
  const buf = new Uint8Array(4);
  for (let x = 5; x < 300; x += 3) {
    for (let yScreen = 5; yScreen < 70; yScreen += 3) {
      const yGL = canvas.height - yScreen - 1;
      gl.readPixels(x, yGL, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, buf);
      if (buf[0] > 180 && buf[1] < 60 && buf[2] < 60 && buf[3] > 100) redPixels++;
    }
  }
  return { found: redPixels > 3, redPixels, source: 'webgl-read' };
}`;

// Lire l'état Phaser
const PHASER_STATE_JS = `() => {
  if (window.benchmarkResult) return { stopped: true, ...window.benchmarkResult };
  try {
    const s = window.phaserGame && window.phaserGame.scene.scenes[0];
    if (!s) return null;
    return {
      stopped: s.stopped,
      sprites: s.activeCount,
      fps: s.game ? Math.floor(s.game.loop.actualFps) : 0,
    };
  } catch(e) { return { error: e.message }; }
}`;

async function runBenchmark(name, url, type, maxWaitMs) {
  console.log(`\n${'═'.repeat(55)}`);
  console.log(`  ${name}`);
  console.log(`${'═'.repeat(55)}`);

  const browser = await chromium.launch({
    headless: false,
    args: [
      '--no-sandbox',
      '--disable-web-security',
      '--disable-background-timer-throttling',
      '--disable-renderer-backgrounding',
      '--disable-backgrounding-occluded-windows',
      '--autoplay-policy=no-user-gesture-required',
    ],
  });

  const context = await browser.newContext({ viewport: { width: 980, height: 580 } });
  const page = await context.newPage();

  const consoleLogs = [];
  page.on('console', msg => consoleLogs.push(msg.text()));
  page.on('pageerror', err => console.log(`  [JS ERROR] ${err.message}`));

  await page.goto(url, { timeout: 60000, waitUntil: 'domcontentloaded' });
  console.log(`  Page chargée → attente du stop (FPS < 20)...`);

  const startMs = Date.now();
  let result = null;
  let screenshotPath = null;
  let lastStatus = '';
  let iteration = 0;

  while (Date.now() - startMs < maxWaitMs) {
    await page.waitForTimeout(3000);
    iteration++;

    let stopped = false;
    let statusLine = '';

    if (type === 'phaser') {
      const state = (await page.evaluate(PHASER_STATE_JS).catch(e => ({ error: e.message }))) || { error: 'null result' };
      if (state.error) {
        statusLine = `erreur JS: ${state.error}`;
      } else {
        statusLine = `sprites=${state.sprites} fps=${state.fps} stopped=${state.stopped}`;
        if (state.stopped) {
          stopped = true;
          result = { sprites: state.sprites, fps: state.fps };
        }
      }
    } else {
      // Godot / Defold : détection rouge dans HUD
      const red = (await page.evaluate(CHECK_RED_HUD_JS).catch(e => ({ found: false, reason: e.message }))) || { found: false, reason: 'undefined result' };
      statusLine = `redPixels=${red.redPixels ?? '?'} (${red.source ?? red.reason})`;
      if (red.found) {
        stopped = true;
        result = { sprites: '(voir screenshot)', fps: '(voir screenshot)' };
      }
    }

    // Afficher le statut toutes les 15s ou si changé
    if (statusLine !== lastStatus || iteration % 5 === 0) {
      const elapsed = ((Date.now() - startMs) / 1000).toFixed(0);
      console.log(`  [${elapsed}s] ${statusLine}`);
      lastStatus = statusLine;
    }

    if (stopped) {
      const elapsed = ((Date.now() - startMs) / 1000).toFixed(1);
      console.log(`  ✓ STOP détecté à ${elapsed}s`);
      screenshotPath = path.join(OUT_DIR, `${name.replace(/[^a-z0-9]/gi, '_')}_STOP.png`);
      await page.screenshot({ path: screenshotPath, fullPage: false });
      console.log(`  Screenshot : ${screenshotPath}`);
      break;
    }
  }

  if (!result) {
    const elapsed = ((Date.now() - startMs) / 1000).toFixed(0);
    console.log(`  ✗ Timeout ${elapsed}s — screenshot de l'état actuel`);
    screenshotPath = path.join(OUT_DIR, `${name.replace(/[^a-z0-9]/gi, '_')}_timeout.png`);
    await page.screenshot({ path: screenshotPath });

    // Pour Phaser, lire l'état même sans stop
    if (type === 'phaser') {
      const state = await page.evaluate(PHASER_STATE_JS).catch(() => null);
      if (state) result = { sprites: state.sprites + ' (pas de stop)', fps: state.fps };
    }
    if (!result) result = { sprites: 'N/A', fps: 'N/A' };
  }

  await browser.close();
  return { name, sprites: result.sprites, fps: result.fps, screenshot: screenshotPath };
}

(async () => {
  const benchmarks = [
    { name: 'Phaser 4.0.0',  url: 'http://localhost:8083/index.html', type: 'phaser',  maxWait: 300000 },
    { name: 'Defold 1.12.3', url: 'http://localhost:8082/index.html', type: 'webgl',   maxWait: 300000 },
    { name: 'Godot 4.6.2',   url: 'http://localhost:8081/index.html', type: 'webgl',   maxWait: 600000 },
  ];

  const results = [];
  for (const b of benchmarks) {
    const r = await runBenchmark(b.name, b.url, b.type, b.maxWait);
    results.push(r);
  }

  console.log('\n\n' + '═'.repeat(62));
  console.log('  RÉSULTATS — Sprites simultanés avec collision (FPS < 20)');
  console.log('═'.repeat(62));
  console.log(`${'Moteur'.padEnd(20)} | ${'Sprites'.padEnd(20)} | FPS final`);
  console.log(`${'-'.repeat(20)}-+-${'-'.repeat(20)}-+-${'-'.repeat(10)}`);
  for (const r of results) {
    console.log(`${r.name.padEnd(20)} | ${String(r.sprites).padEnd(20)} | ${r.fps}`);
  }
  console.log('\n  Screenshots dans : ' + OUT_DIR);
})();
