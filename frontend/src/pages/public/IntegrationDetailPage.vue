<template>
  <div class="int-detail" v-if="integration">
    <!-- Nav -->
    <nav class="id-nav" :class="{ scrolled }">
      <div class="id-nav-row">
        <router-link to="/" class="id-brand">
          <img src="/images/fb-logo.png" alt="FetchBot" class="id-brand-logo" />
          <span class="id-brand-name">FetchBot</span>
        </router-link>
        <div class="id-nav-links">
          <router-link to="/">Home</router-link>
          <router-link to="/integrations">Integrations</router-link>
        </div>
        <div class="id-nav-right">
          <router-link to="/login" class="id-nav-login">Log In</router-link>
          <router-link to="/login" class="id-nav-cta">Get Started</router-link>
        </div>
      </div>
    </nav>

    <!-- Breadcrumb -->
    <div class="id-breadcrumb-wrap">
      <div class="id-breadcrumb">
        <router-link to="/integrations">← All Integrations</router-link>
        <span>/</span>
        <span class="id-bc-current">{{ integration.name }}</span>
      </div>
    </div>

    <!-- Hero -->
    <section class="id-hero">
      <div class="id-hero-inner">
        <div class="id-hero-left">
          <div class="id-hero-icon" :style="{ background: integration.bgColor }">
            <span v-html="integration.icon"></span>
          </div>
          <div>
            <span class="id-hero-tag" :style="{ color: integration.tagColor, background: integration.tagBg }">{{ integration.category }}</span>
            <h1>{{ integration.name }}</h1>
            <p class="id-hero-short">{{ integration.shortDesc }}</p>
          </div>
        </div>
        <div class="id-hero-actions">
          <router-link to="/login" class="id-btn-primary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
            Get Started
          </router-link>
          <a :href="integration.docsUrl || '#'" class="id-btn-ghost">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>
            Setup Guide
          </a>
        </div>
      </div>
    </section>

    <!-- Content -->
    <section class="id-content">
      <div class="id-content-inner">
        <!-- Main Description -->
        <div class="id-main">
          <div class="id-desc-card">
            <h2>About this integration</h2>
            <p>{{ integration.longDesc }}</p>
          </div>

          <!-- How it works -->
          <div class="id-steps-card">
            <h2>How it works</h2>
            <div class="id-steps">
              <div class="id-step" v-for="(step, idx) in setupSteps" :key="idx">
                <div class="id-step-num">{{ idx + 1 }}</div>
                <div>
                  <h4>{{ step.title }}</h4>
                  <p>{{ step.desc }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Sidebar -->
        <aside class="id-aside">
          <!-- Features -->
          <div class="id-features-card">
            <h3>Features</h3>
            <ul>
              <li v-for="f in integration.features" :key="f">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="3"><path d="M20 6 9 17l-5-5"/></svg>
                {{ f }}
              </li>
            </ul>
          </div>

          <!-- Quick Info -->
          <div class="id-info-card">
            <h3>Details</h3>
            <div class="id-info-row">
              <span class="id-info-label">Category</span>
              <span class="id-info-value">{{ integration.category }}</span>
            </div>
            <div class="id-info-row">
              <span class="id-info-label">Setup</span>
              <span class="id-info-value">Under 30 seconds</span>
            </div>
            <div class="id-info-row">
              <span class="id-info-label">Code Required</span>
              <span class="id-info-value">None</span>
            </div>
            <div class="id-info-row">
              <span class="id-info-label">Data Sync</span>
              <span class="id-info-value">Real-time</span>
            </div>
          </div>
        </aside>
      </div>
    </section>

    <!-- Related Integrations -->
    <section class="id-related" v-if="relatedIntegrations.length">
      <div class="id-related-inner">
        <h2>Related Integrations</h2>
        <div class="id-related-grid">
          <router-link
            v-for="rel in relatedIntegrations" :key="rel.slug"
            :to="`/integration/${rel.slug}`"
            class="id-related-card"
          >
            <div class="id-related-icon" :style="{ background: rel.bgColor }">
              <span v-html="rel.icon"></span>
            </div>
            <div>
              <h4>{{ rel.name }}</h4>
              <p>{{ rel.shortDesc }}</p>
            </div>
          </router-link>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="id-cta">
      <div class="id-cta-inner">
        <h2>Ready to connect {{ integration.name }}?</h2>
        <p>Set up in under 30 seconds. No code required.</p>
        <router-link to="/login" class="id-btn-primary-lg">
          Get Started Free
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
        </router-link>
      </div>
    </section>

    <!-- Footer -->
    <footer class="id-footer">
      <div class="id-footer-inner">
        <div class="id-footer-brand">
          <img src="/images/fb-logo.png" alt="FetchBot" width="24" />
          <span>FetchBot</span>
        </div>
        <div class="id-footer-links">
          <router-link to="/">Home</router-link>
          <router-link to="/integrations">Integrations</router-link>
          <router-link to="/terms">Terms</router-link>
          <router-link to="/privacy">Privacy</router-link>
        </div>
        <span class="id-footer-copy">© {{ new Date().getFullYear() }} FetchBot</span>
      </div>
    </footer>
  </div>

  <!-- 404 fallback -->
  <div v-else class="id-not-found">
    <h1>Integration not found</h1>
    <p>The integration you're looking for doesn't exist.</p>
    <router-link to="/integrations" class="id-btn-primary">View all integrations</router-link>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const scrolled = ref(false)

function onScroll() { scrolled.value = window.scrollY > 20 }
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))

// Full integration catalog (shared source of truth)
const allIntegrations = [
  { slug: 'fetchbot-pixel', name: 'FetchBot Pixel', category: 'Analytics', categoryKey: 'analytics', shortDesc: 'One-line JavaScript snippet for real-time visitor tracking, heatmaps, and session recording.', bgColor: 'linear-gradient(135deg, #6366f120, #8b5cf620)', tagColor: '#6366f1', tagBg: '#6366f110', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.5"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>', longDesc: 'Install FetchBot\'s lightweight tracking pixel on any website with a single line of code. Automatically captures pageviews, clicks, scroll depth, and session recordings — zero configuration required. The pixel also powers real-time heatmaps and visitor identification for the full analytics suite.', features: ['Real-time visitor tracking', 'Click and scroll heatmaps', 'Session recording', 'Zero-config installation'], docsUrl: '#' },
  { slug: 'google-analytics', name: 'Google Analytics', category: 'Analytics', categoryKey: 'analytics', shortDesc: 'Import your GA4 data into FetchBot for unified analytics and AI-powered insights.', bgColor: 'linear-gradient(135deg, #f9ab0020, #e3740020)', tagColor: '#e37400', tagBg: '#e3740010', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#e37400"><path d="M22 12c0-5.5-4.5-10-10-10S2 6.5 2 12s4.5 10 10 10c1 0 2-.2 3-.4V14h-4v-3h7v1z"/></svg>', longDesc: 'Bring your Google Analytics 4 data directly into FetchBot. Compare GA metrics with FetchBot\'s server-side data for a complete picture of your traffic. FetchBot\'s AI cross-references both datasets to detect discrepancies and uncover hidden insights.', features: ['GA4 data import', 'Unified dashboard', 'Cross-platform comparison', 'AI anomaly detection'], docsUrl: '#' },
  { slug: 'google-search-console', name: 'Google Search Console', category: 'SEO', categoryKey: 'seo', shortDesc: 'Pull real Google ranking data, impressions, and clicks to power keyword intelligence.', bgColor: 'linear-gradient(135deg, #4285f420, #34a85320)', tagColor: '#4285f4', tagBg: '#4285f410', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#4285f4" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>', longDesc: 'Connect Google Search Console to get real search ranking data, impressions, CTR, and click data directly into FetchBot\'s keyword intelligence engine. Track how your keywords perform over time and correlate ranking changes with content updates.', features: ['Real search rankings', 'Click-through rate tracking', 'Impression data', 'Keyword position history'], docsUrl: '#' },
  { slug: 'slack', name: 'Slack', category: 'Messaging', categoryKey: 'messaging', shortDesc: 'Get daily growth reports, hot lead alerts, and trend intelligence delivered to Slack.', bgColor: 'linear-gradient(135deg, #4A154B15, #E01E5A10)', tagColor: '#4A154B', tagBg: '#4A154B10', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M14.5 2a2.5 2.5 0 0 0 0 5H17V4.5A2.5 2.5 0 0 0 14.5 2z" fill="#E01E5A"/><path d="M2 14.5a2.5 2.5 0 0 0 5 0V12H4.5A2.5 2.5 0 0 0 2 14.5z" fill="#36C5F0"/><path d="M9.5 22a2.5 2.5 0 0 0 0-5H7v2.5A2.5 2.5 0 0 0 9.5 22z" fill="#2EB67D"/><path d="M22 9.5a2.5 2.5 0 0 0-5 0V12h2.5A2.5 2.5 0 0 0 22 9.5z" fill="#ECB22E"/></svg>', longDesc: 'Connect Slack to receive automated daily growth summaries, instant hot lead alerts, weekly SEO trend digests, and growth milestone celebrations — right in your team channels. FetchBot formats messages using Slack Block Kit for rich, scannable reports your whole team can benefit from.', features: ['Daily growth reports', 'Hot lead instant alerts', 'Weekly trend digests', 'Custom channel routing'], docsUrl: '#' },
  { slug: 'discord', name: 'Discord', category: 'Messaging', categoryKey: 'messaging', shortDesc: 'Share rich-embed growth reports and lead alerts in your Discord server.', bgColor: 'linear-gradient(135deg, #5865F215, #5865F210)', tagColor: '#5865F2', tagBg: '#5865F210', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#5865F2"><path d="M20.3 4.1a19.4 19.4 0 0 0-4.8-1.5 14.5 14.5 0 0 0-.6 1.3 18 18 0 0 0-5.4 0c-.2-.5-.4-.9-.6-1.3A19.3 19.3 0 0 0 4 4.1 20 20 0 0 0 .5 17.7a19.5 19.5 0 0 0 6 3 14.6 14.6 0 0 0 1.3-2 12.6 12.6 0 0 1-2-.9l.5-.4c3.8 1.8 8 1.8 11.8 0 .2.1.3.3.5.4-.6.4-1.3.7-2 .9.4.7.8 1.4 1.3 2a19.5 19.5 0 0 0 6-3A20 20 0 0 0 20.3 4.1zM8 14.8c-1.2 0-2.2-1.1-2.2-2.4S6.8 10 8 10s2.2 1.1 2.2 2.4S9.2 14.8 8 14.8zm8 0c-1.2 0-2.2-1.1-2.2-2.4S14.8 10 16 10s2.2 1.1 2.2 2.4S17.2 14.8 16 14.8z"/></svg>', longDesc: 'Get rich embed notifications delivered to your Discord server. FetchBot uses Discord\'s embed format for beautifully formatted growth reports, hot lead alerts, and weekly performance summaries that your team can act on instantly.', features: ['Rich embed messages', 'Weekly performance summaries', 'Hot lead alerts', 'Role mentions on alerts'], docsUrl: '#' },
  { slug: 'telegram', name: 'Telegram', category: 'Messaging', categoryKey: 'messaging', shortDesc: 'Receive instant push notifications for growth milestones and hot leads on mobile.', bgColor: 'linear-gradient(135deg, #229ED915, #229ED910)', tagColor: '#229ED9', tagBg: '#229ED910', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#229ED9"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm4.6 6.8l-1.7 7.9c-.1.5-.5.7-.9.4l-2.5-1.8-1.2 1.2c-.1.2-.3.3-.5.3l.2-2.5 4.5-4c.2-.2 0-.3-.3-.1L8.7 13.5l-2.4-.7c-.5-.2-.5-.5.1-.7l9.5-3.7c.4-.1.8.1.7.7z"/></svg>', longDesc: 'Get instant mobile push notifications for hot leads, growth milestones, and daily summaries right on your phone via Telegram. Perfect for founders and solopreneurs who need to stay informed on the go.', features: ['Instant push notifications', 'Mobile-first growth alerts', 'Daily summaries', 'Milestone celebrations'], docsUrl: '#' },
  { slug: 'stripe', name: 'Stripe', category: 'Payments', categoryKey: 'payments', shortDesc: 'Track subscriptions, payments, and revenue attribution with Stripe billing.', bgColor: 'linear-gradient(135deg, #635bff15, #635bff10)', tagColor: '#635bff', tagBg: '#635bff10', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#635bff"><path d="M13.976 9.15c-2.172-.806-3.356-1.426-3.356-2.409 0-.831.683-1.305 1.901-1.305 2.227 0 4.515.858 6.09 1.631l.89-5.494C18.252.975 15.697 0 12.165 0 9.667 0 7.589.654 6.104 1.872 4.56 3.147 3.757 4.992 3.757 7.218c0 4.039 2.467 5.76 6.476 7.219 2.585.92 3.445 1.574 3.445 2.583 0 .98-.84 1.545-2.354 1.545-1.875 0-4.965-.921-7.076-2.19L3.37 21.8c1.857 1.029 5.166 2.2 8.63 2.2 2.59 0 4.749-.657 6.29-1.834C19.77 20.873 20.5 19 20.5 16.65c0-4.171-2.505-5.834-6.524-7.5z"/></svg>', longDesc: 'Integrate Stripe to track payments, subscriptions, and revenue. See which marketing channels drive the most revenue with full payment attribution. FetchBot auto-creates lead records for new customers.', features: ['Payment tracking', 'Subscription management', 'Revenue attribution', 'Customer portal'], docsUrl: '#' },
  { slug: 'hubspot', name: 'HubSpot', category: 'CRM', categoryKey: 'crm', shortDesc: 'Sync leads, deals, and contacts bidirectionally with HubSpot CRM.', bgColor: 'linear-gradient(135deg, #ff7a5920, #ff5c3510)', tagColor: '#ff5c35', tagBg: '#ff5c3510', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#ff5c35"><circle cx="12" cy="12" r="10"/></svg>', longDesc: 'Connect HubSpot CRM to sync leads, deals, and contacts bidirectionally. FetchBot\'s lead scoring enriches HubSpot records with behavioral data from your website visitors.', features: ['Bidirectional lead sync', 'Deal pipeline tracking', 'Lead score enrichment', 'Contact timeline'], docsUrl: '#' },
  { slug: 'salesforce', name: 'Salesforce', category: 'CRM', categoryKey: 'crm', shortDesc: 'Push enriched leads and opportunity data to Salesforce.', bgColor: 'linear-gradient(135deg, #00a1e020, #1798c110)', tagColor: '#00a1e0', tagBg: '#00a1e010', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#00a1e0"><circle cx="12" cy="12" r="10"/></svg>', longDesc: 'Enterprise-grade Salesforce integration. Push FetchBot\'s AI-enriched leads directly into Salesforce with full field mapping and activity logging.', features: ['Lead push to Salesforce', 'Field mapping', 'Opportunity tracking', 'Activity logging'], docsUrl: '#' },
  { slug: 'facebook-ads', name: 'Facebook Ads', category: 'Ads', categoryKey: 'ads', shortDesc: 'Capture Facebook Lead Ads submissions and track conversions.', bgColor: 'linear-gradient(135deg, #1877f220, #1877f210)', tagColor: '#1877f2', tagBg: '#1877f210', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#1877f2"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>', longDesc: 'Connect Facebook Ads to capture lead form submissions via webhooks and track conversions from ad campaigns directly in FetchBot.', features: ['Lead Ads capture', 'Conversion tracking', 'Audience sync', 'ROAS reporting'], docsUrl: '#' },
  { slug: 'google-ads', name: 'Google Ads', category: 'Ads', categoryKey: 'ads', shortDesc: 'Track Google Ads conversions and sync lead data for better targeting.', bgColor: 'linear-gradient(135deg, #4285f420, #34a85310)', tagColor: '#4285f4', tagBg: '#4285f410', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="18" r="4" fill="#4285f4"/><path d="M2 12l8 8 12-16" stroke="#34a853" stroke-width="2" fill="none"/></svg>', longDesc: 'Integrate Google Ads to track conversions, sync offline leads, and measure true ROAS across your campaigns.', features: ['Conversion imports', 'Offline lead sync', 'ROAS tracking', 'Keyword attribution'], docsUrl: '#' },
  { slug: 'dataforseo', name: 'DataForSEO', category: 'SEO', categoryKey: 'seo', shortDesc: 'Get real Google SERP rankings, search volume, CPC, and difficulty data.', bgColor: 'linear-gradient(135deg, #2ecc7120, #27ae6010)', tagColor: '#27ae60', tagBg: '#27ae6010', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#27ae60" stroke-width="1.5"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>', longDesc: 'DataForSEO powers FetchBot\'s keyword intelligence with real Google SERP data. Get accurate search volume, CPC, keyword difficulty, and SERP feature data for every keyword you track.', features: ['Real SERP rankings', 'Search volume data', 'CPC and difficulty', 'SERP feature detection'], docsUrl: '#' },
  { slug: 'retell-ai', name: 'Retell.ai', category: 'Voice & Calls', categoryKey: 'voice', shortDesc: 'Power AI voice agents with natural-sounding conversations.', bgColor: 'linear-gradient(135deg, #8b5cf620, #6366f110)', tagColor: '#8b5cf6', tagBg: '#8b5cf610', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="1.5"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M12 19v4"/></svg>', longDesc: 'Retell.ai powers FetchBot\'s Voice Agent with ultra-realistic AI voice conversations. Build outbound call campaigns with AI agents that sound human.', features: ['AI voice calling', 'Natural conversations', 'Call campaigns', 'Transcript extraction'], docsUrl: '#' },
  { slug: 'zapier', name: 'Zapier', category: 'Automation', categoryKey: 'automation', shortDesc: 'Connect FetchBot to 5,000+ apps through Zapier.', bgColor: 'linear-gradient(135deg, #ff4a0020, #ff4a0010)', tagColor: '#ff4a00', tagBg: '#ff4a0010', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#ff4a00"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>', longDesc: 'Connect FetchBot to over 5,000 applications through Zapier. Trigger workflows when leads are scored, keywords change rank, or traffic spikes.', features: ['5,000+ app connections', 'Lead triggers', 'Keyword alerts', 'Custom workflows'], docsUrl: '#' },
  { slug: 'webhooks', name: 'Webhooks', category: 'Automation', categoryKey: 'automation', shortDesc: 'Send real-time event data to any custom URL.', bgColor: 'linear-gradient(135deg, #64748b20, #47556910)', tagColor: '#475569', tagBg: '#47556910', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="1.5"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.5 1.5"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.5-1.5"/></svg>', longDesc: 'Send any FetchBot event to your own endpoints via webhooks. Build custom integrations with full control over the data format. Retry logic ensures delivery.', features: ['Real-time events', 'Custom URLs', 'Retry on failure', 'Event filtering'], docsUrl: '#' },
]

const integration = computed(() => {
  return allIntegrations.find(i => i.slug === route.params.slug)
})

const setupSteps = computed(() => {
  if (!integration.value) return []
  return [
    { title: 'Connect your account', desc: `Sign in to FetchBot and navigate to Settings → Integrations → ${integration.value.name}.` },
    { title: 'Authorize access', desc: `Enter your ${integration.value.name} credentials or webhook URL, then click "Connect".` },
    { title: 'Configure preferences', desc: 'Choose which notifications and data syncs you want enabled. Customize channel routing.' },
    { title: 'Start receiving data', desc: `${integration.value.name} is now connected. Data will sync in real-time within seconds.` },
  ]
})

const relatedIntegrations = computed(() => {
  if (!integration.value) return []
  return allIntegrations
    .filter(i => i.categoryKey === integration.value.categoryKey && i.slug !== integration.value.slug)
    .slice(0, 3)
})

// Re-scroll to top on slug change
watch(() => route.params.slug, () => { window.scrollTo({ top: 0, behavior: 'smooth' }) })
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.int-detail, .id-not-found {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  background: #fafafa; color: #0f172a; min-height: 100vh;
}

/* Nav — same as listing */
.id-nav { position: fixed; top: 0; left: 0; right: 0; z-index: 100; background: rgba(255,255,255,0.8); backdrop-filter: blur(20px); border-bottom: 1px solid transparent; transition: all 0.3s; }
.id-nav.scrolled { border-bottom-color: #e2e8f0; box-shadow: 0 1px 8px rgba(0,0,0,0.04); }
.id-nav-row { max-width: 1280px; margin: 0 auto; padding: 14px 32px; display: flex; align-items: center; gap: 32px; }
.id-brand { display: flex; align-items: center; gap: 8px; text-decoration: none; }
.id-brand-logo { width: 32px; height: 32px; border-radius: 8px; }
.id-brand-name { font-weight: 800; font-size: 18px; color: #0f172a; }
.id-nav-links { flex: 1; display: flex; gap: 24px; }
.id-nav-links a { font-size: 14px; font-weight: 500; color: #64748b; text-decoration: none; }
.id-nav-links a:hover { color: #0f172a; }
.id-nav-right { display: flex; align-items: center; gap: 12px; }
.id-nav-login { font-size: 14px; font-weight: 500; color: #64748b; text-decoration: none; }
.id-nav-cta { padding: 8px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; background: #0f172a; color: white; text-decoration: none; transition: all 0.2s; }
.id-nav-cta:hover { background: #1e293b; }

/* Breadcrumb */
.id-breadcrumb-wrap { padding: 80px 32px 0; max-width: 1280px; margin: 0 auto; }
.id-breadcrumb { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #94a3b8; padding-top: 24px; }
.id-breadcrumb a { color: #6366f1; text-decoration: none; font-weight: 500; }
.id-breadcrumb a:hover { color: #4f46e5; }
.id-bc-current { color: #64748b; font-weight: 500; }

/* Hero */
.id-hero { padding: 32px 32px 48px; }
.id-hero-inner { max-width: 1280px; margin: 0 auto; display: flex; align-items: flex-start; justify-content: space-between; gap: 32px; }
.id-hero-left { display: flex; align-items: flex-start; gap: 20px; }
.id-hero-icon { width: 72px; height: 72px; border-radius: 16px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.id-hero-tag { display: inline-block; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 100px; text-transform: uppercase; letter-spacing: 0.3px; margin-bottom: 8px; }
.id-hero h1 { font-size: 36px; font-weight: 800; margin: 0 0 8px; letter-spacing: -0.5px; }
.id-hero-short { font-size: 16px; color: #64748b; margin: 0; line-height: 1.5; max-width: 500px; }
.id-hero-actions { display: flex; gap: 12px; flex-shrink: 0; padding-top: 12px; }
.id-btn-primary { display: inline-flex; align-items: center; gap: 8px; padding: 12px 24px; border-radius: 10px; font-size: 14px; font-weight: 600; background: #0f172a; color: white; text-decoration: none; transition: all 0.2s; }
.id-btn-primary:hover { background: #1e293b; transform: translateY(-1px); }
.id-btn-ghost { display: inline-flex; align-items: center; gap: 8px; padding: 12px 24px; border-radius: 10px; font-size: 14px; font-weight: 600; background: white; color: #0f172a; text-decoration: none; border: 1px solid #e2e8f0; transition: all 0.2s; }
.id-btn-ghost:hover { border-color: #cbd5e1; }

/* Content layout */
.id-content { max-width: 1280px; margin: 0 auto; padding: 0 32px 60px; }
.id-content-inner { display: flex; gap: 32px; }
.id-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 24px; }
.id-aside { width: 320px; flex-shrink: 0; display: flex; flex-direction: column; gap: 20px; }

/* Description card */
.id-desc-card, .id-steps-card { background: white; border-radius: 14px; border: 1px solid #e2e8f0; padding: 28px; }
.id-desc-card h2, .id-steps-card h2 { font-size: 18px; font-weight: 700; margin: 0 0 14px; }
.id-desc-card p { font-size: 15px; color: #475569; line-height: 1.7; margin: 0; }

/* Steps */
.id-steps { display: flex; flex-direction: column; gap: 20px; }
.id-step { display: flex; gap: 16px; }
.id-step-num { width: 32px; height: 32px; border-radius: 10px; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; flex-shrink: 0; }
.id-step h4 { font-size: 14px; font-weight: 600; margin: 0 0 4px; }
.id-step p { font-size: 13px; color: #64748b; margin: 0; line-height: 1.5; }

/* Feature card */
.id-features-card, .id-info-card { background: white; border-radius: 14px; border: 1px solid #e2e8f0; padding: 24px; }
.id-features-card h3, .id-info-card h3 { font-size: 14px; font-weight: 700; margin: 0 0 14px; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; }
.id-features-card ul { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
.id-features-card li { display: flex; align-items: center; gap: 10px; font-size: 14px; font-weight: 500; color: #334155; }

/* Info card */
.id-info-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f1f5f9; }
.id-info-row:last-child { border-bottom: none; }
.id-info-label { font-size: 13px; color: #94a3b8; }
.id-info-value { font-size: 13px; font-weight: 600; color: #334155; }

/* Related */
.id-related { padding: 60px 32px; background: #f8fafc; border-top: 1px solid #e2e8f0; }
.id-related-inner { max-width: 1280px; margin: 0 auto; }
.id-related h2 { font-size: 22px; font-weight: 700; margin: 0 0 20px; }
.id-related-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.id-related-card { display: flex; gap: 16px; padding: 20px; border-radius: 12px; background: white; border: 1px solid #e2e8f0; text-decoration: none; color: inherit; transition: all 0.2s; }
.id-related-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.06); }
.id-related-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.id-related-card h4 { font-size: 15px; font-weight: 700; margin: 0 0 4px; }
.id-related-card p { font-size: 13px; color: #64748b; margin: 0; line-height: 1.4; }

/* CTA */
.id-cta { padding: 80px 32px; text-align: center; }
.id-cta-inner { max-width: 500px; margin: 0 auto; }
.id-cta h2 { font-size: 28px; font-weight: 800; margin: 0 0 8px; }
.id-cta p { font-size: 16px; color: #64748b; margin: 0 0 24px; }
.id-btn-primary-lg { display: inline-flex; align-items: center; gap: 8px; padding: 14px 32px; border-radius: 12px; font-size: 16px; font-weight: 700; background: #0f172a; color: white; text-decoration: none; transition: all 0.2s; }
.id-btn-primary-lg:hover { background: #1e293b; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.12); }

/* Footer */
.id-footer { border-top: 1px solid #e2e8f0; padding: 24px 32px; background: white; }
.id-footer-inner { max-width: 1280px; margin: 0 auto; display: flex; align-items: center; gap: 24px; }
.id-footer-brand { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 14px; }
.id-footer-links { flex: 1; display: flex; gap: 20px; }
.id-footer-links a { font-size: 13px; color: #64748b; text-decoration: none; }
.id-footer-copy { font-size: 12px; color: #94a3b8; }

/* 404 */
.id-not-found { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 60vh; gap: 12px; padding-top: 100px; }
.id-not-found h1 { font-size: 24px; font-weight: 700; }
.id-not-found p { color: #64748b; }

/* Responsive */
@media (max-width: 768px) {
  .id-hero-inner { flex-direction: column; }
  .id-hero-left { flex-direction: column; }
  .id-hero h1 { font-size: 28px; }
  .id-content-inner { flex-direction: column; }
  .id-aside { width: 100%; }
  .id-related-grid { grid-template-columns: 1fr; }
}
</style>
