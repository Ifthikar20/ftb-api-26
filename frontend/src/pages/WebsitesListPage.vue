<template>
  <div class="websites-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Projects</h1>
        <p class="page-subtitle">Manage your projects and tracking pixels.</p>
      </div>
      <button class="btn btn-primary" @click="openWizard" :disabled="!appStore.canCreateProject">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Add Project
      </button>
    </div>

    <div v-if="websites.length === 0" class="empty-state">
      <div class="empty-state-icon"><svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="var(--text-muted)" stroke-width="1.5"><circle cx="24" cy="24" r="20"/><line x1="4" y1="24" x2="44" y2="24"/><ellipse cx="24" cy="24" rx="10" ry="20"/></svg></div>
      <h3 class="empty-state-title">No projects yet</h3>
      <p class="empty-state-desc">Add your first project to start tracking visitors, generating leads, and getting AI-powered growth strategies.</p>
      <button class="btn btn-primary" @click="openWizard">Add Your First Project</button>
    </div>

    <div v-else class="websites-grid">
      <div v-for="site in websites" :key="site.id" class="card card-hover website-card" @click="$router.push(`/websites/${site.id}`)">
        <div class="site-header">
          <div class="site-favicon">{{ site.name?.[0]?.toUpperCase() || '?' }}</div>
          <div>
            <h3 class="site-name">{{ site.name }}</h3>
            <p class="site-url text-muted text-sm truncate">{{ site.url }}</p>
          </div>
          <span class="badge" :class="site.pixel_verified ? 'badge-success' : 'badge-warning'">
            {{ site.pixel_verified ? 'Pixel Active' : 'Pixel Pending' }}
          </span>
          <div class="site-actions">
            <button class="btn-action-project" @click.stop="openRename(site)" title="Rename">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.83 2.83 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg>
            </button>
            <button class="btn-action-project btn-action-danger" @click.stop="confirmDelete(site)" title="Delete">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
            </button>
          </div>
        </div>
        <div class="site-stats">
          <div class="site-stat">
            <span class="text-muted text-xs">Visitors</span>
            <span class="font-semibold">—</span>
          </div>
          <div class="site-stat">
            <span class="text-muted text-xs">Leads</span>
            <span class="font-semibold">—</span>
          </div>
          <div class="site-stat">
            <span class="text-muted text-xs">Score</span>
            <span class="font-semibold">—</span>
          </div>
          <div class="site-stat">
            <span class="text-muted text-xs">Status</span>
            <span class="badge badge-success badge-sm">Active</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Onboarding Wizard Modal -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal-content slide-up wizard-modal">
        <div class="modal-header">
          <div class="wizard-step-label">STEP {{ wizardStep }} OF {{ TOTAL_STEPS }}</div>
          <button class="btn-icon btn-ghost" @click="showAddModal = false">✕</button>
        </div>

        <!-- Step 1: Basic Info -->
        <div v-if="wizardStep === 1" class="wizard-body">
          <h2 class="wizard-title">Add your project</h2>
          <p class="wizard-subtitle">Tell us about your site so we can tailor the rest of the setup.</p>
          <div class="form-group">
            <label class="form-label">Project Name</label>
            <input v-model="newSite.name" class="form-input" placeholder="My Awesome Site" required />
          </div>
          <div class="form-group">
            <label class="form-label">Website URL</label>
            <input v-model="newSite.url" class="form-input" type="url" placeholder="https://example.com" required />
          </div>
          <div class="form-group">
            <label class="form-label">Industry <span class="text-muted">(optional)</span></label>
            <input v-model="newSite.industry" class="form-input" placeholder="SaaS, E-commerce, etc." />
          </div>
          <button class="btn btn-primary btn-wizard-continue" :disabled="!newSite.name || !newSite.url" @click="goToCompetitors">
            Continue
          </button>
        </div>

        <!-- Step 2: AI Competitors -->
        <div v-if="wizardStep === 2" class="wizard-body">
          <h2 class="wizard-title">Your AI competitors</h2>
          <p class="wizard-subtitle">
            We found these brands appearing alongside yours in AI answers. You can track up to
            {{ competitorLimit }}. Remove any that aren't relevant or add your own.
          </p>

          <div v-if="detectingCompetitors" class="competitor-loading">
            <div class="spinner"></div>
            <span>Scanning AI answers for brands appearing alongside {{ displayDomain }}...</span>
          </div>

          <div v-else class="competitor-list">
            <div v-for="(c, i) in competitors" :key="c.domain" class="competitor-row">
              <div class="competitor-favicon" :style="{ background: c.color }">
                {{ c.domain[0].toUpperCase() }}
              </div>
              <span class="competitor-domain">{{ c.domain }}</span>
              <button class="competitor-remove" @click="removeCompetitor(i)" aria-label="Remove">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            <div v-if="!competitors.length" class="competitor-empty">
              No competitors added yet. Add one below to get started.
            </div>
          </div>

          <div class="competitor-add-row">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            <input
              v-model="newCompetitorInput"
              class="competitor-add-input"
              placeholder="Add a competitor (e.g. example.com)"
              @keyup.enter="addCompetitor"
            />
            <button v-if="newCompetitorInput.trim()" class="competitor-add-btn" @click="addCompetitor">Add</button>
          </div>

          <button class="btn btn-primary btn-wizard-continue" :disabled="detectingCompetitors" @click="wizardStep = 3">
            Continue
          </button>

          <div class="wizard-dots">
            <span class="dot" :class="{ active: wizardStep >= 1 }"></span>
            <span class="dot" :class="{ active: wizardStep >= 2 }"></span>
            <span class="dot" :class="{ active: wizardStep >= 3 }"></span>
            <span class="dot" :class="{ active: wizardStep >= 4 }"></span>
            <span class="dot" :class="{ active: wizardStep >= 5 }"></span>
          </div>
        </div>

        <!-- Step 3: Topic Source -->
        <div v-if="wizardStep === 3" class="wizard-body">
          <h2 class="wizard-title">How should we find topics?</h2>
          <p class="wizard-subtitle">Choose how you'd like to discover topics for your project.</p>

          <div class="topic-source-list">
            <div
              class="topic-source-card"
              :class="{ selected: topicSource === 'gsc' }"
              @click="topicSource = 'gsc'"
            >
              <div class="topic-radio">
                <span class="topic-radio-dot" v-if="topicSource === 'gsc'"></span>
              </div>
              <div class="topic-source-body">
                <div class="topic-source-title-row">
                  <svg width="18" height="18" viewBox="0 0 48 48">
                    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                  </svg>
                  <span class="topic-source-title">Google Search Console</span>
                  <span class="badge-recommended">Recommended</span>
                </div>
                <p class="topic-source-desc">
                  Use Google Search Console data to find topics based on your site's actual search performance.
                </p>
              </div>
            </div>

            <div
              class="topic-source-card"
              :class="{ selected: topicSource === 'ai' }"
              @click="topicSource = 'ai'"
            >
              <div class="topic-radio">
                <span class="topic-radio-dot" v-if="topicSource === 'ai'"></span>
              </div>
              <div class="topic-source-body">
                <div class="topic-source-title-row">
                  <span class="topic-source-title">AI-powered suggestions</span>
                </div>
                <p class="topic-source-desc">
                  Let our AI analyze your domain and suggest relevant topics automatically.
                </p>
              </div>
            </div>
          </div>

          <!-- GSC informational note (no fake OAuth) -->
          <div v-if="topicSource === 'gsc'" class="gsc-info-panel">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0;color:var(--text-muted)">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            <span>
              Google Search Console is connected from <strong>Settings &rarr; Integrations</strong> after you finish setting up the project. We'll save your topic-source choice and prompt you to authorise GSC there.
            </span>
          </div>

          <button
            class="btn btn-primary btn-wizard-continue"
            @click="wizardStep = 4"
          >
            Continue
          </button>

          <p class="wizard-helper">You can switch methods anytime from settings.</p>

          <div class="wizard-dots">
            <span class="dot" :class="{ active: wizardStep >= 1 }"></span>
            <span class="dot" :class="{ active: wizardStep >= 2 }"></span>
            <span class="dot" :class="{ active: wizardStep >= 3 }"></span>
            <span class="dot" :class="{ active: wizardStep >= 4 }"></span>
            <span class="dot" :class="{ active: wizardStep >= 5 }"></span>
          </div>
        </div>

        <!-- Step 4: Platform Type -->
        <div v-if="wizardStep === 4" class="wizard-body">
          <h2 class="wizard-title">Choose your platform</h2>
          <p class="wizard-subtitle">What platform is your website built on? This helps us optimize tracking and integrations.</p>
          <div class="platform-grid">
            <div v-for="p in platforms" :key="p.id" class="platform-card" :class="{ selected: newSite.platform_type === p.id }" @click="newSite.platform_type = p.id">
              <div class="platform-icon" :style="{ background: p.color }">
                <span v-html="p.icon"></span>
              </div>
              <div class="platform-name">{{ p.name }}</div>
              <div class="platform-desc">{{ p.desc }}</div>
              <div class="platform-check" v-if="newSite.platform_type === p.id">✓</div>
            </div>
          </div>
          <div class="wizard-nav">
            <button class="btn btn-secondary" @click="wizardStep = 3">Back</button>
            <button class="btn btn-primary" :disabled="!newSite.platform_type" @click="createAndGoToPixel">
              {{ adding ? 'Creating...' : 'Continue' }}
            </button>
          </div>
        </div>

        <!-- Step 5: Pixel Installation -->
        <div v-if="wizardStep === 5" class="wizard-body">
          <div v-if="newSite.platform_type === 'shopify'" class="pixel-instructions">
            <div class="pixel-icon" style="background: #96bf48"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 01-8 0"/></svg></div>
            <h4>Shopify Integration</h4>
            <p>Add this script to your Shopify theme. Go to <strong>Online Store → Themes → Edit Code → theme.liquid</strong> and paste before <code>&lt;/head&gt;</code>:</p>
          </div>
          <div v-else-if="newSite.platform_type === 'wordpress'" class="pixel-instructions">
            <div class="pixel-icon" style="background: #21759b"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 8h10M7 12h7M7 16h9"/></svg></div>
            <h4>WordPress Installation</h4>
            <p>Install via <strong>Appearance → Theme Editor → header.php</strong> or use a plugin like <em>Insert Headers and Footers</em>. Paste before <code>&lt;/head&gt;</code>:</p>
          </div>
          <div v-else-if="newSite.platform_type === 'woocommerce'" class="pixel-instructions">
            <div class="pixel-icon" style="background: #7f54b3"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><circle cx="10" cy="19" r="2"/><circle cx="18" cy="19" r="2"/><path d="M2 3h3l2.5 12h11l2.5-8H7"/></svg></div>
            <h4>WooCommerce Installation</h4>
            <p>Same as WordPress — add to your theme's <code>header.php</code> or use a header script plugin. Paste before <code>&lt;/head&gt;</code>:</p>
          </div>
          <div v-else class="pixel-instructions">
            <div class="pixel-icon" style="background: #6366f1"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><path d="M12 2l3 7h7l-5.5 4 2 7L12 16l-6.5 4 2-7L2 9h7z"/></svg></div>
            <h4>Custom Installation</h4>
            <p>Add this script to every page of your website. Paste it into your HTML <code>&lt;head&gt;</code> section:</p>
          </div>

          <div class="pixel-snippet-box">
            <code class="pixel-code">{{ pixelSnippet }}</code>
            <button class="pixel-copy-btn" @click="copyPixel">{{ copied ? 'Copied!' : 'Copy' }}</button>
          </div>

          <div class="wizard-nav">
            <button class="btn btn-secondary" @click="showAddModal = false">Done</button>
            <button class="btn btn-primary" @click="showAddModal = false; $router.push(`/websites/${createdSite?.id}`)">
              Go to Project →
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Rename Modal -->
    <div v-if="renameTarget" class="modal-overlay" @click.self="renameTarget = null">
      <div class="modal-content slide-up">
        <div class="modal-header">
          <h2 class="modal-title">Rename Project</h2>
          <button class="btn-icon btn-ghost" @click="renameTarget = null">✕</button>
        </div>
        <form @submit.prevent="renameWebsite" style="display:flex;flex-direction:column;gap:16px">
          <div class="form-group">
            <label class="form-label">Project Name</label>
            <input v-model="renameName" class="form-input" placeholder="Project name" required />
          </div>
          <div style="display: flex; gap: 8px; justify-content: flex-end;">
            <button type="button" class="btn btn-secondary" @click="renameTarget = null">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="renaming || !renameName.trim()">{{ renaming ? 'Saving...' : 'Save' }}</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="modal-content slide-up">
        <div class="modal-header">
          <h2 class="modal-title">Delete Project</h2>
          <button class="btn-icon btn-ghost" @click="deleteTarget = null">✕</button>
        </div>
        <p style="margin: 0 0 16px; color: var(--text-secondary); font-size: 13px;">Are you sure you want to delete <strong>{{ deleteTarget.name }}</strong>? This will remove all tracking data, analytics, keywords, and audit history. This cannot be undone.</p>
        <div style="display: flex; gap: 8px; justify-content: flex-end;">
          <button class="btn btn-secondary" @click="deleteTarget = null">Cancel</button>
          <button class="btn btn-danger" @click="deleteWebsite" :disabled="deleting">{{ deleting ? 'Deleting...' : 'Delete' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import websitesApi from '@/api/websites'
import competitorsApi from '@/api/competitors'

import { useRouter } from 'vue-router'

const router = useRouter()
const appStore = useAppStore()
const websites = ref([])
const showAddModal = ref(false)
const adding = ref(false)
const deleting = ref(false)
const deleteTarget = ref(null)
const renameTarget = ref(null)
const renameName = ref('')
const renaming = ref(false)
const wizardStep = ref(1)
const createdSite = ref(null)
const copied = ref(false)
const newSite = reactive({ name: '', url: '', industry: '', platform_type: 'custom' })

const TOTAL_STEPS = 5
const competitorLimit = 10

// Step 2: AI Competitors
const competitors = ref([])
const newCompetitorInput = ref('')
const detectingCompetitors = ref(false)

// Step 3: Topic Source
const topicSource = ref('ai')
// GSC OAuth flow lives in Settings -> Integrations once a real handler
// exists in the integrations app; the wizard only captures the user's
// preferred topic-discovery method.

const COMPETITOR_COLORS = ['#111', '#1A1A1A', '#0F766E', '#0EA5E9', '#F59E0B', '#7C3AED', '#DC2626']

const displayDomain = computed(() => {
  try {
    const u = new URL(newSite.url)
    return u.hostname.replace(/^www\./, '')
  } catch {
    return newSite.url || 'your site'
  }
})

function normalizeDomain(raw) {
  if (!raw) return ''
  let s = raw.trim().toLowerCase()
  s = s.replace(/^https?:\/\//, '').replace(/^www\./, '')
  s = s.split('/')[0]
  return s
}

async function goToCompetitors() {
  wizardStep.value = 2
  if (competitors.value.length) return
  detectingCompetitors.value = true
  try {
    // Real LLM-based suggestion — POSTs to /api/v1/competitors/suggest/.
    // Returns an empty list if Claude can't produce parseable JSON or if
    // ANTHROPIC_API_KEY isn't configured. The UI must render an empty
    // state in that case rather than fall back to seed data.
    const { data } = await competitorsApi.suggest({
      name: newSite.name,
      industry: newSite.industry,
      url: newSite.url,
      description: '',
    })
    const suggested = data?.data?.suggested || data?.suggested || []
    competitors.value = suggested.map((entry, i) => ({
      domain: entry.domain,
      name: entry.name || entry.domain,
      reason: entry.reason || '',
      color: COMPETITOR_COLORS[i % COMPETITOR_COLORS.length],
    }))
  } catch (err) {
    console.error('Competitor suggest failed', err)
    competitors.value = []
  } finally {
    detectingCompetitors.value = false
  }
}

function addCompetitor() {
  const domain = normalizeDomain(newCompetitorInput.value)
  if (!domain) return
  if (competitors.value.some(c => c.domain === domain)) {
    newCompetitorInput.value = ''
    return
  }
  if (competitors.value.length >= competitorLimit) return
  competitors.value.push({
    domain,
    color: COMPETITOR_COLORS[competitors.value.length % COMPETITOR_COLORS.length],
  })
  newCompetitorInput.value = ''
}

function removeCompetitor(i) {
  competitors.value.splice(i, 1)
}


const platforms = [
  { id: 'shopify', name: 'Shopify', desc: 'E-commerce on Shopify', color: '#96bf48', icon: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 01-8 0"/></svg>' },
  { id: 'wordpress', name: 'WordPress', desc: 'Blog or CMS', color: '#21759b', icon: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 8h10M7 12h7M7 16h9"/></svg>' },
  { id: 'woocommerce', name: 'WooCommerce', desc: 'WordPress + E-commerce', color: '#7f54b3', icon: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><circle cx="10" cy="19" r="2"/><circle cx="18" cy="19" r="2"/><path d="M2 3h3l2.5 12h11l2.5-8H7"/></svg>' },
  { id: 'custom', name: 'Custom / Other', desc: 'Any other platform', color: '#6366f1', icon: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><path d="M12 2l3 7h7l-5.5 4 2 7L12 16l-6.5 4 2-7L2 9h7z"/></svg>' },
]

const pixelSnippet = computed(() => {
  if (!createdSite.value) return ''
  return `<script src="https://fetchbot.ai/pixel/growthpilot.min.js" data-key="${createdSite.value.pixel_key}"><\/script>`
})

onMounted(async () => {
  try {
    const { data } = await websitesApi.list()
    websites.value = data?.data || data || []
    appStore.setWebsites(websites.value)
  } catch { /* empty */ }
})

function openRename(site) {
  renameTarget.value = site
  renameName.value = site.name
}

async function renameWebsite() {
  if (!renameTarget.value || !renameName.value.trim()) return
  renaming.value = true
  try {
    await websitesApi.update(renameTarget.value.id, { name: renameName.value.trim() })
    const site = websites.value.find(s => s.id === renameTarget.value.id)
    if (site) site.name = renameName.value.trim()
    appStore.setWebsites(websites.value)
    renameTarget.value = null
  } catch (e) { console.error('Rename failed', e) }
  finally { renaming.value = false }
}

function confirmDelete(site) {
  if (websites.value.length <= 1) {
    alert('You must have at least one project. Add a new project before deleting this one.')
    return
  }
  deleteTarget.value = site
}

async function deleteWebsite() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    const deletedId = deleteTarget.value.id
    await websitesApi.delete(deletedId)
    websites.value = websites.value.filter(s => s.id !== deletedId)
    appStore.setWebsites(websites.value)
    deleteTarget.value = null
    if (appStore.activeWebsite?.id === deletedId) {
      if (websites.value.length) {
        appStore.setActiveWebsite(websites.value[0])
      } else {
        router.push('/websites')
      }
    }
  } catch (e) { console.error('Delete failed', e) }
  finally { deleting.value = false }
}

async function createAndGoToPixel() {
  adding.value = true
  try {
    const { data } = await websitesApi.create(newSite)
    const site = data?.data || data
    createdSite.value = site
    websites.value.push(site)
    appStore.setWebsites(websites.value)
    wizardStep.value = 5
  } catch (e) { console.error('Create failed', e) }
  finally { adding.value = false }
}

function copyPixel() {
  navigator.clipboard.writeText(pixelSnippet.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

function openWizard() {
  wizardStep.value = 1
  createdSite.value = null
  copied.value = false
  newSite.name = ''
  newSite.url = ''
  newSite.industry = ''
  newSite.platform_type = 'custom'
  competitors.value = []
  newCompetitorInput.value = ''
  detectingCompetitors.value = false
  topicSource.value = 'ai'
  showAddModal.value = true
}
</script>

<style scoped>
.websites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 16px;
}

.website-card {
  cursor: pointer;
}

.site-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.site-favicon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: var(--brand-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--font-lg);
  color: #fff;
  flex-shrink: 0;
}

.site-name {
  font-weight: 600;
  font-size: var(--font-md);
}

.site-url {
  max-width: 200px;
}

.site-header .badge {
  margin-left: auto;
}

.site-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.site-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.site-actions {
  display: flex;
  gap: 4px;
  margin-left: auto;
  flex-shrink: 0;
}

.btn-action-project {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  flex-shrink: 0;
}
.btn-action-project:hover {
  border-color: var(--border-hover);
  background: var(--bg-surface);
  color: var(--text-primary);
}
.btn-action-danger:hover {
  border-color: #ef4444;
  background: rgba(239,68,68,0.08);
  color: #ef4444;
}

/* ── Onboarding Wizard ── */
.wizard-modal { max-width: 560px; }
.wizard-step-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 1.2px;
}
.wizard-title {
  font-size: 26px;
  font-weight: 800;
  color: var(--text-primary);
  margin: 4px 0 8px;
  line-height: 1.2;
}
.wizard-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.55;
  margin: 0 0 20px;
}
.wizard-body { display: flex; flex-direction: column; gap: 14px; }
.wizard-nav { display: flex; gap: 12px; justify-content: space-between; margin-top: 8px; }
.wizard-helper {
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}
.btn-wizard-continue {
  width: 100%;
  padding: 14px 24px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 10px;
  margin-top: 8px;
}

/* Progress dots */
.wizard-dots {
  display: flex;
  gap: 8px;
  margin-top: 18px;
  justify-content: flex-start;
}
.wizard-dots .dot {
  width: 28px;
  height: 4px;
  border-radius: 2px;
  background: var(--border-color);
  transition: background 0.2s;
}
.wizard-dots .dot.active { background: var(--brand-accent, #4F46E5); }

/* Competitor list */
.competitor-loading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  font-size: 14px;
  color: var(--text-secondary);
}
.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid var(--border-color);
  border-top-color: var(--brand-accent, #4F46E5);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.competitor-list {
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  background: var(--bg-base, #fff);
  max-height: 280px;
  overflow-y: auto;
}
.competitor-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}
.competitor-row:last-child { border-bottom: none; }
.competitor-favicon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 13px;
  flex-shrink: 0;
}
.competitor-domain {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}
.competitor-remove {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.15s;
}
.competitor-remove:hover {
  background: var(--bg-surface);
  color: var(--color-danger, #DC2626);
}
.competitor-empty {
  padding: 24px;
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
}

.competitor-add-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
  color: var(--brand-accent, #4F46E5);
}
.competitor-add-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 14px;
  color: var(--text-primary);
  outline: none;
  padding: 6px 0;
}
.competitor-add-input::placeholder {
  color: var(--brand-accent, #4F46E5);
  font-weight: 500;
}
.competitor-add-btn {
  padding: 4px 12px;
  background: var(--brand-accent, #4F46E5);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

/* Topic Source */
.topic-source-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.topic-source-card {
  display: flex;
  gap: 14px;
  padding: 16px 18px;
  border: 2px solid var(--border-color);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.15s;
  background: var(--bg-base, #fff);
}
.topic-source-card:hover { border-color: var(--text-muted); }
.topic-source-card.selected {
  border-color: var(--brand-accent, #4F46E5);
  background: rgba(79, 70, 229, 0.04);
}
.topic-radio {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid var(--border-color);
  flex-shrink: 0;
  margin-top: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.topic-source-card.selected .topic-radio { border-color: var(--brand-accent, #4F46E5); }
.topic-radio-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--brand-accent, #4F46E5);
}
.topic-source-body { flex: 1; }
.topic-source-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}
.topic-source-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}
.topic-source-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
}
.badge-recommended {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid var(--brand-accent, #4F46E5);
  color: var(--brand-accent, #4F46E5);
  font-size: 11px;
  font-weight: 600;
}

/* GSC informational note (real OAuth flow lives in Settings -> Integrations) */
.gsc-info-panel {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--bg-surface);
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.platform-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.platform-card { position: relative; padding: 16px; border-radius: 14px; border: 2px solid var(--border-color); cursor: pointer; text-align: center; transition: all 0.2s; background: var(--bg-surface); }
.platform-card:hover { border-color: var(--text-muted); transform: translateY(-1px); }
.platform-card.selected { border-color: var(--brand-accent, #6366f1); background: rgba(99, 102, 241, 0.04); }
.platform-icon { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; margin: 0 auto 10px; font-size: 22px; }
.platform-name { font-weight: 600; font-size: var(--font-sm); margin-bottom: 2px; }
.platform-desc { font-size: var(--font-xs); color: var(--text-muted); }
.platform-check { position: absolute; top: 8px; right: 10px; color: var(--brand-accent, #6366f1); font-weight: 700; font-size: 14px; }

.pixel-instructions { text-align: center; padding: 8px 0; }
.pixel-instructions h4 { margin: 8px 0 4px; font-weight: 700; }
.pixel-instructions p { font-size: var(--font-sm); color: var(--text-secondary); margin: 0; line-height: 1.5; }
.pixel-icon { width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center; margin: 0 auto; font-size: 24px; }
.pixel-snippet-box { position: relative; background: #1a1a2e; border-radius: 10px; padding: 16px; margin: 4px 0; }
.pixel-code { display: block; color: #9effa3; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 12px; word-break: break-all; line-height: 1.6; white-space: pre-wrap; }
.pixel-copy-btn { position: absolute; top: 8px; right: 8px; background: rgba(255,255,255,0.1); border: none; color: #fff; padding: 4px 10px; border-radius: 6px; cursor: pointer; font-size: 12px; transition: background 0.2s; }
.pixel-copy-btn:hover { background: rgba(255,255,255,0.2); }
</style>
