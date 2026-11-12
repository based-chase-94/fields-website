// Lays out a menu board draft with the real fonts and reports where the lettering sits.
// Used by tools/build-screens.py, which draws Midstar and Heart of the Land as outlines
// (the fonts are licensed and can't ship) exactly where the browser set the text.
//
//   node tools/screens-measure.mjs <draft.html>   -> JSON on stdout
//
// For each [data-outline] element: its box, font size, colour, and per line (one text node
// per line, lines split with <br>) the line's text, start x and baseline y, in stage pixels.
// Also every [data-fit] line that runs past its grid cell, so the build can refuse it.
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

// require, not import: it also finds a globally installed Playwright.
const { chromium } = createRequire(import.meta.url)('playwright');

// file:// pages count as opaque origins, and Chromium won't load their fonts without this flag.
const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
const page = await browser.newPage({ viewport: { width: 3840, height: 2160 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(process.argv[2]).href);
// Load every face explicitly: fonts.check() also says yes for a face that failed.
const missing = await page.evaluate(async () => {
  await Promise.allSettled([...document.fonts].map((f) => f.load()));
  return [...document.fonts].filter((f) => f.status !== 'loaded').map((f) => f.family);
});
if (missing.length) { console.error('fonts did not load:', missing); process.exit(1); }

const result = await page.evaluate(() => {
  const stage = document.getElementById('stage').getBoundingClientRect();
  const outlines = [...document.querySelectorAll('[data-outline]')].map((el) => {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const lines = [];
    for (const node of [...el.childNodes]) {
      if (node.nodeType !== Node.TEXT_NODE || !node.textContent.trim()) continue;
      // A zero-size inline-block's bottom edge sits on the baseline.
      const mark = document.createElement('span');
      mark.style.cssText = 'display:inline-block;width:0;height:0;vertical-align:baseline';
      el.insertBefore(mark, node);
      const m = mark.getBoundingClientRect();
      lines.push({ text: node.textContent, x: m.left - stage.left, baseline: m.bottom - stage.top });
    }
    for (const m of el.querySelectorAll('span[style*="inline-block"]')) m.remove();
    return { font: el.dataset.outline, size: parseFloat(cs.fontSize), color: cs.color,
             x: r.left - stage.left, y: r.top - stage.top, w: r.width, h: r.height, lines };
  });
  const overflow = [];
  for (const p of document.querySelectorAll('[data-fit]')) {
    const cell = p.parentElement.getBoundingClientRect();
    for (const node of p.childNodes) {
      if (node.nodeType !== Node.TEXT_NODE) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      const over = Math.max(...[...range.getClientRects()].map((r) => r.right)) - cell.right;
      if (over > 0.5) overflow.push({ what: node.textContent, over });
    }
  }
  return { outlines, overflow };
});
await browser.close();
process.stdout.write(JSON.stringify(result));
