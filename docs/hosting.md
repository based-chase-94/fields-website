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

### 3. Create the Pages project

Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** →
**Connect to Git** → authorise the GitHub app → pick `fields-website`.

Build settings — this repo has no build step:

| Setting | Value |
|---|---|
| Framework preset | None |
| Build command | *(leave empty)* |
| Build output directory | `site` |
| Root directory | `/` |
| Production branch | `main` |

That gives a `*.pages.dev` URL. Confirm it looks right before attaching the
real domain.

### 4. Attach the domain

Pages project → **Custom domains** → **Set up a domain** → the apex
(`example.com`). Cloudflare creates the DNS record itself. Certificate issuance
takes a few minutes.

**Add the apex only.** Attaching `www` as a second custom domain would serve
the identical site on two hostnames, which splits SEO signals between them.

### 5. Redirect www to the apex

Cloudflare → **Rules** → **Redirect Rules** → **Create**:

- If: `Hostname` `equals` `www.example.com`
- Then: **Dynamic** redirect, **301**, expression:
  `concat("https://example.com", http.request.uri.path)`
- Tick **preserve query string**

Then add a DNS record so `www` resolves at all: type `AAAA`, name `www`,
content `100::`, **Proxied**. That is Cloudflare's documented discard address —
the redirect rule fires before anything is actually fetched.

### 6. Verify, then retire GitHub Pages

Once the real domain serves correctly:

```bash
curl -sI https://example.com | grep -iE 'cf-cache-status|cache-control|x-robots'
```

Then delete `.github/workflows/pages.yml` and disable Pages in the GitHub repo
settings. Keep it running until this point — it costs nothing and is the
fallback if anything goes wrong.

---

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
