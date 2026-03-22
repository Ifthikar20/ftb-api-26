"""
Dynamic SEO Optimization — serve optimization script and rules to live websites.
Public (no auth) endpoints for the JS script to consume.
"""
import hashlib
import json
import logging

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.views import View
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.websites.models import Website

logger = logging.getLogger("apps")


class SEOScriptView(View):
    """
    Serve the COMBINED FetchBot script — analytics tracking + SEO optimizer.
    Single JS file, single <script> tag. Public endpoint.
    """

    def get(self, request, website_id):
        try:
            website = Website.objects.get(id=website_id)
        except Website.DoesNotExist:
            return HttpResponse("// invalid site", content_type="application/javascript")

        api_base = request.build_absolute_uri("/api/v1/")
        track_endpoint = request.build_absolute_uri("/api/v1/track/")
        pixel_key = str(website.pixel_key)

        script = f"""
(function() {{
  'use strict';

  /* ═══════════════════════════════════════════════
     FetchBot v1.0 — Analytics + SEO Optimizer
     Single script: visitor tracking + SEO auto-fix
     ═══════════════════════════════════════════════ */

  var FB = window.FetchBot = window.FetchBot || {{}};
  FB.siteId   = '{website_id}';
  FB.pixelKey = '{pixel_key}';
  FB.api      = '{api_base}';
  FB.track    = '{track_endpoint}';
  FB.v        = '1.0';
  FB.applied  = [];

  /* ─── PART 1: ANALYTICS TRACKING ─── */

  var sid = sessionStorage.getItem('fb_sid');
  if (!sid) {{ sid = Math.random().toString(36).substr(2, 12); sessionStorage.setItem('fb_sid', sid); }}
  FB.sessionId = sid;

  function send(eventType, extra) {{
    var payload = Object.assign({{
      pixel_key: FB.pixelKey,
      event_type: eventType,
      url: window.location.href,
      path: window.location.pathname,
      referrer: document.referrer,
      title: document.title,
      session_id: FB.sessionId,
      screen_w: screen.width,
      screen_h: screen.height,
      timestamp: new Date().toISOString()
    }}, extra || {{}});
    navigator.sendBeacon(FB.track + 'event/', JSON.stringify(payload));
  }}

  // Track pageview
  send('pageview');

  // Track clicks
  document.addEventListener('click', function(e) {{
    var t = e.target.closest('a, button, [data-fb-track]');
    if (t) {{
      send('click', {{
        element: t.tagName.toLowerCase(),
        text: (t.textContent || '').trim().slice(0, 100),
        href: t.href || '',
        x: e.clientX,
        y: e.clientY
      }});
    }}
  }});

  // Track scroll depth
  var maxScroll = 0;
  var scrollTimer;
  window.addEventListener('scroll', function() {{
    clearTimeout(scrollTimer);
    scrollTimer = setTimeout(function() {{
      var s = Math.round((window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100);
      if (s > maxScroll) {{
        maxScroll = s;
        if (maxScroll === 25 || maxScroll === 50 || maxScroll === 75 || maxScroll === 100) {{
          send('scroll', {{ depth: maxScroll }});
        }}
      }}
    }}, 200);
  }});

  // Track form submissions
  document.addEventListener('submit', function(e) {{
    var f = e.target;
    send('form_submit', {{ form_id: f.id || '', form_action: f.action || '' }});
  }});

  // Track time on page (send on unload)
  var pageStart = Date.now();
  window.addEventListener('beforeunload', function() {{
    send('time_on_page', {{ duration_ms: Date.now() - pageStart, max_scroll: maxScroll }});
  }});

  /* ─── PART 2: SEO OPTIMIZER ─── */

  function fetchRules() {{
    return fetch(FB.api + 'analytics/{website_id}/seo-rules/')
      .then(function(r) {{ return r.json(); }})
      .catch(function() {{ return {{}}; }});
  }}

  function setMeta(attr, value) {{
    var el = document.querySelector('meta[' + attr + ']');
    if (el) {{
      if (el.getAttribute('content') !== value) {{
        el.setAttribute('content', value);
        FB.applied.push({{ type: 'meta', tag: attr }});
      }}
    }} else {{
      el = document.createElement('meta');
      var parts = attr.split('=');
      el.setAttribute(parts[0].trim(), parts[1].replace(/"/g, '').trim());
      el.setAttribute('content', value);
      document.head.appendChild(el);
      FB.applied.push({{ type: 'meta_add', tag: attr }});
    }}
  }}

  function setSchema(schema) {{
    if (!schema) return;
    var old = document.querySelector('script[type="application/ld+json"][data-fb="1"]');
    if (old) old.remove();
    var s = document.createElement('script');
    s.type = 'application/ld+json'; s.setAttribute('data-fb', '1');
    s.textContent = JSON.stringify(schema);
    document.head.appendChild(s);
    FB.applied.push({{ type: 'schema', t: schema['@type'] || '' }});
  }}

  function setOG(og) {{
    if (!og) return;
    for (var k in og) {{ if (og.hasOwnProperty(k)) setMeta('property="og:' + k + '"', og[k]); }}
  }}

  function setHreflang(tags) {{
    if (!tags) return;
    tags.forEach(function(t) {{
      if (!document.querySelector('link[hreflang="' + t.lang + '"]')) {{
        var l = document.createElement('link');
        l.rel = 'alternate'; l.hreflang = t.lang; l.href = t.href;
        document.head.appendChild(l);
        FB.applied.push({{ type: 'hreflang', lang: t.lang }});
      }}
    }});
  }}

  function optimize() {{
    fetchRules().then(function(data) {{
      var rules = data.rules || data;
      var path = window.location.pathname;

      // Global rules
      if (rules.global) {{
        if (rules.global.schema) setSchema(rules.global.schema);
        if (rules.global.og) setOG(rules.global.og);
        if (rules.global.hreflang) setHreflang(rules.global.hreflang);
        if (rules.global.geo) {{
          var g = rules.global.geo;
          if (g.region) setMeta('name="geo.region"', g.region);
          if (g.placename) setMeta('name="geo.placename"', g.placename);
        }}
        if (rules.global.canonical && !document.querySelector('link[rel="canonical"]')) {{
          var c = document.createElement('link'); c.rel = 'canonical';
          c.href = rules.global.canonical.replace('{{path}}', path);
          document.head.appendChild(c);
          FB.applied.push({{ type: 'canonical' }});
        }}
      }}

      // Page-specific rules
      var pr = null;
      if (rules.pages) {{
        for (var p in rules.pages) {{
          if (path === p || path.indexOf(p) === 0) {{ pr = rules.pages[p]; break; }}
        }}
      }}
      if (pr) {{
        if (pr.title && document.title !== pr.title) {{ document.title = pr.title; FB.applied.push({{ type: 'title' }}); }}
        if (pr.description) setMeta('name="description"', pr.description);
        if (pr.schema) setSchema(pr.schema);
        if (pr.og) setOG(pr.og);
      }}

      // Report optimizations
      if (FB.applied.length) {{
        setTimeout(function() {{
          navigator.sendBeacon(
            FB.api + 'analytics/{website_id}/seo-report/',
            JSON.stringify({{ url: location.href, applied: FB.applied, ts: new Date().toISOString() }})
          );
        }}, 2000);
      }}
    }});
  }}

  // Run SEO optimizer after DOM ready
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', optimize);
  }} else {{
    optimize();
  }}
}})();
"""
        response = HttpResponse(script.strip(), content_type="application/javascript")
        response["Cache-Control"] = "public, max-age=300"
        response["Access-Control-Allow-Origin"] = "*"
        return response


class SEORulesView(View):
    """
    Serve optimization rules for a website.
    Public JSON endpoint consumed by the optimization script.
    Generates rules based on the latest scan data.
    """

    def get(self, request, website_id):
        try:
            website = Website.objects.get(id=website_id)
        except Website.DoesNotExist:
            return JsonResponse({"rules": {}}, status=404)

        cache_key = f"seo_rules_{website_id}"
        cached = cache.get(cache_key)
        if cached:
            resp = JsonResponse(cached)
            resp["Access-Control-Allow-Origin"] = "*"
            return resp

        # Get latest scan data
        scan_key = f"seo_scan_{hashlib.md5(website.url.encode()).hexdigest()}"
        scan_data = cache.get(scan_key) or {}

        from urllib.parse import urlparse
        parsed = urlparse(website.url)
        domain = parsed.netloc
        site_name = domain.replace("www.", "").split(".")[0].title()

        rules = {
            "global": {
                # Schema: WebSite + Organization
                "schema": {
                    "@context": "https://schema.org",
                    "@type": "WebSite",
                    "name": site_name,
                    "url": website.url,
                    "potentialAction": {
                        "@type": "SearchAction",
                        "target": f"{website.url}?q={{search_term_string}}",
                        "query-input": "required name=search_term_string",
                    },
                },
                # Canonical
                "canonical": website.url.rstrip("/") + "{path}",
                # Open Graph defaults
                "og": {
                    "type": "website",
                    "site_name": site_name,
                    "url": website.url,
                },
            },
            "pages": {},
        }

        # Add geo tags if not detected
        if scan_data:
            geo = scan_data.get("geo_data", {})
            if not geo.get("has_geo_tags"):
                rules["global"]["geo"] = {
                    "region": "US",
                }

            # Add hreflang if not present
            if not geo.get("hreflang"):
                rules["global"]["hreflang"] = [
                    {"lang": "en", "href": website.url},
                    {"lang": "x-default", "href": website.url},
                ]

            # Page-specific optimizations from scan
            meta = scan_data.get("page_meta", {})
            keywords = scan_data.get("keywords", [])
            top_kws = [k["keyword"] for k in keywords[:5]]
            kw_str = ", ".join(top_kws) if top_kws else ""

            if meta.get("title"):
                title = meta["title"]
                # If title is short, suggest enhanced version
                if len(title) < 40 and kw_str:
                    rules["pages"]["/"] = {
                        "title": f"{title} | {kw_str.title()}",
                        "description": meta.get("meta_description", ""),
                        "og": {
                            "title": title,
                            "description": meta.get("meta_description", ""),
                        },
                    }

            # Per-page rules from multi-page scan
            for page in scan_data.get("per_page", []):
                page_path = "/"
                try:
                    page_path = urlparse(page["url"]).path or "/"
                except Exception:
                    pass

                if page_path not in rules["pages"]:
                    page_kws = page.get("top_keywords", [])
                    page_title = page.get("title", "")
                    if page_kws and page_title:
                        rules["pages"][page_path] = {
                            "schema": {
                                "@context": "https://schema.org",
                                "@type": "WebPage",
                                "name": page_title,
                                "url": page["url"],
                                "keywords": ", ".join(page_kws[:5]),
                            },
                        }

        cache.set(cache_key, rules, 600)  # Cache 10 min
        resp = JsonResponse(rules)
        resp["Access-Control-Allow-Origin"] = "*"
        return resp


class SEOReportView(View):
    """
    Receive reports from the optimization script.
    Public POST endpoint — receives beacon data.
    """

    def post(self, request, website_id):
        try:
            body = json.loads(request.body) if request.body else {}
            logger.info(f"SEO opt report for {website_id}: {body.get('url', 'unknown')} — {len(body.get('applied', []))} optimizations")
            # TODO: store in DB for dashboard metrics
        except Exception as e:
            logger.warning(f"SEO report parse error: {e}")

        resp = JsonResponse({"ok": True})
        resp["Access-Control-Allow-Origin"] = "*"
        return resp


class SEOEmbedCodeView(APIView):
    """
    GET — return the single combined embed code.
    One <script> tag for both analytics + SEO.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        try:
            website = Website.objects.get(id=website_id, user=request.user)
        except Website.DoesNotExist:
            return Response({"error": "Website not found"}, status=404)

        script_url = request.build_absolute_uri(f"/api/v1/analytics/{website_id}/seo-script/")

        embed_code = (
            f'<!-- FetchBot — Analytics + SEO Optimizer -->\n'
            f'<script src="{script_url}" data-site="{website_id}" defer></script>'
        )

        return Response({
            "data": {
                "embed_code": embed_code,
                "script_url": script_url,
                "website_id": str(website_id),
                "website_url": website.url,
            }
        })
