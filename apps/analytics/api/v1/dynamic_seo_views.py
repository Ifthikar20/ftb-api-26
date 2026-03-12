"""
Dynamic SEO Optimization — serve optimization script and rules to live websites.
Public (no auth) endpoints for the JS script to consume.
"""
import hashlib
import json
import logging

from django.http import HttpResponse, JsonResponse
from django.views import View
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from apps.analytics.services.seo_keyword_scanner import SEOKeywordScanner
from apps.websites.models import Website

logger = logging.getLogger("apps")


class SEOScriptView(View):
    """
    Serve the dynamic optimization JS script.
    Public endpoint — called by <script> tag on user's website.
    """

    def get(self, request, website_id):
        # Validate website exists
        try:
            website = Website.objects.get(id=website_id)
        except Website.DoesNotExist:
            return HttpResponse("// invalid site", content_type="application/javascript")

        api_base = request.build_absolute_uri("/api/v1/analytics/")

        script = f"""
(function() {{
  'use strict';
  var FBOpt = window.FBOpt = window.FBOpt || {{}};
  FBOpt.siteId = '{website_id}';
  FBOpt.apiBase = '{api_base}';
  FBOpt.version = '1.0';
  FBOpt.applied = [];

  // Fetch optimization rules from FetchBot API
  function fetchRules() {{
    return fetch(FBOpt.apiBase + '{website_id}/seo-rules/')
      .then(function(r) {{ return r.json(); }})
      .catch(function() {{ return {{ rules: [] }}; }});
  }}

  // Apply meta tag optimization
  function applyMeta(tag, attr, value) {{
    var el = document.querySelector('meta[' + attr + ']');
    if (el) {{
      var old = el.getAttribute('content');
      if (old !== value) {{
        el.setAttribute('content', value);
        FBOpt.applied.push({{ type: 'meta', tag: attr, old: old, new: value }});
      }}
    }} else {{
      el = document.createElement('meta');
      if (attr.indexOf('property=') === 0) {{
        el.setAttribute('property', attr.split('=')[1].replace(/"/g, ''));
      }} else {{
        el.setAttribute('name', attr.split('=')[1].replace(/"/g, ''));
      }}
      el.setAttribute('content', value);
      document.head.appendChild(el);
      FBOpt.applied.push({{ type: 'meta_add', tag: attr, new: value }});
    }}
  }}

  // Apply title optimization
  function applyTitle(value) {{
    if (value && document.title !== value) {{
      var old = document.title;
      document.title = value;
      FBOpt.applied.push({{ type: 'title', old: old, new: value }});
    }}
  }}

  // Inject JSON-LD schema
  function applySchema(schema) {{
    if (!schema) return;
    var existing = document.querySelector('script[type="application/ld+json"][data-fb="1"]');
    if (existing) existing.remove();
    var el = document.createElement('script');
    el.type = 'application/ld+json';
    el.setAttribute('data-fb', '1');
    el.textContent = JSON.stringify(schema);
    document.head.appendChild(el);
    FBOpt.applied.push({{ type: 'schema', schema_type: schema['@type'] || 'unknown' }});
  }}

  // Inject canonical tag if missing
  function applyCanonical(url) {{
    if (!url) return;
    var existing = document.querySelector('link[rel="canonical"]');
    if (!existing) {{
      var link = document.createElement('link');
      link.rel = 'canonical';
      link.href = url;
      document.head.appendChild(link);
      FBOpt.applied.push({{ type: 'canonical', url: url }});
    }}
  }}

  // Inject Open Graph tags
  function applyOG(og) {{
    if (!og) return;
    for (var key in og) {{
      if (og.hasOwnProperty(key)) {{
        applyMeta('og:' + key, 'property="og:' + key + '"', og[key]);
      }}
    }}
  }}

  // Add hreflang tags
  function applyHreflang(tags) {{
    if (!tags || !tags.length) return;
    tags.forEach(function(t) {{
      var existing = document.querySelector('link[hreflang="' + t.lang + '"]');
      if (!existing) {{
        var link = document.createElement('link');
        link.rel = 'alternate';
        link.hreflang = t.lang;
        link.href = t.href;
        document.head.appendChild(link);
        FBOpt.applied.push({{ type: 'hreflang', lang: t.lang }});
      }}
    }});
  }}

  // Inject geo meta tags
  function applyGeoTags(geo) {{
    if (!geo) return;
    if (geo.region) applyMeta('geo.region', 'name="geo.region"', geo.region);
    if (geo.placename) applyMeta('geo.placename', 'name="geo.placename"', geo.placename);
    if (geo.position) applyMeta('geo.position', 'name="geo.position"', geo.position);
  }}

  // Report what was applied back to FetchBot
  function report() {{
    if (!FBOpt.applied.length) return;
    var payload = {{
      url: window.location.href,
      title: document.title,
      applied: FBOpt.applied,
      timestamp: new Date().toISOString()
    }};
    navigator.sendBeacon(
      FBOpt.apiBase + '{website_id}/seo-report/',
      JSON.stringify(payload)
    );
  }}

  // Main: fetch rules and apply
  function optimize() {{
    fetchRules().then(function(data) {{
      var rules = data.rules || data;
      var path = window.location.pathname;

      // Find matching rule for current page
      var pageRule = null;
      if (rules.pages) {{
        for (var p in rules.pages) {{
          if (path === p || path.indexOf(p) === 0) {{
            pageRule = rules.pages[p];
            break;
          }}
        }}
      }}

      // Apply global rules
      if (rules.global) {{
        if (rules.global.schema) applySchema(rules.global.schema);
        if (rules.global.og) applyOG(rules.global.og);
        if (rules.global.hreflang) applyHreflang(rules.global.hreflang);
        if (rules.global.geo) applyGeoTags(rules.global.geo);
        if (rules.global.canonical) applyCanonical(rules.global.canonical);
      }}

      // Apply page-specific rules
      if (pageRule) {{
        if (pageRule.title) applyTitle(pageRule.title);
        if (pageRule.description) applyMeta('description', 'name="description"', pageRule.description);
        if (pageRule.schema) applySchema(pageRule.schema);
        if (pageRule.og) applyOG(pageRule.og);
      }}

      // Report after short delay
      setTimeout(report, 2000);
    }});
  }}

  // Run after DOM ready
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
    GET — return the embed code snippet for this website.
    Authenticated endpoint for the dashboard.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        try:
            website = Website.objects.get(id=website_id, user=request.user)
        except Website.DoesNotExist:
            return Response({"error": "Website not found"}, status=404)

        script_url = request.build_absolute_uri(f"/api/v1/analytics/{website_id}/seo-script/")

        embed_code = (
            f'<script src="{script_url}" '
            f'data-site="{website_id}" '
            f'id="fb-seo-optimizer" '
            f'defer></script>'
        )

        return Response({
            "data": {
                "embed_code": embed_code,
                "script_url": script_url,
                "website_id": str(website_id),
                "website_url": website.url,
            }
        })
