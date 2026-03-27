<template>
  <div class="billing-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Plans & Billing</h1>
        <p class="page-subtitle">Simple pricing. Powerful growth tools.</p>
      </div>
    </div>

    <div v-if="loading" class="loading-state">Loading billing...</div>
    <template v-else>

      <!-- Pricing Cards — 2 Tiers -->
      <div class="pricing-hero">
        <div class="pricing-pair">

          <!-- Individual -->
          <div class="tier-card" :class="{ active: currentSegment === 'individual' }">
            <div v-if="currentSegment === 'individual'" class="current-badge">Your Plan</div>
            <div class="tier-icon" style="background: linear-gradient(135deg, #8b5cf6, #6366f1)">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            </div>
            <h2 class="tier-name">Individual</h2>
            <p class="tier-tagline">For solopreneurs, freelancers, and indie hackers</p>

            <div class="tier-price">
              <span class="price-amount">$14</span>
              <span class="price-period">/month</span>
            </div>
            <div class="price-annual-note" v-if="annual">Billed $140/year (save 17%)</div>

            <div class="tier-limits">
              <div class="limit-pill"><span class="lp-val">3</span><span class="lp-label">Projects</span></div>
              <div class="limit-pill"><span class="lp-val">50K</span><span class="lp-label">Pageviews</span></div>
              <div class="limit-pill"><span class="lp-val">100</span><span class="lp-label">AI Credits</span></div>
            </div>

            <ul class="tier-features">
              <li><span class="feat-check">✓</span> Full analytics dashboard</li>
              <li><span class="feat-check">✓</span> Lead scoring & hot alerts</li>
              <li><span class="feat-check">✓</span> 5 competitor tracking</li>
              <li><span class="feat-check">✓</span> SEO audits on-demand</li>
              <li><span class="feat-check">✓</span> AI strategy & morning briefs</li>
              <li><span class="feat-check">✓</span> Pipeline builder</li>
              <li><span class="feat-check">✓</span> 2 integrations (Slack/Discord/Telegram)</li>
              <li><span class="feat-check">✓</span> Trend intelligence</li>
              <li class="feat-disabled"><span class="feat-dash">—</span> SSO / SAML</li>
              <li class="feat-disabled"><span class="feat-dash">—</span> API access</li>
              <li class="feat-disabled"><span class="feat-dash">—</span> White-label</li>
            </ul>

            <button v-if="currentSegment !== 'individual'" class="btn btn-primary btn-lg w-full" @click="handlePlanSelect('individual')" :disabled="checkingOut">
              {{ checkingOut === 'individual' ? 'Redirecting...' : 'Get Started' }}
            </button>
            <button v-else class="btn btn-secondary btn-lg w-full" disabled>Active Plan</button>
          </div>

          <!-- Enterprise -->
          <div class="tier-card enterprise" :class="{ active: currentSegment === 'enterprise' }">
            <div v-if="currentSegment === 'enterprise'" class="current-badge enterprise-badge">Your Plan</div>
            <div class="enterprise-glow"></div>
            <div class="tier-icon" style="background: linear-gradient(135deg, #f59e0b, #d97706)">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
            </div>
            <h2 class="tier-name">Enterprise</h2>
            <p class="tier-tagline">For teams, agencies, and organizations</p>

            <div class="tier-price">
              <span class="price-amount">Custom</span>
              <span class="price-period">/user</span>
            </div>
            <div class="price-annual-note">Based on team size & requirements</div>

            <div class="tier-limits">
              <div class="limit-pill"><span class="lp-val">∞</span><span class="lp-label">Projects</span></div>
              <div class="limit-pill"><span class="lp-val">∞</span><span class="lp-label">Pageviews</span></div>
              <div class="limit-pill"><span class="lp-val">∞</span><span class="lp-label">AI Credits</span></div>
            </div>

            <ul class="tier-features">
              <li><span class="feat-check ent">✓</span> Everything in Individual</li>
              <li><span class="feat-check ent">✓</span> Unlimited team members</li>
              <li><span class="feat-check ent">✓</span> Unlimited integrations</li>
              <li><span class="feat-check ent">✓</span> Unlimited competitors</li>
              <li><span class="feat-check ent">✓</span> SSO / SAML authentication</li>
              <li><span class="feat-check ent">✓</span> Full API access</li>
              <li><span class="feat-check ent">✓</span> White-label reports</li>
              <li><span class="feat-check ent">✓</span> Agents & LLM Ranking</li>
              <li><span class="feat-check ent">✓</span> Organization-level billing</li>
              <li><span class="feat-check ent">✓</span> Dedicated support & SLA</li>
              <li><span class="feat-check ent">✓</span> Custom onboarding</li>
            </ul>

            <button v-if="currentSegment !== 'enterprise'" class="btn btn-enterprise btn-lg w-full" @click="contactEnterprise">
              Contact Sales
            </button>
            <button v-else class="btn btn-secondary btn-lg w-full" disabled>Active Plan</button>
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
      </div>

      <!-- What's Included -->
      <div class="card" style="margin-top:32px">
        <div class="card-header">
          <h3 class="card-title">Feature Comparison</h3>
        </div>
        <table class="feature-table">
          <thead>
            <tr>
              <th>Feature</th>
              <th class="text-center">Individual — $14/mo</th>
              <th class="text-center highlight-col">Enterprise — Custom</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in featureRows" :key="f.name" :class="{ 'section-row': f.section }">
              <td :colspan="f.section ? 3 : 1">{{ f.name }}</td>
              <template v-if="!f.section">
                <td class="text-center">
                  <span v-if="f.individual === true" class="check-icon">✓</span>
                  <span v-else-if="f.individual === false" class="dash-icon">—</span>
                  <span v-else>{{ f.individual }}</span>
                </td>
                <td class="text-center highlight-col">
                  <span v-if="f.enterprise === true" class="check-icon">✓</span>
                  <span v-else-if="f.enterprise === false" class="dash-icon">—</span>
                  <span v-else>{{ f.enterprise }}</span>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Subscription Management -->
      <div class="card" style="margin-top:24px" v-if="subscription">
        <div class="card-header">
          <h3 class="card-title">Your Subscription</h3>
        </div>
        <div class="subscription-info">
          <div class="sub-row">
            <span class="text-sm text-muted">Plan</span>
            <span class="font-semibold">{{ subscription.plan_details?.name || currentSegment }}</span>
          </div>
          <div class="sub-row">
            <span class="text-sm text-muted">Status</span>
            <span class="badge" :class="subStatusClass">{{ subscription.subscription_status }}</span>
          </div>
          <div class="sub-row" v-if="subscription.current_period_end">
            <span class="text-sm text-muted">{{ subscription.cancel_at_period_end ? 'Cancels on' : 'Renews on' }}</span>
            <span class="text-sm">{{ formatDate(subscription.current_period_end) }}</span>
          </div>
          <button class="btn btn-secondary btn-sm" @click="openPortal" :disabled="portalLoading" style="margin-top:16px">
            {{ portalLoading ? 'Opening...' : 'Manage Subscription' }}
          </button>
        </div>
      </div>

      <!-- Usage + Invoices -->
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

const limits = { pageviews: 50000, audits: 50, ai_credits: 100, leads: 200 }

const currentSegment = computed(() => subscription.value?.segment || subscription.value?.plan || 'individual')

const featureRows = [
  { name: 'Analytics & Reporting', section: true },
  { name: 'Real-time analytics dashboard', individual: true, enterprise: true },
  { name: 'Traffic & geo breakdown', individual: true, enterprise: true },
  { name: 'Event tracking', individual: true, enterprise: true },
  { name: 'Funnel visualization', individual: true, enterprise: true },
  { name: 'API data export', individual: false, enterprise: true },
  { name: 'Lead Intelligence', section: true },
  { name: 'Behavioral lead scoring', individual: true, enterprise: true },
  { name: 'Hot lead alerts', individual: true, enterprise: true },
  { name: 'Pipeline builder', individual: true, enterprise: true },
  { name: 'Custom scoring rules', individual: false, enterprise: true },
  { name: 'Integrations', section: true },
  { name: 'Slack / Discord / Telegram', individual: '2 connections', enterprise: 'Unlimited' },
  { name: 'Daily growth reports', individual: true, enterprise: true },
  { name: 'Real-time alerts', individual: true, enterprise: true },
  { name: 'SEO & Audits', section: true },
  { name: 'Automated SEO audit', individual: true, enterprise: true },
  { name: 'On-demand audits', individual: true, enterprise: true },
  { name: 'White-label PDF reports', individual: false, enterprise: true },
  { name: 'AI Strategy', section: true },
  { name: 'AI morning brief', individual: true, enterprise: true },
  { name: 'Growth plan generation', individual: true, enterprise: true },
  { name: 'Trend intelligence', individual: true, enterprise: true },
  { name: 'Niche analysis', individual: false, enterprise: true },
  { name: 'Platform', section: true },
  { name: 'Projects', individual: '3', enterprise: 'Unlimited' },
  { name: 'Team members', individual: '1', enterprise: 'Unlimited' },
  { name: 'AI credits / month', individual: '100', enterprise: 'Unlimited' },
  { name: 'SSO / SAML', individual: false, enterprise: true },
  { name: 'API access', individual: false, enterprise: true },
  { name: 'White label', individual: false, enterprise: true },
  { name: 'Agents & LLM Ranking', individual: false, enterprise: true },
  { name: 'Organization billing', individual: false, enterprise: true },
  { name: 'Dedicated support', individual: false, enterprise: true },
]

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
  } catch (e) { /* Toast auto-triggered */ } finally {
    checkingOut.value = null
  }
}

function contactEnterprise() {
  window.open('mailto:sales@fetchbot.ai?subject=Enterprise%20Plan%20Inquiry', '_blank')
  toast.info("Opening email to sales@fetchbot.ai — we'll get back to you within 24 hours.")
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
  } catch (e) { /* Toast auto-triggered */ } finally {
    portalLoading.value = false
  }
}

onMounted(async () => {
  const checkoutParam = route.query.checkout
  if (checkoutParam === 'success') toast.success('Your subscription has been activated! Welcome aboard.')
  else if (checkoutParam === 'canceled') toast.info('Checkout was canceled. You can upgrade anytime.')

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
      ...u, limit: u.limit || limits[u.metric] || 10000,
    })) : []
  } catch (e) { /* Toast auto-triggered */ } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }
.empty-state { text-align: center; padding: 40px; color: var(--text-muted); }

/* ═══════════════════════════════════════
   Pricing Hero — Two Cards
   ═══════════════════════════════════════ */
.pricing-hero { margin-bottom: 8px; }

.pricing-pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.tier-card {
  position: relative;
  background: var(--bg-card);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 32px 28px;
  display: flex;
  flex-direction: column;
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  overflow: hidden;
}

.tier-card:hover { transform: translateY(-3px); box-shadow: 0 12px 32px rgba(0, 0, 0, 0.06); }
.tier-card.active { border-color: #8b5cf6; box-shadow: 0 0 0 1px #8b5cf6; }
.tier-card.enterprise.active { border-color: #f59e0b; box-shadow: 0 0 0 1px #f59e0b; }

.enterprise-glow {
  position: absolute;
  top: -60px; right: -60px;
  width: 160px; height: 160px;
  background: radial-gradient(circle, rgba(245, 158, 11, 0.08), transparent);
  border-radius: 50%;
  pointer-events: none;
}

.current-badge {
  position: absolute;
  top: 16px; right: 16px;
  background: #8b5cf6;
  color: white;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  padding: 3px 10px;
  border-radius: var(--radius-full);
}
.enterprise-badge { background: #f59e0b !important; }

.tier-icon {
  width: 52px; height: 52px;
  border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 16px;
}

.tier-name { font-family: var(--font-display); font-size: var(--font-2xl); font-weight: 800; color: var(--text-primary); margin: 0 0 4px; }
.tier-tagline { font-size: var(--font-xs); color: var(--text-muted); margin-bottom: 16px; }

.tier-price {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 4px;
}
.price-amount { font-family: var(--font-display); font-size: 2.5rem; font-weight: 800; color: var(--text-primary); }
.price-period { font-size: var(--font-sm); color: var(--text-muted); }
.price-annual-note { font-size: var(--font-xs); color: var(--color-success); margin-bottom: 16px; }

.tier-limits {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
}
.limit-pill {
  flex: 1;
  text-align: center;
  padding: 10px 8px;
  background: var(--bg-surface);
  border-radius: var(--radius-sm);
}
.lp-val { display: block; font-size: var(--font-lg); font-weight: 800; color: var(--text-primary); }
.lp-label { display: block; font-size: 0.6rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; }

.tier-features {
  list-style: none;
  padding: 0;
  margin: 0 0 24px;
  flex: 1;
}
.tier-features li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-sm);
  color: var(--text-secondary);
  padding: 4px 0;
}
.feat-check { color: #22c55e; font-weight: 700; font-size: 0.75rem; width: 16px; text-align: center; flex-shrink: 0; }
.feat-check.ent { color: #f59e0b; }
.feat-disabled { opacity: 0.4; }
.feat-dash { color: var(--text-muted); font-size: 0.75rem; width: 16px; text-align: center; flex-shrink: 0; }

.btn-enterprise {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white;
  border: none;
  font-weight: 700;
}
.btn-enterprise:hover { box-shadow: 0 4px 16px rgba(245, 158, 11, 0.3); transform: translateY(-1px); }

/* ── Annual Toggle ── */
.billing-toggle {
  display: flex; align-items: center; justify-content: center;
  gap: 12px; font-size: var(--font-sm); color: var(--text-muted);
}
.billing-toggle .active { color: var(--text-primary); font-weight: 600; }
.toggle-switch {
  width: 44px; height: 24px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  position: relative; cursor: pointer;
  transition: all var(--transition-fast);
}
.toggle-switch.on { background: var(--text-primary); border-color: var(--text-primary); }
.toggle-knob {
  position: absolute; top: 2px; left: 2px;
  width: 18px; height: 18px;
  background: #fff; border-radius: 50%;
  transition: all var(--transition-fast);
}
.toggle-switch.on .toggle-knob { left: 22px; }
.save-badge {
  background: var(--color-success-bg); color: var(--color-success);
  font-size: var(--font-xs); font-weight: 700;
  padding: 2px 8px; border-radius: var(--radius-full); margin-left: 4px;
}

/* ═══════════════════════════════════════
   Feature Table
   ═══════════════════════════════════════ */
.feature-table { width: 100%; border-collapse: collapse; font-size: var(--font-sm); }
.feature-table th, .feature-table td { padding: 10px 16px; border-bottom: 1px solid var(--border-color); text-align: left; }
.feature-table th { font-size: var(--font-xs); font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }
.feature-table .text-center { text-align: center; }
.section-row td { font-weight: 700; font-size: var(--font-sm); color: var(--text-primary); padding-top: 20px; border-bottom: 2px solid var(--border-color); }
.highlight-col { background: rgba(245, 158, 11, 0.04); }
.check-icon { color: var(--color-success); font-weight: 700; }
.dash-icon { color: var(--text-muted); opacity: 0.3; }

/* ── Usage & Invoices ── */
.billing-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.usage-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.usage-item { padding: 14px; background: var(--bg-surface); border-radius: var(--radius-md); }
.usage-label { font-size: var(--font-xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
.usage-value { font-size: var(--font-lg); font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }
.usage-bar { width: 100%; height: 4px; background: var(--bg-input); border-radius: var(--radius-full); overflow: hidden; }
.usage-fill { height: 100%; background: var(--color-success); border-radius: var(--radius-full); }

/* ── Subscription ── */
.subscription-info { padding: 4px 0; }
.sub-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--border-color); }
.sub-row:last-of-type { border-bottom: none; }

@media (max-width: 768px) {
  .pricing-pair { grid-template-columns: 1fr; }
  .billing-row { grid-template-columns: 1fr; }
}
</style>
