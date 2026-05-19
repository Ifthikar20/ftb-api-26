<template>
  <div class="bp fade-in">
    <header class="bp-header">
      <h1 class="bp-title">Plans &amp; Billing</h1>
      <p class="bp-sub">Manage your plan, billing cycle, and payment history.</p>
    </header>

    <div v-if="loading" class="bp-loading">Loading…</div>

    <template v-else>
      <!-- ── Current plan banner ─────────────────────────────────── -->
      <section v-if="currentPlanCode" class="bp-current">
        <div class="bp-current-info">
          <span class="bp-eyebrow">Current plan</span>
          <h2 class="bp-current-name">
            {{ currentTier?.name || currentPlanCode }}
            <span class="bp-current-price">
              · {{ currentPriceLabel }}<span class="bp-current-period">{{ currentPeriodLabel }}</span>
            </span>
          </h2>
          <div class="bp-current-meta">
            <span class="bp-pill" :class="statusClass">{{ statusLabel }}</span>
            <span
              v-if="subscription?.current_period_end"
              class="bp-current-note"
              :class="{ 'is-warn': subscription.cancel_at_period_end }"
            >
              {{ subscription.cancel_at_period_end ? 'Cancels' : 'Renews' }}
              {{ formatDate(subscription.current_period_end) }}
            </span>
            <span v-if="isMockSub" class="bp-pill bp-pill--neutral">Test mode</span>
          </div>
        </div>
        <div class="bp-current-actions">
          <button
            v-if="hasStripeSub"
            class="bp-btn bp-btn--ghost"
            :disabled="portalLoading"
            @click="openPortal"
          >{{ portalLoading ? 'Opening…' : 'Manage in Stripe' }}</button>
          <button
            v-if="subscription?.cancel_at_period_end"
            class="bp-btn bp-btn--primary"
            :disabled="cancelling"
            @click="resume"
          >{{ cancelling ? 'Working…' : 'Resume subscription' }}</button>
          <button
            v-else
            class="bp-btn bp-btn--ghost-danger"
            :disabled="cancelling"
            @click="confirmCancel"
          >{{ cancelling ? 'Working…' : 'Cancel subscription' }}</button>
        </div>
      </section>
      <section v-else class="bp-current bp-current--empty">
        <div class="bp-current-info">
          <span class="bp-eyebrow">No active plan</span>
          <h2 class="bp-current-name">You're not subscribed yet</h2>
          <p class="bp-current-note">Pick a plan below to unlock the full app.</p>
        </div>
      </section>

      <!-- ── At-a-glance row: next charge + payment method ────────── -->
      <div v-if="currentPlanCode" class="bp-glance">
        <div class="bp-glance-card">
          <span class="bp-eyebrow">Next charge</span>
          <div v-if="subscription?.cancel_at_period_end" class="bp-glance-value">—</div>
          <div v-else class="bp-glance-value">
            {{ currentPriceLabel }}
            <span class="bp-glance-period">{{ currentPeriodLabel }}</span>
          </div>
          <p class="bp-glance-note">
            <template v-if="subscription?.cancel_at_period_end">
              Access ends {{ formatDate(subscription.current_period_end) }}. No future charges.
            </template>
            <template v-else-if="subscription?.current_period_end">
              On {{ formatDate(subscription.current_period_end) }} · {{ daysUntilRenewal }} days from today
            </template>
            <template v-else>
              Renewal date will appear after the first invoice.
            </template>
          </p>
        </div>

        <div class="bp-glance-card">
          <span class="bp-eyebrow">Payment method</span>
          <div class="bp-glance-value">
            <template v-if="isMockSub">Test mode</template>
            <template v-else-if="hasStripeSub">On file with Stripe</template>
            <template v-else>—</template>
          </div>
          <p class="bp-glance-note">
            <template v-if="isMockSub">
              No real card is stored. This subscription was created in dev mode.
            </template>
            <template v-else-if="hasStripeSub">
              Card details live in Stripe. Use "Manage in Stripe" above to update.
            </template>
            <template v-else>
              Add a payment method by choosing a plan below.
            </template>
          </p>
        </div>
      </div>

      <!-- ── Pricing tiers (same shape as the paywall) ────────────── -->
      <div class="bp-toggle" role="tablist" aria-label="Billing cycle">
        <button
          type="button"
          class="bp-toggle-opt"
          :class="{ 'is-active': !annual }"
          @click="annual = false"
        >Monthly</button>
        <button
          type="button"
          class="bp-toggle-opt"
          :class="{ 'is-active': annual }"
          @click="annual = true"
        >
          Annual
          <span class="bp-toggle-save">Save 17%</span>
        </button>
      </div>

      <section class="bp-tiers">
        <article
          v-for="tier in mainTiers"
          :key="tier.id"
          class="bp-tier"
          :class="{
            'is-featured': tier.highlight,
            'is-current': isCurrent(tier),
          }"
        >
          <div v-if="isCurrent(tier)" class="bp-tier-pill">Active plan</div>
          <div v-else-if="tier.highlight" class="bp-tier-pill">Most popular</div>

          <div class="bp-tier-head">
            <h3 class="bp-tier-name">{{ tier.name }}</h3>
            <p class="bp-tier-desc">{{ tier.description }}</p>
          </div>

          <div class="bp-tier-price">
            <span class="bp-tier-amount">{{ priceLabel(tier) }}</span>
            <span class="bp-tier-period" v-if="tier.price !== null">
              {{ annual ? '/year' : tier.period }}
            </span>
          </div>
          <p class="bp-tier-note" v-if="tier.price !== null">
            {{ annual ? 'Two months free' : 'Cancel anytime' }}
          </p>

          <ul class="bp-tier-features">
            <li v-for="f in tier.features" :key="f">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 8.5l3.2 3 6.3-6.5"/>
              </svg>
              <span>{{ f }}</span>
            </li>
          </ul>

          <button
            v-if="isCurrent(tier)"
            class="bp-btn bp-btn--ghost"
            disabled
          >You're on this plan</button>
          <button
            v-else
            type="button"
            class="bp-btn"
            :class="{ 'bp-btn--primary': tier.highlight || !currentPlanCode }"
            :disabled="checkingOut === tier.id"
            @click="changePlan(tier)"
          >
            <span v-if="checkingOut === tier.id" class="bp-spinner" aria-hidden="true"></span>
            <span v-else>{{ currentPlanCode ? 'Switch to ' + tier.name : 'Choose ' + tier.name }}</span>
          </button>
        </article>
      </section>

      <p v-if="enterpriseTier" class="bp-enterprise">
        Need more? <a href="#" @click.prevent="contactEnterprise">Talk to us about {{ enterpriseTier.name }}</a>
      </p>

      <p v-if="error" class="bp-error">{{ error }}</p>

      <!-- ── Invoices ─────────────────────────────────────────────── -->
      <section v-if="invoices.length" class="bp-card">
        <header class="bp-card-head">
          <h3 class="bp-card-title">Invoices</h3>
        </header>
        <table class="bp-table">
          <thead>
            <tr><th>Date</th><th>Amount</th><th>Status</th></tr>
          </thead>
          <tbody>
            <tr v-for="inv in invoices" :key="inv.id || inv.stripe_invoice_id">
              <td>{{ formatDate(inv.period_start || inv.created_at) }}</td>
              <td class="bp-amount">${{ (inv.amount_paid / 100).toFixed(2) }}</td>
              <td>
                <span class="bp-pill" :class="inv.status === 'paid' ? 'bp-pill--success' : 'bp-pill--warn'">
                  {{ inv.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ── Usage ────────────────────────────────────────────────── -->
      <section v-if="usage.length" class="bp-card">
        <header class="bp-card-head">
          <h3 class="bp-card-title">Usage this period</h3>
        </header>
        <div class="bp-usage">
          <div v-for="u in usage" :key="u.metric" class="bp-usage-item">
            <div class="bp-usage-label">{{ formatMetric(u.metric) }}</div>
            <div class="bp-usage-value">{{ Number(u.count).toLocaleString() }}</div>
            <div class="bp-usage-bar">
              <div
                class="bp-usage-fill"
                :style="{ width: Math.min((u.count / (u.limit || 1)) * 100, 100) + '%' }"
              ></div>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import billingApi from '@/api/billing'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import { TIERS } from '@/constants/pricing'

const route = useRoute()
const toast = useToast()
const authStore = useAuthStore()

const loading = ref(true)
const subscription = ref(null)
const invoices = ref([])
const usage = ref([])
const annual = ref(false)
const checkingOut = ref(null)
const portalLoading = ref(false)
const cancelling = ref(false)
const error = ref('')

const mainTiers = computed(() => TIERS.filter(t => t.price !== null))
const enterpriseTier = computed(() => TIERS.find(t => t.price === null))

const currentPlanCode = computed(() => {
  const s = subscription.value
  const active = s?.subscription_status === 'active' || s?.subscription_status === 'trialing'
  if (!active) return null
  return s?.plan || s?.plan_code || null
})

const currentTier = computed(() =>
  TIERS.find(t => t.planCode === currentPlanCode.value) || null,
)

const statusClass = computed(() => {
  const s = subscription.value?.subscription_status
  if (s === 'active') return 'bp-pill--success'
  if (s === 'trialing') return 'bp-pill--neutral'
  if (s === 'past_due' || s === 'canceled') return 'bp-pill--danger'
  return 'bp-pill--neutral'
})

const hasStripeSub = computed(
  () => !!subscription.value?.stripe_subscription_id &&
        !String(subscription.value.stripe_subscription_id).startsWith('dev_'),
)

const isMockSub = computed(
  () => String(subscription.value?.stripe_subscription_id || '').startsWith('dev_sub_'),
)

// Infer whether the active subscription is annual from the period
// length. Stripe annual subs have a ~365d gap; monthly is ~30d. Used
// to render the right /year vs /month suffix without forcing the
// user to toggle the pill first.
const isAnnualSub = computed(() => {
  const sub = subscription.value
  if (!sub?.current_period_start || !sub?.current_period_end) return annual.value
  const ms = new Date(sub.current_period_end) - new Date(sub.current_period_start)
  return ms > 1000 * 60 * 60 * 24 * 60   // > 60 days  →  annual
})

const currentPriceLabel = computed(() => {
  const t = currentTier.value
  if (!t || t.price === null) return t?.priceLabel || '—'
  return isAnnualSub.value ? `$${t.price * 10}` : t.priceLabel
})

const currentPeriodLabel = computed(() => {
  const t = currentTier.value
  if (!t || t.price === null) return ''
  return isAnnualSub.value ? '/year' : t.period || '/month'
})

const statusLabel = computed(() => {
  const s = subscription.value?.subscription_status
  if (!s || s === 'none') return 'Inactive'
  const map = {
    active: 'Active',
    trialing: 'Trialing',
    past_due: 'Past due',
    canceled: 'Canceled',
    incomplete: 'Incomplete',
    incomplete_expired: 'Expired',
    unpaid: 'Unpaid',
  }
  return map[s] || s.replace(/_/g, ' ')
})

const daysUntilRenewal = computed(() => {
  const end = subscription.value?.current_period_end
  if (!end) return 0
  const diff = new Date(end) - new Date()
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)))
})

function isCurrent(tier) { return currentPlanCode.value === tier.planCode }

function priceLabel(tier) {
  if (!tier) return ''
  if (tier.price === null) return tier.priceLabel
  if (annual.value) return `$${tier.price * 10}`
  return tier.priceLabel
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
function formatMetric(m) {
  return (m || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

async function changePlan(tier) {
  error.value = ''
  checkingOut.value = tier.id
  try {
    // Dev path: instant subscription switch via the mock endpoint.
    // Falls back to real Stripe Checkout on 404 (prod).
    const res = await billingApi.devSubscribe({
      plan: tier.planCode,
      annual: annual.value,
    })
    if (res?.data?.success || res?.data?.data?.dev_mode) {
      toast.success(`Switched to ${tier.name}.`)
      await refresh()
      try { await authStore.fetchSession() } catch (_) {}
      return
    }
    error.value = "We couldn't switch plans. Please try again."
  } catch (e) {
    if (e?.response?.status === 404) {
      try {
        const res = await billingApi.checkout({
          plan: tier.planCode,
          annual: annual.value,
        })
        const url = res.data?.data?.checkout_url || res.data?.checkout_url
        if (url) {
          window.location.href = url
          return
        }
      } catch (e2) {
        error.value = e2?.response?.data?.error?.message || "We couldn't start checkout."
      }
    } else {
      error.value = e?.response?.data?.error?.message || "We couldn't switch plans."
    }
  } finally {
    checkingOut.value = null
  }
}

function contactEnterprise() {
  window.location.href = enterpriseTier.value?.contactTarget || 'mailto:sales@fetchbot.ai'
}

async function openPortal() {
  portalLoading.value = true
  try {
    const res = await billingApi.portal()
    const url = res.data?.data?.portal_url || res.data?.portal_url
    if (url) window.location.href = url
    else toast.error("We couldn't open the billing portal.")
  } catch {
    toast.error("We couldn't open the billing portal.")
  } finally {
    portalLoading.value = false
  }
}

async function confirmCancel() {
  const end = subscription.value?.current_period_end
  const tail = end ? ` Access continues until ${formatDate(end)}.` : ''
  if (!window.confirm(`Cancel your ${currentTier.value?.name || 'subscription'}?${tail}`)) return
  cancelling.value = true
  try {
    await billingApi.cancel()
    toast.success('Subscription will end at the period end.')
    await refresh()
  } catch (e) {
    toast.error(e?.response?.data?.error?.message || "We couldn't cancel.")
  } finally {
    cancelling.value = false
  }
}

async function resume() {
  cancelling.value = true
  try {
    await billingApi.resume()
    toast.success('Subscription resumed.')
    await refresh()
  } catch (e) {
    toast.error(e?.response?.data?.error?.message || "We couldn't resume.")
  } finally {
    cancelling.value = false
  }
}

async function refresh() {
  try {
    const [subRes, invRes, usageRes] = await Promise.all([
      billingApi.getCurrent().catch(() => ({ data: null })),
      billingApi.invoices().catch(() => ({ data: [] })),
      billingApi.usage().catch(() => ({ data: [] })),
    ])
    subscription.value = subRes.data?.data || subRes.data || null
    const inv = invRes.data?.data || invRes.data || []
    invoices.value = Array.isArray(inv) ? inv : (inv.results || [])
    const u = usageRes.data?.data || usageRes.data || []
    usage.value = Array.isArray(u) ? u : (u.results || [])
  } catch (_) {
    // soft-fail; the UI degrades to "no active plan" state
  }
}

onMounted(async () => {
  const checkoutParam = route.query.checkout
  if (checkoutParam === 'success') toast.success('Subscription activated!')
  else if (checkoutParam === 'canceled') toast.info('Checkout canceled.')
  await refresh()
  loading.value = false
})
</script>

<style scoped>
.bp {
  --bp-fg: #0a0a0a;
  --bp-muted: #6b6b6b;
  --bp-border: rgba(10, 10, 10, 0.10);
  --bp-surface: #fafafa;
  --bp-bg: #ffffff;
  --bp-accent: #ff6a2c;
  --bp-accent-soft: rgba(255, 106, 44, 0.10);
  --bp-spring: cubic-bezier(0.22, 1, 0.36, 1);

  max-width: 1080px;
  margin: 0 auto;
  padding: 32px 24px 96px;
  color: var(--bp-fg);
  font-feature-settings: 'cv11', 'ss01';
}

[data-theme='dark'] .bp {
  --bp-fg: #f7f7f7;
  --bp-muted: #888;
  --bp-border: rgba(255, 255, 255, 0.10);
  --bp-surface: #0e0e0e;
  --bp-bg: #060606;
  --bp-accent-soft: rgba(255, 106, 44, 0.14);
}

.bp-header { margin-bottom: 24px; }
.bp-title {
  font-size: clamp(28px, 3vw, 36px);
  font-weight: 600;
  letter-spacing: -0.02em;
  margin: 0 0 6px;
}
.bp-sub {
  margin: 0;
  color: var(--bp-muted);
  font-size: 14px;
}

.bp-loading {
  padding: 80px 0;
  text-align: center;
  color: var(--bp-muted);
}

/* ── Current-plan banner ──────────────────────────────────── */
.bp-current {
  margin-bottom: 28px;
  padding: 22px 26px;
  border-radius: 18px;
  background: var(--bp-surface);
  border: 1px solid var(--bp-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.bp-current--empty {
  border-style: dashed;
}
.bp-eyebrow {
  display: inline-block;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--bp-muted);
  margin-bottom: 6px;
}
.bp-current-name {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.015em;
}
.bp-current-info { display: flex; flex-direction: column; min-width: 0; }
.bp-current-actions { display: flex; gap: 8px; flex-shrink: 0; flex-wrap: wrap; justify-content: flex-end; }
.bp-current-price {
  font-size: 14px;
  font-weight: 500;
  color: var(--bp-muted);
  letter-spacing: 0;
}
.bp-current-period {
  font-size: 13px;
  color: var(--bp-muted);
  font-weight: 500;
}
.bp-current-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin: 0;
  font-size: 13px;
  color: var(--bp-muted);
}
.bp-current-note {
  font-size: 13px;
  color: var(--bp-muted);
  margin: 0;
}
.bp-current-note.is-warn {
  color: #b45309;
  font-weight: 500;
}

/* At-a-glance row: next charge + payment method. */
.bp-glance {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 28px;
}
.bp-glance-card {
  padding: 20px 22px;
  background: var(--bp-bg);
  border: 1px solid var(--bp-border);
  border-radius: 16px;
}
.bp-glance-value {
  margin: 4px 0 6px;
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.015em;
  font-variant-numeric: tabular-nums;
}
.bp-glance-period {
  font-size: 13px;
  color: var(--bp-muted);
  font-weight: 500;
}
.bp-glance-note {
  margin: 0;
  font-size: 12px;
  color: var(--bp-muted);
  line-height: 1.5;
}

.bp-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: capitalize;
  background: var(--bp-surface);
  border: 1px solid var(--bp-border);
}
.bp-pill--success { background: rgba(34, 197, 94, 0.10); color: #15803d; border-color: rgba(34, 197, 94, 0.30); }
.bp-pill--warn    { background: rgba(234, 179, 8, 0.12); color: #a16207; border-color: rgba(234, 179, 8, 0.30); }
.bp-pill--danger  { background: rgba(239, 68, 68, 0.10); color: #b91c1c; border-color: rgba(239, 68, 68, 0.30); }
.bp-pill--neutral { background: var(--bp-surface); color: var(--bp-muted); }

/* ── Pill toggle (mirrors paywall) ────────────────────────── */
.bp-toggle {
  display: inline-flex;
  align-items: center;
  padding: 4px;
  border-radius: 999px;
  background: var(--bp-surface);
  border: 1px solid var(--bp-border);
  margin: 0 0 20px;
  gap: 2px;
}
.bp-toggle-opt {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 18px;
  border: none;
  background: transparent;
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  color: var(--bp-muted);
  border-radius: 999px;
  cursor: pointer;
  transition: color 0.25s var(--bp-spring), background 0.25s var(--bp-spring);
}
.bp-toggle-opt.is-active {
  background: var(--bp-bg);
  color: var(--bp-fg);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}
.bp-toggle-save {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--bp-accent-soft);
  color: var(--bp-accent);
  font-weight: 600;
}

/* ── Tier cards ───────────────────────────────────────────── */
.bp-tiers {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin-bottom: 24px;
}
.bp-tier {
  position: relative;
  padding: 26px;
  background: var(--bp-bg);
  border: 1px solid var(--bp-border);
  border-radius: 22px;
  display: flex;
  flex-direction: column;
  transition: transform 0.25s var(--bp-spring), box-shadow 0.25s var(--bp-spring), border-color 0.25s var(--bp-spring);
}
.bp-tier:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.06), 0 4px 12px rgba(0, 0, 0, 0.04);
}
.bp-tier.is-featured {
  border-color: var(--bp-fg);
}
.bp-tier.is-current {
  border-color: var(--bp-accent);
  box-shadow: 0 0 0 1px var(--bp-accent), 0 18px 40px rgba(255, 106, 44, 0.08);
}
.bp-tier-pill {
  position: absolute;
  top: -10px;
  right: 20px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  border-radius: 999px;
  background: var(--bp-fg);
  color: var(--bp-bg);
}
.bp-tier.is-current .bp-tier-pill {
  background: var(--bp-accent);
  color: var(--bp-bg);
}
.bp-tier-head { margin-bottom: 18px; }
.bp-tier-name {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 600;
  letter-spacing: -0.015em;
}
.bp-tier-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--bp-muted);
}
.bp-tier-price {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 4px;
}
.bp-tier-amount {
  font-size: 34px;
  font-weight: 600;
  letter-spacing: -0.025em;
}
.bp-tier-period {
  font-size: 13px;
  color: var(--bp-muted);
  font-weight: 500;
}
.bp-tier-note {
  margin: 0 0 20px;
  font-size: 12px;
  color: var(--bp-muted);
}
.bp-tier-features {
  list-style: none;
  padding: 0;
  margin: 0 0 24px;
  display: flex;
  flex-direction: column;
  gap: 9px;
  flex-grow: 1;
}
.bp-tier-features li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  line-height: 1.45;
}
.bp-tier-features svg {
  flex-shrink: 0;
  margin-top: 3px;
  color: var(--bp-accent);
}

.bp-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 18px;
  border-radius: 12px;
  border: 1px solid var(--bp-border);
  background: var(--bp-bg);
  color: var(--bp-fg);
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.005em;
  cursor: pointer;
  transition: transform 0.2s var(--bp-spring), background 0.25s var(--bp-spring), color 0.25s, border-color 0.25s;
}
.bp-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: var(--bp-fg);
}
.bp-btn--primary {
  background: var(--bp-fg);
  color: var(--bp-bg);
  border-color: var(--bp-fg);
}
.bp-btn--primary:hover:not(:disabled) {
  background: var(--bp-accent);
  border-color: var(--bp-accent);
}
.bp-btn--ghost {
  background: transparent;
}
.bp-btn--ghost-danger {
  background: transparent;
  color: #b91c1c;
  border-color: rgba(239, 68, 68, 0.25);
}
.bp-btn--ghost-danger:hover:not(:disabled) {
  border-color: #b91c1c;
  background: rgba(239, 68, 68, 0.06);
  transform: translateY(-1px);
}
.bp-btn:disabled { opacity: 0.55; cursor: not-allowed; }

.bp-spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid currentColor;
  border-right-color: transparent;
  animation: bp-spin 0.7s linear infinite;
}
@keyframes bp-spin { to { transform: rotate(360deg); } }

.bp-enterprise {
  margin: 0 0 28px;
  font-size: 14px;
  color: var(--bp-muted);
}
.bp-enterprise a {
  color: var(--bp-fg);
  font-weight: 500;
  text-decoration: none;
  border-bottom: 1px solid var(--bp-border);
  transition: border-color 0.2s;
}
.bp-enterprise a:hover { border-color: var(--bp-accent); }
.bp-error { margin: 0 0 16px; color: var(--bp-accent); font-size: 13px; }

/* ── Invoices / usage cards ───────────────────────────────── */
.bp-card {
  margin-top: 16px;
  padding: 22px 26px;
  background: var(--bp-bg);
  border: 1px solid var(--bp-border);
  border-radius: 18px;
}
.bp-card-head { margin-bottom: 14px; }
.bp-card-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.005em;
}

.bp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.bp-table th,
.bp-table td {
  text-align: left;
  padding: 12px 8px;
  border-bottom: 1px solid var(--bp-border);
}
.bp-table th {
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--bp-muted);
  border-bottom: 1px solid var(--bp-border);
}
.bp-table tbody tr:last-child td { border-bottom: none; }
.bp-amount { font-variant-numeric: tabular-nums; font-weight: 600; }

.bp-usage {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 18px;
}
.bp-usage-item { display: flex; flex-direction: column; gap: 6px; }
.bp-usage-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--bp-muted);
  font-weight: 600;
}
.bp-usage-value {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.015em;
  font-variant-numeric: tabular-nums;
}
.bp-usage-bar {
  width: 100%;
  height: 4px;
  border-radius: 999px;
  background: var(--bp-surface);
  border: 1px solid var(--bp-border);
  overflow: hidden;
}
.bp-usage-fill {
  height: 100%;
  background: var(--bp-accent);
  transition: width 0.4s var(--bp-spring);
}

@media (max-width: 720px) {
  .bp { padding: 18px 16px 64px; }
  .bp-current {
    flex-direction: column;
    align-items: flex-start;
  }
  .bp-current-actions { width: 100%; justify-content: flex-start; }
  .bp-glance { grid-template-columns: 1fr; }
  .bp-tiers { grid-template-columns: 1fr; }
}
</style>
