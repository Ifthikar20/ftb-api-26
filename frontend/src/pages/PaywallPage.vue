<template>
  <div class="pw">
    <div class="pw-glow" aria-hidden="true"></div>

    <header class="pw-top">
      <div class="pw-brand">
        <span class="pw-brand-dot"></span>
        FetchBot
      </div>
      <button type="button" class="pw-signout" @click.prevent="signOut">Sign out</button>
    </header>

    <main class="pw-main">
      <Transition name="pw-fade" mode="out-in">
        <!-- ── Phase 1: pick a tier ──────────────────────────── -->
        <div v-if="phase === 'select'" key="select" class="pw-stagger">
          <span class="pw-eyebrow">Choose your plan</span>
          <h1 class="pw-title">Get serious about how AI sees you.</h1>
          <p class="pw-sub">
            Weekly audits across every major LLM. See what they say about you,
            who they recommend instead, and how to win.
          </p>

          <div class="pw-toggle" role="tablist" aria-label="Billing cycle">
            <button
              type="button"
              class="pw-toggle-opt"
              :class="{ 'is-active': !annual }"
              :aria-selected="!annual"
              @click="annual = false"
            >Monthly</button>
            <button
              type="button"
              class="pw-toggle-opt"
              :class="{ 'is-active': annual }"
              :aria-selected="annual"
              @click="annual = true"
            >
              Annual
              <span class="pw-toggle-save">Save 17%</span>
            </button>
          </div>

          <section class="pw-tiers">
            <article
              v-for="tier in mainTiers"
              :key="tier.id"
              class="pw-tier"
              :class="{ 'is-featured': tier.highlight }"
            >
              <div v-if="tier.highlight" class="pw-tier-pill">Most popular</div>

              <div class="pw-tier-head">
                <h2 class="pw-tier-name">{{ tier.name }}</h2>
                <p class="pw-tier-desc">{{ tier.description }}</p>
              </div>

              <div class="pw-tier-price">
                <span class="pw-tier-amount">{{ priceLabel(tier) }}</span>
                <span class="pw-tier-period" v-if="tier.price !== null">
                  {{ annual ? '/year' : tier.period }}
                </span>
              </div>
              <p class="pw-tier-note" v-if="tier.price !== null && annual">
                Two months free
              </p>
              <p class="pw-tier-note" v-else-if="tier.price !== null && !annual">
                Cancel anytime
              </p>

              <ul class="pw-tier-features">
                <li v-for="f in tier.features" :key="f">
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 8.5l3.2 3 6.3-6.5"/>
                  </svg>
                  <span>{{ f }}</span>
                </li>
              </ul>

              <button
                type="button"
                class="pw-tier-cta"
                :class="{ 'is-primary': tier.highlight }"
                @click="goToCheckout(tier)"
              >Continue with {{ tier.name }}</button>
            </article>
          </section>

          <p v-if="enterpriseTier" class="pw-enterprise">
            Need more? <a href="#" @click.prevent="contactSales">Talk to us about {{ enterpriseTier.name }}</a>
          </p>

          <p class="pw-fineprint">
            Secure checkout. Change or cancel any time. No charges until you confirm a plan.
          </p>
        </div>

        <!-- ── Phase 2: inline card form ─────────────────────── -->
        <div v-else key="checkout" class="pw-checkout">
          <button type="button" class="pw-back" @click="phase = 'select'">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10 4l-4 4 4 4"/>
            </svg>
            <span>Back to plans</span>
          </button>

          <div class="pw-checkout-grid">
            <!-- Order summary -->
            <aside class="pw-summary">
              <span class="pw-eyebrow">Order summary</span>
              <h2 class="pw-summary-name">{{ selectedTier?.name }}</h2>
              <p class="pw-summary-desc">{{ selectedTier?.description }}</p>

              <div class="pw-summary-row">
                <span>{{ annual ? 'Annual subscription' : 'Monthly subscription' }}</span>
                <span class="pw-summary-amount">{{ priceLabel(selectedTier) }}</span>
              </div>
              <div v-if="annual && selectedTier?.price" class="pw-summary-row pw-summary-row--muted">
                <span>Two months free</span>
                <span>−${{ selectedTier.price * 2 }}</span>
              </div>
              <div class="pw-summary-row pw-summary-total">
                <span>Total due today</span>
                <span class="pw-summary-amount">{{ priceLabel(selectedTier) }}</span>
              </div>
              <p class="pw-summary-note">
                Renews {{ annual ? 'yearly' : 'monthly' }} at the same price.
                Cancel any time from Settings → Billing.
              </p>
            </aside>

            <!-- Card form -->
            <form class="pw-form" @submit.prevent="submitCheckout">
              <h2 class="pw-form-title">Payment details</h2>

              <label class="pw-field">
                <span class="pw-label">Cardholder name</span>
                <input
                  v-model="card.name"
                  type="text"
                  autocomplete="cc-name"
                  placeholder="Jane Appleseed"
                  required
                  class="pw-input"
                />
              </label>

              <label class="pw-field">
                <span class="pw-label">Card number</span>
                <input
                  v-model="card.number"
                  type="text"
                  inputmode="numeric"
                  autocomplete="cc-number"
                  placeholder="4242 4242 4242 4242"
                  maxlength="23"
                  required
                  class="pw-input"
                  @input="formatCardNumber"
                />
              </label>

              <div class="pw-row">
                <label class="pw-field">
                  <span class="pw-label">Expiry</span>
                  <input
                    v-model="card.expiry"
                    type="text"
                    inputmode="numeric"
                    autocomplete="cc-exp"
                    placeholder="MM/YY"
                    maxlength="5"
                    required
                    class="pw-input"
                    @input="formatExpiry"
                  />
                </label>
                <label class="pw-field">
                  <span class="pw-label">CVC</span>
                  <input
                    v-model="card.cvc"
                    type="text"
                    inputmode="numeric"
                    autocomplete="cc-csc"
                    placeholder="123"
                    maxlength="4"
                    required
                    class="pw-input"
                  />
                </label>
                <label class="pw-field">
                  <span class="pw-label">ZIP</span>
                  <input
                    v-model="card.zip"
                    type="text"
                    autocomplete="postal-code"
                    placeholder="94103"
                    maxlength="10"
                    required
                    class="pw-input"
                  />
                </label>
              </div>

              <button
                type="submit"
                class="pw-submit"
                :disabled="submitting"
              >
                <span v-if="submitting" class="pw-spinner" aria-hidden="true"></span>
                <span v-else>Pay {{ priceLabel(selectedTier) }} & continue</span>
              </button>

              <p v-if="error" class="pw-error">{{ error }}</p>

              <p class="pw-form-fineprint">
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <rect x="3" y="7" width="10" height="7" rx="1.5"/>
                  <path d="M5 7V5a3 3 0 016 0v2"/>
                </svg>
                Encrypted in transit. We never store your full card number.
              </p>
            </form>
          </div>
        </div>
      </Transition>
    </main>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import billingApi from '@/api/billing'
import { useAuthStore } from '@/stores/auth'
import { TIERS } from '@/constants/pricing'

const router = useRouter()
const authStore = useAuthStore()

const phase = ref('select')        // 'select' | 'checkout'
const annual = ref(false)
const selectedTier = ref(null)
const submitting = ref(false)
const error = ref('')

const card = reactive({
  name: '',
  number: '',
  expiry: '',
  cvc: '',
  zip: '',
})

const mainTiers = computed(() => TIERS.filter(t => t.price !== null))
const enterpriseTier = computed(() => TIERS.find(t => t.price === null))

function priceLabel(tier) {
  if (!tier) return ''
  if (tier.price === null) return tier.priceLabel
  if (annual.value) return `$${tier.price * 10}`
  return tier.priceLabel
}

function goToCheckout(tier) {
  error.value = ''
  selectedTier.value = tier
  phase.value = 'checkout'
}

function contactSales() {
  const t = enterpriseTier.value
  window.location.href = t?.contactTarget || 'mailto:sales@fetchbot.ai'
}

// Visual-only formatters. The form accepts dummy data — the backend
// dev endpoint doesn't validate the card. These just keep the input
// readable as the user types.
function formatCardNumber(e) {
  const raw = e.target.value.replace(/\D/g, '').slice(0, 19)
  card.number = raw.replace(/(.{4})/g, '$1 ').trim()
}
function formatExpiry(e) {
  const raw = e.target.value.replace(/\D/g, '').slice(0, 4)
  card.expiry = raw.length > 2 ? `${raw.slice(0, 2)}/${raw.slice(2)}` : raw
}

async function submitCheckout() {
  if (!selectedTier.value) return
  submitting.value = true
  error.value = ''
  try {
    // Dev / demo path: hits the mock endpoint, which marks the
    // subscription ACTIVE without calling Stripe. Any card values
    // are accepted. Falls back to the real Stripe checkout when the
    // dev endpoint is disabled (prod) — see the 404 branch.
    const res = await billingApi.devSubscribe({
      plan: selectedTier.value.planCode,
      annual: annual.value,
    })
    if (res?.data?.success || res?.data?.data?.dev_mode) {
      await authStore.fetchSession()
      router.replace('/dashboard')
      return
    }
    error.value = "We couldn't complete checkout. Please try again."
  } catch (e) {
    if (e?.response?.status === 404) {
      // Dev endpoint isn't enabled — fall back to real Stripe.
      try {
        const res = await billingApi.checkout({
          plan: selectedTier.value.planCode,
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
      error.value = e?.response?.data?.error?.message || "We couldn't complete checkout."
    }
  } finally {
    submitting.value = false
  }
}

async function signOut() {
  try { await authStore.logout() } catch (_) {}
  router.replace('/login')
}
</script>

<style scoped>
.pw {
  --pw-bg: #ffffff;
  --pw-fg: #0a0a0a;
  --pw-muted: #6b6b6b;
  --pw-border: rgba(10, 10, 10, 0.10);
  --pw-surface: #fafafa;
  --pw-accent: #ff6a2c;
  --pw-accent-soft: rgba(255, 106, 44, 0.10);
  --pw-spring: cubic-bezier(0.22, 1, 0.36, 1);
  --pw-spring-strong: cubic-bezier(0.16, 1, 0.3, 1);

  position: relative;
  min-height: 100vh;
  background: var(--pw-bg);
  color: var(--pw-fg);
  font-feature-settings: 'cv11', 'ss01';
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
}

[data-theme='dark'] .pw {
  --pw-bg: #060606;
  --pw-fg: #f7f7f7;
  --pw-muted: #888;
  --pw-border: rgba(255, 255, 255, 0.10);
  --pw-surface: #0e0e0e;
  --pw-accent-soft: rgba(255, 106, 44, 0.14);
}

.pw-glow {
  position: fixed;
  top: 30%;
  left: 50%;
  width: 720px;
  height: 720px;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle, var(--pw-accent-soft) 0%, transparent 60%);
  filter: blur(40px);
  pointer-events: none;
  opacity: 0.85;
  z-index: 0;
}

.pw-top {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28px 40px;
}
.pw-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: 16px;
  letter-spacing: -0.01em;
}
.pw-brand-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--pw-accent);
  box-shadow: 0 0 0 4px var(--pw-accent-soft);
}
.pw-signout {
  background: transparent;
  border: none;
  font: inherit;
  color: var(--pw-muted);
  font-size: 13px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 8px;
  transition: color 0.15s, background 0.15s;
}
.pw-signout:hover { color: var(--pw-fg); background: var(--pw-surface); }

.pw-main {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 24px 24px 96px;
}

/* ── Phase 1: tier selection ─────────────────────────────── */
.pw-stagger {
  width: 100%;
  max-width: 960px;
  text-align: center;
}
.pw-stagger > * {
  animation: pw-rise 0.6s var(--pw-spring-strong) both;
}
.pw-stagger > *:nth-child(2) { animation-delay: 0.05s; }
.pw-stagger > *:nth-child(3) { animation-delay: 0.10s; }
.pw-stagger > *:nth-child(4) { animation-delay: 0.15s; }
.pw-stagger > *:nth-child(5) { animation-delay: 0.20s; }
.pw-stagger > *:nth-child(6) { animation-delay: 0.25s; }
@keyframes pw-rise {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}

.pw-eyebrow {
  display: inline-block;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--pw-muted);
  margin-bottom: 14px;
}
.pw-title {
  font-size: clamp(32px, 4.5vw, 48px);
  line-height: 1.05;
  font-weight: 600;
  letter-spacing: -0.025em;
  margin: 0 0 14px;
}
.pw-sub {
  font-size: 16px;
  line-height: 1.55;
  color: var(--pw-muted);
  margin: 0 auto 32px;
  max-width: 540px;
}

.pw-toggle {
  display: inline-flex;
  align-items: center;
  padding: 4px;
  border-radius: 999px;
  background: var(--pw-surface);
  border: 1px solid var(--pw-border);
  margin: 0 auto 40px;
  gap: 2px;
}
.pw-toggle-opt {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 18px;
  border: none;
  background: transparent;
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  color: var(--pw-muted);
  border-radius: 999px;
  cursor: pointer;
  transition: color 0.25s var(--pw-spring), background 0.25s var(--pw-spring);
}
.pw-toggle-opt.is-active {
  background: var(--pw-bg);
  color: var(--pw-fg);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}
.pw-toggle-save {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--pw-accent-soft);
  color: var(--pw-accent);
  font-weight: 600;
}

.pw-tiers {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  text-align: left;
  margin-bottom: 28px;
}
.pw-tier {
  position: relative;
  padding: 28px;
  background: var(--pw-bg);
  border: 1px solid var(--pw-border);
  border-radius: 22px;
  display: flex;
  flex-direction: column;
  transition: transform 0.25s var(--pw-spring), box-shadow 0.25s var(--pw-spring), border-color 0.25s var(--pw-spring);
}
.pw-tier:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.06), 0 4px 12px rgba(0, 0, 0, 0.04);
}
.pw-tier.is-featured {
  border-color: var(--pw-fg);
  box-shadow: 0 20px 44px rgba(0, 0, 0, 0.10), 0 4px 12px rgba(0, 0, 0, 0.06);
}
.pw-tier-pill {
  position: absolute;
  top: -10px;
  right: 20px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  border-radius: 999px;
  background: var(--pw-fg);
  color: var(--pw-bg);
}
.pw-tier-head { margin-bottom: 20px; }
.pw-tier-name {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.015em;
}
.pw-tier-desc {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--pw-muted);
}
.pw-tier-price {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 4px;
}
.pw-tier-amount {
  font-size: 38px;
  font-weight: 600;
  letter-spacing: -0.025em;
}
.pw-tier-period {
  font-size: 14px;
  color: var(--pw-muted);
  font-weight: 500;
}
.pw-tier-note {
  margin: 0 0 22px;
  font-size: 12px;
  color: var(--pw-muted);
}
.pw-tier-features {
  list-style: none;
  padding: 0;
  margin: 0 0 28px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex-grow: 1;
}
.pw-tier-features li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 14px;
  line-height: 1.45;
  color: var(--pw-fg);
}
.pw-tier-features svg {
  flex-shrink: 0;
  margin-top: 3px;
  color: var(--pw-accent);
}
.pw-tier-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 13px 18px;
  border-radius: 12px;
  border: 1px solid var(--pw-border);
  background: var(--pw-bg);
  color: var(--pw-fg);
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.005em;
  cursor: pointer;
  transition: transform 0.2s var(--pw-spring), background 0.25s var(--pw-spring), color 0.25s var(--pw-spring), border-color 0.25s var(--pw-spring);
}
.pw-tier-cta:hover { transform: translateY(-1px); border-color: var(--pw-fg); }
.pw-tier-cta.is-primary {
  background: var(--pw-fg);
  color: var(--pw-bg);
  border-color: var(--pw-fg);
}
.pw-tier-cta.is-primary:hover { background: var(--pw-accent); border-color: var(--pw-accent); }

.pw-enterprise {
  margin: 0 0 16px;
  font-size: 14px;
  color: var(--pw-muted);
}
.pw-enterprise a {
  color: var(--pw-fg);
  font-weight: 500;
  text-decoration: none;
  border-bottom: 1px solid var(--pw-border);
  transition: border-color 0.2s;
}
.pw-enterprise a:hover { border-color: var(--pw-accent); }

.pw-fineprint {
  margin: 0 auto;
  max-width: 480px;
  font-size: 12px;
  color: var(--pw-muted);
  line-height: 1.5;
}

/* ── Phase 2: checkout panel ─────────────────────────────── */
.pw-checkout {
  width: 100%;
  max-width: 960px;
  animation: pw-rise 0.5s var(--pw-spring-strong) both;
}
.pw-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px 6px 6px;
  margin-bottom: 18px;
  background: transparent;
  border: none;
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  color: var(--pw-muted);
  border-radius: 8px;
  cursor: pointer;
  transition: color 0.15s, background 0.15s;
}
.pw-back:hover { color: var(--pw-fg); background: var(--pw-surface); }

.pw-checkout-grid {
  display: grid;
  grid-template-columns: 1fr 1.3fr;
  gap: 24px;
  align-items: start;
}

.pw-summary {
  padding: 28px;
  background: var(--pw-surface);
  border: 1px solid var(--pw-border);
  border-radius: 22px;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.pw-summary-name {
  margin: 4px 0 6px;
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.015em;
}
.pw-summary-desc {
  margin: 0 0 18px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--pw-muted);
}
.pw-summary-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 14px;
  padding: 10px 0;
  border-top: 1px solid var(--pw-border);
}
.pw-summary-row:first-of-type { border-top: none; }
.pw-summary-row--muted { color: var(--pw-muted); }
.pw-summary-total {
  font-weight: 600;
  font-size: 15px;
  padding-top: 16px;
  margin-top: 4px;
}
.pw-summary-amount {
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
}
.pw-summary-note {
  margin: 14px 0 0;
  font-size: 12px;
  color: var(--pw-muted);
  line-height: 1.5;
}

.pw-form {
  padding: 28px;
  background: var(--pw-bg);
  border: 1px solid var(--pw-border);
  border-radius: 22px;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 14px;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.04);
}
.pw-form-title {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.pw-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}
.pw-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--pw-muted);
}
.pw-input {
  border: 1px solid var(--pw-border);
  border-radius: 10px;
  padding: 12px 14px;
  font-size: 15px;
  color: var(--pw-fg);
  background: var(--pw-bg);
  outline: none;
  font-family: inherit;
  transition: border-color 0.2s var(--pw-spring), box-shadow 0.2s var(--pw-spring);
}
.pw-input:focus {
  border-color: var(--pw-accent);
  box-shadow: 0 0 0 3px var(--pw-accent-soft);
}
.pw-row { display: flex; gap: 10px; }

.pw-submit {
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 18px;
  border-radius: 12px;
  border: 1px solid var(--pw-fg);
  background: var(--pw-fg);
  color: var(--pw-bg);
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.005em;
  cursor: pointer;
  transition: transform 0.2s var(--pw-spring), background 0.25s var(--pw-spring), border-color 0.25s var(--pw-spring);
}
.pw-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  background: var(--pw-accent);
  border-color: var(--pw-accent);
}
.pw-submit:disabled { opacity: 0.6; cursor: not-allowed; }

.pw-spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid currentColor;
  border-right-color: transparent;
  animation: pw-spin 0.7s linear infinite;
}
@keyframes pw-spin { to { transform: rotate(360deg); } }

.pw-error {
  margin: 0;
  color: var(--pw-accent);
  font-size: 13px;
}
.pw-form-fineprint {
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--pw-muted);
}
.pw-form-fineprint svg { color: var(--pw-muted); }

/* ── Phase transition ────────────────────────────────────── */
.pw-fade-enter-active, .pw-fade-leave-active {
  transition: opacity 0.4s var(--pw-spring), transform 0.5s var(--pw-spring);
}
.pw-fade-enter-from { opacity: 0; transform: translateY(12px); }
.pw-fade-leave-to   { opacity: 0; transform: translateY(-12px); }

@media (max-width: 760px) {
  .pw-top { padding: 22px 22px; }
  .pw-main { padding: 16px 18px 64px; }
  .pw-tiers { grid-template-columns: 1fr; gap: 14px; }
  .pw-checkout-grid { grid-template-columns: 1fr; }
  .pw-title { font-size: clamp(28px, 7vw, 36px); }
}
</style>
