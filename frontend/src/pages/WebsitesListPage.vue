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
      <div class="modal-content slide-up" style="max-width: 560px">
        <div class="modal-header">
          <h2 class="modal-title">{{ wizardStep === 1 ? 'Add Project' : wizardStep === 2 ? 'Choose Platform' : 'Install Pixel' }}</h2>
          <button class="btn-icon btn-ghost" @click="showAddModal = false">✕</button>
        </div>

        <!-- Progress Bar -->
        <div class="wizard-progress">
          <div class="wizard-progress-bar" :style="{ width: (wizardStep / 3 * 100) + '%' }"></div>
        </div>
        <div class="wizard-steps-label">
          <span :class="{ active: wizardStep >= 1 }">1. Basics</span>
          <span :class="{ active: wizardStep >= 2 }">2. Platform</span>
          <span :class="{ active: wizardStep >= 3 }">3. Pixel</span>
        </div>

        <!-- Step 1: Basic Info -->
        <div v-if="wizardStep === 1" class="wizard-body">
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
          <button class="btn btn-primary w-full" :disabled="!newSite.name || !newSite.url" @click="wizardStep = 2">
            Next →
          </button>
        </div>

        <!-- Step 2: Platform Type -->
        <div v-if="wizardStep === 2" class="wizard-body">
          <p class="wizard-desc">What platform is your website built on? This helps us optimize tracking and integrations.</p>
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
            <button class="btn btn-secondary" @click="wizardStep = 1">← Back</button>
            <button class="btn btn-primary" :disabled="!newSite.platform_type" @click="createAndGoToPixel">
              {{ adding ? 'Creating...' : 'Next →' }}
            </button>
          </div>
        </div>

        <!-- Step 3: Pixel Installation -->
        <div v-if="wizardStep === 3" class="wizard-body">
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
    wizardStep.value = 3
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
.wizard-progress { height: 4px; background: var(--border-color); border-radius: 4px; margin: 0 0 12px; }
.wizard-progress-bar { height: 100%; background: var(--brand-accent, #6366f1); border-radius: 4px; transition: width 0.3s ease; }
.wizard-steps-label { display: flex; justify-content: space-between; margin-bottom: 20px; font-size: var(--font-xs); color: var(--text-muted); }
.wizard-steps-label .active { color: var(--text-primary); font-weight: 600; }
.wizard-body { display: flex; flex-direction: column; gap: 16px; }
.wizard-desc { font-size: var(--font-sm); color: var(--text-secondary); margin: 0; }
.wizard-nav { display: flex; gap: 12px; justify-content: space-between; margin-top: 8px; }

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
