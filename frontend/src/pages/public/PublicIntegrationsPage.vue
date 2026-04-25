<template>
  <div class="pub-int">
    <!-- Nav -->
    <nav class="pi-nav" :class="{ scrolled }">
      <div class="pi-nav-row">
        <router-link to="/" class="pi-brand">
          <img src="/images/fb-logo.png" alt="FetchBot" class="pi-brand-logo" />
          <span class="pi-brand-name">FetchBot</span>
        </router-link>
        <div class="pi-nav-links">
          <router-link to="/">Home</router-link>
          <router-link to="/integrations" class="active">Integrations</router-link>
        </div>
        <div class="pi-nav-right">
          <router-link to="/login" class="pi-nav-login">Log In</router-link>
          <router-link to="/login" class="pi-nav-cta">Get Started</router-link>
        </div>
      </div>
    </nav>

    <!-- Hero -->
    <section class="pi-hero">
      <div class="pi-hero-inner">
        <span class="pi-badge">{{ integrations.length }}+ Integrations</span>
        <h1>Connect Your<br/>Entire Stack</h1>
        <p>Sync your analytics, CRM, messaging, and ad tools with FetchBot.<br/>No code required. Setup in under 30 seconds.</p>
        <div class="pi-hero-search">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
          <input v-model="searchQuery" type="text" placeholder="Search integrations..." />
        </div>
      </div>
    </section>

    <!-- Main -->
    <section class="pi-main">
      <div class="pi-layout">
        <!-- Category Sidebar -->
        <aside class="pi-sidebar">
          <h4 class="pi-sidebar-title">Categories</h4>
          <button
            v-for="cat in categories" :key="cat.key"
            class="pi-cat-btn"
            :class="{ active: activeCategory === cat.key }"
            @click="activeCategory = cat.key"
          >
            <span class="pi-cat-icon" v-html="cat.icon"></span>
            <span>{{ cat.label }}</span>
            <span class="pi-cat-count">{{ getCategoryCount(cat.key) }}</span>
          </button>
        </aside>

        <!-- Integration Cards Grid -->
        <div class="pi-grid-wrap">
          <div class="pi-grid-header">
            <h2>{{ activeCategoryLabel }}</h2>
            <span class="pi-grid-count">{{ filteredIntegrations.length }} integrations</span>
          </div>
          <div class="pi-grid">
            <router-link
              v-for="intg in filteredIntegrations" :key="intg.slug"
              :to="`/integration/${intg.slug}`"
              class="pi-card"
            >
              <div class="pi-card-top">
                <div class="pi-card-icon">
                  <img :src="intg.logo" :alt="intg.name" @error="onLogoError($event)" />
                </div>
                <div class="pi-card-badges">
                  <span v-if="intg.status === 'active'" class="pi-card-status pi-status-active">Active</span>
                  <span v-else-if="intg.status === 'needs-key'" class="pi-card-status pi-status-unavailable">Unavailable</span>
                  <span v-else class="pi-card-status pi-status-soon">Coming Soon</span>
                  <span class="pi-card-tag" :style="{ color: intg.tagColor, background: intg.tagBg }">{{ intg.category }}</span>
                </div>
              </div>
              <h3 class="pi-card-name">{{ intg.name }}</h3>
              <p class="pi-card-desc">{{ intg.shortDesc }}</p>
              <div class="pi-card-used-in" v-if="intg.usedIn">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
                <span>{{ intg.usedIn }}</span>
              </div>
              <div class="pi-card-arrow">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
              </div>
            </router-link>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="pi-cta-section">
      <div class="pi-cta-inner">
        <h2>Don't see your tool?</h2>
        <p>Use our Webhook integration to connect any platform, or request a new integration.</p>
        <div class="pi-cta-btns">
          <router-link to="/integration/webhooks" class="pi-btn-primary">Use Webhooks</router-link>
          <a href="mailto:support@fetchbot.ai" class="pi-btn-ghost">Request Integration</a>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="pi-footer">
      <div class="pi-footer-inner">
        <div class="pi-footer-brand">
          <img src="/images/fb-logo.png" alt="FetchBot" width="24" />
          <span>FetchBot</span>
        </div>
        <div class="pi-footer-links">
          <router-link to="/">Home</router-link>
          <router-link to="/terms">Terms</router-link>
          <router-link to="/privacy">Privacy</router-link>
        </div>
        <span class="pi-footer-copy">© {{ new Date().getFullYear() }} FetchBot. All rights reserved.</span>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const searchQuery = ref('')
const activeCategory = ref('all')
const scrolled = ref(false)

function onScroll() { scrolled.value = window.scrollY > 20 }
function onLogoError(e) { e.target.style.display = 'none' }
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))

const categories = [
  { key: 'all',          label: 'All Integrations', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>' },
  { key: 'analytics',    label: 'Analytics & AI',   icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>' },
  { key: 'messaging',    label: 'Messaging',        icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>' },
  { key: 'crm',          label: 'CRM & Email',      icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>' },
  { key: 'ads',          label: 'Ads & Social',     icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>' },
  { key: 'payments',     label: 'Payments',         icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="20" height="14" x="2" y="5" rx="2"/><path d="M2 10h20"/></svg>' },
  { key: 'seo',          label: 'SEO & Search',     icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>' },
  { key: 'automation',   label: 'Automation',       icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.5 1.5"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.5-1.5"/></svg>' },
]

// ─── Real integrations with actual logos, real status, and in-app locations ───
const integrations = [
  // Analytics & AI
  { slug: 'fetchbot-pixel', name: 'FetchBot Pixel', category: 'Analytics & AI', categoryKey: 'analytics', status: 'active', usedIn: 'Analytics → Pixel', shortDesc: 'One-line JavaScript snippet for real-time visitor tracking, heatmaps, and session recording.', logo: '/images/fb-logo.png', tagColor: '#6366f1', tagBg: '#6366f110' },
  { slug: 'anthropic', name: 'Anthropic Claude', category: 'Analytics & AI', categoryKey: 'analytics', status: 'active', usedIn: 'Agents, AI Insights, LLM Ranking', shortDesc: 'Powers AI lead finder, agent engine, LLM ranking checker, and AI keyword insights.', logo: 'https://cdn.simpleicons.org/anthropic/d97706', tagColor: '#d97706', tagBg: '#d9770610' },
  { slug: 'google-search', name: 'Google Custom Search', category: 'Analytics & AI', categoryKey: 'analytics', status: 'active', usedIn: 'Leads → AI Lead Finder', shortDesc: 'Enables AI Lead Finder to discover prospects by scraping Google search results.', logo: 'https://cdn.simpleicons.org/google/4285F4', tagColor: '#4285f4', tagBg: '#4285f410' },
  { slug: 'google-analytics', name: 'Google Analytics 4', category: 'Analytics & AI', categoryKey: 'analytics', status: 'active', usedIn: 'fetchbot.ai → Visitor Tracking', shortDesc: 'Track visitors, page views, and conversions across fetchbot.ai with GA4.', logo: 'https://cdn.simpleicons.org/googleanalytics/E37400', tagColor: '#E37400', tagBg: '#E3740010' },
  { slug: 'microsoft-clarity', name: 'Microsoft Clarity', category: 'Analytics & AI', categoryKey: 'analytics', status: 'active', usedIn: 'fetchbot.ai → Heatmaps', shortDesc: 'Free heatmaps, session recordings, and rage-click detection on fetchbot.ai.', logo: 'https://cdn.simpleicons.org/microsoft/5E5E5E', tagColor: '#5E5E5E', tagBg: '#5E5E5E10' },
  { slug: 'gemini', name: 'Google Gemini', category: 'Analytics & AI', categoryKey: 'analytics', status: 'needs-key', usedIn: 'Reserved for future AI tasks', shortDesc: 'Google\'s multimodal AI model — configured but not yet active in any module.', logo: 'https://cdn.simpleicons.org/googlegemini/886FBF', tagColor: '#886FBF', tagBg: '#886FBF10' },
  { slug: 'perplexity', name: 'Perplexity AI', category: 'Analytics & AI', categoryKey: 'analytics', status: 'needs-key', usedIn: 'LLM Ranking', shortDesc: 'Test how your brand appears in Perplexity AI search responses.', logo: 'https://cdn.simpleicons.org/perplexity/20808D', tagColor: '#20808d', tagBg: '#20808d10' },

  // Messaging
  { slug: 'slack', name: 'Slack', category: 'Messaging', categoryKey: 'messaging', status: 'active', usedIn: 'Settings → Integrations', shortDesc: 'Daily growth reports, hot lead alerts, and trend intelligence delivered to Slack channels.', logo: 'https://cdn.simpleicons.org/slack/4A154B', tagColor: '#4A154B', tagBg: '#4A154B10' },
  { slug: 'discord', name: 'Discord', category: 'Messaging', categoryKey: 'messaging', status: 'active', usedIn: 'Settings → Integrations', shortDesc: 'Rich-embed growth reports and lead alerts in your Discord server.', logo: 'https://cdn.simpleicons.org/discord/5865F2', tagColor: '#5865F2', tagBg: '#5865F210' },
  { slug: 'telegram', name: 'Telegram', category: 'Messaging', categoryKey: 'messaging', status: 'active', usedIn: 'Settings → Integrations', shortDesc: 'Instant push notifications for growth milestones and hot leads on mobile.', logo: 'https://cdn.simpleicons.org/telegram/26A5E4', tagColor: '#26A5E4', tagBg: '#26A5E410' },

  // CRM & Email
  { slug: 'sendgrid', name: 'SendGrid', category: 'CRM & Email', categoryKey: 'crm', status: 'active', usedIn: 'Campaigns → Email', shortDesc: 'Transactional and campaign email delivery powered by SendGrid\'s API.', logo: '/images/integrations/sendgrid.svg', tagColor: '#F22F46', tagBg: '#F22F4610' },
  { slug: 'mailchimp', name: 'Mailchimp', category: 'CRM & Email', categoryKey: 'crm', status: 'active', usedIn: 'Campaigns → Audience Sync', shortDesc: 'Sync lead segments to Mailchimp audiences for targeted email campaigns.', logo: 'https://cdn.simpleicons.org/mailchimp/FFE01B', tagColor: '#FFE01B', tagBg: '#FFE01B15' },
  { slug: 'hubspot', name: 'HubSpot', category: 'CRM & Email', categoryKey: 'crm', status: 'needs-key', usedIn: 'Leads → CRM Sync', shortDesc: 'Bidirectional lead, deal, and contact sync with HubSpot CRM.', logo: 'https://cdn.simpleicons.org/hubspot/FF7A59', tagColor: '#FF7A59', tagBg: '#FF7A5910' },

  // Ads & Social
  { slug: 'facebook', name: 'Facebook / Meta', category: 'Ads & Social', categoryKey: 'ads', status: 'needs-key', usedIn: 'Social Leads → Facebook', shortDesc: 'Capture Facebook Lead Ads and track ad-driven conversions.', logo: 'https://cdn.simpleicons.org/facebook/0866FF', tagColor: '#0866FF', tagBg: '#0866FF10' },
  { slug: 'linkedin', name: 'LinkedIn', category: 'Ads & Social', categoryKey: 'ads', status: 'needs-key', usedIn: 'Social Leads → LinkedIn', shortDesc: 'Import leads and sync B2B contact data from LinkedIn.', logo: '/images/integrations/linkedin.svg', tagColor: '#0A66C2', tagBg: '#0A66C210' },
  { slug: 'x-twitter', name: 'X (Twitter)', category: 'Ads & Social', categoryKey: 'ads', status: 'needs-key', usedIn: 'Keywords → Trending Topics', shortDesc: 'Import trending topics from X to drive content strategy.', logo: 'https://cdn.simpleicons.org/x/000000', tagColor: '#000000', tagBg: '#00000010' },
  { slug: 'tiktok', name: 'TikTok', category: 'Ads & Social', categoryKey: 'ads', status: 'needs-key', usedIn: 'Social Leads (planned)', shortDesc: 'Social lead capture and ad attribution from TikTok.', logo: 'https://cdn.simpleicons.org/tiktok/000000', tagColor: '#000000', tagBg: '#00000008' },
  { slug: 'bing-ads', name: 'Bing / Microsoft Ads', category: 'Ads & Social', categoryKey: 'ads', status: 'active', usedIn: 'fetchbot.ai → Ad Tracking', shortDesc: 'Universal Event Tracking for Bing Ads conversion attribution.', logo: 'https://cdn.simpleicons.org/microsoftbing/258FFA', tagColor: '#258FFA', tagBg: '#258FFA10' },

  // Payments
  { slug: 'stripe', name: 'Stripe', category: 'Payments', categoryKey: 'payments', status: 'active', usedIn: 'Billing → Subscriptions', shortDesc: 'Subscription billing, payment processing, and revenue attribution.', logo: 'https://cdn.simpleicons.org/stripe/635BFF', tagColor: '#635BFF', tagBg: '#635BFF10' },

  // SEO & Search
  { slug: 'google-search-console', name: 'Google Search Console', category: 'SEO & Search', categoryKey: 'seo', status: 'needs-key', usedIn: 'Keywords → Rankings (planned)', shortDesc: 'Pull real Google ranking data, impressions, and CTR.', logo: 'https://cdn.simpleicons.org/googlesearchconsole/458CF5', tagColor: '#458CF5', tagBg: '#458CF510' },
  { slug: 'dataforseo', name: 'DataForSEO', category: 'SEO & Search', categoryKey: 'seo', status: 'active', usedIn: 'Keywords → Position Tracking', shortDesc: 'Real Google SERP rankings, search volume, CPC, and keyword difficulty data.', logo: 'https://cdn.simpleicons.org/googleanalytics/E37400', tagColor: '#27ae60', tagBg: '#27ae6010' },
  { slug: 'semrush', name: 'Semrush', category: 'SEO & Search', categoryKey: 'seo', status: 'needs-key', usedIn: 'Keywords (planned)', shortDesc: 'Compete analysis, keyword rankings, backlink data from Semrush.', logo: 'https://cdn.simpleicons.org/semrush/FF622D', tagColor: '#FF622D', tagBg: '#FF622D10' },

  // Automation
  { slug: 'google-oauth', name: 'Google OAuth', category: 'Automation', categoryKey: 'automation', status: 'active', usedIn: 'Login, Google Drive Export', shortDesc: 'Secure login and data export to Google Sheets and Google Drive.', logo: 'https://cdn.simpleicons.org/google/4285F4', tagColor: '#4285f4', tagBg: '#4285f410' },
  { slug: 'google-drive', name: 'Google Drive', category: 'Automation', categoryKey: 'automation', status: 'active', usedIn: 'Leads → Export to Drive', shortDesc: 'Export leads and analytics data to Google Drive spreadsheets.', logo: 'https://cdn.simpleicons.org/googledrive/4285F4', tagColor: '#4285f4', tagBg: '#4285f410' },
  { slug: 'sentry', name: 'Sentry', category: 'Automation', categoryKey: 'automation', status: 'active', usedIn: 'Error Monitoring (infra)', shortDesc: 'Real-time error tracking and performance monitoring for the platform.', logo: 'https://cdn.simpleicons.org/sentry/362D59', tagColor: '#362d59', tagBg: '#362d5910' },
  { slug: 'webhooks', name: 'Webhooks', category: 'Automation', categoryKey: 'automation', status: 'active', usedIn: 'Settings → Integrations', shortDesc: 'Send real-time event data to any custom URL for complete flexibility.', logo: '/images/fb-logo.png', tagColor: '#475569', tagBg: '#47556910' },
]

const activeCategoryLabel = computed(() => {
  const cat = categories.find(c => c.key === activeCategory.value)
  return cat ? cat.label : 'All Integrations'
})

function getCategoryCount(key) {
  if (key === 'all') return integrations.length
  return integrations.filter(i => i.categoryKey === key).length
}

const filteredIntegrations = computed(() => {
  let list = integrations
  if (activeCategory.value !== 'all') {
    list = list.filter(i => i.categoryKey === activeCategory.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(i =>
      i.name.toLowerCase().includes(q) ||
      i.shortDesc.toLowerCase().includes(q) ||
      i.category.toLowerCase().includes(q) ||
      (i.usedIn && i.usedIn.toLowerCase().includes(q))
    )
  }
  return list
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.pub-int {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  background: #fafafa;
  color: #0f172a;
  min-height: 100vh;
}

/* ═══ Nav ═══ */
.pi-nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  background: rgba(255,255,255,0.8);
  backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid transparent;
  transition: all 0.3s;
}
.pi-nav.scrolled { border-bottom-color: #e2e8f0; box-shadow: 0 1px 8px rgba(0,0,0,0.04); }
.pi-nav-row {
  max-width: 1280px; margin: 0 auto; padding: 14px 32px;
  display: flex; align-items: center; gap: 32px;
}
.pi-brand { display: flex; align-items: center; gap: 8px; text-decoration: none; }
.pi-brand-logo { width: 32px; height: 32px; border-radius: 8px; }
.pi-brand-name { font-weight: 800; font-size: 18px; color: #0f172a; }
.pi-nav-links { flex: 1; display: flex; gap: 24px; }
.pi-nav-links a { font-size: 14px; font-weight: 500; color: #64748b; text-decoration: none; transition: color 0.2s; }
.pi-nav-links a:hover, .pi-nav-links a.active { color: #0f172a; }
.pi-nav-right { display: flex; align-items: center; gap: 12px; }
.pi-nav-login { font-size: 14px; font-weight: 500; color: #64748b; text-decoration: none; }
.pi-nav-login:hover { color: #0f172a; }
.pi-nav-cta {
  padding: 8px 20px; border-radius: 8px; font-size: 14px; font-weight: 600;
  background: #0f172a; color: white; text-decoration: none; transition: all 0.2s;
}
.pi-nav-cta:hover { background: #1e293b; transform: translateY(-1px); }

/* ═══ Hero ═══ */
.pi-hero {
  padding: 140px 32px 60px; text-align: center;
  background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
}
.pi-hero-inner { max-width: 720px; margin: 0 auto; }
.pi-badge {
  display: inline-block; padding: 6px 16px; border-radius: 100px;
  font-size: 12px; font-weight: 600; letter-spacing: 0.5px;
  background: linear-gradient(135deg, #6366f115, #8b5cf615);
  color: #6366f1; margin-bottom: 20px;
}
.pi-hero h1 {
  font-size: 52px; font-weight: 800; line-height: 1.1;
  letter-spacing: -1.5px; margin: 0 0 16px;
  background: linear-gradient(135deg, #0f172a, #334155);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.pi-hero p { font-size: 18px; color: #64748b; line-height: 1.6; margin-bottom: 32px; }
.pi-hero-search {
  max-width: 480px; margin: 0 auto;
  display: flex; align-items: center; gap: 12px;
  background: white; border: 1px solid #e2e8f0;
  border-radius: 12px; padding: 12px 20px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.04);
  transition: all 0.2s;
}
.pi-hero-search:focus-within { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
.pi-hero-search svg { color: #94a3b8; flex-shrink: 0; }
.pi-hero-search input {
  flex: 1; border: none; outline: none; font-size: 15px;
  font-family: inherit; background: transparent; color: #0f172a;
}
.pi-hero-search input::placeholder { color: #94a3b8; }

/* ═══ Main Layout ═══ */
.pi-main { max-width: 1280px; margin: 0 auto; padding: 0 32px 60px; }
.pi-layout { display: flex; gap: 32px; }

/* ═══ Sidebar ═══ */
.pi-sidebar { width: 220px; flex-shrink: 0; position: sticky; top: 80px; align-self: flex-start; }
.pi-sidebar-title {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1px; color: #94a3b8; margin: 0 0 12px; padding: 0 12px;
}
.pi-cat-btn {
  display: flex; align-items: center; gap: 10px; width: 100%;
  padding: 10px 12px; border: none; border-radius: 8px;
  background: transparent; font-size: 13px; font-weight: 500;
  color: #64748b; cursor: pointer; transition: all 0.15s;
  font-family: inherit; text-align: left;
}
.pi-cat-btn:hover { background: #f1f5f9; color: #0f172a; }
.pi-cat-btn.active { background: #0f172a; color: white; }
.pi-cat-btn.active .pi-cat-count { background: rgba(255,255,255,0.15); color: white; }
.pi-cat-icon { display: flex; align-items: center; opacity: 0.7; }
.pi-cat-btn.active .pi-cat-icon { opacity: 1; }
.pi-cat-btn.active .pi-cat-icon svg { stroke: white; }
.pi-cat-count {
  margin-left: auto; font-size: 11px; font-weight: 600;
  padding: 2px 8px; border-radius: 100px;
  background: #f1f5f9; color: #94a3b8;
}

/* ═══ Grid ═══ */
.pi-grid-wrap { flex: 1; min-width: 0; }
.pi-grid-header {
  display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 20px;
}
.pi-grid-header h2 { font-size: 20px; font-weight: 700; margin: 0; }
.pi-grid-count { font-size: 13px; color: #94a3b8; font-weight: 500; }
.pi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}
.pi-card {
  position: relative; display: flex; flex-direction: column;
  padding: 24px; border-radius: 14px; background: white;
  border: 1px solid #e2e8f0; text-decoration: none; color: inherit;
  transition: all 0.25s cubic-bezier(0.22,1,0.36,1);
}
.pi-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 40px rgba(0,0,0,0.08);
  border-color: #cbd5e1;
}
.pi-card-top { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 14px; }
.pi-card-icon {
  width: 48px; height: 48px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden; background: #f8fafc; border: 1px solid #f1f5f9;
}
.pi-card-icon img { width: 100%; height: 100%; object-fit: cover; border-radius: 12px; }
.pi-card-badges { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
.pi-card-status {
  font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 100px;
  text-transform: uppercase; letter-spacing: 0.3px;
}
.pi-status-active { background: #dcfce7; color: #16a34a; }
.pi-status-unavailable { background: #f1f5f9; color: #64748b; }
.pi-status-soon { background: #f1f5f9; color: #94a3b8; }
.pi-card-tag {
  font-size: 10px; font-weight: 600; padding: 3px 8px;
  border-radius: 100px; text-transform: uppercase; letter-spacing: 0.3px;
}
.pi-card-name { font-size: 16px; font-weight: 700; margin: 0 0 6px; color: #0f172a; }
.pi-card-desc { font-size: 13px; color: #64748b; line-height: 1.5; margin: 0 0 10px; flex: 1; }
.pi-card-used-in {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; font-weight: 500; color: #6366f1;
  padding: 6px 10px; background: #f5f3ff; border-radius: 6px;
  margin-top: auto;
}
.pi-card-used-in svg { stroke: #6366f1; }
.pi-card-arrow {
  position: absolute; bottom: 20px; right: 20px;
  opacity: 0; transition: all 0.2s; color: #6366f1;
  transform: translateX(-4px);
}
.pi-card:hover .pi-card-arrow { opacity: 1; transform: translateX(0); }

/* ═══ CTA ═══ */
.pi-cta-section {
  padding: 80px 32px;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
}
.pi-cta-inner { max-width: 600px; margin: 0 auto; text-align: center; }
.pi-cta-inner h2 { font-size: 32px; font-weight: 800; margin: 0 0 12px; letter-spacing: -0.5px; }
.pi-cta-inner p { font-size: 16px; color: #64748b; margin: 0 0 28px; }
.pi-cta-btns { display: flex; gap: 12px; justify-content: center; }
.pi-btn-primary {
  padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600;
  background: #0f172a; color: white; text-decoration: none; transition: all 0.2s;
}
.pi-btn-primary:hover { background: #1e293b; transform: translateY(-1px); }
.pi-btn-ghost {
  padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600;
  background: white; color: #0f172a; text-decoration: none;
  border: 1px solid #e2e8f0; transition: all 0.2s;
}
.pi-btn-ghost:hover { border-color: #cbd5e1; transform: translateY(-1px); }

/* ═══ Footer ═══ */
.pi-footer { border-top: 1px solid #e2e8f0; padding: 24px 32px; background: white; }
.pi-footer-inner {
  max-width: 1280px; margin: 0 auto;
  display: flex; align-items: center; gap: 24px;
}
.pi-footer-brand { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 14px; }
.pi-footer-links { flex: 1; display: flex; gap: 20px; }
.pi-footer-links a { font-size: 13px; color: #64748b; text-decoration: none; }
.pi-footer-links a:hover { color: #0f172a; }
.pi-footer-copy { font-size: 12px; color: #94a3b8; }

/* ═══ Responsive ═══ */
@media (max-width: 768px) {
  .pi-hero h1 { font-size: 36px; }
  .pi-layout { flex-direction: column; }
  .pi-sidebar { width: 100%; position: static; display: flex; flex-wrap: wrap; gap: 6px; }
  .pi-sidebar-title { width: 100%; }
  .pi-cat-btn { width: auto; padding: 8px 14px; font-size: 12px; }
  .pi-grid { grid-template-columns: 1fr; }
  .pi-nav-links { display: none; }
}
</style>
