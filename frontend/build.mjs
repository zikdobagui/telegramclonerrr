import { build } from 'esbuild';
import { mkdir, readFile, writeFile } from 'node:fs/promises';

await mkdir('static/ui', { recursive: true });
await build({
  entryPoints: ['frontend/interface.jsx'],
  outfile: 'static/ui/interface.js',
  bundle: true,
  minify: true,
  format: 'iife',
  target: ['es2020'],
  jsx: 'automatic',
  define: { 'process.env.NODE_ENV': '"production"' },
  legalComments: 'linked',
  metafile: false,
});
// License accompanies the compiled components as well as their editable source.
await writeFile('static/ui/LICENSE.react-bits.md', await readFile('frontend/reactbits/LICENSE.md'));
for (const name of ['react', 'react-dom', 'lenis']) {
  await writeFile(`static/ui/LICENSE.${name}.txt`, await readFile(`node_modules/${name}/LICENSE`));
}
