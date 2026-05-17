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
      <div class="pw-stagger">
        <span class="pw-eyebrow">Choose your plan</span>
        <h1 class="pw-title">Get serious about how AI sees you.</h1>
        <p class="pw-sub">
          Run weekly audits across every major LLM. See what they say about you,
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
              :disabled="loadingPlan === tier.id"
              @click="selectTier(tier)"
            >
              <span v-if="loadingPlan === tier.id" class="pw-spinner" aria-hidden="true"></span>
              <span v-else>{{ tier.cta }}</span>
            </button>
          </article>
        </section>

        <p v-if="enterpriseTier" class="pw-enterprise">
          Need more? <a href="#" @click.prevent="selectTier(enterpriseTier)">Talk to us about {{ enterpriseTier.name }}</a>
        </p>

        <p v-if="error" class="pw-error">{{ error }}</p>

        <p class="pw-fineprint">
          Secure checkout via Stripe. Change or cancel any time. No charges
          until you confirm a plan.
        </p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import billingApi from '@/api/billing'
import { useAuthStore } from '@/stores/auth'
import { TIERS } from '@/constants/pricing'

const router = useRouter()
const authStore = useAuthStore()

const annual = ref(false)
const loadingPlan = ref(null)
const error = ref('')

// Split tiers: paying ones go in the grid, enterprise gets a softer
// link below so the upgrade UI stays focused on the two real CTAs.
const mainTiers = computed(() => TIERS.filter(t => t.price !== null))
const enterpriseTier = computed(() => TIERS.find(t => t.price === null))

function priceLabel(tier) {
  if (tier.price === null) return tier.priceLabel
  if (annual.value) return `$${tier.price * 10}`
  return tier.priceLabel
}

async function selectTier(tier) {
  error.value = ''
  if (tier.planCode === 'enterprise') {
    window.location.href = tier.contactTarget || 'mailto:sales@fetchbot.ai'
    return
  }
  loadingPlan.value = tier.id
  try {
    const res = await billingApi.checkout({ plan: tier.planCode, annual: annual.value })
    const url = res.data?.data?.checkout_url || res.data?.checkout_url
    if (url) {
      window.location.href = url
    } else {
      error.value = "We couldn't start checkout. Please try again."
    }
  } catch (e) {
    error.value = e.response?.data?.error?.message || "We couldn't start checkout. Please try again."
  } finally {
    loadingPlan.value = null
  }
}

async function signOut() {
  try {
    await authStore.logout()
  } catch (_) {
    // ignore — we redirect regardless
  }
  router.replace('/login')
}
</script>

<style scoped>
/* ── Palette ──────────────────────────────────────────────
   Mirrors OnboardingModal so the unpaid->onboarded->app flow
   feels like one continuous canvas. */
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

/* Soft orange ambient glow tucked behind the content. */
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

/* ── Top bar ─────────────────────────────────────────────── */
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
  letter-spacing: -0.01em;
  font-size: 16px;
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

/* ── Main column ─────────────────────────────────────────── */
.pw-main {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 24px 24px 96px;
}
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

/* ── Pill toggle ─────────────────────────────────────────── */
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

/* ── Tier grid ───────────────────────────────────────────── */
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
.pw-tier-cta:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: var(--pw-fg);
}
.pw-tier-cta.is-primary {
  background: var(--pw-fg);
  color: var(--pw-bg);
  border-color: var(--pw-fg);
}
.pw-tier-cta.is-primary:hover:not(:disabled) {
  background: var(--pw-accent);
  border-color: var(--pw-accent);
}
.pw-tier-cta:active:not(:disabled) { transform: translateY(0) scale(0.99); }
.pw-tier-cta:disabled { opacity: 0.55; cursor: not-allowed; }

.pw-spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid currentColor;
  border-right-color: transparent;
  animation: pw-spin 0.7s linear infinite;
}
@keyframes pw-spin { to { transform: rotate(360deg); } }

/* ── Enterprise & fineprint ──────────────────────────────── */
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

.pw-error {
  margin: 0 0 12px;
  color: var(--pw-accent);
  font-size: 13px;
}

.pw-fineprint {
  margin: 0 auto;
  max-width: 480px;
  font-size: 12px;
  color: var(--pw-muted);
  line-height: 1.5;
}

@media (max-width: 760px) {
  .pw-top { padding: 22px 22px; }
  .pw-main { padding: 16px 18px 64px; }
  .pw-tiers {
    grid-template-columns: 1fr;
    gap: 14px;
  }
  .pw-title { font-size: clamp(28px, 7vw, 36px); }
}
</style>
