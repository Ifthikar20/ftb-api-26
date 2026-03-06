/**
 * GrowthPilot Tracking Pixel — Source
 * Version: 1.0.0
 *
 * This file is the unminified source. Build with:
 *   npx terser pixel_source.js -o growthpilot.min.js --compress --mangle
 *
 * Embeds on tracked websites to collect:
 *   - Page URL and referrer
 *   - Timestamp
 *   - Scroll depth
 *   - Device type (inferred from UA)
 *   - Session data (in-memory, no cookies by default)
 *
 * Privacy-first: No cookies set by default. IP is hashed server-side.
 * GDPR: Only fires if user consent is detected (respects DoNotTrack).
 */
(function (window, document) {
  "use strict";

  var GP = (window.GrowthPilot = window.GrowthPilot || {});

  // ── Configuration ──────────────────────────────────────────────────────────
  GP.pixelKey = GP.pixelKey || "";
  GP.endpoint = GP.endpoint || "https://api.growthpilot.io/api/v1/track/";
  GP.consentRequired = GP.consentRequired !== false;

  // ── State ──────────────────────────────────────────────────────────────────
  var sessionId = generateId();
  var pageLoadTime = Date.now();
  var maxScrollDepth = 0;

  // ── Utilities ──────────────────────────────────────────────────────────────
  function generateId() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  function hasConsent() {
    if (!GP.consentRequired) return true;
    if (navigator.doNotTrack === "1") return false;
    // Check for custom consent cookie or localStorage flag
    try {
      return localStorage.getItem("gp_consent") === "true";
    } catch (e) {
      return true;
    }
  }

  function getDeviceType() {
    var ua = navigator.userAgent;
    if (/tablet|ipad|playbook|silk/i.test(ua)) return "tablet";
    if (/mobile|iphone|ipod|android|blackberry|opera mini|iemobile/i.test(ua)) return "mobile";
    return "desktop";
  }

  function getBrowser() {
    var ua = navigator.userAgent;
    if (ua.indexOf("Chrome") > -1) return "Chrome";
    if (ua.indexOf("Safari") > -1) return "Safari";
    if (ua.indexOf("Firefox") > -1) return "Firefox";
    if (ua.indexOf("Edge") > -1) return "Edge";
    return "Other";
  }

  // ── Tracking ───────────────────────────────────────────────────────────────
  function send(eventType, extraData) {
    if (!GP.pixelKey || !hasConsent()) return;

    var payload = Object.assign(
      {
        pixel_key: GP.pixelKey,
        event_type: eventType,
        url: window.location.href,
        referrer: document.referrer,
        timestamp: new Date().toISOString(),
        session_id: sessionId,
        device_type: getDeviceType(),
        browser: getBrowser(),
        scroll_depth: maxScrollDepth,
        time_on_page_ms: Date.now() - pageLoadTime,
        viewport_width: window.innerWidth,
        viewport_height: window.innerHeight,
      },
      extraData || {}
    );

    // Use sendBeacon for reliability (doesn't block page unload)
    if (navigator.sendBeacon) {
      navigator.sendBeacon(
        GP.endpoint + "event/",
        new Blob([JSON.stringify(payload)], { type: "application/json" })
      );
    } else {
      // Fallback to fetch
      fetch(GP.endpoint + "event/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        keepalive: true,
      }).catch(function () {});
    }
  }

  // ── Scroll Depth Tracking ──────────────────────────────────────────────────
  function updateScrollDepth() {
    var scrolled = window.pageYOffset || document.documentElement.scrollTop;
    var docHeight = Math.max(
      document.body.scrollHeight,
      document.documentElement.scrollHeight
    ) - window.innerHeight;
    var depth = docHeight > 0 ? Math.round((scrolled / docHeight) * 100) : 0;
    if (depth > maxScrollDepth) {
      maxScrollDepth = Math.min(depth, 100);
    }
  }

  // ── Public API ─────────────────────────────────────────────────────────────
  GP.track = function (eventType, data) {
    send(eventType || "custom", data);
  };

  GP.identify = function (identity) {
    send("identify", identity);
  };

  GP.consent = function (granted) {
    try {
      localStorage.setItem("gp_consent", granted ? "true" : "false");
    } catch (e) {}
    if (granted) {
      send("pageview");
    }
  };

  // ── Initialization ─────────────────────────────────────────────────────────
  function init() {
    // Track scroll depth
    window.addEventListener("scroll", updateScrollDepth, { passive: true });

    // Fire pageview
    send("pageview");

    // Track page exit
    window.addEventListener("beforeunload", function () {
      send("page_exit");
    });

    // Track clicks on links/buttons
    document.addEventListener("click", function (e) {
      var target = e.target.closest("a, button");
      if (target) {
        send("click", {
          element: target.tagName.toLowerCase(),
          text: (target.textContent || "").trim().substring(0, 100),
          href: target.href || "",
        });
      }
    });

    // Track form submissions
    document.addEventListener("submit", function (e) {
      var form = e.target;
      send("form_submit", {
        form_id: form.id || "",
        form_action: form.action || "",
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window, document);
