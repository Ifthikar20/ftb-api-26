/*
 * FetchBot tracking pixel — readable source.
 *
 * The minified deploy artifact (p.min.js) is served at https://fetchbot.ai/p.js.
 * This file is the maintenance reference: keep them in lock-step on every edit.
 *
 * Design notes:
 *   - Reads the per-site pixel_key from `data-key` on its own <script> tag.
 *   - Exposes only `window._fb` (intentionally non-branded so it doesn't
 *     advertise FetchBot on every customer site).
 *   - Honors browser-level Do-Not-Track and Global Privacy Control before
 *     doing anything else — silent no-op in either case.
 *   - All events POST to /api/v1/track/event/ via sendBeacon, falling back
 *     to XHR keepalive if sendBeacon is unavailable.
 *   - The backend enforces a per-pixel_key Origin allowlist, so an exfiltrated
 *     key cannot fire events from another domain.
 */
(function () {
  var s = document.currentScript;
  if (!s) return;
  var key = s.getAttribute('data-key') || '';
  if (!key) return;

  // Respect browser-level consent signals before anything else.
  if (navigator.doNotTrack === '1' || navigator.globalPrivacyControl) return;

  var w = window._fb = window._fb || {};
  w.k = key;
  w.e = 'https://fetchbot.ai/api/v1/track/';
  w.t0 = Date.now();
  w.ms = 0;                       // max scroll depth seen this pageview
  w.u = location.href;             // last URL we sent a pageview for
  w.f = [
    navigator.userAgent,
    screen.width, screen.height,
    navigator.language,
    new Date().getTimezoneOffset(),
    navigator.hardwareConcurrency || '',
  ].join('|');

  // Best-effort region from the browser's own timezone (e.g. "America/
  // New_York"). Sent as a weak last-resort hint; the server resolves the
  // authoritative country from the request IP / edge header.
  function tz() {
    try { return Intl.DateTimeFormat().resolvedOptions().timeZone || ''; }
    catch (_) { return ''; }
  }

  function send(event, extra) {
    var p = {
      pixel_key: w.k,
      event_type: event,
      url: location.href,
      referrer: document.referrer,
      timestamp: new Date().toISOString(),
      user_agent: navigator.userAgent,
      screen_width: screen.width,
      screen_height: screen.height,
      viewport_width: innerWidth,
      viewport_height: innerHeight,
      language: navigator.language,
      timezone: tz(),
      fingerprint: w.f,
      scroll_depth: w.ms,
      time_on_page_ms: Date.now() - w.t0,
    };
    if (extra) for (var k in extra) p[k] = extra[k];
    var body = JSON.stringify(p);
    try {
      navigator.sendBeacon(w.e + 'event/', body);
    } catch (_) {
      var q = new XMLHttpRequest();
      q.open('POST', w.e + 'event/', true);
      q.setRequestHeader('Content-Type', 'application/json');
      q.send(body);
    }
  }
  w.track = send;

  addEventListener('scroll', function () {
    var st = pageYOffset || document.documentElement.scrollTop;
    var dh = Math.max(
      document.body.scrollHeight,
      document.documentElement.scrollHeight,
    ) - innerHeight;
    var p = dh > 0 ? Math.round(st / dh * 100) : 0;
    if (p > w.ms) w.ms = Math.min(p, 100);
  }, { passive: true });

  document.addEventListener('click', function (e) {
    var el = e.target.closest('a,button,[role="button"]');
    if (!el) return;
    send('click', { properties: {
      element: el.tagName.toLowerCase(),
      text: (el.textContent || '').trim().substring(0, 100),
      href: el.href || '',
      id: el.id || '',
    }});
  });

  document.addEventListener('submit', function (e) {
    send('form_submit', { properties: {
      form_id: e.target.id || '',
      form_action: e.target.action || '',
    }});
  });

  // SPA pageview detection via history.pushState + popstate.
  var orig = history.pushState;
  history.pushState = function () {
    orig.apply(this, arguments);
    setTimeout(function () {
      if (location.href !== w.u) {
        w.u = location.href; w.ms = 0; w.t0 = Date.now();
        send('pageview');
      }
    }, 50);
  };
  addEventListener('popstate', function () {
    setTimeout(function () {
      if (location.href !== w.u) {
        w.u = location.href; w.ms = 0; w.t0 = Date.now();
        send('pageview');
      }
    }, 50);
  });

  send('pageview');
  addEventListener('beforeunload', function () {
    send('session_end', { duration: Math.round((Date.now() - w.t0) / 1000) });
  });
})();
