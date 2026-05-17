<template>
  <div class="ob-modal-root" role="dialog" aria-modal="true" aria-labelledby="ob-modal-title">
    <div class="ob-backdrop" aria-hidden="true"></div>

    <div class="ob-panel" :data-step="step">
      <div class="ob-glow" aria-hidden="true"></div>

      <header class="ob-topbar">
        <div class="ob-brand">
          <span class="ob-brand-dot"></span>
          FetchBot
        </div>
        <div class="ob-progress" :aria-label="`Step ${step + 1} of ${steps.length}`">
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
          <!-- ── Step 0: URL ─────────────────────────────────── -->
          <section v-if="step === 0" key="url" class="ob-step">
            <div class="ob-stagger">
              <span class="ob-eyebrow">Let's get you set up</span>
              <h1 id="ob-modal-title" class="ob-title">What's your website?</h1>
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

          <!-- ── Step 1: Scanning ────────────────────────────── -->
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

          <!-- ── Step 2: Confirm description + business ─────── -->
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

                <div class="ob-field">
                  <span class="ob-label">Topics we'll measure</span>
                  <div v-if="form.keywords.length" class="ob-topics">
                    <div
                      v-for="(k, i) in form.keywords"
                      :key="k + i"
                      class="ob-topic-row"
                    >
                      <span class="ob-chip">
                        {{ k }}
                        <button class="ob-chip-x" @click="removeKeyword(k)">×</button>
                      </span>
                      <span
                        v-if="form.topic_brands[i] && form.topic_brands[i].length"
                        class="ob-topic-vs"
                      >vs {{ form.topic_brands[i].join(', ') }}</span>
                    </div>
                  </div>

                  <!-- Add your own topic. Stays alongside the LLM picks so
                       the audit measures both. -->
                  <div class="ob-add-topic">
                    <input
                      v-model="newTopic"
                      placeholder='Add a topic, e.g. "best payer credentialing in California"'
                      class="ob-text-input ob-add-input"
                      @keydown.enter.prevent="addCustomTopic"
                    />
                    <button
                      type="button"
                      class="ob-add-btn"
                      :disabled="!newTopic.trim()"
                      @click="addCustomTopic"
                    >Add</button>
                  </div>
                </div>
              </div>

              <div class="ob-step-actions">
                <button class="ob-link-btn" @click="back">Back</button>
                <button class="ob-cta" @click="goToCompetitors">
                  <span>Continue</span>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 8h10M9 4l4 4-4 4"/>
                  </svg>
                </button>
              </div>
            </div>
          </section>

          <!-- ── Step 3: Confirm competitors ─────────────────── -->
          <section v-else-if="step === 3" key="competitors" class="ob-step ob-step-wide">
            <div class="ob-stagger">
              <span class="ob-eyebrow">Step 3 of 3 — competitors</span>
              <h1 class="ob-title">Who should we benchmark you against?</h1>
              <p class="ob-sub">
                We found these from your space. Uncheck any that aren't real
                competitors, or add your own below — they shape which brands
                the audit tracks.
              </p>

              <div class="ob-card">
                <div v-if="form.competitors.length" class="ob-competitors">
                  <div
                    v-for="(c, i) in form.competitors"
                    :key="(c.domain || c.name) + i"
                    class="ob-competitor"
                    :class="{ 'is-selected': c.selected, 'is-custom': c.custom }"
                  >
                    <label class="ob-competitor-label">
                      <input
                        type="checkbox"
                        v-model="c.selected"
                        class="ob-competitor-check"
                      />
                      <!-- Logo lookup: Clearbit returns the brand mark for
                           most known companies; on 404 the @error handler
                           swaps to Google's favicon service; if that also
                           fails we fall back to a circled initial. -->
                      <span class="ob-competitor-logo" v-if="c.domain || c.name">
                        <img
                          v-if="c.domain && !c._logoErr"
                          :src="`https://logo.clearbit.com/${c.domain}`"
                          :alt="`${c.name} logo`"
                          loading="lazy"
                          width="24"
                          height="24"
                          @error="onLogoError(c)"
                        />
                        <img
                          v-else-if="c.domain && c._logoErr === 'clearbit'"
                          :src="`https://www.google.com/s2/favicons?domain=${c.domain}&sz=64`"
                          :alt="`${c.name} favicon`"
                          loading="lazy"
                          width="24"
                          height="24"
                          @error="onLogoError(c)"
                        />
                        <span v-else class="ob-competitor-logo-fallback">
                          {{ (c.name || '?').trim().charAt(0).toUpperCase() }}
                        </span>
                      </span>
                      <div class="ob-competitor-body">
                        <div class="ob-competitor-name">{{ c.name }}</div>
                        <div v-if="c.domain" class="ob-competitor-domain">{{ c.domain }}</div>
                      </div>
                    </label>
                    <button
                      v-if="c.custom"
                      type="button"
                      class="ob-competitor-remove"
                      @click="removeCompetitor(i)"
                      aria-label="Remove competitor"
                    >×</button>
                  </div>
                </div>
                <p v-else class="ob-sub" style="margin: 0;">
                  We didn't find any competitors automatically. Add your own below.
                </p>

                <!-- Add-your-own row -->
                <div class="ob-add-competitor">
                  <input
                    v-model="newCompetitorName"
                    placeholder="Competitor name (e.g. Stripe)"
                    class="ob-text-input ob-add-input"
                    @keydown.enter.prevent="addCustomCompetitor"
                  />
                  <input
                    v-model="newCompetitorDomain"
                    placeholder="domain.com (optional)"
                    class="ob-text-input ob-add-input ob-add-input--narrow"
                    @keydown.enter.prevent="addCustomCompetitor"
                  />
                  <button
                    type="button"
                    class="ob-add-btn"
                    :disabled="!newCompetitorName.trim()"
                    @click="addCustomCompetitor"
                  >Add</button>
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
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import onboardingApi from '@/api/onboarding'

const emit = defineEmits(['complete'])

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
  // Parallel to `keywords`: brand names that show up alongside the
  // topic in well-ranked LLM answers. Rendered under each chip on
  // step 2 so the user can see what they're benchmarked against.
  topic_brands: [],
  competitors: [],
})

const urlInputRef = ref(null)

// "Add your own topic" input on step 2.
const newTopic = ref('')

// "Add your own competitor" inputs on step 3.
const newCompetitorName = ref('')
const newCompetitorDomain = ref('')

const urlHostname = computed(() => {
  try {
    const raw = form.value.url || urlInput.value
    return new URL(raw.startsWith('http') ? raw : `https://${raw}`).hostname
  } catch (_) {
    return urlInput.value
  }
})

const SCAN_LINES = [
  'Reading your homepage…',
  'Spotting products and features…',
  'Drafting a clean description…',
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
      topic_brands: (payload.topic_brands || []).slice(0, 8),
      competitors: (payload.competitors || []).slice(0, 12).map(c => ({
        name: c.name || c.domain || '',
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
  if (step.value === 3) step.value = 2
  else if (step.value === 2) step.value = 0
  else if (step.value > 0) step.value -= 1
}

function goToCompetitors() {
  step.value = 3
}

function _normalizeDomain(d) {
  return (d || '').trim().toLowerCase()
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .replace(/\/$/, '')
}

function addCustomCompetitor() {
  const name = newCompetitorName.value.trim()
  if (!name) return
  const domain = _normalizeDomain(newCompetitorDomain.value)
  // Dedupe against existing rows by domain (preferred) or name (fallback).
  const exists = form.value.competitors.some(c => {
    const cDom = _normalizeDomain(c.domain)
    if (domain && cDom) return cDom === domain
    return c.name.toLowerCase() === name.toLowerCase()
  })
  if (exists) {
    newCompetitorName.value = ''
    newCompetitorDomain.value = ''
    return
  }
  form.value.competitors.push({
    name,
    domain,
    selected: true,
    custom: true,
  })
  newCompetitorName.value = ''
  newCompetitorDomain.value = ''
}

function removeCompetitor(index) {
  if (index < 0 || index >= form.value.competitors.length) return
  form.value.competitors.splice(index, 1)
}

// Two-tier logo fallback: Clearbit -> Google favicon -> initial.
// State machine driven by an internal `_logoErr` field on the row.
function onLogoError(competitor) {
  if (!competitor._logoErr) {
    competitor._logoErr = 'clearbit'
  } else {
    competitor._logoErr = 'fallback'
  }
}

function removeKeyword(k) {
  // Drop the matching brand list at the same index to keep the two
  // arrays aligned for the "vs Brand1, Brand2" sub-label.
  const idx = form.value.keywords.indexOf(k)
  if (idx === -1) return
  form.value.keywords.splice(idx, 1)
  if (idx < form.value.topic_brands.length) {
    form.value.topic_brands.splice(idx, 1)
  }
}

function addCustomTopic() {
  const t = newTopic.value.trim().replace(/[.,]+$/, '')
  if (!t) return
  // Dedupe against the existing list, case-insensitive.
  const exists = form.value.keywords.some(
    k => k.toLowerCase() === t.toLowerCase(),
  )
  if (exists) {
    newTopic.value = ''
    return
  }
  form.value.keywords.push(t)
  // Push an empty brand slot so the parallel arrays stay aligned.
  // User-added topics show no "vs ..." sub-label.
  form.value.topic_brands.push([])
  newTopic.value = ''
}

async function finish() {
  saving.value = true
  try {
    await onboardingApi.save({
      url: form.value.url,
      business_name: form.value.business_name,
      industry: form.value.industry,
      description: form.value.description,
      keywords: form.value.keywords,
      competitors: form.value.competitors
        .filter(c => c.selected)
        .map(c => ({ name: c.name, domain: c.domain })),
    })
    await auth.fetchSession()
    emit('complete')
  } catch (e) {
    toast.error(e.response?.data?.error?.message || 'Could not save. Try again.')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  document.body.style.overflow = 'hidden'
  nextTick(() => urlInputRef.value?.focus?.())
})

onBeforeUnmount(() => {
  document.body.style.overflow = ''
  stopScanLines()
})
</script>

<style scoped>
.ob-modal-root {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  animation: ob-modal-in 280ms cubic-bezier(0.22, 1, 0.36, 1);
}

.ob-backdrop {
  position: absolute;
  inset: 0;
  /* Solid brand surface — the dashboard is hidden behind us, so there
     is nothing to peek at. Soft gradient keeps the modal centred. */
  background: radial-gradient(circle at 50% 30%, #fff5ec 0%, #ffffff 60%);
}

.ob-panel {
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
  z-index: 1;
  width: 100%;
  max-width: 720px;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--ob-bg);
  color: var(--ob-fg);
  border-radius: 22px;
  box-shadow:
    0 30px 80px rgba(0, 0, 0, 0.35),
    0 8px 24px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  font-feature-settings: 'cv11', 'ss01';
  animation: ob-panel-in 360ms var(--ob-spring) both;
}

[data-theme='dark'] .ob-panel {
  --ob-bg: #0e0e10;
  --ob-fg: #f7f7f7;
  --ob-muted: #888;
  --ob-border: rgba(255, 255, 255, 0.10);
  --ob-surface: #161618;
  --ob-accent-soft: rgba(255, 106, 44, 0.14);
}

@keyframes ob-modal-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes ob-panel-in {
  from { opacity: 0; transform: translateY(16px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

.ob-glow {
  position: absolute;
  top: 30%;
  left: 50%;
  width: 480px;
  height: 480px;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle, var(--ob-accent-soft) 0%, transparent 60%);
  filter: blur(40px);
  pointer-events: none;
  transition: transform 1.2s var(--ob-spring), opacity 0.8s ease;
  opacity: 0.75;
  z-index: 0;
}
.ob-panel[data-step='0'] .ob-glow { transform: translate(-50%, -50%) translateX(-8vw); }
.ob-panel[data-step='1'] .ob-glow { transform: translate(-50%, -50%) scale(1.15); opacity: 0.9; }
.ob-panel[data-step='2'] .ob-glow { transform: translate(-50%, -50%) translateX(6vw); }
.ob-panel[data-step='3'] .ob-glow { transform: translate(-50%, -50%) translateX(4vw) translateY(6vh); }

.ob-topbar {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22px 28px 0;
}
.ob-brand {
  display: flex; align-items: center; gap: 10px;
  font-weight: 600; font-size: 15px; letter-spacing: -0.01em;
}
.ob-brand-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--ob-accent);
  box-shadow: 0 0 0 4px var(--ob-accent-soft);
}
.ob-progress { display: flex; gap: 6px; }
.ob-progress-dot {
  width: 22px; height: 4px; border-radius: 2px;
  background: var(--ob-border);
  transition: background 0.4s var(--ob-spring), width 0.5s var(--ob-spring);
}
.ob-progress-dot.is-done { background: var(--ob-fg); }
.ob-progress-dot.is-active { background: var(--ob-accent); width: 36px; }

.ob-main {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 36px 28px 40px;
}
.ob-step { width: 100%; max-width: 540px; text-align: center; }
.ob-step-wide { max-width: 640px; text-align: left; }

.ob-stagger > * { animation: ob-rise 0.6s var(--ob-spring-strong) both; }
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
  font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--ob-muted); margin-bottom: 14px;
}
.ob-title {
  font-size: clamp(28px, 4vw, 40px);
  line-height: 1.08;
  font-weight: 600;
  letter-spacing: -0.025em;
  margin: 0 0 12px;
}
.ob-sub {
  font-size: 15px; line-height: 1.55;
  color: var(--ob-muted);
  margin: 0 auto 24px;
  max-width: 480px;
}
.ob-step-wide .ob-sub { margin-left: 0; }

.ob-input-wrap {
  display: flex; align-items: center;
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
  flex: 1; border: none; background: transparent; outline: none;
  padding: 12px 12px; font-size: 16px; color: var(--ob-fg);
  font-family: inherit; min-width: 0;
}
.ob-cta {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 11px 18px; border: none; border-radius: 999px;
  background: var(--ob-fg); color: var(--ob-bg);
  font-size: 14px; font-weight: 600; letter-spacing: -0.005em;
  cursor: pointer;
  transition: transform 0.2s var(--ob-spring), background 0.25s var(--ob-spring), opacity 0.2s;
}
.ob-cta:hover:not(:disabled) { transform: translateY(-1px); background: var(--ob-accent); }
.ob-cta:active:not(:disabled) { transform: translateY(0) scale(0.98); }
.ob-cta:disabled { opacity: 0.5; cursor: not-allowed; }

.ob-error { margin-top: 14px; color: var(--ob-accent); font-size: 14px; }
.ob-hints {
  margin-top: 22px; display: flex; justify-content: center; gap: 10px;
  font-size: 12px; color: var(--ob-muted);
}
.ob-hints kbd {
  font-family: 'SF Mono', monospace; font-size: 11px;
  border: 1px solid var(--ob-border); padding: 1px 6px;
  border-radius: 4px; background: var(--ob-surface);
}
.ob-dot-sep { opacity: 0.5; }

.ob-orbit { position: relative; width: 120px; height: 120px; margin: 0 auto 24px; }
.ob-orbit-core {
  position: absolute; top: 50%; left: 50%;
  width: 16px; height: 16px; border-radius: 50%;
  background: var(--ob-accent); transform: translate(-50%, -50%);
  box-shadow: 0 0 24px var(--ob-accent);
  animation: ob-pulse 1.6s ease-in-out infinite;
}
.ob-orbit-ring {
  position: absolute; top: 50%; left: 50%;
  border-radius: 50%; border: 1px solid var(--ob-border);
  transform: translate(-50%, -50%);
}
.ob-orbit-r1 { width: 56px; height: 56px; animation: ob-spin 6s linear infinite; }
.ob-orbit-r2 { width: 88px; height: 88px; animation: ob-spin 9s linear reverse infinite; border-color: rgba(255,106,44,0.35); }
.ob-orbit-r3 { width: 120px; height: 120px; animation: ob-spin 14s linear infinite; }
@keyframes ob-pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
  50%      { transform: translate(-50%, -50%) scale(1.25); opacity: 0.8; }
}
@keyframes ob-spin {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to   { transform: translate(-50%, -50%) rotate(360deg); }
}

.ob-card {
  margin-top: 18px;
  background: var(--ob-surface);
  border: 1px solid var(--ob-border);
  border-radius: 16px;
  padding: 22px;
  display: flex; flex-direction: column; gap: 16px;
}
.ob-field { display: flex; flex-direction: column; gap: 6px; position: relative; }
.ob-label {
  font-size: 12px; font-weight: 600; letter-spacing: 0.04em;
  text-transform: uppercase; color: var(--ob-muted);
}
.ob-text-input {
  border: 1px solid var(--ob-border); border-radius: 10px;
  padding: 11px 14px; font-size: 15px;
  color: var(--ob-fg); background: var(--ob-bg);
  outline: none; font-family: inherit;
  transition: border-color 0.2s var(--ob-spring), box-shadow 0.2s var(--ob-spring);
}
.ob-text-input:focus {
  border-color: var(--ob-accent);
  box-shadow: 0 0 0 3px var(--ob-accent-soft);
}
.ob-textarea { resize: vertical; min-height: 80px; line-height: 1.5; }
.ob-counter {
  position: absolute; right: 8px; bottom: -18px;
  font-size: 11px; color: var(--ob-muted);
}

.ob-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.ob-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 4px 4px 10px; border-radius: 999px;
  background: var(--ob-bg); border: 1px solid var(--ob-border);
  font-size: 13px;
  transition: transform 0.2s var(--ob-spring), border-color 0.2s;
}
.ob-chip:hover { border-color: var(--ob-accent); }
.ob-chip-x {
  background: transparent; border: none;
  color: var(--ob-muted); cursor: pointer;
  padding: 0 6px; font-size: 14px; line-height: 1;
  border-radius: 50%;
  transition: background 0.15s, color 0.15s;
}
.ob-chip-x:hover { background: var(--ob-accent-soft); color: var(--ob-accent); }

/* Each topic row stacks the chip with a small "vs Brand1, Brand2"
   sub-label so the user can see who they're being benchmarked against
   per topic. */
.ob-topics { display: flex; flex-direction: column; gap: 8px; }
.ob-topic-row { display: flex; flex-direction: column; gap: 2px; align-items: flex-start; }
.ob-topic-vs {
  font-size: 11px;
  color: var(--ob-muted);
  letter-spacing: 0.01em;
  padding-left: 10px;
}

.ob-competitors { display: grid; grid-template-columns: 1fr; gap: 8px; }
.ob-competitor {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--ob-border); border-radius: 10px;
  background: var(--ob-bg); cursor: pointer;
  transition: border-color 160ms var(--ob-spring), background 160ms var(--ob-spring);
}
.ob-competitor:hover { border-color: var(--ob-accent); }
.ob-competitor.is-selected { background: var(--ob-accent-soft); border-color: var(--ob-accent); }
.ob-competitor-check { width: 16px; height: 16px; accent-color: var(--ob-accent); }

/* Logo block: fixed 24x24 round container. img fills; if both
   external sources fail we render a circled initial via the fallback
   span. */
.ob-competitor-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--ob-surface);
  border: 1px solid var(--ob-border);
  overflow: hidden;
  flex-shrink: 0;
}
.ob-competitor-logo img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #fff;
}
.ob-competitor-logo-fallback {
  font-size: 11px;
  font-weight: 600;
  color: var(--ob-fg);
}
.ob-competitor-body { display: flex; flex-direction: column; line-height: 1.2; }
.ob-competitor-name { font-size: 14px; font-weight: 500; }
.ob-competitor-domain { font-size: 12px; color: var(--ob-muted); }

/* Wrap label so the row can host a remove × on the right for custom
   entries. */
.ob-competitor {
  /* keep existing rules, add justify so the label fills and × sits
     on the far right. */
  justify-content: space-between;
}
.ob-competitor-label {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  cursor: pointer;
  min-width: 0;
}
.ob-competitor.is-custom { border-style: dashed; }
.ob-competitor-remove {
  background: transparent;
  border: none;
  color: var(--ob-muted);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.15s, color 0.15s;
}
.ob-competitor-remove:hover { background: var(--ob-accent-soft); color: var(--ob-accent); }

/* "Add your own" row sits below the discovered list. */
.ob-add-competitor,
.ob-add-topic {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  align-items: stretch;
  flex-wrap: wrap;
}
.ob-add-input { flex: 1; min-width: 0; }
.ob-add-input--narrow { max-width: 200px; }
.ob-add-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 18px;
  border-radius: 10px;
  border: 1px solid var(--ob-border);
  background: var(--ob-bg);
  color: var(--ob-fg);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.2s var(--ob-spring), background 0.2s var(--ob-spring), color 0.2s;
}
.ob-add-btn:hover:not(:disabled) {
  border-color: var(--ob-accent);
  background: var(--ob-accent);
  color: var(--ob-bg);
}
.ob-add-btn:disabled { opacity: 0.45; cursor: not-allowed; }

.ob-step-actions {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 22px;
}
.ob-link-btn {
  background: transparent; border: none;
  color: var(--ob-muted); font-size: 14px; font-weight: 500;
  cursor: pointer; padding: 8px 12px; border-radius: 8px;
  transition: color 0.2s, background 0.2s;
}
.ob-link-btn:hover { color: var(--ob-fg); background: var(--ob-surface); }

.ob-spinner {
  width: 14px; height: 14px; border-radius: 50%;
  border: 2px solid currentColor; border-right-color: transparent;
  animation: ob-spin-cw 0.7s linear infinite;
}
@keyframes ob-spin-cw { to { transform: rotate(360deg); } }

.ob-fade-enter-active, .ob-fade-leave-active {
  transition: opacity 0.35s var(--ob-spring), transform 0.4s var(--ob-spring);
}
.ob-fade-enter-from { opacity: 0; transform: translateY(16px); }
.ob-fade-leave-to   { opacity: 0; transform: translateY(-16px); }

.ob-text-enter-active, .ob-text-leave-active {
  transition: opacity 0.3s, transform 0.3s var(--ob-spring);
}
.ob-text-enter-from { opacity: 0; transform: translateY(8px); }
.ob-text-leave-to   { opacity: 0; transform: translateY(-8px); }

@media (max-width: 640px) {
  .ob-modal-root { padding: 0; }
  .ob-panel { border-radius: 0; max-width: 100%; max-height: 100vh; height: 100vh; }
  .ob-topbar { padding: 18px 18px 0; }
  .ob-main { padding: 28px 18px 32px; }
  .ob-input-wrap { border-radius: 14px; flex-wrap: wrap; padding: 6px; }
  .ob-input-prefix { padding-left: 12px; }
  .ob-input { padding: 12px 8px; }
}
</style>
