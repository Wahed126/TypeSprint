import { createHash } from 'node:crypto';
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = path.dirname(fileURLToPath(import.meta.url));
export const files = ['index.html', 'styles.css', 'app.js', 'engine.js', 'storage.js', 'data/exercises.json', 'icon.svg', 'manifest.webmanifest'];
const buffers = await Promise.all(files.map(file => readFile(path.join(root, file))));
JSON.parse(buffers[files.indexOf('data/exercises.json')] + '');
JSON.parse(buffers[files.indexOf('manifest.webmanifest')] + '');
const hash = createHash('sha256'); for (const buffer of buffers) hash.update(buffer);
const version = hash.digest('hex').slice(0, 16);
const dist = path.join(root, 'dist');
await rm(dist, { recursive: true, force: true });
for (let i = 0; i < files.length; i++) { const out = path.join(dist, files[i]); await mkdir(path.dirname(out), { recursive: true }); await writeFile(out, buffers[i]); }
const worker = (await readFile(path.join(root, 'sw.js'), 'utf8')).replace('__CACHE_VERSION__', version);
await writeFile(path.join(dist, 'sw.js'), worker);
await writeFile(path.join(dist, '.nojekyll'), '');
console.log(`Built web/dist (${files.length + 2} files; offline cache ${version})`);
