<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': appStore.sidebarCollapsed }">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="brand-mark">FB</div>
        <span v-if="!appStore.sidebarCollapsed" class="brand-name">FetchBot</span>
      </div>

      <!-- Project Selector -->
      <div v-if="!appStore.sidebarCollapsed" class="project-select">
        <select class="form-input" @change="switchWebsite($event.target.value)" style="font-size:var(--font-sm);padding:8px 12px">
          <option v-for="w in appStore.websites" :key="w.id" :value="w.id" :selected="w.id === appStore.activeWebsite?.id">
            {{ w.name }}
          </option>
        </select>
        <div class="project-limit-row">
          <span class="project-limit-badge">{{ appStore.projectLimitLabel }}</span>
          <button class="btn-add-project" :disabled="!appStore.canCreateProject" @click="showAddProject = true" :title="appStore.canCreateProject ? 'Add a new project' : 'Upgrade your plan to add more'">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2"><line x1="7" y1="2" x2="7" y2="12"/><line x1="2" y1="7" x2="12" y2="7"/></svg>
          </button>
        </div>
      </div>

      <!-- Nav -->
      <nav class="sidebar-nav">
        <div class="nav-section-label">Overview</div>
        <router-link to="/dashboard" class="nav-link" active-class="active">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><rect x="1" y="1" width="6" height="6" rx="1"/><rect x="9" y="1" width="6" height="6" rx="1"/><rect x="1" y="9" width="6" height="6" rx="1"/><rect x="9" y="9" width="6" height="6" rx="1"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Dashboard</span>
        </router-link>
        <router-link to="/websites" class="nav-link" active-class="active">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="1" y1="8" x2="15" y2="8" stroke="currentColor" stroke-width="1.5"/><ellipse cx="8" cy="8" rx="3" ry="7" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Projects</span>
        </router-link>

        <div class="nav-section-label">Intelligence</div>
        <router-link :to="analyticsRoute" class="nav-link" active-class="active">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M2 14V6l4-4 4 4 4-4v12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Analytics</span>
        </router-link>
        <router-link :to="leadsRoute" class="nav-link" active-class="active">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><circle cx="8" cy="5" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M2 14c0-3 3-5 6-5s6 2 6 5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Leads</span>
        </router-link>
        <router-link :to="competitorsRoute" class="nav-link" active-class="active">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><rect x="2" y="4" width="5" height="10" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="2" width="5" height="12" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Competitors</span>
        </router-link>
        <router-link :to="auditsRoute" class="nav-link" active-class="active">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="11" y1="11" x2="14" y2="14" stroke="currentColor" stroke-width="1.5"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Audits</span>
        </router-link>
        <router-link :to="strategyRoute" class="nav-link" active-class="active">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1l2 4h4l-3 3 1 4-4-2-4 2 1-4-3-3h4z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Strategy</span>
        </router-link>

        <div class="nav-section-label">Account</div>
        <router-link to="/billing" class="nav-link" active-class="active">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><rect x="1" y="3" width="14" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="1" y1="7" x2="15" y2="7" stroke="currentColor" stroke-width="1.5"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Billing</span>
        </router-link>
        <router-link to="/settings" class="nav-link" active-class="active">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><circle cx="8" cy="8" r="2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3 3l1.5 1.5M11.5 11.5L13 13M13 3l-1.5 1.5M4.5 11.5L3 13" stroke="currentColor" stroke-width="1.5"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Settings</span>
        </router-link>
      </nav>

      <!-- User Footer -->
      <div class="sidebar-footer" v-if="!appStore.sidebarCollapsed">
        <div class="user-block">
          <div class="avatar avatar-sm">{{ userInitials }}</div>
          <div class="user-info">
            <div class="user-name">{{ authStore.user?.full_name || 'User' }}</div>
            <div class="user-plan">{{ authStore.user?.plan || 'Free' }}</div>
          </div>
        </div>
        <button class="btn-ghost btn-icon" @click="handleLogout" title="Logout" style="color:var(--text-muted)">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 2H3v12h3M11 4l4 4-4 4M7 8h8"/></svg>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="main-wrapper">
      <header class="topbar">
        <button class="btn-icon sidebar-toggle" @click="appStore.toggleSidebar">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="5" x2="15" y2="5"/><line x1="3" y1="9" x2="15" y2="9"/><line x1="3" y1="13" x2="15" y2="13"/></svg>
        </button>

        <div class="topbar-search">
          <input class="form-input" placeholder="Search..." style="padding:8px 16px;font-size:var(--font-sm);border-radius:var(--radius-full);background:var(--bg-surface)" />
        </div>

        <div class="topbar-actions">
          <!-- Theme Toggle -->
          <button class="theme-toggle" @click="appStore.toggleTheme" :title="appStore.theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'">
            <svg v-if="appStore.theme === 'light'" width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M15 10A7 7 0 1 1 8 3a5 5 0 0 0 7 7z"/></svg>
            <svg v-else width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="9" cy="9" r="4"/><path d="M9 1v2M9 15v2M1 9h2M15 9h2M3.3 3.3l1.4 1.4M13.3 13.3l1.4 1.4M14.7 3.3l-1.4 1.4M4.7 13.3l-1.4 1.4"/></svg>
          </button>

          <!-- Notifications -->
          <button class="topbar-btn" title="Notifications">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13 6a4 4 0 0 0-8 0c0 5-2 6-2 6h12s-2-1-2-6M7 15a2 2 0 0 0 4 0"/></svg>
            <span v-if="appStore.unreadCount" class="notif-dot"></span>
          </button>
        </div>
      </header>

      <main class="page-content" :style="{ background: pageTint }">
        <router-view />
      </main>
    </div>
    <!-- Add Project Modal -->
    <div v-if="showAddProject" class="modal-overlay" @click.self="showAddProject = false">
      <div class="modal-card">
        <h3 class="card-title" style="margin-bottom:16px">Add New Project</h3>
        <div v-if="!appStore.canCreateProject" class="upgrade-notice">
          <p>Your <strong>{{ appStore.userPlan }}</strong> plan allows {{ appStore.projectLimit }} project(s).</p>
          <p style="margin-top:8px">Upgrade to <strong>Growth</strong> for up to 5 projects.</p>
          <router-link to="/billing" class="btn btn-primary" style="margin-top:16px" @click="showAddProject = false">View Plans</router-link>
        </div>
        <template v-else>
          <div style="margin-bottom:12px">
            <label class="form-label">Project Name</label>
            <input v-model="newProject.name" class="form-input" placeholder="My Website" />
          </div>
          <div style="margin-bottom:12px">
            <label class="form-label">Website URL</label>
            <input v-model="newProject.url" class="form-input" placeholder="https://example.com" />
          </div>
          <div style="margin-bottom:16px">
            <label class="form-label">Industry (optional)</label>
            <input v-model="newProject.industry" class="form-input" placeholder="SaaS, E-commerce, etc." />
          </div>
          <div class="flex gap-8" style="justify-content:flex-end">
            <button class="btn btn-secondary" @click="showAddProject = false">Cancel</button>
            <button class="btn btn-primary" @click="createProject" :disabled="!newProject.name || !newProject.url || creating">{{ creating ? 'Creating...' : 'Create Project' }}</button>
          </div>
          <p v-if="createError" class="text-sm" style="color:var(--color-danger);margin-top:12px">{{ createError }}</p>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import websitesApi from '@/api/websites'
import billingApi from '@/api/billing'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const appStore = useAppStore()

// Add project modal state
const showAddProject = ref(false)
const creating = ref(false)
const createError = ref('')
const newProject = ref({ name: '', url: '', industry: '' })

const userInitials = computed(() => {
  const name = authStore.user?.full_name || ''
  return name.split(' ').map(n => n[0]).filter(Boolean).join('').toUpperCase().slice(0, 2)
})

const websiteId = computed(() => appStore.activeWebsite?.id)
const analyticsRoute = computed(() => websiteId.value ? `/analytics/${websiteId.value}` : '/websites')
const leadsRoute = computed(() => websiteId.value ? `/leads/${websiteId.value}` : '/websites')
const competitorsRoute = computed(() => websiteId.value ? `/competitors/${websiteId.value}` : '/websites')
const auditsRoute = computed(() => websiteId.value ? `/audits/${websiteId.value}` : '/websites')
const strategyRoute = computed(() => websiteId.value ? `/strategy/${websiteId.value}` : '/websites')

// Dynamic page background tint based on current route
const pageTint = computed(() => {
  const path = route.path
  if (path.startsWith('/dashboard') || path === '/') return 'var(--tint-dashboard)'
  if (path.startsWith('/analytics')) return 'var(--tint-analytics)'
  if (path.startsWith('/leads')) return 'var(--tint-leads)'
  if (path.startsWith('/competitors')) return 'var(--tint-competitors)'
  if (path.startsWith('/audits')) return 'var(--tint-audits)'
  if (path.startsWith('/strategy')) return 'var(--tint-strategy)'
  if (path.startsWith('/billing')) return 'var(--tint-billing)'
  if (path.startsWith('/settings')) return 'var(--tint-settings)'
  if (path.startsWith('/websites')) return 'var(--tint-dashboard)'
  return 'var(--bg-page-tint)'
})

function switchWebsite(id) {
  const website = appStore.websites.find(w => w.id === id)
  if (!website) return
  appStore.setActiveWebsite(website)

  // Re-route current page to use the new project ID
  const path = route.path
  const routeMap = [
    { prefix: '/analytics/', target: `/analytics/${id}` },
    { prefix: '/leads/', target: `/leads/${id}` },
    { prefix: '/competitors/', target: `/competitors/${id}` },
    { prefix: '/audits/', target: `/audits/${id}` },
    { prefix: '/strategy/', target: `/strategy/${id}` },
    { prefix: '/websites/', target: `/websites/${id}` },
  ]
  const match = routeMap.find(r => path.startsWith(r.prefix))
  if (match) {
    router.push(match.target)
  }
  // Dashboard, billing, settings don't have websiteId — store update is enough
}

async function createProject() {
  creating.value = true
  createError.value = ''
  try {
    const { data } = await websitesApi.create(newProject.value)
    const project = data?.data || data
    appStore.websites.push(project)
    appStore.setActiveWebsite(project)
    newProject.value = { name: '', url: '', industry: '' }
    showAddProject.value = false
    router.push(`/websites/${project.id}`)
  } catch (err) {
    const resp = err.response?.data
    if (resp?.error === 'project_limit_reached') {
      createError.value = resp.message
    } else {
      createError.value = resp?.detail || resp?.url?.[0] || 'Failed to create project.'
    }
  } finally {
    creating.value = false
  }
}

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}

onMounted(async () => {
  if (!authStore.user) {
    try { await authStore.fetchMe() } catch {}
  }
  try {
    const { data } = await websitesApi.list()
    appStore.setWebsites(data?.results || data || [])
  } catch {}
  // Fetch plan info for project limits
  try {
    const { data } = await billingApi.getCurrent()
    const plan = data?.plan || data?.data?.plan || 'starter'
    const limits = { starter: 1, growth: 5, scale: -1 }
    appStore.setPlanInfo(plan, limits[plan] ?? 1)
  } catch {}
})
</script>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
}

/* Sidebar */
.sidebar {
  width: var(--sidebar-width);
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 100;
  transition: width var(--transition-base);
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-collapsed .sidebar { width: var(--sidebar-collapsed); }

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 16px;
}

.brand-mark {
  width: 32px;
  height: 32px;
  background: var(--text-primary);
  color: var(--text-inverse);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: var(--font-sm);
  letter-spacing: -0.02em;
  flex-shrink: 0;
}

.brand-name {
  font-family: var(--font-display);
  font-size: var(--font-xl);
  font-weight: 400;
  color: var(--text-primary);
}

.project-select { padding: 0 16px 16px; }

.project-limit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.project-limit-badge {
  font-size: var(--font-xs);
  color: var(--text-muted);
  font-weight: 500;
}

.btn-add-project {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-add-project:hover:not(:disabled) {
  border-color: var(--text-primary);
  color: var(--text-primary);
  background: var(--bg-card);
}

.btn-add-project:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.sidebar-nav { flex: 1; padding: 0 12px; }

.nav-section-label {
  font-size: var(--font-xs);
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  padding: 20px 8px 8px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: var(--radius-md);
  font-size: var(--font-base);
  font-weight: 500;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  text-decoration: none;
}

.nav-link:hover {
  color: var(--text-primary);
  background: rgba(0, 0, 0, 0.04);
}

[data-theme="dark"] .nav-link:hover { background: rgba(255, 255, 255, 0.06); }

.nav-link.active {
  color: var(--text-primary);
  background: var(--bg-page-tint);
  font-weight: 600;
}

.nav-icon { width: 24px; text-align: center; display: flex; align-items: center; justify-content: center; }
.nav-text { white-space: nowrap; }

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.user-block { display: flex; align-items: center; gap: 10px; }
.user-name { font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); }
.user-plan { font-size: var(--font-xs); color: var(--text-muted); text-transform: capitalize; }

/* Main */
.main-wrapper {
  flex: 1;
  margin-left: var(--sidebar-width);
  transition: margin-left var(--transition-base);
  display: flex;
  flex-direction: column;
}

.sidebar-collapsed .main-wrapper { margin-left: var(--sidebar-collapsed); }

/* Topbar */
.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  height: var(--topbar-height);
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  padding: 0 28px;
  gap: 16px;
}

.sidebar-toggle {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
  transition: color var(--transition-fast);
  padding: 4px;
  display: flex;
  align-items: center;
}

.sidebar-toggle:hover { color: var(--text-primary); }
.topbar-search { flex: 1; max-width: 360px; }

.topbar-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.topbar-btn {
  position: relative;
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  transition: color var(--transition-fast);
}

.topbar-btn:hover { color: var(--text-primary); }

.notif-dot {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 7px;
  height: 7px;
  background: var(--color-danger);
  border-radius: 50%;
}

/* Page Content */
.page-content {
  flex: 1;
  padding: 28px;
  background: var(--bg-page-tint);
  min-height: calc(100vh - var(--topbar-height));
}

/* Responsive */
@media (max-width: 768px) {
  .sidebar { transform: translateX(-100%); width: var(--sidebar-width); }
  .main-wrapper { margin-left: 0; }
  .page-content { padding: 16px; }
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: var(--bg-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 28px;
  width: 440px;
  max-width: 90vw;
  box-shadow: var(--shadow-lg);
}

.upgrade-notice {
  font-size: var(--font-sm);
  color: var(--text-secondary);
  text-align: center;
  padding: 12px 0;
}

.form-label {
  display: block;
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}
</style>
