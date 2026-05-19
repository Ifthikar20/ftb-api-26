<template>
  <InfoPage title="Documentation" eyebrow="Guides" intro="Everything you need to set up FetchBot, connect your stack, and start measuring AI visibility within minutes.">
    <h2>Getting started</h2>
    <ol>
      <li><strong>Create an account.</strong> An admin provisions your user; check the welcome email for credentials.</li>
      <li><strong>Add your first website.</strong> Paste the URL — onboarding scans the homepage and seeds a starter prompt library.</li>
      <li><strong>Run your first audit.</strong> FetchBot probes Claude, GPT-4, Gemini, and Perplexity for each prompt and stores the citations.</li>
      <li><strong>Review the dashboard.</strong> Visibility score, source mix, and competitor share are ready inside 10 minutes.</li>
    </ol>

    <h2>Core concepts</h2>
    <div class="info-grid">
      <div>
        <h4>Prompt Library</h4>
        <p>The set of demand-side queries we ask the LLMs on your behalf each week.</p>
      </div>
      <div>
        <h4>Brand Vault</h4>
        <p>Your verified facts — the only grounding context Content Studio is allowed to use.</p>
      </div>
      <div>
        <h4>Source Influence</h4>
        <p>Per-provider breakdown of which domains each model is citing.</p>
      </div>
      <div>
        <h4>Content Studio</h4>
        <p>Turn a visibility gap into a grounded brief, draft, and publish.</p>
      </div>
    </div>

    <h2>Need a deeper dive?</h2>
    <p>
      The full handbook lives at <a href="https://docs.fetchbot.ai" target="_blank" rel="noopener">docs.fetchbot.ai</a>.
    </p>
  </InfoPage>
</template>

<script setup>
import InfoPage from './InfoPage.vue'
</script>
