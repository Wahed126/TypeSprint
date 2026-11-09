import { createHash } from 'node:crypto';
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = path.dirname(fileURLToPath(import.meta.url));
export const files = ['index.html', 'styles.css', 'app.js', 'engine.js', 'storage.js', 'data/exercises.json', 'icon.svg', 'manifest.webmanifest'];
const buffers = await Promise.all(files.map(file => readFile(path.join(root, file))));
JSON.parse(buffers[files.indexOf('data/exercises.json')] + '');
JSON.parse(buffers[files.indexOf('manifest.webmanifest')] + '');
const workerTemplate = await readFile(path.join(root, 'sw-template.js'), 'utf8');
const hash = createHash('sha256'); for (const buffer of buffers) hash.update(buffer);
hash.update(workerTemplate);
const version = hash.digest('hex').slice(0, 16);
const dist = path.join(root, 'dist');
await rm(dist, { recursive: true, force: true });
for (let i = 0; i < files.length; i++) { const out = path.join(dist, files[i]); await mkdir(path.dirname(out), { recursive: true }); await writeFile(out, buffers[i]); }
const worker = workerTemplate.replace('__CACHE_VERSION__', version);
// Keep direct branch-hosted play offline-capable with the same versioned assets.
await writeFile(path.join(root, 'sw.js'), worker);
await writeFile(path.join(dist, 'sw.js'), worker);
await writeFile(path.join(dist, '.nojekyll'), '');
console.log(`Built web/dist (${files.length + 2} files; offline cache ${version})`);
