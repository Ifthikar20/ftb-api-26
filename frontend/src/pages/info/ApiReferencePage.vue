<template>
  <InfoPage title="API reference" eyebrow="Developers" intro="The FetchBot REST API exposes every dashboard primitive — prompts, probes, citations, briefs — for programmatic use.">
    <h2>Base URL</h2>
    <div class="info-card">
      <p><strong>https://api.fetchbot.ai/api/v1/</strong></p>
      <p>All endpoints accept and return JSON. Authentication is via JWT bearer tokens issued by <code>/auth/login/</code>.</p>
    </div>

    <h2>Authentication</h2>
    <p>Exchange email + password for a short-lived access token and an HttpOnly refresh cookie:</p>
    <div class="info-card">
      <p><strong>POST</strong> <code>/auth/login/</code> &middot; body: <code>{ "email": "...", "password": "..." }</code></p>
      <p>Subsequent requests pass <code>Authorization: Bearer &lt;access&gt;</code>. Refresh with <code>POST /auth/refresh/</code>.</p>
    </div>

    <h2>Common endpoints</h2>
    <div class="info-grid">
      <div>
        <h4>GET /websites/</h4>
        <p>List the websites accessible to the authenticated user.</p>
      </div>
      <div>
        <h4>POST /llm-ranking/audits/</h4>
        <p>Trigger a fresh multi-LLM probe for a website's prompt library.</p>
      </div>
      <div>
        <h4>GET /citations/source-influence/</h4>
        <p>Per-provider source-mix breakdown over a rolling window.</p>
      </div>
      <div>
        <h4>POST /content-studio/briefs/</h4>
        <p>Generate a grounded brief from a visibility gap.</p>
      </div>
    </div>

    <h2>Rate limits</h2>
    <p>
      Authenticated requests are capped at 60 per minute per user by default. Audit-trigger
      endpoints obey an additional per-website quota to protect upstream LLM providers.
    </p>

    <h2>Full spec</h2>
    <p>
      The complete OpenAPI schema is published at
      <a href="https://docs.fetchbot.ai/api" target="_blank" rel="noopener">docs.fetchbot.ai/api</a>.
    </p>
  </InfoPage>
</template>

<script setup>
import InfoPage from './InfoPage.vue'
</script>
