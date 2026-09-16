# Hosting

Domain registered at **Porkbun**, DNS and hosting on **Cloudflare**.

The domain stays at Porkbun. We only change its nameservers — that is not a
transfer, costs nothing, and is reversible in minutes.

---

## Migration runbook

Order matters: DNS first, then the Pages project, then the domain attachment.
GitHub Pages keeps serving throughout, so there is no window where nothing works.

### 1. Add the site to Cloudflare

Cloudflare dashboard → **Add a site** → enter the apex domain (no `www`) →
choose the **Free** plan. Cloudflare scans existing DNS and then shows two
nameservers, something like `xxx.ns.cloudflare.com`.

If the scan imports any placeholder records Porkbun created (parking pages,
`_domainconnect`, a default A record), delete them — they will only conflict later.

### 2. Repoint nameservers at Porkbun

Porkbun → the domain → **Authoritative Nameservers** → **Edit** → replace both
entries with the pair Cloudflare gave you → save.

Cloudflare emails when it takes over. Usually minutes; allow a few hours.
Nothing else can be done until Cloudflare reports the zone **Active**.

### 3. Create the project

**Cloudflare has moved new Git-connected projects from Pages to Workers.** The
old "Build output directory" field is gone from the dashboard — the assets
directory is declared in `wrangler.jsonc` at the repo root instead, which is an
improvement, since it is versioned rather than set once in a web form.

Do **not** reach for the legacy Pages flow. Pages still works, but it is in
maintenance and new projects are steered to Workers. Everything this site needs
— custom domains, `_headers`, Git deploys, preview URLs — works on Workers, and
**requests to static assets are free and unlimited on both plans**, exactly as
they were on Pages.

Dashboard → **Workers & Pages** → **Create** → **Import a repository** → pick
`fields-website`.

| Setting | Value |
|---|---|
| Build command | *(leave empty — there is no build step)* |
| Deploy command | `npx wrangler deploy` *(usually prefilled)* |
| Production branch | `main` |

The assets directory is **not** set here. It comes from `wrangler.jsonc`:

```jsonc
{
  "name": "fields-website",
  "compatibility_date": "2026-09-16",
  "assets": { "directory": "./site" }
}
```

There is no `main` key on purpose — with no Worker script this deploys as a
pure static site. If the build fails with *"Missing entry-point to Worker
script or to assets directory"*, that path is the thing to check.

That gives a `*.workers.dev` URL. Confirm it looks right before attaching the
real domain.

### 4. Attach the domain

The Worker → **Settings** → **Domains & Routes** → **Add** → **Custom domain**
→ the apex (`example.com`). Cloudflare creates the DNS record itself.
Certificate issuance takes a few minutes.

**Add the apex only.** Attaching `www` as a second custom domain would serve
the identical site on two hostnames, which splits SEO signals between them.

### 5. Force HTTPS

**SSL/TLS → Edge Certificates → Always Use HTTPS → on.**

Not on by default. Until it is, `http://fieldsbowls.com` serves the site over an
unencrypted connection rather than redirecting — verified by requesting port 80
directly, which returned `200`, not a `301`.

Two reasons it matters beyond the obvious: anyone typing the bare domain gets
plain HTTP, and search engines treat `http://` and `https://` as separate URLs,
so without the redirect the ranking signals split between them.

Leave **HSTS** alone for now. It is worth enabling at launch, but browsers cache
the policy for its full duration and it cannot be withdrawn quickly — so it is a
bad thing to switch on while the site is still moving around.

### 6. Send www to the apex

Two parts, in this order. The DNS record must exist first, or the redirect rule
has nothing to fire on.

**a. A placeholder DNS record**

DNS → Records → Add **two** records, both proxied:

| Type | Name | Content |
|---|---|---|
| `AAAA` | `www` | `100::` |
| `A` | `www` | `192.0.2.1` |

**Both address families are required.** A hostname with only an `AAAA` resolves
for IPv6 clients and fails outright for everyone else — plenty of corporate and
older ISP networks are still IPv4-only, and they would get a DNS error rather
than the redirect. The apex does not need this handled manually because
attaching the Worker custom domain creates both families automatically.

`100::` is the IPv6 discard address and `192.0.2.1` is TEST-NET-1, both
reserved by RFC for exactly this purpose. Neither is ever contacted — the
records exist purely so Cloudflare accepts the connection, and the redirect
below fires at the edge first.

**Proxied is essential.** A grey-clouded record bypasses the rules engine, so
the redirect never runs and the request goes nowhere.

**b. The redirect rule**

Rules → Redirect Rules → Create rule. If a **"Redirect from WWW to Root"**
template is offered, use it — it builds exactly this. Otherwise, by hand:

- **If** — Custom filter expression: `Hostname` `equals` `www.fieldsbowls.com`
- **Then** — URL redirect, type **Dynamic**
- **Expression**: `concat("https://fieldsbowls.com", http.request.uri.path)`
- **Status code**: `301`
- **Preserve query string**: on

301 rather than 302 because this is permanent, and a permanent redirect passes
ranking signals to the apex. The dynamic expression carries the path through, so
`www.fieldsbowls.com/menu` lands on `fieldsbowls.com/menu` rather than dumping
everyone on the homepage.

Verify:

```bash
curl -sI https://www.fieldsbowls.com/ | grep -iE 'HTTP/|location'
```

Expect `301` and `location: https://fieldsbowls.com/`.

### 7. Verify, then retire GitHub Pages

Once the real domain serves correctly:

```bash
curl -sI https://example.com | grep -iE 'cf-cache-status|cache-control|x-robots'
```

Then delete `.github/workflows/pages.yml` and disable Pages in the GitHub repo
settings. Keep it running until this point — it costs nothing and is the
fallback if anything goes wrong.

---

## Email and DMARC

The domain is `fieldsbowls.com`, registered at Porkbun, DNS on Cloudflare.

Inbound mail uses **Porkbun forwarding** — two `MX` records to `fwd1`/`fwd2
.porkbun.com` plus an SPF `TXT`. Those were imported when Cloudflare scanned
the domain and are deliberately kept; they are unrelated to the website and
deleting them breaks any address at the domain.

A `_dmarc` `TXT` record is published as `v=DMARC1; p=reject;`.

**Why reject, and why now.** Nothing currently sends mail *from* the domain, so
a strict policy costs nothing and blocks anyone spoofing the brand while it
goes up on signage and a public site. This is the safest window to publish it.

> **When catering email is set up — read this first.**
>
> Real outbound mail (`hello@`, `catering@`, a POS emailing receipts, a mailing
> list) must have SPF **and** DKIM configured for whichever provider sends it.
> With `p=reject` in place, anything sending as `@fieldsbowls.com` without
> being authorised will be **rejected outright**.
>
> That is deliberate. A rejection bounces visibly and gets investigated;
> `p=quarantine` would route it silently to spam and be far harder to diagnose
> months after the record was set. Whoever configures the mailbox will be in
> this same DNS panel adding `MX` and DKIM records, so the `_dmarc` record is
> right there to review.
>
> Adding a `rua=mailto:` address at that point is also worth doing — it turns
> DMARC from a blunt policy into something that reports who is sending as you.

## Launch checklist

Everything below is deliberately *not* done yet, because the site is still a
private review link.

- [ ] Delete the `X-Robots-Tag` line from `site/_headers`
- [ ] Delete `<meta name="robots" content="noindex, nofollow">` from `index.html`
- [ ] Replace `site/robots.txt` with a real one (at an apex domain it is finally
      honoured — see the note in that file about why it was inert on Pages)
- [ ] Add `<link rel="canonical">` with the real domain
- [ ] Add `sitemap.xml`
- [ ] Add `LocalBusiness` JSON-LD — name, the Research Complex 2 address, hours,
      the ordering links. **The address must match the Google Business Profile
      character for character.**
- [ ] Update `og:image` to an absolute URL on the real domain (relative paths
      do not work for social scrapers)
- [ ] Claim the Google Business Profile. For a campus location this drives more
      traffic than the site does.

## A note on file handling

Pages used to silently exclude `node_modules`, `.git` and `.DS_Store` from
uploads. **Workers does not.** Deploying through Workers Builds is safe, because
it deploys the repo checkout and those are gitignored — but a local
`wrangler deploy` uploads the working directory as-is and would publish
`.DS_Store`. `site/.assetsignore` covers that case.

Limits worth knowing: 20,000 files per deployment, 25 MiB per file. The largest
asset here is the 3.6 MB hero video.

## Why Cloudflare over the alternatives

- **GitHub Pages** (current): terms of service say it is not for running a
  business site, it cannot send custom headers or redirects, and it has no
  preview deployments.
- **Vercel**: the free Hobby plan is non-commercial only, and their definition
  explicitly covers a paid consultant writing the code. Commercial use needs Pro.
- **Netlify**: comparable, but bandwidth is metered and overage is expensive.

Cloudflare's free tier has no metered bandwidth. The one caveat in their
self-serve terms is a restriction on using the CDN *primarily* to distribute
video — a hero background clip is normal usage, but if this ever grows a
video-heavy gallery, put the long-form material on YouTube or Vimeo and embed.
