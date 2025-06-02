// Lightweight static file server for the pre-built Vite assets found in `dist/`.
//
// We use this instead of the standard `vite dev` or `vite preview` commands
// because those rely on *esbuild* which spawns a native child process that is
// blocked in certain sandboxed environments (spawn EPERM).  By serving the
// already-checked-in production build we avoid that limitation while still
// making the application available at http://localhost:5173.
//
// The server has a single responsibility: return files from the `dist/` folder.
// For unknown routes (e.g. deep links in the SPA) it falls back to the
// top-level `index.html` so that the client-side router can handle the path.

import http from 'node:http';
import { createReadStream, promises as fs } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Resolve __dirname in ESM.
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// The folder containing the pre-built assets.
const DIST_DIR = path.join(__dirname, 'dist');

// Allow overriding the port via environment (falls back to the same default
// port used by Vite so that existing documentation and scripts keep working).
const PORT = process.env.PORT || 5173;

// Minimal content-type map – extend when needed.
const MIME_TYPES = {
  '.html': 'text/html; charset=UTF-8',
  '.js': 'text/javascript; charset=UTF-8',
  '.css': 'text/css; charset=UTF-8',
  '.svg': 'image/svg+xml',
  '.json': 'application/json; charset=UTF-8',
  '.ico': 'image/x-icon',
};

function sendFile(res, filePath) {
  const ext = path.extname(filePath);
  const mime = MIME_TYPES[ext] || 'application/octet-stream';
  res.writeHead(200, { 'Content-Type': mime });
  createReadStream(filePath).pipe(res);
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host}`);
    // Default to index.html for the root path.
    let reqPath = url.pathname === '/' ? '/index.html' : url.pathname;

    // Prevent directory traversal.
    reqPath = path.normalize(reqPath).replace(/^\/+/, '');

    let filePath = path.join(DIST_DIR, reqPath);
    let stat;

    try {
      stat = await fs.stat(filePath);
    } catch {
      // Not found – fall back to SPA entry point so client-side routing works.
      filePath = path.join(DIST_DIR, 'index.html');
      stat = await fs.stat(filePath);
    }

    if (stat.isDirectory()) {
      // Serve index.html for directory paths.
      filePath = path.join(filePath, 'index.html');
    }

    sendFile(res, filePath);
  } catch (err) {
    console.error('Static server error:', err);
    res.writeHead(500);
    res.end('Internal Server Error');
  }
});

server.listen(PORT, '0.0.0.0', () => {
  // eslint-disable-next-line no-console
  console.log(`✅ Frontend available at http://localhost:${PORT}`);
});
