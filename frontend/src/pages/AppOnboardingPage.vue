<template>
  <div class="ob-shell" :data-step="step">
    <!-- Subtle ambient orange glow that drifts as steps advance -->
    <div class="ob-glow" aria-hidden="true"></div>

    <header class="ob-topbar">
      <div class="ob-brand">
        <span class="ob-brand-dot"></span>
        FetchBot
      </div>
      <div class="ob-progress">
        <span
          v-for="(s, i) in steps"
          :key="s.id"
          class="ob-progress-dot"
          :class="{ 'is-active': i === step, 'is-done': i < step }"
        />
      </div>
    </header>

    <main class="ob-main">
      <Transition name="ob-fade" mode="out-in">
        <!-- ── Step 0: URL ───────────────────────────────────────── -->
        <section v-if="step === 0" key="url" class="ob-step">
          <div class="ob-stagger">
            <span class="ob-eyebrow">Let's get you set up</span>
            <h1 class="ob-title">What's your website?</h1>
            <p class="ob-sub">
              We'll read your homepage, draft a description, and find the
              competitors you'll be measured against.
            </p>

            <div class="ob-input-wrap">
              <span class="ob-input-prefix">https://</span>
              <input
                ref="urlInputRef"
                v-model="urlInput"
                class="ob-input"
                placeholder="acme.com"
                @keydown.enter.prevent="startScan"
                :disabled="loading"
              />
              <button
                class="ob-cta"
                :disabled="loading || !urlInput.trim()"
                @click="startScan"
              >
                <span v-if="!loading">Continue</span>
                <span v-else class="ob-spinner" aria-hidden="true"></span>
                <svg v-if="!loading" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 8h10M9 4l4 4-4 4"/>
                </svg>
              </button>
            </div>

            <p v-if="error" class="ob-error">{{ error }}</p>

            <div class="ob-hints">
              <span>Press <kbd>Enter</kbd> to continue</span>
              <span class="ob-dot-sep">·</span>
              <span>No credit card required</span>
            </div>
          </div>
        </section>

        <!-- ── Step 1: Scanning ─────────────────────────────────── -->
        <section v-else-if="step === 1" key="scanning" class="ob-step">
          <div class="ob-stagger">
            <div class="ob-orbit" aria-hidden="true">
              <span class="ob-orbit-core"></span>
              <span class="ob-orbit-ring ob-orbit-r1"></span>
              <span class="ob-orbit-ring ob-orbit-r2"></span>
              <span class="ob-orbit-ring ob-orbit-r3"></span>
            </div>
            <h1 class="ob-title">Reading {{ urlHostname }}</h1>
            <p class="ob-sub">
              <Transition name="ob-text" mode="out-in">
                <span :key="scanLine">{{ scanLine }}</span>
              </Transition>
            </p>
          </div>
        </section>

        <!-- ── Step 2: Confirm description + business ──────────── -->
        <section v-else-if="step === 2" key="describe" class="ob-step ob-step-wide">
          <div class="ob-stagger">
            <span class="ob-eyebrow">Step 2 of 3 — about you</span>
            <h1 class="ob-title">Does this sound right?</h1>
            <p class="ob-sub">
              We pulled this from your homepage. Tweak anything that's off —
              the more accurate, the better the audit.
            </p>

            <div class="ob-card">
              <label class="ob-field">
                <span class="ob-label">Business name</span>
                <input v-model="form.business_name" class="ob-text-input" />
              </label>

              <label class="ob-field">
                <span class="ob-label">Industry</span>
                <input v-model="form.industry" class="ob-text-input" />
              </label>

              <label class="ob-field">
                <span class="ob-label">Description</span>
                <textarea
                  v-model="form.description"
                  rows="3"
                  maxlength="600"
                  class="ob-text-input ob-textarea"
                ></textarea>
                <span class="ob-counter">{{ form.description.length }}/600</span>
              </label>

              <div v-if="form.keywords.length" class="ob-field">
                <span class="ob-label">Topics we'll measure</span>
                <div class="ob-chips">
                  <span
                    v-for="(k, i) in form.keywords"
                    :key="k + i"
                    class="ob-chip"
                  >
                    {{ k }}
                    <button class="ob-chip-x" @click="removeKeyword(k)">×</button>
                  </span>
                </div>
              </div>
            </div>

            <div class="ob-step-actions">
              <button class="ob-link-btn" @click="back">Back</button>
              <button class="ob-cta" @click="step = 3">
                Continue
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 8h10M9 4l4 4-4 4"/>
                </svg>
              </button>
            </div>
          </div>
        </section>

        <!-- ── Step 3: Confirm competitors ───────────────────────── -->
        <section v-else-if="step === 3" key="competitors" class="ob-step ob-step-wide">
          <div class="ob-stagger">
            <span class="ob-eyebrow">Step 3 of 3 — competitors</span>
            <h1 class="ob-title">Who do you compete against?</h1>
            <p class="ob-sub">
              We found these from public sources. Pick the ones that
              actually show up next to you, or add your own.
            </p>

            <div class="ob-card">
              <div class="ob-comp-list">
                <label
                  v-for="c in form.competitors"
                  :key="c.domain || c.name"
                  class="ob-comp"
                  :class="{ 'is-selected': c.selected }"
                >
                  <input type="checkbox" v-model="c.selected" />
                  <span class="ob-comp-icon">{{ (c.name || '?')[0].toUpperCase() }}</span>
                  <span class="ob-comp-meta">
                    <span class="ob-comp-name">{{ c.name }}</span>
                    <span v-if="c.domain" class="ob-comp-domain">{{ c.domain }}</span>
                  </span>
                </label>
                <div v-if="!form.competitors.length" class="ob-comp-empty">
                  We couldn't find competitors automatically. Add some below.
                </div>
              </div>

              <div class="ob-comp-add">
                <input
                  v-model="newCompetitor"
                  class="ob-text-input"
                  placeholder="Name or domain (e.g. mixpanel.com)"
                  @keydown.enter.prevent="addCompetitor"
                />
                <button class="ob-link-btn" @click="addCompetitor">Add</button>
              </div>
            </div>

            <div class="ob-step-actions">
              <button class="ob-link-btn" @click="back">Back</button>
              <button class="ob-cta" :disabled="saving" @click="finish">
                <span v-if="!saving">Finish setup</span>
                <span v-else class="ob-spinner" aria-hidden="true"></span>
                <svg v-if="!saving" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 8h10M9 4l4 4-4 4"/>
                </svg>
              </button>
            </div>
          </div>
        </section>
      </Transition>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import onboardingApi from '@/api/onboarding'

const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const steps = Object.freeze([
  { id: 'url' }, { id: 'scanning' }, { id: 'describe' }, { id: 'competitors' },
])

const step = ref(0)
const urlInput = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref('')

const form = ref({
  url: '',
  business_name: '',
  industry: '',
  description: '',
  keywords: [],
  competitors: [],     // [{name, domain, selected}]
})

const urlInputRef = ref(null)
const newCompetitor = ref('')

const urlHostname = computed(() => {
  try {
    const raw = form.value.url || urlInput.value
    return new URL(raw.startsWith('http') ? raw : `https://${raw}`).hostname
  } catch (_) {
    return urlInput.value
  }
})

// ── Animated scan-status copy ─────────────────────────────────────
//
// The scan call is one HTTP request, but the user-perceived wait is
// a few seconds. Rotating short status lines makes the wait feel
// purposeful (similar to how Framer Sites shows "Reading layout /
// Extracting colors / Generating preview"). Lines are advisory —
// the scan API doesn't expose phase events, so we cycle on a timer.
const SCAN_LINES = [
  'Reading your homepage…',
  'Spotting products and features…',
  'Drafting a clean description…',
  'Searching the web for competitors…',
  'Wrapping up…',
]
const scanLine = ref(SCAN_LINES[0])
let scanLineTimer = null

function rotateScanLines() {
  let i = 0
  scanLine.value = SCAN_LINES[0]
  scanLineTimer = setInterval(() => {
    i = (i + 1) % SCAN_LINES.length
    scanLine.value = SCAN_LINES[i]
  }, 1700)
}
function stopScanLines() {
  if (scanLineTimer) {
    clearInterval(scanLineTimer)
    scanLineTimer = null
  }
}

// ── Actions ───────────────────────────────────────────────────────

async function startScan() {
  const raw = (urlInput.value || '').trim()
  if (!raw) return
  const url = raw.startsWith('http') ? raw : `https://${raw}`
  loading.value = true
  error.value = ''
  step.value = 1
  rotateScanLines()
  try {
    const { data } = await onboardingApi.scan(url)
    const payload = data?.data || data
    if (!payload?.success) {
      throw new Error(payload?.error || 'Could not read this site.')
    }
    form.value = {
      url: payload.url || url,
      business_name: payload.business_name || '',
      industry: payload.industry || '',
      description: payload.description_short || payload.description_raw || '',
      keywords: (payload.topics || []).slice(0, 8),
      competitors: (payload.competitors || []).map(c => ({
        name: c.name || '',
        domain: c.domain || '',
        selected: true,
      })),
    }
    step.value = 2
  } catch (e) {
    error.value = e.message || e.response?.data?.error?.message || 'Scan failed.'
    step.value = 0
    nextTick(() => urlInputRef.value?.focus())
  } finally {
    stopScanLines()
    loading.value = false
  }
}

function back() {
  if (step.value > 0) step.value -= 1
}

function removeKeyword(k) {
  form.value.keywords = form.value.keywords.filter(x => x !== k)
}

function addCompetitor() {
  const raw = newCompetitor.value.trim()
  if (!raw) return
  const isDomain = /^[a-z0-9.-]+\.[a-z]{2,}$/i.test(raw)
  form.value.competitors.push({
    name: isDomain ? raw.split('.')[0] : raw,
    domain: isDomain ? raw : '',
    selected: true,
  })
  newCompetitor.value = ''
}

async function finish() {
  saving.value = true
  try {
    const selected = form.value.competitors.filter(c => c.selected).map(c => ({
      name: c.name, domain: c.domain,
    }))
    await onboardingApi.save({
      url: form.value.url,
      business_name: form.value.business_name,
      industry: form.value.industry,
      description: form.value.description,
      keywords: form.value.keywords,
      competitors: selected,
    })
    // Refresh the auth session so the gate sees the next step
    // (paywall) instead of routing back to onboarding.
    await auth.fetchSession()
    const next = auth.session?.next_route
    if (next === 'paywall') {
      router.push('/paywall')
    } else {
      router.push('/dashboard')
    }
  } catch (e) {
    toast.error(e.response?.data?.error?.message || 'Could not save. Try again.')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  nextTick(() => urlInputRef.value?.focus?.())
})
</script>

<style scoped>
/* ── Palette ──────────────────────────────────────────────
   Mostly black / white with one accent — a deliberate orange
   that surfaces in CTAs, focus rings, and the ambient glow.
*/
.ob-shell {
  --ob-bg: #ffffff;
  --ob-fg: #0a0a0a;
  --ob-muted: #6b6b6b;
  --ob-border: rgba(10, 10, 10, 0.10);
  --ob-surface: #fafafa;
  --ob-accent: #ff6a2c;
  --ob-accent-soft: rgba(255, 106, 44, 0.10);
  --ob-spring: cubic-bezier(0.22, 1, 0.36, 1);
  --ob-spring-strong: cubic-bezier(0.16, 1, 0.3, 1);

  position: relative;
  min-height: 100vh;
  background: var(--ob-bg);
  color: var(--ob-fg);
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  font-feature-settings: 'cv11', 'ss01';
}

[data-theme='dark'] .ob-shell {
  --ob-bg: #060606;
  --ob-fg: #f7f7f7;
  --ob-muted: #888;
  --ob-border: rgba(255, 255, 255, 0.10);
  --ob-surface: #0e0e0e;
  --ob-accent-soft: rgba(255, 106, 44, 0.14);
}

/* Drifting glow — moves slightly per step so the screen feels alive. */
.ob-glow {
  position: fixed;
  top: 30%;
  left: 50%;
  width: 720px;
  height: 720px;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle, var(--ob-accent-soft) 0%, transparent 60%);
  filter: blur(40px);
  pointer-events: none;
  transition: transform 1.2s var(--ob-spring), opacity 0.8s ease;
  opacity: 0.85;
  z-index: 0;
}
.ob-shell[data-step='0'] .ob-glow { transform: translate(-50%, -50%) translateX(-12vw); }
.ob-shell[data-step='1'] .ob-glow { transform: translate(-50%, -50%) scale(1.15); opacity: 1; }
.ob-shell[data-step='2'] .ob-glow { transform: translate(-50%, -50%) translateX(10vw); }
.ob-shell[data-step='3'] .ob-glow { transform: translate(-50%, -50%) translateX(8vw) translateY(8vh); }

/* ── Top bar ─────────────────────────────────────────────── */
.ob-topbar {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28px 40px;
}
.ob-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  letter-spacing: -0.01em;
  font-size: 16px;
}
.ob-brand-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--ob-accent);
  box-shadow: 0 0 0 4px var(--ob-accent-soft);
}
.ob-progress { display: flex; gap: 6px; }
.ob-progress-dot {
  width: 22px;
  height: 4px;
  border-radius: 2px;
  background: var(--ob-border);
  transition: background 0.4s var(--ob-spring), width 0.5s var(--ob-spring);
}
.ob-progress-dot.is-done { background: var(--ob-fg); }
.ob-progress-dot.is-active { background: var(--ob-accent); width: 36px; }

/* ── Main column ─────────────────────────────────────────── */
.ob-main {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px 96px;
}
.ob-step {
  width: 100%;
  max-width: 540px;
  text-align: center;
}
.ob-step-wide { max-width: 640px; text-align: left; }

/* Stagger children with small per-child delays. */
.ob-stagger > * {
  animation: ob-rise 0.6s var(--ob-spring-strong) both;
}
.ob-stagger > *:nth-child(2) { animation-delay: 0.06s; }
.ob-stagger > *:nth-child(3) { animation-delay: 0.12s; }
.ob-stagger > *:nth-child(4) { animation-delay: 0.18s; }
.ob-stagger > *:nth-child(5) { animation-delay: 0.24s; }
.ob-stagger > *:nth-child(6) { animation-delay: 0.30s; }
@keyframes ob-rise {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}

.ob-eyebrow {
  display: inline-block;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ob-muted);
  margin-bottom: 16px;
}
.ob-title {
  font-size: clamp(34px, 5vw, 56px);
  line-height: 1.05;
  font-weight: 600;
  letter-spacing: -0.025em;
  margin: 0 0 14px;
}
.ob-sub {
  font-size: 17px;
  line-height: 1.55;
  color: var(--ob-muted);
  margin: 0 auto 32px;
  max-width: 480px;
}
.ob-step-wide .ob-sub { margin-left: 0; }

/* ── URL input row ───────────────────────────────────────── */
.ob-input-wrap {
  display: flex;
  align-items: center;
  gap: 0;
  background: var(--ob-bg);
  border: 1px solid var(--ob-border);
  border-radius: 999px;
  padding: 6px 6px 6px 22px;
  transition: border-color 0.25s var(--ob-spring), box-shadow 0.25s var(--ob-spring), transform 0.25s var(--ob-spring);
  margin: 0 auto;
  max-width: 500px;
}
.ob-input-wrap:focus-within {
  border-color: var(--ob-accent);
  box-shadow: 0 0 0 4px var(--ob-accent-soft);
  transform: translateY(-1px);
}
.ob-input-prefix {
  color: var(--ob-muted);
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 14px;
}
.ob-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  padding: 14px 12px;
  font-size: 16px;
  color: var(--ob-fg);
  font-family: inherit;
  min-width: 0;
}
.ob-cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border: none;
  border-radius: 999px;
  background: var(--ob-fg);
  color: var(--ob-bg);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.005em;
  cursor: pointer;
  transition: transform 0.2s var(--ob-spring), background 0.25s var(--ob-spring), opacity 0.2s;
}
.ob-cta:hover:not(:disabled) {
  transform: translateY(-1px);
  background: var(--ob-accent);
}
.ob-cta:active:not(:disabled) { transform: translateY(0) scale(0.98); }
.ob-cta:disabled { opacity: 0.5; cursor: not-allowed; }

.ob-error {
  margin-top: 14px;
  color: var(--ob-accent);
  font-size: 14px;
}
.ob-hints {
  margin-top: 24px;
  display: flex;
  justify-content: center;
  gap: 10px;
  font-size: 12px;
  color: var(--ob-muted);
}
.ob-hints kbd {
  font-family: 'SF Mono', monospace;
  font-size: 11px;
  border: 1px solid var(--ob-border);
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--ob-surface);
}
.ob-dot-sep { opacity: 0.5; }

/* ── Scanning orbit ──────────────────────────────────────── */
.ob-orbit {
  position: relative;
  width: 140px;
  height: 140px;
  margin: 0 auto 32px;
}
.ob-orbit-core {
  position: absolute;
  top: 50%; left: 50%;
  width: 18px; height: 18px;
  border-radius: 50%;
  background: var(--ob-accent);
  transform: translate(-50%, -50%);
  box-shadow: 0 0 24px var(--ob-accent);
  animation: ob-pulse 1.6s ease-in-out infinite;
}
.ob-orbit-ring {
  position: absolute;
  top: 50%; left: 50%;
  border-radius: 50%;
  border: 1px solid var(--ob-border);
  transform: translate(-50%, -50%);
}
.ob-orbit-r1 { width: 60px;  height: 60px;  animation: ob-spin 6s linear infinite; }
.ob-orbit-r2 { width: 100px; height: 100px; animation: ob-spin 9s linear reverse infinite; border-color: rgba(255,106,44,0.35); }
.ob-orbit-r3 { width: 140px; height: 140px; animation: ob-spin 14s linear infinite; }
@keyframes ob-pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
  50%      { transform: translate(-50%, -50%) scale(1.25); opacity: 0.8; }
}
@keyframes ob-spin {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to   { transform: translate(-50%, -50%) rotate(360deg); }
}

/* ── Card / form ─────────────────────────────────────────── */
.ob-card {
  margin-top: 24px;
  background: var(--ob-surface);
  border: 1px solid var(--ob-border);
  border-radius: 18px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.ob-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
}
.ob-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ob-muted);
}
.ob-text-input {
  border: 1px solid var(--ob-border);
  border-radius: 10px;
  padding: 11px 14px;
  font-size: 15px;
  color: var(--ob-fg);
  background: var(--ob-bg);
  outline: none;
  font-family: inherit;
  transition: border-color 0.2s var(--ob-spring), box-shadow 0.2s var(--ob-spring);
}
.ob-text-input:focus {
  border-color: var(--ob-accent);
  box-shadow: 0 0 0 3px var(--ob-accent-soft);
}
.ob-textarea { resize: vertical; min-height: 80px; line-height: 1.5; }
.ob-counter {
  position: absolute;
  right: 8px;
  bottom: -18px;
  font-size: 11px;
  color: var(--ob-muted);
}

/* Chip group */
.ob-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.ob-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 4px 4px 10px;
  border-radius: 999px;
  background: var(--ob-bg);
  border: 1px solid var(--ob-border);
  font-size: 13px;
  transition: transform 0.2s var(--ob-spring), border-color 0.2s;
}
.ob-chip:hover { border-color: var(--ob-accent); }
.ob-chip-x {
  background: transparent;
  border: none;
  color: var(--ob-muted);
  cursor: pointer;
  padding: 0 6px;
  font-size: 14px;
  line-height: 1;
  border-radius: 50%;
  transition: background 0.15s, color 0.15s;
}
.ob-chip-x:hover { background: var(--ob-accent-soft); color: var(--ob-accent); }

/* Competitor list */
.ob-comp-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ob-comp {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--ob-border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s var(--ob-spring);
}
.ob-comp:hover { border-color: var(--ob-accent); transform: translateX(2px); }
.ob-comp.is-selected {
  border-color: var(--ob-accent);
  background: var(--ob-accent-soft);
}
.ob-comp input[type='checkbox'] {
  accent-color: var(--ob-accent);
  width: 16px; height: 16px;
  flex-shrink: 0;
}
.ob-comp-icon {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: var(--ob-fg);
  color: var(--ob-bg);
  display: inline-flex;
  align-items: center; justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}
.ob-comp-meta { display: flex; flex-direction: column; min-width: 0; }
.ob-comp-name { font-weight: 500; font-size: 14px; }
.ob-comp-domain {
  font-family: 'SF Mono', monospace;
  font-size: 11px;
  color: var(--ob-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ob-comp-empty {
  padding: 16px;
  font-size: 13px;
  color: var(--ob-muted);
  text-align: center;
}
.ob-comp-add {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.ob-comp-add .ob-text-input { flex: 1; }

/* Action bar */
.ob-step-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 24px;
}
.ob-link-btn {
  background: transparent;
  border: none;
  color: var(--ob-muted);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 8px;
  transition: color 0.2s, background 0.2s;
}
.ob-link-btn:hover { color: var(--ob-fg); background: var(--ob-surface); }

/* Spinner */
.ob-spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid currentColor;
  border-right-color: transparent;
  animation: ob-spin-cw 0.7s linear infinite;
}
@keyframes ob-spin-cw {
  to { transform: rotate(360deg); }
}

/* ── Step transitions ────────────────────────────────────── */
.ob-fade-enter-active, .ob-fade-leave-active {
  transition: opacity 0.4s var(--ob-spring), transform 0.5s var(--ob-spring);
}
.ob-fade-enter-from { opacity: 0; transform: translateY(20px); }
.ob-fade-leave-to   { opacity: 0; transform: translateY(-20px); }

.ob-text-enter-active, .ob-text-leave-active {
  transition: opacity 0.3s, transform 0.3s var(--ob-spring);
}
.ob-text-enter-from { opacity: 0; transform: translateY(8px); }
.ob-text-leave-to   { opacity: 0; transform: translateY(-8px); }

@media (max-width: 640px) {
  .ob-topbar { padding: 20px 20px; }
  .ob-input-wrap { border-radius: 14px; flex-wrap: wrap; padding: 6px; }
  .ob-input-prefix { padding-left: 12px; }
  .ob-input { padding: 12px 8px; }
}
</style>
