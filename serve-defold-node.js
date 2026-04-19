const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve('C:/Users/kuhle/source/repos/moteur-jeux-comparatif/defold-build-web4/Defold Benchmark');
const PORT = 8768;

const MIME = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.wasm': 'application/wasm',
  '.png': 'image/png',
  '.json': 'application/json',
  '.css': 'text/css',
};

http.createServer((req, res) => {
  let filePath = path.join(ROOT, req.url === '/' ? '/index.html' : req.url);
  // Sécurité basique
  if (!filePath.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }

  fs.readFile(filePath, (err, data) => {
    const ext = path.extname(filePath);
    const mime = MIME[ext] || 'application/octet-stream';
    if (err) {
      res.writeHead(404);
      res.end();
      return;
    }
    res.writeHead(200, {
      'Content-Type': mime,
      'Content-Length': data.length,
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Cross-Origin-Embedder-Policy': 'require-corp',
    });
    res.end(data);
  });
}).listen(PORT, () => {
  console.log(`Defold COOP/COEP server on http://localhost:${PORT}`);
});
