/* Fields — hero video loader.
 *
 * The <video> ships with no <source> at all. We decide here whether it's worth
 * downloading a few megabytes, and which size, then attach the sources. If any
 * part of that fails the poster stays up and the page still reads correctly.
 */
(function () {
  "use strict";

  var video = document.getElementById("hero-video");
  var hero = document.querySelector(".hero");
  if (!video || !hero) return;

  function stayStill() {
    hero.classList.add("is-still");
    if (video) video.removeAttribute("autoplay");
  }

  // 1. Honour the user's stated preferences before anything else.
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (reduced.matches) return stayStill();

  // 2. Don't burn someone's metered connection on decoration.
  var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  if (conn) {
    if (conn.saveData) return stayStill();
    if (/^(slow-)?2g$/.test(conn.effectiveType || "")) return stayStill();
  }

  // 3. Pick a rendition. CSS pixels x DPR, capped — a 3x phone doesn't need 4K.
  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var needed = Math.max(window.innerWidth, window.innerHeight * 0.6) * dpr;
  var size = needed > 1400 ? "1920" : "1280";

  var sources = [
    ["webm", 'video/webm; codecs="vp9"'],
    ["mp4",  'video/mp4; codecs="avc1.640028"']
  ];

  var attached = 0;
  sources.forEach(function (pair) {
    var url = video.getAttribute("data-src-" + size + "-" + pair[0]);
    if (!url) return;
    var el = document.createElement("source");
    el.src = url;
    el.type = pair[1];
    video.appendChild(el);
    attached++;
  });

  if (!attached) return stayStill();

  // 4. Load, then play. preload="none" means nothing moved until now.
  video.preload = "auto";
  video.load();

  video.addEventListener("error", stayStill, { once: true });
  video.addEventListener("stalled", function () {
    // Give it a moment; if it never gets going, fall back to the still.
    window.setTimeout(function () {
      if (video.readyState < 2) stayStill();
    }, 6000);
  });

  video.addEventListener("canplay", function () {
    var p = video.play();
    if (p && typeof p.catch === "function") {
      // iOS low-power mode and some autoplay policies reject this. The poster
      // is already on screen, so there is nothing to clean up but the class.
      p.catch(stayStill);
    }
  }, { once: true });

  // 5. A tab that loads in the background — or an iOS device that drops into
  //    Low Power Mode — gets its playback suspended and never resumes on its
  //    own. Nudge it whenever the page becomes visible again.
  document.addEventListener("visibilitychange", function () {
    if (document.hidden || hero.classList.contains("is-still")) return;
    if (video.paused && video.readyState >= 2) {
      var p = video.play();
      if (p && typeof p.catch === "function") p.catch(function () {});
    }
  });
})();

/* Fields — hero intro.
 *
 * The pre-paint state is set by the inline script in <head>; this only
 * enhances (splits the tagline into words) and decides when to start.
 *
 * Starting is gated on the webfont, because an entrance that plays while Jost
 * is still swapping in animates the fallback and then jumps. The head script's
 * failsafe means a font that never loads costs a slightly late start, never a
 * blank hero.
 */
(function () {
  "use strict";

  var html = document.documentElement;
  if (html.getAttribute("data-intro") !== "pending") return;  // reduced motion, or already run

  // Split the tagline so it can sweep word by word. Done before the start
  // signal, so nothing animates and then re-renders underneath itself.
  var tagline = document.querySelector(".hero__tagline");
  if (tagline && !tagline.querySelector(".word")) {
    var words = tagline.textContent.trim().split(/\s+/);
    if (words.length > 1 && words.length <= 12) {
      tagline.textContent = "";
      words.forEach(function (word, i) {
        var span = document.createElement("span");
        span.className = "word";
        span.style.setProperty("--i", i);
        span.textContent = word;
        tagline.appendChild(span);
        if (i < words.length - 1) tagline.appendChild(document.createTextNode(" "));
      });
      tagline.classList.add("is-split");
    }
  }

  function start() {
    if (html.getAttribute("data-intro") === "pending") html.setAttribute("data-intro", "run");
  }

  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(start, start);
  } else {
    start();
  }
})();
