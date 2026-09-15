# Motion

One entrance, played once, on load. Nothing scroll-driven — the page is a
single viewport.

## Why there's no animation library

The obvious candidates were all on the table: GSAP (~70 KB gzipped), Anime.js
(~17 KB), Framer Motion and React Spring (both need React, which this page
doesn't have). For **four elements animating once**, none of them earn their
transfer cost on a page whose entire job is fast first paint.

Everything here is CSS keyframes plus ~30 lines of vanilla JS, so the motion
adds **zero bytes** to the critical path. If the page ever grows scroll
choreography or page transitions, revisit — that's where GSAP starts paying
for itself.

## The choreography

| Element | Starts | Duration |
|---|---|---|
| Veil lifting off the scrim | 0 | 1900ms |
| Logo | 0 | 1100ms |
| Tagline, per word | 380ms, +55ms each | 850ms |
| "Coming Soon…" | 700ms | 800ms |
| Address | 860ms | 800ms |

Settled by ~1.7s.

**One motion language for everything** — blur off, rise a little, settle — with
the stagger doing the work. Varying the technique per element looks busy; a
consistent move arriving in sequence looks composed.

**Blur-to-sharp is the load-bearing idea.** It reads as the page coming into
focus, which suits a soft-focus video background, and it carries the entrance
without needing distance. Large translations are what make an entrance feel
overbearing.

**Amounts scale with element size** — 14px of blur on the logo, 4px on the
11px address. Heavy blur on small type looks like a rendering fault rather
than a transition.

**No overshoot.** Every element uses `--ease-settle`,
`cubic-bezier(0.22, 1, 0.36, 1)` — a strong ease-out. Springs and elastic
easing are what read as "jittery"; this reads as settling into place.

**The word stagger is deliberately tight** at 55ms, so the tagline reads as one
soft sweep across the line rather than four words arriving separately.

## The three states it has to survive

The intro is the only thing on the page with real movement, so the ways it can
fail all had to be closed off:

1. **Reduced motion** — the inline `<head>` script checks
   `prefers-reduced-motion` and returns *before* setting `data-intro`. Since
   every hidden-state rule is scoped to that attribute, the page renders
   finished. There's an explicit `!important` override too.
2. **No JavaScript, or `site.js` fails to load** — the head script carries its
   own 1600ms failsafe that promotes the intro regardless. Worst case the
   entrance starts late; it can never leave the hero blank. The tagline simply
   animates as one block instead of word by word.
3. **Slow webfont** — the start is gated on `document.fonts.ready`, because an
   entrance that plays while Jost is still swapping in animates the fallback
   and then jumps. The failsafe above caps the wait.

The hidden state is applied *only* by JS setting an attribute before first
paint, never in the base stylesheet — so there's no way for a visitor to be
left looking at an invisible page.
