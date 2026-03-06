<template>
  <div class="websites-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Projects</h1>
        <p class="page-subtitle">Manage your projects and tracking pixels.</p>
      </div>
      <button class="btn btn-primary" @click="showAddModal = true" :disabled="!appStore.canCreateProject">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Add Project
      </button>
    </div>

    <div v-if="websites.length === 0" class="empty-state">
      <div class="empty-state-icon"><svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="var(--text-muted)" stroke-width="1.5"><circle cx="24" cy="24" r="20"/><line x1="4" y1="24" x2="44" y2="24"/><ellipse cx="24" cy="24" rx="10" ry="20"/></svg></div>
      <h3 class="empty-state-title">No projects yet</h3>
      <p class="empty-state-desc">Add your first project to start tracking visitors, generating leads, and getting AI-powered growth strategies.</p>
      <button class="btn btn-primary" @click="showAddModal = true">Add Your First Project</button>
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

    <!-- Add Website Modal -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal-content slide-up">
        <div class="modal-header">
          <h2 class="modal-title">Add Website</h2>
          <button class="btn-icon btn-ghost" @click="showAddModal = false">✕</button>
        </div>
        <form @submit.prevent="addWebsite" style="display:flex;flex-direction:column;gap:16px">
          <div class="form-group">
            <label class="form-label">Website Name</label>
            <input v-model="newSite.name" class="form-input" placeholder="My Awesome Site" required />
          </div>
          <div class="form-group">
            <label class="form-label">URL</label>
            <input v-model="newSite.url" class="form-input" type="url" placeholder="https://example.com" required />
          </div>
          <div class="form-group">
            <label class="form-label">Industry <span class="text-muted">(optional)</span></label>
            <input v-model="newSite.industry" class="form-input" placeholder="SaaS, E-commerce, etc." />
          </div>
          <button type="submit" class="btn btn-primary w-full" :disabled="adding">
            {{ adding ? 'Adding...' : 'Add Website' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import websitesApi from '@/api/websites'

const appStore = useAppStore()
const websites = ref([])
const showAddModal = ref(false)
const adding = ref(false)
const newSite = reactive({ name: '', url: '', industry: '' })

onMounted(async () => {
  try {
    const { data } = await websitesApi.list()
    websites.value = data?.data || data || []
    appStore.setWebsites(websites.value)
  } catch { /* empty */ }
})

async function addWebsite() {
  adding.value = true
  try {
    const { data } = await websitesApi.create(newSite)
    const site = data?.data || data
    websites.value.push(site)
    appStore.setWebsites(websites.value)
    showAddModal.value = false
    newSite.name = ''
    newSite.url = ''
    newSite.industry = ''
  } catch { /* handle */ }
  finally { adding.value = false }
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
</style>
