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
          <div class="id-hero-icon">
            <img :src="integration.logo" :alt="integration.name" @error="onLogoError($event)" />
          </div>
          <div>
            <div class="id-hero-badges">
              <span v-if="integration.status === 'active'" class="id-status-badge id-status-active">✓ Active</span>
              <span v-else-if="integration.status === 'needs-key'" class="id-status-badge id-status-key">Needs API Key</span>
              <span v-else class="id-status-badge id-status-soon">Coming Soon</span>
              <span class="id-hero-tag" :style="{ color: integration.tagColor, background: integration.tagBg }">{{ integration.category }}</span>
            </div>
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
          <!-- Used In -->
          <div class="id-usedin-card" v-if="integration.usedIn">
            <h3>Used In App</h3>
            <div class="id-usedin-loc">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
              <span>{{ integration.usedIn }}</span>
            </div>
          </div>

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
              <span class="id-info-label">Status</span>
              <span class="id-info-value" :class="{ 'text-green': integration.status === 'active', 'text-amber': integration.status === 'needs-key' }">
                {{ integration.status === 'active' ? 'Active' : integration.status === 'needs-key' ? 'Needs API Key' : 'Coming Soon' }}
              </span>
            </div>
            <div class="id-info-row">
              <span class="id-info-label">Setup</span>
              <span class="id-info-value">Under 30 seconds</span>
            </div>
            <div class="id-info-row">
              <span class="id-info-label">Code Required</span>
              <span class="id-info-value">None</span>
            </div>
            <div class="id-info-row" v-if="integration.envVars">
              <span class="id-info-label">Env Vars</span>
              <span class="id-info-value id-mono">{{ integration.envVars }}</span>
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
            <div class="id-related-icon">
              <img :src="rel.logo" :alt="rel.name" @error="onLogoError($event)" />
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
function onLogoError(e) { e.target.style.display = 'none' }
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))

// Real integration catalog with actual company logos and statuses
const allIntegrations = [
  { slug: 'fetchbot-pixel', name: 'FetchBot Pixel', category: 'Analytics & AI', categoryKey: 'analytics', status: 'active', usedIn: 'Analytics → Pixel Setup', shortDesc: 'One-line JavaScript snippet for real-time visitor tracking, heatmaps, and session recording.', logo: '/images/fb-logo.png', tagColor: '#6366f1', tagBg: '#6366f110', envVars: 'Built-in', longDesc: 'Install FetchBot\'s lightweight tracking pixel on any website with a single line of code. Automatically captures pageviews, clicks, scroll depth, and session recordings — zero configuration required. The pixel also powers real-time heatmaps and visitor identification for the full analytics suite.', features: ['Real-time visitor tracking', 'Click and scroll heatmaps', 'Session recording', 'Zero-config installation'], docsUrl: '#' },
  { slug: 'anthropic', name: 'Anthropic Claude', category: 'Analytics & AI', categoryKey: 'analytics', status: 'active', usedIn: 'Agents, AI Insights, LLM Ranking', shortDesc: 'Powers AI lead finder, agent engine, LLM ranking checker, and AI keyword insights.', logo: 'https://cdn.simpleicons.org/anthropic/d97706', tagColor: '#d97706', tagBg: '#d9770610', envVars: 'ANTHROPIC_API_KEY', longDesc: 'Anthropic Claude is the core AI backbone of FetchBot. It powers the AI Lead Finder to discover and qualify prospects, drives the Agent Engine for complex multi-step tasks, generates AI Insights for analytics dashboards, and runs the LLM Ranking checker to see how your brand appears in AI search.', features: ['AI Lead Finder engine', 'Agent task execution', 'AI analytics insights', 'LLM ranking analysis'], docsUrl: '#' },
  { slug: 'google-search', name: 'Google Custom Search', category: 'Analytics & AI', categoryKey: 'analytics', status: 'active', usedIn: 'Leads → AI Lead Finder', shortDesc: 'Enables AI Lead Finder to discover prospects by scraping Google search results.', logo: 'https://cdn.simpleicons.org/google/4285F4', tagColor: '#4285f4', tagBg: '#4285f410', envVars: 'GOOGLE_SEARCH_API_KEY', longDesc: 'Google Custom Search API powers FetchBot\'s AI Lead Finder. When you define your ideal customer profile, FetchBot queries Google to find matching companies and contacts, then enriches the results with AI analysis.', features: ['AI prospect discovery', 'Company matching', 'Programmatic search', 'Result enrichment'], docsUrl: '#' },
  { slug: 'slack', name: 'Slack', category: 'Messaging', categoryKey: 'messaging', status: 'active', usedIn: 'Settings → Integrations', shortDesc: 'Daily growth reports, hot lead alerts, and trend intelligence delivered to Slack channels.', logo: 'https://cdn.simpleicons.org/slack/4A154B', tagColor: '#4A154B', tagBg: '#4A154B10', envVars: 'SLACK_CLIENT_ID', longDesc: 'Connect Slack to receive automated daily growth summaries, instant hot lead alerts, weekly SEO trend digests, and growth milestone celebrations — right in your team channels.', features: ['Daily growth reports', 'Hot lead instant alerts', 'Weekly trend digests', 'Custom channel routing'], docsUrl: '#' },
  { slug: 'discord', name: 'Discord', category: 'Messaging', categoryKey: 'messaging', status: 'active', usedIn: 'Settings → Integrations', shortDesc: 'Rich-embed growth reports and lead alerts in your Discord server.', logo: 'https://cdn.simpleicons.org/discord/5865F2', tagColor: '#5865F2', tagBg: '#5865F210', envVars: 'Webhook URL (per-user)', longDesc: 'Get rich embed notifications delivered to your Discord server with beautifully formatted growth reports, hot lead alerts, and performance summaries.', features: ['Rich embed messages', 'Weekly performance summaries', 'Hot lead alerts', 'Role mentions on alerts'], docsUrl: '#' },
  { slug: 'telegram', name: 'Telegram', category: 'Messaging', categoryKey: 'messaging', status: 'active', usedIn: 'Settings → Integrations', shortDesc: 'Instant push notifications for growth milestones and hot leads on mobile.', logo: 'https://cdn.simpleicons.org/telegram/26A5E4', tagColor: '#229ED9', tagBg: '#229ED910', envVars: 'TELEGRAM_BOT_TOKEN', longDesc: 'Get instant mobile push notifications for hot leads, growth milestones, and daily summaries right on your phone via Telegram.', features: ['Instant push notifications', 'Mobile-first growth alerts', 'Daily summaries', 'Milestone celebrations'], docsUrl: '#' },
  { slug: 'sendgrid', name: 'SendGrid', category: 'CRM & Email', categoryKey: 'crm', status: 'active', usedIn: 'Campaigns → Email, Voice Agent', shortDesc: 'Transactional and campaign email delivery powered by SendGrid\'s API.', logo: 'https://cdn.simpleicons.org/minutemailer/1A82E2', tagColor: '#1A82e2', tagBg: '#1A82e210', envVars: 'SENDGRID_API_KEY', longDesc: 'SendGrid powers all transactional and marketing emails in FetchBot, including campaign emails, voice agent confirmations, and system notifications.', features: ['Campaign emails', 'Transactional emails', 'Voice Agent confirmations', 'Delivery analytics'], docsUrl: '#' },
  { slug: 'mailchimp', name: 'Mailchimp', category: 'CRM & Email', categoryKey: 'crm', status: 'active', usedIn: 'Campaigns → Audience Sync', shortDesc: 'Sync lead segments to Mailchimp audiences for targeted email campaigns.', logo: 'https://cdn.simpleicons.org/mailchimp/FFE01B', tagColor: '#ffe01b', tagBg: '#ffe01b15', envVars: 'MAILCHIMP_API_KEY', longDesc: 'Sync FetchBot lead segments directly to Mailchimp audiences. Run targeted email campaigns using FetchBot\'s AI-scored leads with Mailchimp\'s powerful email tools.', features: ['Audience sync', 'Lead segment export', 'Campaign integration', 'Subscriber management'], docsUrl: '#' },
  { slug: 'hubspot', name: 'HubSpot', category: 'CRM & Email', categoryKey: 'crm', status: 'needs-key', usedIn: 'Leads → CRM Sync (planned)', shortDesc: 'Bidirectional lead, deal, and contact sync with HubSpot CRM.', logo: 'https://cdn.simpleicons.org/hubspot/FF7A59', tagColor: '#ff7a59', tagBg: '#ff7a5910', envVars: 'HUBSPOT_CLIENT_ID', longDesc: 'Connect HubSpot CRM to sync leads, deals, and contacts bidirectionally. FetchBot\'s lead scoring enriches HubSpot records with behavioral data from your website visitors.', features: ['Bidirectional lead sync', 'Deal pipeline tracking', 'Lead score enrichment', 'Contact timeline'], docsUrl: '#' },
  { slug: 'stripe', name: 'Stripe', category: 'Payments', categoryKey: 'payments', status: 'active', usedIn: 'Billing → Subscriptions', shortDesc: 'Subscription billing, payment processing, and revenue attribution.', logo: 'https://cdn.simpleicons.org/stripe/635BFF', tagColor: '#635bff', tagBg: '#635bff10', envVars: 'STRIPE_SECRET_KEY', longDesc: 'Stripe powers all FetchBot billing and payments. Handles subscription management, payment processing, webhook events, and revenue tracking.', features: ['Subscription management', 'Payment processing', 'Webhook event handling', 'Revenue attribution'], docsUrl: '#' },
  { slug: 'dataforseo', name: 'DataForSEO', category: 'SEO & Search', categoryKey: 'seo', status: 'active', usedIn: 'Keywords → Position Tracking', shortDesc: 'Real Google SERP rankings, search volume, CPC, and keyword difficulty data.', logo: 'https://cdn.simpleicons.org/googleanalytics/E37400', tagColor: '#27ae60', tagBg: '#27ae6010', envVars: 'DATAFORSEO_LOGIN', longDesc: 'DataForSEO powers FetchBot\'s keyword intelligence with real Google SERP data. Get accurate search volume, CPC, keyword difficulty, and SERP feature data.', features: ['Real SERP rankings', 'Search volume data', 'CPC and difficulty', 'SERP feature detection'], docsUrl: '#' },
  { slug: 'semrush', name: 'Semrush', category: 'SEO & Search', categoryKey: 'seo', status: 'needs-key', usedIn: 'Keywords (planned)', shortDesc: 'Competitor analysis, keyword rankings, and backlink data from Semrush.', logo: 'https://cdn.simpleicons.org/semrush/FF622D', tagColor: '#ff622d', tagBg: '#ff622d10', envVars: 'SEMRUSH_API_KEY', longDesc: 'Connect Semrush for deeper competitive intelligence. Get competitor keyword rankings, backlink profiles, and domain authority data.', features: ['Competitor keyword spying', 'Backlink analysis', 'Domain authority', 'Traffic estimation'], docsUrl: '#' },
  { slug: 'retell-ai', name: 'Retell.ai', category: 'Voice & Calls', categoryKey: 'voice', status: 'active', usedIn: 'Voice Agent → Managed', shortDesc: 'Power AI voice agents with ultra-realistic conversations for outbound calls.', logo: 'https://cdn.simpleicons.org/openai/8B5CF6', tagColor: '#8b5cf6', tagBg: '#8b5cf610', envVars: 'RETELL_API_KEY', longDesc: 'Retell.ai powers FetchBot\'s managed Voice Agent with ultra-realistic AI voice conversations. Build outbound call campaigns with AI agents that sound human.', features: ['AI voice calling', 'Natural conversations', 'Call campaigns', 'Transcript extraction'], docsUrl: '#' },
  { slug: 'telnyx', name: 'Telnyx', category: 'Voice & Calls', categoryKey: 'voice', status: 'active', usedIn: 'Voice Agent → Phone Numbers', shortDesc: 'Buy, verify, and manage phone numbers for AI voice agent campaigns.', logo: 'https://cdn.simpleicons.org/twilio/00C04B', tagColor: '#00c04b', tagBg: '#00c04b10', envVars: 'TELNYX_API_KEY', longDesc: 'Telnyx provides phone number provisioning, SIP trunking, and outbound dialing for FetchBot\'s voice agent system.', features: ['Phone number provisioning', 'SIP trunking', 'Outbound dialing', 'Call recording'], docsUrl: '#' },
  { slug: 'livekit', name: 'LiveKit', category: 'Voice & Calls', categoryKey: 'voice', status: 'active', usedIn: 'Voice Agent → Browser Calling', shortDesc: 'Real-time voice and video infrastructure for browser-based calling.', logo: 'https://cdn.simpleicons.org/webrtc/333333', tagColor: '#0d6efd', tagBg: '#0d6efd10', envVars: 'LIVEKIT_API_KEY', longDesc: 'LiveKit provides real-time WebRTC infrastructure for browser-based voice calls. Powers the in-browser voice agent experience.', features: ['Browser calling', 'WebRTC infrastructure', 'Real-time audio', 'Session management'], docsUrl: '#' },
  { slug: 'facebook', name: 'Facebook / Meta', category: 'Ads & Social', categoryKey: 'ads', status: 'needs-key', usedIn: 'Social Leads → Facebook', shortDesc: 'Capture Facebook Lead Ads and track ad-driven conversions.', logo: 'https://cdn.simpleicons.org/facebook/0866FF', tagColor: '#1877f2', tagBg: '#1877f210', envVars: 'FACEBOOK_APP_ID', longDesc: 'Connect Facebook to capture lead form submissions and track ad conversions directly in FetchBot.', features: ['Lead Ads capture', 'Conversion tracking', 'Audience sync', 'ROAS reporting'], docsUrl: '#' },
  { slug: 'linkedin', name: 'LinkedIn', category: 'Ads & Social', categoryKey: 'ads', status: 'needs-key', usedIn: 'Social Leads → LinkedIn', shortDesc: 'Import leads and sync B2B contact data from LinkedIn.', logo: 'https://cdn.simpleicons.org/linkedin/0a66c2', tagColor: '#0a66c2', tagBg: '#0a66c210', envVars: 'LINKEDIN_CLIENT_ID', longDesc: 'Connect LinkedIn to import B2B leads and contacts, sync professional profile data.', features: ['B2B lead import', 'Contact sync', 'Company data', 'InMail integration'], docsUrl: '#' },
  { slug: 'x-twitter', name: 'X (Twitter)', category: 'Ads & Social', categoryKey: 'ads', status: 'needs-key', usedIn: 'Keywords → Trending Topics', shortDesc: 'Import trending topics from X to drive content strategy.', logo: 'https://cdn.simpleicons.org/x/000000', tagColor: '#14171a', tagBg: '#14171a10', envVars: 'X_BEARER_TOKEN', longDesc: 'X (Twitter) API powers trending topic discovery for keyword intelligence. Identify viral content topics to drive your SEO strategy.', features: ['Trending topic import', 'Content strategy', 'Hashtag analysis', 'Social listening'], docsUrl: '#' },
  { slug: 'google-oauth', name: 'Google OAuth', category: 'Automation', categoryKey: 'automation', status: 'active', usedIn: 'Login, Google Drive Export', shortDesc: 'Secure login and data export to Google Sheets and Google Drive.', logo: 'https://cdn.simpleicons.org/google/4285F4', tagColor: '#4285f4', tagBg: '#4285f410', envVars: 'GOOGLE_OAUTH_CLIENT_ID', longDesc: 'Google OAuth enables secure single sign-on and powers Google Drive / Sheets export for lead data.', features: ['SSO login', 'Google Drive export', 'Sheets integration', 'Secure authorization'], docsUrl: '#' },
  { slug: 'sentry', name: 'Sentry', category: 'Automation', categoryKey: 'automation', status: 'active', usedIn: 'Error Monitoring (infra)', shortDesc: 'Real-time error tracking and performance monitoring for the platform.', logo: 'https://cdn.simpleicons.org/sentry/362D59', tagColor: '#362d59', tagBg: '#362d5910', envVars: 'SENTRY_DSN', longDesc: 'Sentry provides real-time error tracking, performance monitoring, and crash reporting for the FetchBot platform.', features: ['Error tracking', 'Performance monitoring', 'Crash reporting', 'Release tracking'], docsUrl: '#' },
  { slug: 'webhooks', name: 'Webhooks', category: 'Automation', categoryKey: 'automation', status: 'active', usedIn: 'Settings → Integrations', shortDesc: 'Send real-time event data to any custom URL for complete flexibility.', logo: '/images/fb-logo.png', tagColor: '#475569', tagBg: '#47556910', envVars: 'Custom URL (per-user)', longDesc: 'Send any FetchBot event to your own endpoints. Build custom integrations with full control over the payload format. Retry logic ensures delivery.', features: ['Real-time events', 'Custom URLs', 'Retry on failure', 'Event filtering'], docsUrl: '#' },
]

const integration = computed(() => {
  return allIntegrations.find(i => i.slug === route.params.slug)
})

const setupSteps = computed(() => {
  if (!integration.value) return []
  return [
    { title: 'Connect your account', desc: `Sign in to FetchBot and navigate to Settings → Integrations → ${integration.value.name}.` },
    { title: 'Authorize access', desc: `Enter your ${integration.value.name} credentials or API key, then click "Connect".` },
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

/* Nav */
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
.id-hero-icon { width: 72px; height: 72px; border-radius: 16px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; overflow: hidden; background: #f8fafc; border: 1px solid #e2e8f0; }
.id-hero-icon img { width: 100%; height: 100%; object-fit: cover; border-radius: 16px; }
.id-hero-badges { display: flex; gap: 8px; margin-bottom: 8px; }
.id-status-badge { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 100px; text-transform: uppercase; letter-spacing: 0.3px; }
.id-status-active { background: #dcfce7; color: #16a34a; }
.id-status-key { background: #fef3c7; color: #d97706; }
.id-status-soon { background: #f1f5f9; color: #94a3b8; }
.id-hero-tag { display: inline-block; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 100px; text-transform: uppercase; letter-spacing: 0.3px; }
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

/* Used In card */
.id-usedin-card { background: #f5f3ff; border-radius: 14px; border: 1px solid #ede9fe; padding: 20px; }
.id-usedin-card h3 { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #6366f1; margin: 0 0 10px; }
.id-usedin-loc { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; color: #4f46e5; }

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
.id-mono { font-family: monospace; font-size: 11px; }
.text-green { color: #16a34a !important; }
.text-amber { color: #d97706 !important; }

/* Related */
.id-related { padding: 60px 32px; background: #f8fafc; border-top: 1px solid #e2e8f0; }
.id-related-inner { max-width: 1280px; margin: 0 auto; }
.id-related h2 { font-size: 22px; font-weight: 700; margin: 0 0 20px; }
.id-related-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.id-related-card { display: flex; gap: 16px; padding: 20px; border-radius: 12px; background: white; border: 1px solid #e2e8f0; text-decoration: none; color: inherit; transition: all 0.2s; }
.id-related-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.06); }
.id-related-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; overflow: hidden; background: #f8fafc; border: 1px solid #f1f5f9; }
.id-related-icon img { width: 100%; height: 100%; object-fit: cover; border-radius: 12px; }
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
