import { mkdirSync, copyFileSync, existsSync, readFileSync, writeFileSync } from 'node:fs';
mkdirSync('static/vendor', {recursive:true});
mkdirSync('static/css', {recursive:true});
for (const [src, dst] of [
  ['node_modules/htmx.org/dist/htmx.min.js','htmx.min.js'],
  ['node_modules/alpinejs/dist/cdn.min.js','alpine.min.js'],
  ['node_modules/chart.js/dist/chart.umd.min.js','chart.min.js'],
  ['node_modules/htmx.org/LICENSE','htmx.LICENSE'],
  ['node_modules/alpinejs/LICENSE.md','alpine.LICENSE'],
  ['node_modules/chart.js/LICENSE.md','chart.LICENSE'],
]) { if (existsSync(src)) {
  if (dst.endsWith('.js')) writeFileSync(`static/vendor/${dst}`, readFileSync(src, 'utf8').replace(/\/\/[#@] sourceMappingURL=.*$/gm, '').trimEnd() + '\n');
  else copyFileSync(src, `static/vendor/${dst}`);
} }
