#!/usr/bin/env node
/**
 * Fail si le plus gros chunk JS de dist/assets/ dépasse 300 KB gzipped.
 */
import { readdirSync, readFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { resolve } from 'node:path';

const LIMIT_KB = 300;
const distAssets = resolve(new URL('.', import.meta.url).pathname, '..', 'dist', 'assets');

let maxKB = 0;
let maxFile = '';
for (const name of readdirSync(distAssets)) {
  if (!name.endsWith('.js')) continue;
  const buf = readFileSync(resolve(distAssets, name));
  const gz = gzipSync(buf);
  const kb = gz.length / 1024;
  console.log(`${name}  ${buf.length / 1024 | 0} KB  (gz ${kb.toFixed(1)} KB)`);
  if (kb > maxKB) { maxKB = kb; maxFile = name; }
}

console.log(`→ max gzipped: ${maxFile} @ ${maxKB.toFixed(1)} KB (limit ${LIMIT_KB} KB)`);
if (maxKB > LIMIT_KB) {
  console.error(`FAIL: ${maxFile} > ${LIMIT_KB} KB gzipped`);
  process.exit(1);
}
