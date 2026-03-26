<template>
  <div class="billing-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Plans & Billing</h1>
        <p class="page-subtitle">One platform, every growth tool you need.</p>
      </div>
    </div>

    <div v-if="loading" class="loading-state">Loading billing...</div>
    <template v-else>

      <!-- Savings Banner -->
      <div class="savings-banner">
        <div class="savings-inner">
          <div class="savings-text">
            <div class="savings-headline">Replace 5 tools with 1</div>
            <div class="savings-sub">Separate tools cost $184-561/mo. FetchBot starts at $29/mo.</div>
          </div>
          <div class="savings-tags">
            <span class="savings-tag">Analytics</span>
            <span class="savings-tag">Lead Scoring</span>
            <span class="savings-tag">SEO Audits</span>
            <span class="savings-tag">Competitor Intel</span>
            <span class="savings-tag">AI Strategy</span>
          </div>
        </div>
      </div>

      <!-- Pricing Cards -->
      <div class="pricing-grid">
        <div v-for="plan in plans" :key="plan.id" class="pricing-card" :class="{ 'card-popular': plan.popular, 'card-current': currentPlan === plan.id }">
          <div v-if="plan.popular" class="popular-tag">Most Popular</div>
          <div v-if="currentPlan === plan.id" class="current-tag">Current Plan</div>
          <div class="plan-name">{{ plan.name }}</div>
          <div class="plan-price">
            <span class="price-amount">${{ annual ? plan.price_yearly / 12 : plan.price_monthly }}</span>
            <span class="price-period">/mo</span>
          </div>
          <div v-if="annual" class="price-annual">Billed ${{ plan.price_yearly }}/yr (save {{ Math.round((1 - plan.price_yearly / (plan.price_monthly * 12)) * 100) }}%)</div>
          <div class="plan-replaces">
            <span class="replaces-label">Replaces</span>
            <span class="replaces-value">${{ plan.replaces }}/mo</span>
            <span class="replaces-label">in separate tools</span>
          </div>
          <ul class="plan-features">
            <li v-for="f in plan.features" :key="f">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="2,7 5.5,10.5 12,3.5"/></svg>
              {{ f }}
            </li>
          </ul>
          <button v-if="currentPlan !== plan.id" class="btn" :class="plan.popular ? 'btn-primary' : 'btn-secondary'" style="width:100%;margin-top:auto" @click="handlePlanSelect(plan.id)" :disabled="checkingOut">
            {{ checkingOut === plan.id ? 'Redirecting...' : isPlanUpgrade(plan.id) ? 'Upgrade' : 'Downgrade' }}
          </button>
          <button v-else class="btn btn-secondary" style="width:100%;margin-top:auto" disabled>Active</button>
        </div>
      </div>

      <!-- Annual toggle -->
      <div class="billing-toggle">
        <span :class="{ active: !annual }">Monthly</span>
        <button class="toggle-switch" :class="{ on: annual }" @click="annual = !annual">
          <span class="toggle-knob"></span>
        </button>
        <span :class="{ active: annual }">Annual <span class="save-badge">Save 17%</span></span>
      </div>

      <!-- Feature Comparison Table -->
      <div class="card" style="margin-top:32px">
        <div class="card-header">
          <h3 class="card-title">Full Feature Comparison</h3>
        </div>
        <table class="feature-table">
          <thead>
            <tr>
              <th>Feature</th>
              <th class="text-center">Starter</th>
              <th class="text-center highlight-col">Growth</th>
              <th class="text-center">Scale</th>
            </tr>
          </thead>
          <tbody>
            <tr class="section-row"><td colspan="4">Analytics</td></tr>
            <tr v-for="f in featureRows.analytics" :key="f.name"><td>{{ f.name }}</td><td class="text-center" v-for="(v, i) in f.tiers" :key="i" :class="{ 'highlight-col': i === 1 }"><span v-if="v === true" class="check-icon"><svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="var(--color-success)" stroke-width="2"><polyline points="2,7 5.5,10.5 12,3.5"/></svg></span><span v-else-if="v === false" class="dash-icon">--</span><span v-else>{{ v }}</span></td></tr>

            <tr class="section-row"><td colspan="4">Lead Intelligence</td></tr>
            <tr v-for="f in featureRows.leads" :key="f.name"><td>{{ f.name }}</td><td class="text-center" v-for="(v, i) in f.tiers" :key="i" :class="{ 'highlight-col': i === 1 }"><span v-if="v === true" class="check-icon"><svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="var(--color-success)" stroke-width="2"><polyline points="2,7 5.5,10.5 12,3.5"/></svg></span><span v-else-if="v === false" class="dash-icon">--</span><span v-else>{{ v }}</span></td></tr>

            <tr class="section-row"><td colspan="4">SEO Audits</td></tr>
            <tr v-for="f in featureRows.audits" :key="f.name"><td>{{ f.name }}</td><td class="text-center" v-for="(v, i) in f.tiers" :key="i" :class="{ 'highlight-col': i === 1 }"><span v-if="v === true" class="check-icon"><svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="var(--color-success)" stroke-width="2"><polyline points="2,7 5.5,10.5 12,3.5"/></svg></span><span v-else-if="v === false" class="dash-icon">--</span><span v-else>{{ v }}</span></td></tr>

            <tr class="section-row"><td colspan="4">Competitor Intel</td></tr>
            <tr v-for="f in featureRows.competitors" :key="f.name"><td>{{ f.name }}</td><td class="text-center" v-for="(v, i) in f.tiers" :key="i" :class="{ 'highlight-col': i === 1 }"><span v-if="v === true" class="check-icon"><svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="var(--color-success)" stroke-width="2"><polyline points="2,7 5.5,10.5 12,3.5"/></svg></span><span v-else-if="v === false" class="dash-icon">--</span><span v-else>{{ v }}</span></td></tr>

            <tr class="section-row"><td colspan="4">AI Strategy Engine</td></tr>
            <tr v-for="f in featureRows.strategy" :key="f.name"><td>{{ f.name }}</td><td class="text-center" v-for="(v, i) in f.tiers" :key="i" :class="{ 'highlight-col': i === 1 }"><span v-if="v === true" class="check-icon"><svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="var(--color-success)" stroke-width="2"><polyline points="2,7 5.5,10.5 12,3.5"/></svg></span><span v-else-if="v === false" class="dash-icon">--</span><span v-else>{{ v }}</span></td></tr>

            <tr class="section-row"><td colspan="4">Platform</td></tr>
            <tr v-for="f in featureRows.platform" :key="f.name"><td>{{ f.name }}</td><td class="text-center" v-for="(v, i) in f.tiers" :key="i" :class="{ 'highlight-col': i === 1 }"><span v-if="v === true" class="check-icon"><svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="var(--color-success)" stroke-width="2"><polyline points="2,7 5.5,10.5 12,3.5"/></svg></span><span v-else-if="v === false" class="dash-icon">--</span><span v-else>{{ v }}</span></td></tr>
          </tbody>
        </table>
      </div>

      <!-- Competitor Cost Breakdown -->
      <div class="card" style="margin-top:24px">
        <div class="card-header">
          <h3 class="card-title">What You'd Pay Separately</h3>
          <span class="text-sm text-muted">vs FetchBot Growth at $79/mo</span>
        </div>
        <div class="competitor-grid">
          <div v-for="c in competitorCosts" :key="c.category" class="competitor-row">
            <div class="comp-category">{{ c.category }}</div>
            <div class="comp-tools">{{ c.tools }}</div>
            <div class="comp-price">${{ c.typical }}/mo</div>
          </div>
          <div class="competitor-row total-row">
            <div class="comp-category">Total with separate tools</div>
            <div class="comp-tools"></div>
            <div class="comp-price comp-total">${{ competitorTotal }}/mo</div>
          </div>
          <div class="competitor-row savings-row">
            <div class="comp-category">FetchBot Growth (all-in-one)</div>
            <div class="comp-tools"></div>
            <div class="comp-price comp-savings">$79/mo</div>
          </div>
        </div>
        <div class="savings-summary">
          You save <strong>${{ competitorTotal - 79 }}/mo</strong> (${{ (competitorTotal - 79) * 12 }}/yr) compared to using separate tools.
        </div>
      </div>

      <!-- Subscription Management -->
      <div class="card" style="margin-top:24px" v-if="subscription">
        <div class="card-header">
          <h3 class="card-title">Your Subscription</h3>
        </div>
        <div class="subscription-info">
          <div class="sub-row">
            <span class="text-sm text-muted">Plan</span>
            <span class="font-semibold">{{ subscription.plan_details?.name || currentPlan }}</span>
          </div>
          <div class="sub-row">
            <span class="text-sm text-muted">Status</span>
            <span class="badge" :class="subStatusClass">{{ subscription.subscription_status }}</span>
          </div>
          <div class="sub-row" v-if="subscription.current_period_end">
            <span class="text-sm text-muted">{{ subscription.cancel_at_period_end ? 'Cancels on' : 'Renews on' }}</span>
            <span class="text-sm">{{ formatDate(subscription.current_period_end) }}</span>
          </div>
          <div v-if="subscription.cancel_at_period_end" class="cancel-notice">
            Your subscription will not renew. You'll retain access until the end of your billing period.
          </div>
          <button class="btn btn-secondary btn-sm" @click="openPortal" :disabled="portalLoading" style="margin-top:16px">
            {{ portalLoading ? 'Opening...' : 'Manage Subscription' }}
          </button>
        </div>
      </div>

      <!-- Current Usage + Invoices -->
      <div class="billing-row" style="margin-top:24px">
        <div class="card" v-if="usage.length">
          <div class="card-header"><h3 class="card-title">Usage This Period</h3></div>
          <div class="usage-grid">
            <div v-for="u in usage" :key="u.metric" class="usage-item">
              <div class="usage-label">{{ formatMetric(u.metric) }}</div>
              <div class="usage-value">{{ u.count.toLocaleString() }}</div>
              <div class="usage-bar"><div class="usage-fill" :style="{ width: Math.min((u.count / u.limit) * 100, 100) + '%' }"></div></div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3 class="card-title">Invoices</h3></div>
          <table class="data-table" v-if="invoices.length">
            <thead><tr><th>Date</th><th>Amount</th><th>Status</th></tr></thead>
            <tbody>
              <tr v-for="inv in invoices" :key="inv.id || inv.stripe_invoice_id">
                <td>{{ formatDate(inv.period_start || inv.created_at) }}</td>
                <td class="font-semibold">${{ (inv.amount_paid / 100).toFixed(2) }}</td>
                <td><span class="badge" :class="inv.status === 'paid' ? 'badge-success' : 'badge-warning'">{{ inv.status }}</span></td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-state">No invoices yet.</div>
        </div>
      </div>

    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from '@/composables/useToast'
import billingApi from '@/api/billing'

const route = useRoute()
const toast = useToast()

const loading = ref(true)
const subscription = ref(null)
const invoices = ref([])
const usage = ref([])
const annual = ref(false)
const checkingOut = ref(null)
const portalLoading = ref(false)

const limits = { pageviews: 100000, audits: 50, ai_calls: 200, leads: 500 }

const currentPlan = computed(() => subscription.value?.plan || 'growth')

const planOrder = ['starter', 'growth', 'scale']
function isPlanUpgrade(id) {
  return planOrder.indexOf(id) > planOrder.indexOf(currentPlan.value)
}

const plans = [
  {
    id: 'starter', name: 'Starter', price_monthly: 29, price_yearly: 290, replaces: 184,
    features: ['1 project', '10,000 pageviews/mo', 'Lead scoring & alerts', '3 competitor tracking', 'Weekly SEO audit', 'Email support'],
  },
  {
    id: 'growth', name: 'Growth', price_monthly: 79, price_yearly: 790, popular: true, replaces: 561,
    features: ['5 projects', 'Unlimited pageviews', 'AI strategy & morning briefs', '10 competitor tracking', 'Content calendar', '5 team members', 'Priority support'],
  },
  {
    id: 'scale', name: 'Scale', price_monthly: 199, price_yearly: 1990, replaces: 800,
    features: ['Unlimited projects', 'Unlimited pageviews', 'AI strategy & chat', '50 competitor tracking', 'Unlimited team members', 'API access', 'White label', 'Dedicated support'],
  },
]

const featureRows = {
  analytics: [
    { name: 'Cookieless visitor tracking', tiers: [true, true, true] },
    { name: 'Real-time dashboard', tiers: [true, true, true] },
    { name: 'Traffic & geo breakdown', tiers: [true, true, true] },
    { name: 'Event tracking', tiers: [false, true, true] },
    { name: 'Funnel visualization', tiers: [false, true, true] },
    { name: 'API export', tiers: [false, false, true] },
  ],
  leads: [
    { name: 'Visitor identification', tiers: [true, true, true] },
    { name: 'Behavioral lead scoring', tiers: [true, true, true] },
    { name: 'Hot lead alerts', tiers: [true, true, true] },
    { name: 'CRM integration', tiers: [false, true, true] },
    { name: 'Contact-level ID', tiers: [false, false, true] },
    { name: 'Custom scoring rules', tiers: [false, false, true] },
  ],
  audits: [
    { name: 'Automated SEO audit', tiers: [true, true, true] },
    { name: 'Performance (Core Web Vitals)', tiers: [true, true, true] },
    { name: 'Security scan', tiers: [true, true, true] },
    { name: 'Issue prioritization', tiers: [true, true, true] },
    { name: 'On-demand audits', tiers: [false, true, true] },
    { name: 'White-label PDF reports', tiers: [false, false, true] },
  ],
  competitors: [
    { name: 'Competitors tracked', tiers: ['3', '10', '50'] },
    { name: 'Traffic estimation', tiers: [true, true, true] },
    { name: 'Change detection', tiers: [true, true, true] },
    { name: 'Keyword gap analysis', tiers: [false, true, true] },
    { name: 'Ranking change alerts', tiers: [false, true, true] },
  ],
  strategy: [
    { name: 'AI morning brief', tiers: [false, true, true] },
    { name: 'Growth plan generation', tiers: [false, true, true] },
    { name: 'Content calendar', tiers: [false, true, true] },
    { name: 'Strategy chat', tiers: [false, true, true] },
    { name: 'Niche analysis & predictions', tiers: [false, false, true] },
  ],
  platform: [
    { name: 'Projects', tiers: ['1', '5', 'Unlimited'] },
    { name: 'Team members', tiers: ['1', '5', 'Unlimited'] },
    { name: 'Role-based access', tiers: [true, true, true] },
    { name: 'Dark/light theme', tiers: [true, true, true] },
    { name: 'API access', tiers: [false, false, true] },
    { name: 'White label', tiers: [false, false, true] },
  ],
}

const competitorCosts = [
  { category: 'Analytics', tools: 'Fathom / Plausible', typical: 14 },
  { category: 'Lead Scoring', tools: 'Leadpipe / Leadfeeder', typical: 149 },
  { category: 'SEO Audits', tools: 'Semrush / SE Ranking', typical: 249 },
  { category: 'AI Strategy', tools: 'Jasper / Surfer SEO', typical: 99 },
  { category: 'CRM & Alerts', tools: 'HubSpot', typical: 50 },
]

const competitorTotal = computed(() => competitorCosts.reduce((s, c) => s + c.typical, 0))

function formatDate(d) {
  if (!d) return '--'
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatMetric(m) { return (m || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) }

const subStatusClass = computed(() => {
  const s = subscription.value?.subscription_status
  if (s === 'active') return 'badge-success'
  if (s === 'trialing') return 'badge-neutral'
  if (s === 'past_due') return 'badge-danger'
  if (s === 'canceled') return 'badge-danger'
  return 'badge-neutral'
})

async function handlePlanSelect(planId) {
  checkingOut.value = planId
  try {
    const res = await billingApi.checkout({ plan: planId, annual: annual.value })
    const url = res.data?.checkout_url || res.checkout_url
    if (url) {
      window.location.href = url
    } else {
      toast.error("We couldn't start the checkout. Please try again.")
    }
  } catch (e) {
    // Toast is auto-triggered by client.js interceptor
  } finally {
    checkingOut.value = null
  }
}

async function openPortal() {
  portalLoading.value = true
  try {
    const res = await billingApi.portal()
    const url = res.data?.portal_url || res.portal_url
    if (url) {
      window.location.href = url
    } else {
      toast.error("We couldn't open the billing portal. Please try again.")
    }
  } catch (e) {
    // Toast is auto-triggered by client.js interceptor
  } finally {
    portalLoading.value = false
  }
}

onMounted(async () => {
  // Check for checkout return params
  const checkoutParam = route.query.checkout
  if (checkoutParam === 'success') {
    toast.success('Your subscription has been activated! Welcome aboard.')
  } else if (checkoutParam === 'canceled') {
    toast.info('Checkout was canceled. You can upgrade anytime.')
  }

  try {
    const [subRes, invRes, usageRes] = await Promise.all([
      billingApi.getCurrent().catch(() => ({ data: null })),
      billingApi.invoices().catch(() => ({ data: [] })),
      billingApi.usage().catch(() => ({ data: [] })),
    ])
    subscription.value = subRes.data?.data || subRes.data || null
    invoices.value = invRes.data?.data || invRes.data || []
    const usageData = usageRes.data?.data || usageRes.data || []
    usage.value = Array.isArray(usageData) ? usageData.map(u => ({
      ...u,
      limit: u.limit || limits[u.metric] || 10000,
    })) : []
  } catch (e) {
    // Toast auto-triggered
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }
.empty-state { text-align: center; padding: 40px; color: var(--text-muted); }

/* ── Savings Banner ── */
.savings-banner {
  background: var(--text-primary);
  color: var(--text-inverse);
  border-radius: var(--radius-md);
  padding: 28px 32px;
  margin-bottom: 32px;
}

.savings-inner { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px; }
.savings-headline { font-family: var(--font-display); font-size: var(--font-2xl); margin-bottom: 4px; }
.savings-sub { font-size: var(--font-sm); opacity: 0.7; }
.savings-tags { display: flex; gap: 8px; flex-wrap: wrap; }
.savings-tag {
  padding: 4px 12px;
  border: 1px solid rgba(255,255,255,0.25);
  border-radius: var(--radius-full);
  font-size: var(--font-xs);
  font-weight: 500;
  opacity: 0.85;
}

/* ── Pricing Grid ── */
.pricing-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 16px;
}

.pricing-card {
  background: var(--bg-card);
  border: none;
  border-radius: var(--radius-md);
  padding: 28px 24px;
  display: flex;
  flex-direction: column;
  position: relative;
  transition: all var(--transition-base);
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
}

.pricing-card:hover { box-shadow: var(--shadow-lg); transform: translateY(-2px); }
.card-popular { border-color: var(--brand-accent); box-shadow: 0 0 0 1px var(--brand-accent); }
.card-current { border-color: var(--color-success); }

.popular-tag {
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--brand-accent);
  color: #fff;
  font-size: var(--font-xs);
  font-weight: 700;
  padding: 3px 14px;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.current-tag {
  position: absolute;
  top: -10px;
  right: 16px;
  background: var(--color-success);
  color: #fff;
  font-size: var(--font-xs);
  font-weight: 600;
  padding: 3px 12px;
  border-radius: var(--radius-full);
}

.plan-name { font-size: var(--font-lg); font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }
.plan-price { display: flex; align-items: baseline; gap: 2px; margin-bottom: 4px; }
.price-amount { font-family: var(--font-display); font-size: var(--font-3xl); color: var(--text-primary); }
.price-period { font-size: var(--font-sm); color: var(--text-muted); }
.price-annual { font-size: var(--font-xs); color: var(--color-success); margin-bottom: 12px; }

.plan-replaces {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--font-xs);
  color: var(--text-muted);
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
}
.replaces-value { font-weight: 700; color: var(--text-primary); text-decoration: line-through; opacity: 0.6; }

.plan-features {
  list-style: none;
  padding: 0;
  margin: 0 0 20px;
  flex: 1;
}

.plan-features li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-sm);
  color: var(--text-secondary);
  padding: 5px 0;
}

.plan-features li svg { color: var(--color-success); flex-shrink: 0; }

/* ── Toggle ── */
.billing-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  font-size: var(--font-sm);
  color: var(--text-muted);
}

.billing-toggle .active { color: var(--text-primary); font-weight: 600; }

.toggle-switch {
  width: 44px;
  height: 24px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  position: relative;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.toggle-switch.on { background: var(--text-primary); border-color: var(--text-primary); }

.toggle-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  background: #fff;
  border-radius: 50%;
  transition: all var(--transition-fast);
}

.toggle-switch.on .toggle-knob { left: 22px; }

.save-badge {
  background: var(--color-success-bg);
  color: var(--color-success);
  font-size: var(--font-xs);
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  margin-left: 4px;
}

/* ── Feature Table ── */
.feature-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-sm);
}

.feature-table th, .feature-table td {
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-color);
  text-align: left;
}

.feature-table th { font-size: var(--font-xs); font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }
.feature-table .text-center { text-align: center; }

.section-row td {
  font-weight: 700;
  font-size: var(--font-sm);
  color: var(--text-primary);
  padding-top: 20px;
  border-bottom: 2px solid var(--border-color);
  background: transparent;
}

.highlight-col { background: var(--brand-accent-light, rgba(212,149,106,0.06)); }

.check-icon { color: var(--color-success); }
.dash-icon { color: var(--text-muted); opacity: 0.4; }

/* ── Competitor Grid ── */
.competitor-grid { margin-bottom: 16px; }

.competitor-row {
  display: grid;
  grid-template-columns: 1fr 1.5fr auto;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  font-size: var(--font-sm);
}

.comp-category { font-weight: 600; color: var(--text-primary); }
.comp-tools { color: var(--text-muted); font-size: var(--font-xs); }
.comp-price { font-weight: 700; color: var(--text-primary); text-align: right; }
.total-row { border-top: 2px solid var(--border-color); background: var(--bg-surface); }
.comp-total { font-size: var(--font-lg); }
.savings-row { background: var(--text-primary); border-radius: 0 0 var(--radius-md) var(--radius-md); }
.savings-row .comp-category { color: var(--text-inverse); }
.savings-row .comp-savings { color: var(--text-inverse); font-size: var(--font-lg); }

.savings-summary {
  text-align: center;
  padding: 16px;
  font-size: var(--font-sm);
  color: var(--color-success);
}

/* ── Usage & Invoices Row ── */
.billing-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.usage-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.usage-item { padding: 14px; background: var(--bg-surface); border-radius: var(--radius-md); }
.usage-label { font-size: var(--font-xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
.usage-value { font-size: var(--font-lg); font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }
.usage-bar { width: 100%; height: 4px; background: var(--bg-input); border-radius: var(--radius-full); overflow: hidden; }
.usage-fill { height: 100%; background: var(--color-success); border-radius: var(--radius-full); }

/* ── Subscription Management ── */
.subscription-info { padding: 4px 0; }
.sub-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--border-color); }
.sub-row:last-of-type { border-bottom: none; }
.cancel-notice { font-size: var(--font-sm); color: var(--color-warning); background: rgba(245, 158, 11, 0.08); padding: 12px 14px; border-radius: var(--radius-md); margin-top: 12px; line-height: 1.5; }

@media (max-width: 768px) {
  .pricing-grid { grid-template-columns: 1fr; }
  .billing-row { grid-template-columns: 1fr; }
  .savings-inner { flex-direction: column; }
}
</style>
