<template>
  <div class="onboarding-page">
    <!-- Left sidebar stepper -->
    <aside class="ob-sidebar">
      <div class="ob-brand">
        <img src="/images/fb-logo.png" alt="FetchBot" class="ob-logo" />
        <span class="ob-logo-text" v-if="false">FetchBot</span>
      </div>
      <nav class="ob-steps">
        <div v-for="(s, i) in steps" :key="s.key" class="ob-step" :class="{ active: step === i, done: step > i }">
          <div class="ob-step-dot">
            <svg v-if="step > i" width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M6.5 12.5l-4-4 1.4-1.4 2.6 2.6 5.6-5.6 1.4 1.4z"/></svg>
            <span v-else></span>
          </div>
          <span class="ob-step-label">{{ s.label }}</span>
          <div v-if="i < steps.length - 1" class="ob-step-line" :class="{ filled: step > i }"></div>
        </div>
      </nav>
    </aside>

    <!-- Main content area -->
    <main class="ob-main">
      <!-- Step 0: Website -->
      <div v-if="step === 0" class="ob-card fade-in">
        <h2 class="ob-title">Welcome to Bear</h2>
        <p class="ob-desc">Enter your website and company name</p>
        <div class="ob-field">
          <div class="ob-input-icon">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><line x1="2" y1="8" x2="14" y2="8"/><ellipse cx="8" cy="8" rx="3" ry="6"/></svg>
          </div>
          <input v-model="form.url" class="ob-input" placeholder="https://yoursite.com" type="url" @keydown.enter="nextStep" />
        </div>
        <div class="ob-field">
          <div class="ob-input-icon">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="12" height="10" rx="2"/><path d="M5 7h6M5 10h4"/></svg>
          </div>
          <input v-model="form.name" class="ob-input" placeholder="Company name" @keydown.enter="nextStep" />
        </div>
        <button class="ob-btn-primary" :disabled="!form.url || !form.name" @click="nextStep">Continue</button>
      </div>

      <!-- Step 1: Description -->
      <div v-if="step === 1" class="ob-card fade-in">
        <h2 class="ob-title">Tell us about your business</h2>
        <textarea v-model="form.description" class="ob-textarea" rows="6" placeholder="Describe what your business does..." maxlength="500"></textarea>
        <div class="ob-textarea-footer">
          <span class="ob-char-count">{{ (form.description || '').length }}/500 characters</span>
          <button class="ob-link-btn" @click="regenerateDescription" :disabled="generatingDesc">
            ✨ {{ generatingDesc ? 'Generating...' : 'Regenerate Description' }}
          </button>
        </div>
        <button class="ob-btn-primary" :disabled="!form.description" @click="nextStep">Continue</button>
      </div>

      <!-- Step 2: Topics -->
      <div v-if="step === 2" class="ob-card ob-card-wide fade-in">
        <h2 class="ob-title">What do you want to show up on ChatGPT for?</h2>
        <p class="ob-desc ob-desc-purple">Pick the categories that you want to show up on ChatGPT for.</p>
        <div class="ob-topics-grid">
          <button v-for="t in availableTopics" :key="t" class="ob-topic-chip" :class="{ selected: form.topics.includes(t), loading: loadingMoreTopics }" @click="toggleTopic(t)">
            {{ t }}
          </button>
          <template v-if="loadingMoreTopics">
            <div v-for="n in 6" :key="'skel-'+n" class="ob-topic-skeleton"></div>
          </template>
        </div>
        <p v-if="loadingMoreTopics" class="ob-loading-hint">✨ Finding more ways for you to show up on ChatGPT...</p>
        <p v-else-if="form.topics.length < 3" class="ob-pick-hint">Pick {{ 3 - form.topics.length }} more to unlock additional options</p>
        <div class="ob-nav-row">
          <button class="ob-btn-secondary" @click="step--">Back</button>
          <button class="ob-btn-primary" :disabled="form.topics.length < 3 || loadingMoreTopics" @click="nextStep">
            {{ loadingMoreTopics ? 'Generating More Topics...' : 'Continue' }}
          </button>
        </div>
      </div>

      <!-- Step 3: Competitors -->
      <div v-if="step === 3" class="ob-card ob-card-wide fade-in">
        <h2 class="ob-title">Add Your Competitors</h2>
        <p class="ob-desc">Track up to 20 competitors to monitor your relative AI visibility</p>
        <div class="ob-comp-header">
          <strong>Add New Competitor</strong>
          <span class="ob-comp-count">{{ competitors.length }}/20</span>
        </div>
        <div class="ob-comp-input-row">
          <div class="ob-field ob-field-grow">
            <div class="ob-input-icon"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="12" height="10" rx="2"/><path d="M5 7h6"/></svg></div>
            <input v-model="newComp.name" class="ob-input" placeholder="Competitor name" @keydown.enter="addCompetitor" />
          </div>
          <div class="ob-field ob-field-grow">
            <div class="ob-input-icon"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><line x1="2" y1="8" x2="14" y2="8"/></svg></div>
            <input v-model="newComp.url" class="ob-input" placeholder="www.example.com (optional)" @keydown.enter="addCompetitor" />
          </div>
          <button class="ob-btn-add" @click="addCompetitor" :disabled="!newComp.name || competitors.length >= 20">+</button>
        </div>
        <div class="ob-comp-grid">
          <div v-for="c in competitors" :key="c.id || c.name" class="ob-comp-card">
            <div class="ob-comp-avatar">{{ (c.name || '?')[0].toUpperCase() }}</div>
            <div class="ob-comp-info">
              <div class="ob-comp-name">{{ c.name }}</div>
              <div class="ob-comp-url">{{ c.competitor_url || c.url || '' }}</div>
            </div>
            <button class="ob-comp-remove" @click="removeCompetitor(c)">×</button>
          </div>
        </div>
        <div class="ob-nav-row">
          <button class="ob-btn-secondary" @click="step--">Back</button>
          <button class="ob-btn-primary" @click="nextStep">Simulate AI Searches</button>
        </div>
      </div>

      <!-- Step 4: Analysis -->
      <div v-if="step === 4" class="ob-card fade-in">
        <h2 class="ob-title">Running AI Visibility Analysis</h2>
        <p class="ob-desc">We're simulating searches across ChatGPT, Claude, Gemini, and Perplexity to measure your visibility...</p>
        <div class="ob-analysis-progress">
          <div class="ob-progress-track"><div class="ob-progress-fill" :style="{ width: analysisPct + '%' }"></div></div>
          <p class="ob-analysis-status">{{ analysisStatus }}</p>
        </div>
        <div class="ob-nav-row">
          <button class="ob-btn-secondary" @click="step--">Back</button>
          <button class="ob-btn-primary" :disabled="analysisPct < 100" @click="nextStep">Continue</button>
        </div>
      </div>

      <!-- Step 5: Complete -->
      <div v-if="step === 5" class="ob-card fade-in">
        <div class="ob-complete-icon">🎉</div>
        <h2 class="ob-title">You're all set!</h2>
        <p class="ob-desc">Your project is configured and ready. We'll start tracking your AI visibility across all major LLM platforms.</p>
        <button class="ob-btn-primary" @click="finish">Go to Dashboard</button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import websitesApi from '@/api/websites'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()

const step = ref(0)
const generatingDesc = ref(false)
const loadingMoreTopics = ref(false)
const analysisPct = ref(0)
const analysisStatus = ref('Preparing queries...')

const steps = [
  { key: 'website', label: 'Website' },
  { key: 'description', label: 'Description' },
  { key: 'topics', label: 'Topics' },
  { key: 'competitors', label: 'Competitors' },
  { key: 'analysis', label: 'Analysis' },
  { key: 'complete', label: 'Complete' },
]

const form = reactive({
  url: '',
  name: '',
  description: '',
  topics: [],
  industry: '',
})

const websiteId = ref(route.params.websiteId || null)
const availableTopics = ref([])
const competitors = ref([])
const newComp = reactive({ name: '', url: '' })

onMounted(async () => {
  // If we have a websiteId, load existing data
  if (websiteId.value) {
    try {
      const { data } = await websitesApi.get(websiteId.value)
      const site = data?.data || data
      form.url = site.url || ''
      form.name = site.name || ''
      form.description = site.description || ''
      form.topics = site.topics || []
      form.industry = site.industry || ''

      // If onboarding was already completed, skip to step 0 (re-do flow)
      // Load existing competitors
      try {
        const compResp = await websitesApi.listCompetitors(websiteId.value)
        competitors.value = compResp.data?.data || compResp.data || []
      } catch {}
    } catch {}
  }
})

function toggleTopic(t) {
  const idx = form.topics.indexOf(t)
  if (idx >= 0) form.topics.splice(idx, 1)
  else form.topics.push(t)
}

async function regenerateDescription() {
  if (!websiteId.value) return
  generatingDesc.value = true
  try {
    const { data } = await websitesApi.onboardingAssist(websiteId.value, { action: 'describe' })
    form.description = data?.description || data?.data?.description || form.description
  } catch {}
  generatingDesc.value = false
}

async function loadTopics() {
  if (!websiteId.value) return
  loadingMoreTopics.value = true
  try {
    const { data } = await websitesApi.onboardingAssist(websiteId.value, {
      action: 'topics',
      description: form.description,
      industry: form.industry,
    })
    const topics = data?.topics || data?.data?.topics || []
    // Merge with existing, deduplicate
    const existing = new Set(availableTopics.value.map(t => t.toLowerCase()))
    for (const t of topics) {
      if (!existing.has(t.toLowerCase())) {
        availableTopics.value.push(t)
        existing.add(t.toLowerCase())
      }
    }
  } catch {}
  loadingMoreTopics.value = false
}

async function addCompetitor() {
  if (!newComp.name || competitors.value.length >= 20) return
  const compUrl = newComp.url ? (newComp.url.startsWith('http') ? newComp.url : `https://${newComp.url}`) : ''
  if (websiteId.value) {
    try {
      const { data } = await websitesApi.addCompetitor(websiteId.value, {
        name: newComp.name,
        competitor_url: compUrl || `https://${newComp.name.toLowerCase().replace(/\s+/g, '')}.com`,
      })
      competitors.value.push(data?.data || data)
    } catch {
      // Still add locally
      competitors.value.push({ name: newComp.name, competitor_url: compUrl, id: Date.now() })
    }
  } else {
    competitors.value.push({ name: newComp.name, competitor_url: compUrl, id: Date.now() })
  }
  newComp.name = ''
  newComp.url = ''
}

async function removeCompetitor(c) {
  if (c.id && websiteId.value && typeof c.id === 'string') {
    try { await websitesApi.deleteCompetitor(websiteId.value, c.id) } catch {}
  }
  competitors.value = competitors.value.filter(x => x !== c)
}

async function saveStepData() {
  if (!websiteId.value) return
  try {
    await websitesApi.update(websiteId.value, {
      name: form.name,
      description: form.description,
      topics: form.topics,
      industry: form.industry,
    })
  } catch {}
}

function simulateAnalysis() {
  analysisPct.value = 0
  analysisStatus.value = 'Preparing queries...'
  const stages = [
    { pct: 15, msg: 'Querying ChatGPT...' },
    { pct: 35, msg: 'Querying Claude...' },
    { pct: 55, msg: 'Querying Gemini...' },
    { pct: 75, msg: 'Querying Perplexity...' },
    { pct: 90, msg: 'Analyzing responses...' },
    { pct: 100, msg: 'Analysis complete!' },
  ]
  let i = 0
  const timer = setInterval(() => {
    if (i < stages.length) {
      analysisPct.value = stages[i].pct
      analysisStatus.value = stages[i].msg
      i++
    } else {
      clearInterval(timer)
    }
  }, 800)
}

async function nextStep() {
  // Step 0 → 1: Create website if needed, then generate description
  if (step.value === 0) {
    if (!websiteId.value) {
      try {
        const { data } = await websitesApi.create({ url: form.url, name: form.name, industry: form.industry })
        const site = data?.data || data
        websiteId.value = site.id
        appStore.websites.push(site)
        appStore.setActiveWebsite(site)
      } catch (e) {
        return
      }
    } else {
      await saveStepData()
    }
    // Auto-generate description
    if (!form.description) {
      generatingDesc.value = true
      try {
        const { data } = await websitesApi.onboardingAssist(websiteId.value, { action: 'describe' })
        form.description = data?.description || data?.data?.description || ''
      } catch {}
      generatingDesc.value = false
    }
  }

  // Step 1 → 2: Save description, load topics
  if (step.value === 1) {
    await saveStepData()
    if (availableTopics.value.length === 0) {
      await loadTopics()
    }
  }

  // Step 2 → 3: Save topics
  if (step.value === 2) {
    await saveStepData()
  }

  // Step 3 → 4: Save and start analysis
  if (step.value === 3) {
    await saveStepData()
    step.value = 4
    simulateAnalysis()
    return
  }

  // Step 4 → 5: Mark onboarding complete
  if (step.value === 4) {
    if (websiteId.value) {
      try {
        await websitesApi.update(websiteId.value, { onboarding_completed: true })
      } catch {}
    }
  }

  step.value++
}

async function finish() {
  // Re-check session — onboarding just changed onboarding_completed, so the
  // gate may now point at paywall (new users) or app (returning users).
  const session = await authStore.fetchSession()
  const next = session?.next_route
  if (next === 'paywall') {
    router.push('/paywall')
  } else if (websiteId.value) {
    router.push(`/analytics/${websiteId.value}`)
  } else {
    router.push('/dashboard')
  }
}
</script>

<style scoped>
.onboarding-page {
  display: flex;
  min-height: 100vh;
  background: #fafafa;
  font-family: 'Inter', 'SF Pro Display', system-ui, sans-serif;
}

/* Sidebar */
.ob-sidebar {
  width: 200px;
  padding: 32px 24px;
  border-right: 1px solid #eee;
  background: #fff;
  display: flex;
  flex-direction: column;
}
.ob-brand { display: flex; align-items: center; gap: 10px; margin-bottom: 40px; }
.ob-logo { width: 32px; height: 32px; }
.ob-steps { display: flex; flex-direction: column; gap: 0; }
.ob-step {
  display: flex; align-items: center; gap: 10px;
  position: relative; padding: 8px 0;
  color: #aaa; font-size: 13px; font-weight: 500;
  transition: color 0.2s;
}
.ob-step.active { color: #111; font-weight: 600; }
.ob-step.done { color: #22c55e; }
.ob-step-dot {
  width: 20px; height: 20px; border-radius: 50%;
  border: 2px solid #ddd; display: flex; align-items: center; justify-content: center;
  font-size: 10px; flex-shrink: 0; transition: all 0.2s;
}
.ob-step.active .ob-step-dot { border-color: #111; background: #111; }
.ob-step.done .ob-step-dot { border-color: #22c55e; background: #22c55e; color: #fff; }
.ob-step-line {
  position: absolute; left: 9px; top: 32px;
  width: 2px; height: 16px; background: #eee;
}
.ob-step-line.filled { background: #22c55e; }
.ob-step-label { white-space: nowrap; }

/* Main */
.ob-main {
  flex: 1; display: flex; align-items: center; justify-content: center;
  padding: 40px;
}
.ob-card {
  background: #fff; border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.04);
  padding: 40px; width: 100%; max-width: 480px;
}
.ob-card-wide { max-width: 680px; }
.ob-title { font-size: 22px; font-weight: 700; color: #111; margin: 0 0 8px; }
.ob-desc { font-size: 14px; color: #666; margin: 0 0 24px; line-height: 1.5; }
.ob-desc-purple { color: #8b5cf6; }

/* Fields */
.ob-field { position: relative; margin-bottom: 12px; }
.ob-field-grow { flex: 1; }
.ob-input-icon {
  position: absolute; left: 14px; top: 50%; transform: translateY(-50%);
  color: #999; display: flex;
}
.ob-input {
  width: 100%; padding: 12px 14px 12px 42px;
  border: 1px solid #e0e0e0; border-radius: 10px;
  font-size: 14px; color: #111; background: #fff;
  outline: none; transition: border-color 0.15s;
  box-sizing: border-box;
}
.ob-input:focus { border-color: #111; }
.ob-input::placeholder { color: #bbb; }

/* Textarea */
.ob-textarea {
  width: 100%; padding: 14px; border: 1px solid #e0e0e0;
  border-radius: 10px; font-size: 14px; color: #111;
  resize: vertical; outline: none; font-family: inherit;
  line-height: 1.6; box-sizing: border-box;
}
.ob-textarea:focus { border-color: #111; }
.ob-textarea-footer {
  display: flex; justify-content: space-between; align-items: center;
  margin: 8px 0 20px; font-size: 12px; color: #999;
}
.ob-char-count { color: #999; }
.ob-link-btn {
  background: none; border: none; color: #8b5cf6;
  cursor: pointer; font-size: 12px; font-weight: 500;
}
.ob-link-btn:disabled { opacity: 0.5; cursor: wait; }

/* Buttons */
.ob-btn-primary {
  width: 100%; padding: 13px 24px; background: #111; color: #fff;
  border: none; border-radius: 10px; font-size: 15px; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
}
.ob-btn-primary:hover:not(:disabled) { background: #333; }
.ob-btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
.ob-btn-secondary {
  padding: 11px 24px; background: #fff; color: #111;
  border: 1px solid #ddd; border-radius: 10px; font-size: 14px;
  font-weight: 500; cursor: pointer; transition: all 0.15s;
}
.ob-btn-secondary:hover { border-color: #111; }
.ob-nav-row { display: flex; gap: 12px; justify-content: center; margin-top: 24px; }
.ob-nav-row .ob-btn-primary { width: auto; }

/* Topics */
.ob-topics-grid {
  display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px;
  justify-content: center;
}
.ob-topic-chip {
  padding: 10px 20px; border: 1.5px solid #e0e0e0; border-radius: 24px;
  background: #fff; font-size: 13px; font-weight: 500; color: #333;
  cursor: pointer; transition: all 0.2s; white-space: nowrap;
}
.ob-topic-chip:hover { border-color: #999; }
.ob-topic-chip.selected {
  border-color: #111; background: #111; color: #fff;
}
.ob-topic-skeleton {
  width: 140px; height: 40px; border-radius: 24px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e8e8e8 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.ob-loading-hint { text-align: center; font-size: 13px; color: #999; margin: 8px 0 0; }
.ob-pick-hint { text-align: center; font-size: 13px; color: #8b5cf6; margin: 8px 0 0; }

/* Competitors */
.ob-comp-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px; font-size: 14px;
}
.ob-comp-count { color: #999; font-size: 13px; font-weight: 500; }
.ob-comp-input-row { display: flex; gap: 8px; margin-bottom: 16px; align-items: flex-start; }
.ob-btn-add {
  width: 44px; height: 44px; border-radius: 10px; border: none;
  background: #111; color: #fff; font-size: 20px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.ob-btn-add:disabled { opacity: 0.3; }
.ob-comp-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 8px; }
.ob-comp-card {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 14px; border: 1px solid #eee; border-radius: 12px;
  background: #fafafa; position: relative;
}
.ob-comp-avatar {
  width: 36px; height: 36px; border-radius: 8px; background: #e0e0e0;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 14px; color: #555; flex-shrink: 0;
}
.ob-comp-info { flex: 1; min-width: 0; }
.ob-comp-name { font-size: 13px; font-weight: 600; color: #111; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ob-comp-url { font-size: 11px; color: #999; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ob-comp-remove {
  position: absolute; top: 6px; right: 8px;
  background: none; border: none; color: #ccc; font-size: 16px;
  cursor: pointer; padding: 2px;
}
.ob-comp-remove:hover { color: #ef4444; }

/* Analysis */
.ob-analysis-progress { margin: 24px 0; }
.ob-progress-track { height: 6px; background: #eee; border-radius: 3px; overflow: hidden; }
.ob-progress-fill { height: 100%; background: #111; border-radius: 3px; transition: width 0.5s ease; }
.ob-analysis-status { text-align: center; font-size: 13px; color: #666; margin-top: 12px; }

/* Complete */
.ob-complete-icon { font-size: 48px; text-align: center; margin-bottom: 16px; }

/* Fade in animation */
.fade-in { animation: fadeInUp 0.3s ease; }
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Responsive */
@media (max-width: 768px) {
  .ob-sidebar { display: none; }
  .ob-main { padding: 20px; }
  .ob-comp-grid { grid-template-columns: 1fr 1fr; }
}
</style>
