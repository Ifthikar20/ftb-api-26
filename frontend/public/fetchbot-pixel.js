/**
 * FetchBot Tracking Pixel v1.0
 * Lightweight analytics & heatmap data collector.
 * Embed: <script src="https://YOUR_HOST/fetchbot-pixel.js" data-site="YOUR_PIXEL_KEY"></script>
 */
(function () {
    "use strict";

    var script = document.currentScript;
    var pixelKey = script && script.getAttribute("data-site");
    if (!pixelKey) {
        console.warn("[FetchBot] Missing data-site attribute on pixel script.");
        return;
    }

    // API endpoint — same origin or override
    var apiBase = script.getAttribute("data-api") || (script.src ? new URL(script.src).origin : "") || "";
    var endpoint = apiBase + "/api/v1/events/ingest/";
    var batchEndpoint = apiBase + "/api/v1/events/batch/";

    // ── Fingerprint (privacy-first, no cookies) ──
    function fingerprint() {
        var nav = navigator;
        var scr = screen;
        var raw = [
            nav.userAgent,
            nav.language,
            scr.width + "x" + scr.height,
            scr.colorDepth,
            new Date().getTimezoneOffset(),
            nav.hardwareConcurrency || 0,
        ].join("|");
        // Simple hash
        var hash = 0;
        for (var i = 0; i < raw.length; i++) {
            hash = ((hash << 5) - hash + raw.charCodeAt(i)) | 0;
        }
        return "fb_" + Math.abs(hash).toString(36);
    }

    var fp = fingerprint();
    var pageStart = Date.now();
    var maxScroll = 0;
    var eventQueue = [];
    var flushTimer = null;

    // ── Device detection ──
    function deviceType() {
        var ua = navigator.userAgent;
        if (/Mobi|Android/i.test(ua)) return "mobile";
        if (/Tablet|iPad/i.test(ua)) return "tablet";
        return "desktop";
    }

    function browserName() {
        var ua = navigator.userAgent;
        if (ua.indexOf("Chrome") > -1) return "Chrome";
        if (ua.indexOf("Safari") > -1) return "Safari";
        if (ua.indexOf("Firefox") > -1) return "Firefox";
        if (ua.indexOf("Edge") > -1) return "Edge";
        return "Other";
    }

    // ── Send event ──
    function send(eventType, props) {
        var payload = {
            pixel_key: pixelKey,
            url: location.href,
            referrer: document.referrer || "",
            event_type: eventType,
            fingerprint: fp,
            device_type: deviceType(),
            browser: browserName(),
            os: navigator.platform || "",
            timestamp: new Date().toISOString(),
            properties: props || {},
        };

        // Use sendBeacon for reliability (doesn't block page unload)
        if (navigator.sendBeacon) {
            navigator.sendBeacon(endpoint, JSON.stringify(payload));
        } else {
            var xhr = new XMLHttpRequest();
            xhr.open("POST", endpoint, true);
            xhr.setRequestHeader("Content-Type", "application/json");
            xhr.send(JSON.stringify(payload));
        }
    }

    // ── Queue + batch ──
    function queueEvent(eventType, props) {
        eventQueue.push({
            url: location.href,
            referrer: document.referrer || "",
            event_type: eventType,
            fingerprint: fp,
            device_type: deviceType(),
            browser: browserName(),
            os: navigator.platform || "",
            timestamp: new Date().toISOString(),
            properties: props || {},
        });

        if (!flushTimer) {
            flushTimer = setTimeout(flushQueue, 3000);
        }
    }

    function flushQueue() {
        flushTimer = null;
        if (!eventQueue.length) return;
        var batch = eventQueue.splice(0, 50);
        var payload = JSON.stringify({ pixel_key: pixelKey, events: batch });
        if (navigator.sendBeacon) {
            navigator.sendBeacon(batchEndpoint, payload);
        } else {
            var xhr = new XMLHttpRequest();
            xhr.open("POST", batchEndpoint, true);
            xhr.setRequestHeader("Content-Type", "application/json");
            xhr.send(payload);
        }
    }

    // ── 1. Pageview ──
    send("pageview");

    // ── 2. Click tracking (heatmap) ──
    document.addEventListener(
        "click",
        function (e) {
            var rect = document.documentElement;
            var xPct = ((e.clientX + window.scrollX) / Math.max(rect.scrollWidth, 1)) * 100;
            var yPct = ((e.clientY + window.scrollY) / Math.max(rect.scrollHeight, 1)) * 100;

            var target = e.target;
            var selector = target.tagName.toLowerCase();
            if (target.id) selector += "#" + target.id;
            else if (target.className && typeof target.className === "string")
                selector += "." + target.className.trim().split(/\s+/).slice(0, 2).join(".");

            queueEvent("click", {
                x_pct: Math.round(xPct * 10) / 10,
                y_pct: Math.round(yPct * 10) / 10,
                selector: selector,
                text: (target.textContent || "").trim().substring(0, 50),
                viewport_w: window.innerWidth,
                viewport_h: window.innerHeight,
            });
        },
        true
    );

    // ── 3. Scroll depth ──
    var scrollMilestones = { 25: false, 50: false, 75: false, 100: false };

    function trackScroll() {
        var winH = window.innerHeight;
        var docH = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight) - winH;
        if (docH <= 0) return;
        var pct = Math.min(100, Math.round((window.scrollY / docH) * 100));
        maxScroll = Math.max(maxScroll, pct);

        [25, 50, 75, 100].forEach(function (milestone) {
            if (pct >= milestone && !scrollMilestones[milestone]) {
                scrollMilestones[milestone] = true;
                queueEvent("scroll", { depth: milestone });
            }
        });
    }

    var scrollDebounce = null;
    window.addEventListener("scroll", function () {
        if (scrollDebounce) return;
        scrollDebounce = setTimeout(function () {
            scrollDebounce = null;
            trackScroll();
        }, 200);
    });

    // ── 4. Time on page + exit ──
    function sendExit() {
        var timeMs = Date.now() - pageStart;
        send("exit", {
            time_on_page_ms: timeMs,
            max_scroll_pct: maxScroll,
        });
        flushQueue();
    }

    // Use both visibilitychange and beforeunload for coverage
    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "hidden") sendExit();
    });
    window.addEventListener("beforeunload", sendExit);

    // ── 5. Form submit tracking ──
    document.addEventListener(
        "submit",
        function (e) {
            var form = e.target;
            if (!form || form.tagName !== "FORM") return;
            send("form_submit", {
                action: form.action || "",
                method: form.method || "get",
                id: form.id || "",
            });
        },
        true
    );

    // Expose for manual custom events
    window.fetchbot = {
        track: function (name, props) {
            send("custom", { event_name: name, ...(props || {}) });
        },
    };
})();
