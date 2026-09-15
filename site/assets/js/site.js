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

  // Two different failures, two different responses.
  //   stayStill()     — the video is not coming: no sources, a decode/network
  //                     error, or the visitor asked us not to. Hide it and let
  //                     the poster carry the frame.
  //   awaitGesture()  — the video is fine but autoplay was refused (iOS Low
  //                     Power Mode is the common one). Keep the element on
  //                     screen showing its poster frame and start on the first
  //                     touch, rather than killing playback for the pageview.
  function stayStill() {
    hero.classList.add("is-still");
    if (video) video.removeAttribute("autoplay");
  }

  var gestureArmed = false;
  function awaitGesture() {
    if (gestureArmed) return;
    gestureArmed = true;
    var events = ["touchstart", "pointerdown", "keydown"];
    function go() {
      events.forEach(function (e) { document.removeEventListener(e, go); });
      var p = video.play();
      if (p && typeof p.catch === "function") p.catch(function () {});
    }
    events.forEach(function (e) {
      document.addEventListener(e, go, { once: true, passive: true });
    });
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

  function attempt() {
    // Some WebKit builds only honour muted autoplay when it's set as a
    // property, not just the markup attribute.
    video.muted = true;
    var p = video.play();
    if (p && typeof p.catch === "function") p.catch(awaitGesture);
  }

  // 4. Listeners first, then load — otherwise a cached video can reach
  //    `canplay` before anything is listening and never get played.
  video.addEventListener("error", stayStill, { once: true });
  video.addEventListener("canplay", attempt, { once: true });
  video.addEventListener("loadeddata", attempt, { once: true });
  video.addEventListener("stalled", function () {
    // Give it a moment; if it never gets going, fall back to the still.
    window.setTimeout(function () {
      if (video.readyState < 2) stayStill();
    }, 6000);
  });

  video.preload = "auto";
  video.load();

  // 5. A tab that loads in the background — or an iOS device that drops into
  //    Low Power Mode — gets its playback suspended and never resumes on its
  //    own. Nudge it whenever the page becomes visible again.
  document.addEventListener("visibilitychange", function () {
    if (document.hidden || hero.classList.contains("is-still")) return;
    if (video.paused && video.readyState >= 2) {
      var p = video.play();
      if (p && typeof p.catch === "function") p.catch(awaitGesture);
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
