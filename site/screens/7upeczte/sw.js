// Offline cache for the menu board pages (built into site/screens/<code>/sw.js by
// tools/build-screens.py, which fills in the build id and the file list).
//
// - The pages: network first, so an update shows as soon as it's live; the cached copy
//   if the network is down or slower than 4 s.
// - version.json: network only. When it fails the page knows it's offline.
// - Everything under /screens/assets/ has a content hash in its name and never changes:
//   cache first. Video range requests are answered from the cached file, so the loop
//   keeps playing with no connection.
const BUILD = '16d2cdd94b49';
const CACHE = `fields-screens-${BUILD}`;
const PRECACHE = ["/screens/7upeczte/grow-your-own/", "/screens/7upeczte/house-bowls/", "/screens/7upeczte/proteins-upgrades/", "/screens/assets/fieldsbowls.609a3543c9.svg", "/screens/assets/fredoka.8d14f8dd64.woff2", "/screens/assets/grass-grow-your-own-1080.e3510ba23d.mp4", "/screens/assets/grass-grow-your-own-2160.942870e650.mp4", "/screens/assets/grass-grow-your-own.9f31a18ad8.jpg", "/screens/assets/grass-house-bowls-1080.67ddd6d8cb.mp4", "/screens/assets/grass-house-bowls-2160.77f784e11d.mp4", "/screens/assets/grass-house-bowls.3a3f16f615.jpg", "/screens/assets/grass-proteins-upgrades-1080.3b5058ad25.mp4", "/screens/assets/grass-proteins-upgrades-2160.cbefc97e7c.mp4", "/screens/assets/grass-proteins-upgrades.5c2fe53aab.jpg", "/screens/assets/grow-2.bea3a54368.svg", "/screens/assets/order-online.5954ba76d0.svg", "/screens/assets/own.8a1bb6852c.svg", "/screens/assets/price-6.f0a84052fd.svg", "/screens/assets/starts-at-6.fbcef16d98.svg", "/screens/assets/step1.0c21096521.svg", "/screens/assets/step2.5cd3ba4231.svg", "/screens/assets/step3.5006ac8ae5.svg", "/screens/assets/step4.4b438dbd44.svg", "/screens/assets/vegetarian.764b341977.svg", "/screens/assets/your.7f1e16c2b8.svg"];

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    // One at a time: the XOGO Mini is a small box and the loops are big.
    for (const url of PRECACHE) {
      if (!(await c.match(url))) await c.add(url);
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k.startsWith('fields-screens-') && k !== CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});

const timeout = (ms) => new Promise((_, no) => setTimeout(() => no(new Error('timeout')), ms));

async function page(req) {
  const c = await caches.open(CACHE);
  try {
    const r = await Promise.race([fetch(req, { cache: 'no-store' }), timeout(4000)]);
    if (r.ok) c.put(req, r.clone());
    return r;
  } catch {
    return (await c.match(req, { ignoreSearch: true })) || Response.error();
  }
}

async function asset(req) {
  const c = await caches.open(CACHE);
  const url = new URL(req.url).pathname;
  let full = await c.match(url);
  if (!full) {
    const r = await fetch(url);
    if (!r.ok) return r;
    await c.put(url, r.clone());
    full = r;
  }
  const range = req.headers.get('range');
  if (!range) return full;
  // Answer a byte range from the cached whole file. A Blob slice reads from disk
  // rather than copying the whole loop into memory on every request.
  const blob = await full.blob();
  const [, a, b] = /bytes=(\d*)-(\d*)/.exec(range) || [];
  const start = a ? +a : Math.max(0, blob.size - +b);
  const end = a && b ? Math.min(+b, blob.size - 1) : blob.size - 1;
  return new Response(blob.slice(start, end + 1), {
    status: 206,
    headers: {
      'Content-Type': full.headers.get('Content-Type') || 'video/mp4',
      'Content-Range': `bytes ${start}-${end}/${blob.size}`,
      'Content-Length': String(end - start + 1),
      'Accept-Ranges': 'bytes',
    },
  });
}

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  if (url.pathname.endsWith('/version.json')) return; // network only
  if (url.pathname.startsWith('/screens/assets/')) return e.respondWith(asset(e.request));
  if (e.request.mode === 'navigate' || url.pathname.startsWith(new URL('./', location).pathname)) {
    return e.respondWith(page(e.request));
  }
});
