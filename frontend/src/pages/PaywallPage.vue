<template>
  <div class="paywall-page">
    <div class="paywall-container">
      <header class="paywall-header">
        <h1 class="paywall-title">Choose your plan</h1>
        <p class="paywall-sub">
          Pick a plan to start running AI visibility audits. You can change or cancel any time.
        </p>

        <div class="billing-toggle">
          <button
            type="button"
            class="toggle-btn"
            :class="{ active: !annual }"
            @click="annual = false"
          >Monthly</button>
          <button
            type="button"
            class="toggle-btn"
            :class="{ active: annual }"
            @click="annual = true"
          >Annual <span class="save-badge">Save ~17%</span></button>
        </div>
      </header>

      <section class="tier-grid">
        <article
          v-for="tier in TIERS"
          :key="tier.id"
          class="tier-card"
          :class="{ 'tier-highlight': tier.highlight }"
        >
          <div v-if="tier.highlight" class="tier-badge">Most popular</div>

          <div class="tier-head">
            <h2 class="tier-name">{{ tier.name }}</h2>
            <p class="tier-desc">{{ tier.description }}</p>
          </div>

          <div class="tier-price">
            <span class="price-amount">{{ priceLabel(tier) }}</span>
            <span class="price-period" v-if="tier.price !== null">{{ annual ? '/year' : tier.period }}</span>
          </div>
          <div class="price-note" v-if="tier.price !== null && annual">
            Billed ${{ tier.price * 10 }}/year · ~17% savings
          </div>
          <div class="price-note" v-else-if="tier.price === null">
            Based on team size and requirements
          </div>

          <ul class="tier-features">
            <li v-for="f in tier.features" :key="f">
              <span class="check">✓</span>{{ f }}
            </li>
          </ul>

          <button
            type="button"
            class="tier-cta"
            :class="{ 'cta-primary': tier.highlight, 'cta-secondary': !tier.highlight }"
            :disabled="loadingPlan === tier.id"
            @click="selectTier(tier)"
          >
            <span v-if="loadingPlan === tier.id">Starting checkout…</span>
            <span v-else>{{ tier.cta }}</span>
          </button>
        </article>
      </section>

      <footer class="paywall-footer">
        <p v-if="error" class="error">{{ error }}</p>
        <p class="signout-hint">
          Wrong account?
          <a href="#" @click.prevent="signOut">Sign out</a>
        </p>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import billingApi from '@/api/billing'
import { useAuthStore } from '@/stores/auth'
import { TIERS } from '@/constants/pricing'

const router = useRouter()
const authStore = useAuthStore()

const annual = ref(false)
const loadingPlan = ref(null)
const error = ref('')

function priceLabel(tier) {
  if (tier.price === null) return tier.priceLabel
  if (annual.value) return `$${tier.price * 10}`
  return tier.priceLabel
}

async function selectTier(tier) {
  error.value = ''
  if (tier.planCode === 'enterprise') {
    window.location.href = tier.contactTarget
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
  await authStore.logout()
  router.replace('/login')
}
</script>

<style scoped>
.paywall-page {
  min-height: 100vh;
  background: var(--bg-primary, #0b0d12);
  padding: 48px 20px;
  display: flex;
  justify-content: center;
}

.paywall-container {
  width: 100%;
  max-width: 1120px;
}

.paywall-header {
  text-align: center;
  margin-bottom: 40px;
}

.paywall-title {
  font-family: var(--font-display);
  font-size: 2.5rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0 0 12px;
}

.paywall-sub {
  color: var(--text-muted);
  font-size: 1.05rem;
  margin: 0 auto 28px;
  max-width: 640px;
}

.billing-toggle {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  background: var(--bg-surface, #15181f);
  border-radius: 10px;
}

.toggle-btn {
  padding: 8px 18px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 0.95rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
}

.toggle-btn.active {
  background: var(--bg-primary-hover, #1f232c);
  color: var(--text-primary);
}

.save-badge {
  font-size: 0.75rem;
  color: var(--color-success, #22c55e);
  margin-left: 4px;
}

.tier-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.tier-card {
  position: relative;
  background: var(--bg-surface, #15181f);
  border: 1px solid var(--border-subtle, #2a2f3a);
  border-radius: 14px;
  padding: 28px;
  display: flex;
  flex-direction: column;
}

.tier-highlight {
  border-color: var(--color-primary, #6366f1);
  box-shadow: 0 0 0 1px var(--color-primary, #6366f1);
}

.tier-badge {
  position: absolute;
  top: -10px;
  left: 24px;
  background: var(--color-primary, #6366f1);
  color: white;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 4px 10px;
  border-radius: 999px;
}

.tier-head { margin-bottom: 20px; }

.tier-name {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 6px;
}

.tier-desc {
  color: var(--text-muted);
  font-size: 0.9rem;
  margin: 0;
  line-height: 1.45;
}

.tier-price {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 4px;
}

.price-amount {
  font-family: var(--font-display);
  font-size: 2.5rem;
  font-weight: 800;
  color: var(--text-primary);
}

.price-period {
  font-size: 0.9rem;
  color: var(--text-muted);
}

.price-note {
  font-size: 0.75rem;
  color: var(--color-success, #22c55e);
  margin-bottom: 20px;
  min-height: 1em;
}

.tier-features {
  list-style: none;
  padding: 0;
  margin: 0 0 24px;
  flex: 1;
}

.tier-features li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  color: var(--text-primary);
  font-size: 0.92rem;
}

.check {
  display: inline-flex;
  width: 18px;
  height: 18px;
  align-items: center;
  justify-content: center;
  color: var(--color-success, #22c55e);
  font-weight: 700;
}

.tier-cta {
  width: 100%;
  padding: 12px 16px;
  border-radius: 10px;
  border: none;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.tier-cta:disabled { opacity: 0.6; cursor: wait; }

.cta-primary {
  background: var(--color-primary, #6366f1);
  color: white;
}

.cta-secondary {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-subtle, #2a2f3a);
}

.paywall-footer {
  text-align: center;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.error {
  color: var(--color-danger, #ef4444);
  margin-bottom: 8px;
}

.signout-hint a {
  color: var(--color-primary, #6366f1);
  text-decoration: underline;
}
</style>
