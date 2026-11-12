// Offline cache for the menu board pages (built into site/screens/<code>/sw.js by
// tools/build-screens.py, which fills in the build id and the file list).
//
// - The pages: network first, so an update shows as soon as it's live; the cached copy
//   if the network is down or slower than 4 s.
// - version.json: network only. When it fails the page knows it's offline.
// - Everything under /screens/assets/ has a content hash in its name and never changes:
//   cache first. Video range requests are answered from the cached file, so the loop
//   keeps playing with no connection.
const BUILD = '07510275758d';
const CACHE = `fields-screens-${BUILD}`;
const PRECACHE = ["/screens/7upeczte/house-bowls/", "/screens/assets/fredoka.8d14f8dd64.woff2", "/screens/assets/grass-house-bowls-1080.9c5a5dd76c.mp4", "/screens/assets/grass-house-bowls-2160.c8ae81d9e5.mp4", "/screens/assets/grass-house-bowls.3a3f16f615.jpg", "/screens/assets/vegetarian.764b341977.svg"];

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
