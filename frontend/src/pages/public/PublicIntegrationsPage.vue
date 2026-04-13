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
        <span class="pi-badge">70+ Integrations</span>
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
                <div class="pi-card-icon" :style="{ background: intg.bgColor }">
                  <span v-html="intg.icon"></span>
                </div>
                <span class="pi-card-tag" :style="{ color: intg.tagColor, background: intg.tagBg }">{{ intg.category }}</span>
              </div>
              <h3 class="pi-card-name">{{ intg.name }}</h3>
              <p class="pi-card-desc">{{ intg.shortDesc }}</p>
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
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))

const categories = [
  { key: 'all',          label: 'All Integrations', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>' },
  { key: 'analytics',    label: 'Analytics',        icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>' },
  { key: 'messaging',    label: 'Messaging',        icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21 15-3.17-3.17a2 2 0 0 0-2.83 0L12 15"/><path d="M21 3v18H3V3z"/></svg>' },
  { key: 'crm',          label: 'CRM',              icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>' },
  { key: 'ads',          label: 'Ads',              icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>' },
  { key: 'payments',     label: 'Payments',         icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="20" height="14" x="2" y="5" rx="2"/><path d="M2 10h20"/></svg>' },
  { key: 'automation',   label: 'Automation',       icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4"/><path d="m6.34 6.34 2.83 2.83"/><path d="M2 12h4"/><path d="m6.34 17.66 2.83-2.83"/><path d="M12 18v4"/><path d="m17.66 17.66-2.83-2.83"/><path d="M18 12h4"/><path d="m17.66 6.34-2.83 2.83"/></svg>' },
  { key: 'seo',          label: 'SEO',              icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>' },
  { key: 'voice',        label: 'Voice & Calls',    icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72"/></svg>' },
  { key: 'social',       label: 'Social',           icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>' },
]

const integrations = [
  // Analytics & Tracking
  { slug: 'fetchbot-pixel', name: 'FetchBot Pixel', category: 'Analytics', categoryKey: 'analytics', shortDesc: 'One-line JavaScript snippet for real-time visitor tracking, heatmaps, and session recording.', bgColor: 'linear-gradient(135deg, #6366f120, #8b5cf620)', tagColor: '#6366f1', tagBg: '#6366f110', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.5"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>', longDesc: 'Install FetchBot\'s lightweight tracking pixel on any website with a single line of code. Automatically captures pageviews, clicks, scroll depth, and session recordings — zero configuration required. The pixel also powers real-time heatmaps and visitor identification.', features: ['Real-time visitor tracking', 'Click and scroll heatmaps', 'Session recording', 'Zero-config installation'] },
  { slug: 'google-analytics', name: 'Google Analytics', category: 'Analytics', categoryKey: 'analytics', shortDesc: 'Import your GA4 data into FetchBot for unified analytics and AI-powered insights.', bgColor: 'linear-gradient(135deg, #f9ab0020, #e3740020)', tagColor: '#e37400', tagBg: '#e3740010', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#e37400"><path d="M22 12c0-5.5-4.5-10-10-10S2 6.5 2 12s4.5 10 10 10c1 0 2-.2 3-.4V14h-4v-3h7v1z"/></svg>', longDesc: 'Bring your Google Analytics 4 data directly into FetchBot. Compare GA metrics with FetchBot\'s server-side data for a complete picture of your traffic.', features: ['GA4 data import', 'Unified dashboard', 'Cross-platform comparison', 'AI anomaly detection'] },
  { slug: 'google-search-console', name: 'Google Search Console', category: 'SEO', categoryKey: 'seo', shortDesc: 'Pull real Google ranking data, impressions, and clicks to power keyword intelligence.', bgColor: 'linear-gradient(135deg, #4285f420, #34a85320)', tagColor: '#4285f4', tagBg: '#4285f410', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#4285f4" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>', longDesc: 'Connect Google Search Console to get real search ranking data, impressions, CTR, and click data directly into FetchBot\'s keyword intelligence engine.', features: ['Real search rankings', 'Click-through rate tracking', 'Impression data', 'Keyword position history'] },

  // Messaging
  { slug: 'slack', name: 'Slack', category: 'Messaging', categoryKey: 'messaging', shortDesc: 'Get daily growth reports, hot lead alerts, and trend intelligence delivered to your Slack channels.', bgColor: 'linear-gradient(135deg, #4A154B15, #E01E5A10)', tagColor: '#4A154B', tagBg: '#4A154B10', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M14.5 2a2.5 2.5 0 0 0 0 5H17V4.5A2.5 2.5 0 0 0 14.5 2z" fill="#E01E5A"/><path d="M2 14.5a2.5 2.5 0 0 0 5 0V12H4.5A2.5 2.5 0 0 0 2 14.5z" fill="#36C5F0"/><path d="M9.5 22a2.5 2.5 0 0 0 0-5H7v2.5A2.5 2.5 0 0 0 9.5 22z" fill="#2EB67D"/><path d="M22 9.5a2.5 2.5 0 0 0-5 0V12h2.5A2.5 2.5 0 0 0 22 9.5z" fill="#ECB22E"/></svg>', longDesc: 'Connect Slack to receive automated daily growth summaries, instant hot lead alerts, weekly SEO trend digests, and growth milestone celebrations — right in your team channels.', features: ['Daily growth reports', 'Hot lead instant alerts', 'Weekly trend digests', 'Custom channel routing'] },
  { slug: 'discord', name: 'Discord', category: 'Messaging', categoryKey: 'messaging', shortDesc: 'Share rich-embed growth reports and lead alerts in your Discord server.', bgColor: 'linear-gradient(135deg, #5865F215, #5865F210)', tagColor: '#5865F2', tagBg: '#5865F210', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#5865F2"><path d="M20.3 4.1a19.4 19.4 0 0 0-4.8-1.5 14.5 14.5 0 0 0-.6 1.3 18 18 0 0 0-5.4 0c-.2-.5-.4-.9-.6-1.3A19.3 19.3 0 0 0 4 4.1 20 20 0 0 0 .5 17.7a19.5 19.5 0 0 0 6 3 14.6 14.6 0 0 0 1.3-2 12.6 12.6 0 0 1-2-.9l.5-.4c3.8 1.8 8 1.8 11.8 0 .2.1.3.3.5.4-.6.4-1.3.7-2 .9.4.7.8 1.4 1.3 2a19.5 19.5 0 0 0 6-3A20 20 0 0 0 20.3 4.1zM8 14.8c-1.2 0-2.2-1.1-2.2-2.4S6.8 10 8 10s2.2 1.1 2.2 2.4S9.2 14.8 8 14.8zm8 0c-1.2 0-2.2-1.1-2.2-2.4S14.8 10 16 10s2.2 1.1 2.2 2.4S17.2 14.8 16 14.8z"/></svg>', longDesc: 'Get rich embed notifications delivered to your Discord server. Perfect for dev teams and growth hackers who live in Discord.', features: ['Rich embed messages', 'Weekly performance summaries', 'Hot lead alerts', 'Role mentions on key alerts'] },
  { slug: 'telegram', name: 'Telegram', category: 'Messaging', categoryKey: 'messaging', shortDesc: 'Receive instant push notifications for growth milestones and hot leads on mobile.', bgColor: 'linear-gradient(135deg, #229ED915, #229ED910)', tagColor: '#229ED9', tagBg: '#229ED910', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#229ED9"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm4.6 6.8l-1.7 7.9c-.1.5-.5.7-.9.4l-2.5-1.8-1.2 1.2c-.1.2-.3.3-.5.3l.2-2.5 4.5-4c.2-.2 0-.3-.3-.1L8.7 13.5l-2.4-.7c-.5-.2-.5-.5.1-.7l9.5-3.7c.4-.1.8.1.7.7z"/></svg>', longDesc: 'Get instant mobile push notifications for hot leads, growth milestones, and daily summaries right on your phone via Telegram.', features: ['Instant push notifications', 'Mobile-first growth alerts', 'Daily summaries', 'Milestone celebrations'] },

  // Payments
  { slug: 'stripe', name: 'Stripe', category: 'Payments', categoryKey: 'payments', shortDesc: 'Track subscriptions, payments, and revenue attribution with Stripe billing integration.', bgColor: 'linear-gradient(135deg, #635bff15, #635bff10)', tagColor: '#635bff', tagBg: '#635bff10', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#635bff"><path d="M13.976 9.15c-2.172-.806-3.356-1.426-3.356-2.409 0-.831.683-1.305 1.901-1.305 2.227 0 4.515.858 6.09 1.631l.89-5.494C18.252.975 15.697 0 12.165 0 9.667 0 7.589.654 6.104 1.872 4.56 3.147 3.757 4.992 3.757 7.218c0 4.039 2.467 5.76 6.476 7.219 2.585.92 3.445 1.574 3.445 2.583 0 .98-.84 1.545-2.354 1.545-1.875 0-4.965-.921-7.076-2.19L3.37 21.8c1.857 1.029 5.166 2.2 8.63 2.2 2.59 0 4.749-.657 6.29-1.834C19.77 20.873 20.5 19 20.5 16.65c0-4.171-2.505-5.834-6.524-7.5z"/></svg>', longDesc: 'Integrate Stripe to track payments, subscriptions, and revenue. See which marketing channels drive the most revenue with full payment attribution.', features: ['Payment tracking', 'Subscription management', 'Revenue attribution', 'Customer portal'] },

  // CRM
  { slug: 'hubspot', name: 'HubSpot', category: 'CRM', categoryKey: 'crm', shortDesc: 'Sync leads, deals, and contacts bidirectionally with HubSpot CRM.', bgColor: 'linear-gradient(135deg, #ff7a5920, #ff5c3510)', tagColor: '#ff5c35', tagBg: '#ff5c3510', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#ff5c35"><circle cx="12" cy="12" r="10"/></svg>', longDesc: 'Connect HubSpot CRM to sync leads, deals, and contacts bidirectionally. FetchBot\'s lead scoring enriches HubSpot records with behavioral data.', features: ['Bidirectional lead sync', 'Deal pipeline tracking', 'Lead score enrichment', 'Contact timeline'] },
  { slug: 'salesforce', name: 'Salesforce', category: 'CRM', categoryKey: 'crm', shortDesc: 'Push enriched leads and opportunity data to Salesforce for enterprise sales teams.', bgColor: 'linear-gradient(135deg, #00a1e020, #1798c110)', tagColor: '#00a1e0', tagBg: '#00a1e010', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#00a1e0"><circle cx="12" cy="12" r="10"/></svg>', longDesc: 'Enterprise-grade Salesforce integration. Push FetchBot\'s enriched leads directly into Salesforce with full field mapping.', features: ['Lead push to Salesforce', 'Field mapping', 'Opportunity tracking', 'Activity logging'] },
  { slug: 'mailchimp', name: 'Mailchimp', category: 'CRM', categoryKey: 'crm', shortDesc: 'Sync lead segments to Mailchimp audiences for targeted email campaigns.', bgColor: 'linear-gradient(135deg, #ffe01b15, #f2ca0010)', tagColor: '#8b6914', tagBg: '#ffe01b15', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#8b6914"><circle cx="12" cy="12" r="10"/></svg>', longDesc: 'Push your FetchBot lead segments directly to Mailchimp audiences. Tag contacts based on lead score, behavior, and engagement.', features: ['Audience sync', 'Segment targeting', 'Tag management', 'Open tracking'] },

  // Ads
  { slug: 'facebook-ads', name: 'Facebook Ads', category: 'Ads', categoryKey: 'ads', shortDesc: 'Capture Facebook Lead Ads submissions and track ad-driven conversions.', bgColor: 'linear-gradient(135deg, #1877f220, #1877f210)', tagColor: '#1877f2', tagBg: '#1877f210', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#1877f2"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>', longDesc: 'Connect Facebook Ads to capture lead form submissions via webhooks and track conversions from ad campaigns directly in FetchBot.', features: ['Lead Ads capture', 'Conversion tracking', 'Audience sync', 'ROAS reporting'] },
  { slug: 'google-ads', name: 'Google Ads', category: 'Ads', categoryKey: 'ads', shortDesc: 'Track Google Ads conversions and sync lead data for better targeting.', bgColor: 'linear-gradient(135deg, #4285f420, #34a85310)', tagColor: '#4285f4', tagBg: '#4285f410', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="18" r="4" fill="#4285f4"/><path d="M2 12l8 8 12-16" stroke="#34a853" stroke-width="2" fill="none"/></svg>', longDesc: 'Integrate Google Ads to track conversions, sync offline leads, and measure true ROAS across your campaigns with FetchBot\'s attribution engine.', features: ['Conversion imports', 'Offline lead sync', 'ROAS tracking', 'Keyword attribution'] },
  { slug: 'linkedin-ads', name: 'LinkedIn Ads', category: 'Ads', categoryKey: 'ads', shortDesc: 'Track LinkedIn lead gen form submissions and ad-driven B2B conversions.', bgColor: 'linear-gradient(135deg, #0a66c220, #0a66c210)', tagColor: '#0a66c2', tagBg: '#0a66c210', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#0a66c2"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452z"/></svg>', longDesc: 'Connect LinkedIn Ads to capture lead gen form data and track B2B conversions. Perfect for enterprise lead generation.', features: ['Lead Gen Forms', 'B2B conversion tracking', 'Account-based targeting', 'Campaign ROAS'] },

  // SEO
  { slug: 'dataforseo', name: 'DataForSEO', category: 'SEO', categoryKey: 'seo', shortDesc: 'Get real Google SERP rankings, search volume, CPC, and difficulty data for your keywords.', bgColor: 'linear-gradient(135deg, #2ecc7120, #27ae6010)', tagColor: '#27ae60', tagBg: '#27ae6010', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#27ae60" stroke-width="1.5"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>', longDesc: 'DataForSEO powers FetchBot\'s keyword intelligence with real Google SERP data. Get accurate search volume, CPC, keyword difficulty, and SERP feature data for every keyword you track.', features: ['Real SERP rankings', 'Search volume data', 'CPC and difficulty', 'SERP feature detection'] },

  // Voice & Calls
  { slug: 'retell-ai', name: 'Retell.ai', category: 'Voice & Calls', categoryKey: 'voice', shortDesc: 'Power AI voice agents with natural-sounding conversations for outbound calls.', bgColor: 'linear-gradient(135deg, #8b5cf620, #6366f110)', tagColor: '#8b5cf6', tagBg: '#8b5cf610', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="1.5"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M12 19v4"/></svg>', longDesc: 'Retell.ai powers FetchBot\'s Voice Agent with ultra-realistic AI voice conversations. Build outbound call campaigns with AI agents that sound human.', features: ['AI voice calling', 'Natural conversations', 'Call campaigns', 'Transcript extraction'] },
  { slug: 'telnyx', name: 'Telnyx', category: 'Voice & Calls', categoryKey: 'voice', shortDesc: 'Buy, verify, and manage phone numbers for AI voice agent campaigns.', bgColor: 'linear-gradient(135deg, #00c04b20, #00c04b10)', tagColor: '#00c04b', tagBg: '#00c04b10', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#00c04b" stroke-width="1.5"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.81.36 1.6.68 2.35a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.75.32 1.54.55 2.35.68A2 2 0 0 1 22 16.92z"/></svg>', longDesc: 'Telnyx provides the phone infrastructure for FetchBot\'s Voice Agent. Buy numbers, verify callers, and manage your voice communication stack.', features: ['Phone number management', 'Caller verification', 'Number porting', 'Usage tracking'] },
  { slug: 'livekit', name: 'LiveKit', category: 'Voice & Calls', categoryKey: 'voice', shortDesc: 'Real-time voice and video infrastructure for browser-based calling.', bgColor: 'linear-gradient(135deg, #0d6efd20, #0d6efd10)', tagColor: '#0d6efd', tagBg: '#0d6efd10', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#0d6efd" stroke-width="1.5"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>', longDesc: 'LiveKit provides the real-time voice infrastructure for FetchBot\'s web-based calling. Handle inbound and outbound calls directly from the browser.', features: ['Browser-based calls', 'Real-time audio', 'Call recording', 'WebRTC support'] },

  // Social
  { slug: 'facebook-leads', name: 'Facebook Lead Ads', category: 'Social', categoryKey: 'social', shortDesc: 'Capture leads from Facebook Lead Ads forms via webhook and auto-score them.', bgColor: 'linear-gradient(135deg, #1877f215, #1877f210)', tagColor: '#1877f2', tagBg: '#1877f210', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#1877f2"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>', longDesc: 'Automatically capture leads from Facebook Lead Ads forms. Leads are scored and added to your pipeline in real-time.', features: ['Auto lead capture', 'Lead scoring', 'Pipeline integration', 'Instant notifications'] },
  { slug: 'linkedin-leads', name: 'LinkedIn', category: 'Social', categoryKey: 'social', shortDesc: 'Import and sync leads from LinkedIn for B2B prospecting and outreach.', bgColor: 'linear-gradient(135deg, #0a66c215, #0a66c210)', tagColor: '#0a66c2', tagBg: '#0a66c210', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#0a66c2"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452z"/></svg>', longDesc: 'Import leads from LinkedIn and sync B2B contact data for outreach. Combine LinkedIn insights with FetchBot\'s visitor intelligence.', features: ['Lead import', 'B2B enrichment', 'CSV sync', 'Contact matching'] },
  { slug: 'x-twitter', name: 'X (Twitter)', category: 'Social', categoryKey: 'social', shortDesc: 'Import leads and trending topics from X to drive content strategy.', bgColor: 'linear-gradient(135deg, #14171a15, #14171a10)', tagColor: '#14171a', tagBg: '#14171a10', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#14171a"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>', longDesc: 'Leverage X (Twitter) for lead import and trending topic analysis. Use real-time trending data to power your content and SEO strategy.', features: ['Lead CSV import', 'Trending topics', 'Content ideas', 'Engagement tracking'] },

  // Automation
  { slug: 'zapier', name: 'Zapier', category: 'Automation', categoryKey: 'automation', shortDesc: 'Connect FetchBot to 5,000+ apps through Zapier\'s automation platform.', bgColor: 'linear-gradient(135deg, #ff4a0020, #ff4a0010)', tagColor: '#ff4a00', tagBg: '#ff4a0010', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="#ff4a00"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>', longDesc: 'Connect FetchBot to over 5,000 applications through Zapier. Trigger workflows when leads are scored, keywords change rank, or traffic spikes.', features: ['5,000+ app connections', 'Lead triggers', 'Keyword alerts', 'Custom workflows'] },
  { slug: 'webhooks', name: 'Webhooks', category: 'Automation', categoryKey: 'automation', shortDesc: 'Send real-time event data to any custom URL for complete flexibility.', bgColor: 'linear-gradient(135deg, #64748b20, #47556910)', tagColor: '#475569', tagBg: '#47556910', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="1.5"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.5 1.5"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.5-1.5"/></svg>', longDesc: 'Send any FetchBot event to your own endpoints via webhooks. Build custom integrations with full control over the data format.', features: ['Real-time events', 'Custom URLs', 'Retry on failure', 'Event filtering'] },
  { slug: 'google-oauth', name: 'Google OAuth', category: 'Automation', categoryKey: 'automation', shortDesc: 'Secure login and data export to Google Sheets and Google Drive.', bgColor: 'linear-gradient(135deg, #4285f420, #ea433510)', tagColor: '#4285f4', tagBg: '#4285f410', icon: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#4285f4"/><path d="M12 6v6l4.5 2.5" stroke="white" stroke-width="2"/></svg>', longDesc: 'Use Google OAuth for secure login and seamlessly export leads and analytics data to Google Sheets and Google Drive.', features: ['One-click login', 'Google Sheets export', 'Google Drive sync', 'Secure OAuth 2.0'] },
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
      i.category.toLowerCase().includes(q)
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
.pi-sidebar {
  width: 220px; flex-shrink: 0; position: sticky; top: 80px; align-self: flex-start;
}
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
  display: flex; align-items: baseline; justify-content: space-between;
  margin-bottom: 20px;
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
.pi-card-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.pi-card-icon {
  width: 48px; height: 48px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
}
.pi-card-tag {
  font-size: 11px; font-weight: 600; padding: 4px 10px;
  border-radius: 100px; text-transform: uppercase; letter-spacing: 0.3px;
}
.pi-card-name { font-size: 16px; font-weight: 700; margin: 0 0 6px; color: #0f172a; }
.pi-card-desc { font-size: 13px; color: #64748b; line-height: 1.5; margin: 0; flex: 1; }
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
.pi-cta-inner {
  max-width: 600px; margin: 0 auto; text-align: center;
}
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
