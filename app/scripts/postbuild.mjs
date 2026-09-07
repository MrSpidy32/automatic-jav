import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const docsDir = path.resolve(__dirname, '../../docs');
const publicDir = path.resolve(__dirname, '../public');

// 1. Create directory aliases for static routing parity: /route/ -> route/index.html
const routes = ['browse', 'codes', 'models', 'stats', 'sitemap'];
routes.forEach((route) => {
  const htmlFile = path.join(docsDir, `${route}.html`);
  const targetDir = path.join(docsDir, route);
  const targetIndex = path.join(targetDir, 'index.html');

  if (fs.existsSync(htmlFile)) {
    fs.mkdirSync(targetDir, { recursive: true });
    fs.copyFileSync(htmlFile, targetIndex);
    console.log(`✓ Created directory alias: docs/${route}/index.html`);
  }
});

// 2. Restore data files to docs/ (Astro build cleans outDir, so re-copy from app/public)
const dataExtensions = ['.json', '.csv', '.txt', '.xml'];
if (fs.existsSync(publicDir)) {
  const files = fs.readdirSync(publicDir);
  files.forEach((file) => {
    if (file === 'favicon.svg') return;
    const ext = path.extname(file);
    if (dataExtensions.includes(ext)) {
      try {
        fs.copyFileSync(path.join(publicDir, file), path.join(docsDir, file));
        console.log(`✓ Restored data file to docs/: ${file}`);
      } catch (e) {
        // ignore
      }
    }
  });
}

// 3. Clean temporary duplicate data files from app/public
const cleanExtensions = ['.json', '.csv', '.txt', '.xml', '.js'];
if (fs.existsSync(publicDir)) {
  const files = fs.readdirSync(publicDir);
  files.forEach((file) => {
    if (file === 'favicon.svg') return; // preserve static asset
    const ext = path.extname(file);
    if (cleanExtensions.includes(ext)) {
      try {
        fs.unlinkSync(path.join(publicDir, file));
        console.log(`✓ Cleaned temporary public file: app/public/${file}`);
      } catch (e) {
        // ignore
      }
    }
  });
}
