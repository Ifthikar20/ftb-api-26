<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': appStore.sidebarCollapsed }">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <img src="/images/fb-logo.png" alt="FetchBot" class="brand-logo" />
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
        <router-link to="/dashboard" class="nav-link" exact-active-class="active" style="--nav-color: #5B8DEF">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><rect x="1" y="1" width="6" height="6" rx="1"/><rect x="9" y="1" width="6" height="6" rx="1"/><rect x="1" y="9" width="6" height="6" rx="1"/><rect x="9" y="9" width="6" height="6" rx="1"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Dashboard</span>
        </router-link>
        <router-link to="/websites" class="nav-link" exact-active-class="active" style="--nav-color: #8b5cf6">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="1" y1="8" x2="15" y2="8" stroke="currentColor" stroke-width="1.5"/><ellipse cx="8" cy="8" rx="3" ry="7" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Projects</span>
        </router-link>

        <div class="nav-section-label">Intelligence</div>
        <router-link :to="analyticsRoute" class="nav-link" exact-active-class="active" style="--nav-color: #f97316">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M2 14V6l4-4 4 4 4-4v12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Analytics</span>
        </router-link>
        <router-link :to="leadsRoute" class="nav-link" exact-active-class="active" style="--nav-color: #22c55e">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><circle cx="8" cy="5" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M2 14c0-3 3-5 6-5s6 2 6 5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Leads</span>
        </router-link>

        <router-link :to="auditsRoute" class="nav-link" exact-active-class="active" style="--nav-color: #06b6d4">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="11" y1="11" x2="14" y2="14" stroke="currentColor" stroke-width="1.5"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Audits</span>
        </router-link>
        <router-link :to="heatmapRoute" class="nav-link" exact-active-class="active" style="--nav-color: #ef4444">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="1" width="14" height="14" rx="2"/><circle cx="6" cy="6" r="2" fill="currentColor" opacity="0.6"/><circle cx="10" cy="5" r="1.5" fill="currentColor" opacity="0.4"/><circle cx="8" cy="10" r="2.5" fill="currentColor" opacity="0.8"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Heatmaps</span>
        </router-link>
        <router-link :to="keywordsRoute" class="nav-link" exact-active-class="active" style="--nav-color: #eab308">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 12l4-4 3 3 5-7"/><circle cx="14" cy="4" r="1.5" fill="currentColor"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Keywords</span>
        </router-link>
        <router-link :to="strategyRoute" class="nav-link" exact-active-class="active" style="--nav-color: #a855f7">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1l2 4h4l-3 3 1 4-4-2-4 2 1-4-3-3h4z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Strategy</span>
        </router-link>
        <router-link :to="agentsRoute" class="nav-link" exact-active-class="active" style="--nav-color: #14b8a6">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="6" r="3"/><path d="M3 14c0-3 2.2-5 5-5s5 2 5 5"/><path d="M12 4l2-2M4 4L2 2" stroke-linecap="round"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Agents</span>
        </router-link>
        <router-link :to="campaignsRoute" class="nav-link" exact-active-class="active" style="--nav-color: #3b82f6">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 3h12c.6 0 1 .4 1 1v8c0 .6-.4 1-1 1H2c-.6 0-1-.4-1-1V4c0-.6.4-1 1-1z"/><polyline points="14,4 8,9 2,4"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Campaigns</span>
        </router-link>
        <router-link :to="llmRankingRoute" class="nav-link" exact-active-class="active" style="--nav-color: #ec4899">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M8 4v4l3 2"/><path d="M5 2l6 0" stroke-linecap="round"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">LLM Ranking</span>
        </router-link>

        <router-link to="/rewards" class="nav-link" exact-active-class="active" style="--nav-color: #f59e0b">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 1l2 4h4l-3 3 1 4-4-2-4 2 1-4-3-3h4z" stroke-linejoin="round"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Rewards</span>
        </router-link>

        <router-link to="/integrations" class="nav-link" exact-active-class="active" style="--nav-color: #22c55e">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M10 13a5 5 0 007.5.5l3-3a5 5 0 00-7-7l-1.5 1.5"/><path d="M14 11a5 5 0 00-7.5-.5l-3 3a5 5 0 007 7l1.5-1.5"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Integrations</span>
        </router-link>

        <div class="nav-section-label">Account</div>
        <router-link to="/billing" class="nav-link" exact-active-class="active" style="--nav-color: #64748b">
          <span class="nav-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><rect x="1" y="3" width="14" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="1" y1="7" x2="15" y2="7" stroke="currentColor" stroke-width="1.5"/></svg></span>
          <span v-if="!appStore.sidebarCollapsed" class="nav-text">Billing</span>
        </router-link>
        <router-link to="/settings" class="nav-link" exact-active-class="active" style="--nav-color: #78716c">
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
        <button class="btn-icon sidebar-toggle" @click="appStore.toggleSidebar" :title="appStore.sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'">
          <!-- Collapse: panel + left arrow. Expand: panel + right arrow. -->
          <svg v-if="!appStore.sidebarCollapsed" width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.75">
            <rect x="1" y="1" width="16" height="16" rx="2.5" />
            <line x1="6" y1="1" x2="6" y2="17" />
            <polyline points="10,6 8,9 10,12" />
          </svg>
          <svg v-else width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.75">
            <rect x="1" y="1" width="16" height="16" rx="2.5" />
            <line x1="6" y1="1" x2="6" y2="17" />
            <polyline points="8,6 10,9 8,12" />
          </svg>
        </button>

        <div class="topbar-search" @click="openSearch">
          <div class="search-trigger">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="6" cy="6" r="4.5"/><line x1="9.5" y1="9.5" x2="13" y2="13"/></svg>
            <span class="search-placeholder">Search pages...</span>
            <span class="search-shortcut">{{ isMac ? '⌘' : 'Ctrl' }}+K</span>
          </div>
        </div>

        <div class="topbar-actions">
          <!-- Gamification Points Badge -->
          <router-link to="/rewards" class="points-badge" title="Your rewards">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1l2 4h4l-3 3 1 4-4-2-4 2 1-4-3-3h4z"/></svg>
            <span class="points-value">{{ userPoints }} pts</span>
            <span class="points-level">Lv {{ userLevel }}</span>
          </router-link>

          <!-- Theme Toggle -->
          <button class="theme-toggle" @click="appStore.toggleTheme" :title="appStore.theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'">
            <svg v-if="appStore.theme === 'light'" width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M15 10A7 7 0 1 1 8 3a5 5 0 0 0 7 7z"/></svg>
            <svg v-else width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="9" cy="9" r="4"/><path d="M9 1v2M9 15v2M1 9h2M15 9h2M3.3 3.3l1.4 1.4M13.3 13.3l1.4 1.4M14.7 3.3l-1.4 1.4M4.7 13.3l-1.4 1.4"/></svg>
          </button>

          <!-- Help Button -->
          <HelpButton />

          <!-- Notifications -->
          <button class="topbar-btn" title="Notifications">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13 6a4 4 0 0 0-8 0c0 5-2 6-2 6h12s-2-1-2-6M7 15a2 2 0 0 0 4 0"/></svg>
            <span v-if="appStore.unreadCount" class="notif-dot"></span>
          </button>
        </div>
      </header>

      <main class="page-content">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <keep-alive :max="10">
              <component :is="Component" :key="pageKey" />
            </keep-alive>
          </transition>
        </router-view>
      </main>
    </div>

    <!-- Toast Notifications (global) -->
    <ToastContainer />
    <!-- Onboarding Tooltips (first-time users) -->
    <OnboardingTooltip :steps="onboardingSteps" storage-key="fb_onboarding_done" />
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

    <!-- Command Palette Search -->
    <Teleport to="body">
      <div v-if="showSearch" class="cmd-backdrop" @click="showSearch = false">
        <div class="cmd-palette" @click.stop>
          <div class="cmd-input-wrap">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" class="cmd-search-icon"><circle cx="7" cy="7" r="5"/><line x1="11" y1="11" x2="14" y2="14"/></svg>
            <input
              ref="searchInputRef"
              v-model="searchQuery"
              class="cmd-input"
              placeholder="Search pages, features, and settings..."
              @keydown.down.prevent="moveHighlight(1)"
              @keydown.up.prevent="moveHighlight(-1)"
              @keydown.enter.prevent="selectHighlighted"
              @keydown.escape="showSearch = false"
            />
          </div>
          <div class="cmd-results">
            <template v-if="filteredSearchPages.length">
              <template v-for="(group, gIdx) in groupedResults" :key="group.label">
                <div class="cmd-group-label">{{ group.label }}</div>
                <div
                  v-for="(item, iIdx) in group.items"
                  :key="item.name"
                  class="cmd-item"
                  :class="{ 'cmd-item-active': item._flatIdx === highlightIdx }"
                  @click="navigateToPage(item)"
                  @mouseenter="highlightIdx = item._flatIdx"
                >
                  <span class="cmd-item-icon" v-html="item.icon"></span>
                  <div class="cmd-item-text">
                    <span class="cmd-item-name">{{ item.label }}</span>
                    <span class="cmd-item-desc">{{ item.description }}</span>
                  </div>
                  <span class="cmd-item-shortcut" v-if="item.shortcut">{{ item.shortcut }}</span>
                </div>
              </template>
            </template>
            <div v-else class="cmd-empty">No results for "{{ searchQuery }}"</div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { useToast } from '@/composables/useToast'
import websitesApi from '@/api/websites'
import billingApi from '@/api/billing'
import gamificationApi from '@/api/gamification'
import HelpButton from '@/components/HelpButton.vue'
import OnboardingTooltip from '@/components/OnboardingTooltip.vue'
import ToastContainer from '@/components/ToastContainer.vue'

const toast = useToast()

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const appStore = useAppStore()

// Add project modal state
const showAddProject = ref(false)
const creating = ref(false)
const createError = ref('')
const newProject = ref({ name: '', url: '', industry: '' })

// Gamification
const userPoints = ref(0)
const userLevel = ref(1)

// ── Command palette search ──
const showSearch = ref(false)
const searchQuery = ref('')
const highlightIdx = ref(0)
const searchInputRef = ref(null)
const isMac = navigator.platform?.toUpperCase().includes('MAC')

const searchPages = [
  { name: 'dashboard', label: 'Dashboard', description: 'Overview of all your projects', category: 'Navigation', route: '/dashboard', icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><rect x="1" y="1" width="6" height="6" rx="1"/><rect x="9" y="1" width="6" height="6" rx="1"/><rect x="1" y="9" width="6" height="6" rx="1"/><rect x="9" y="9" width="6" height="6" rx="1"/></svg>' },
  { name: 'websites', label: 'Projects', description: 'Manage your tracked websites', category: 'Navigation', route: '/websites', icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="7"/><line x1="1" y1="8" x2="15" y2="8"/><ellipse cx="8" cy="8" rx="3" ry="7"/></svg>' },
  { name: 'analytics', label: 'Analytics', description: 'Visitor data, traffic sources, engagement', category: 'Intelligence', routeFn: () => analyticsRoute.value, icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 14V6l4-4 4 4 4-4v12"/></svg>' },
  { name: 'leads', label: 'Leads', description: 'Lead capture and pipeline management', category: 'Intelligence', routeFn: () => leadsRoute.value, icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="5" r="3"/><path d="M2 14c0-3 3-5 6-5s6 2 6 5"/></svg>' },
  { name: 'audits', label: 'Audits', description: 'SEO, performance, and security audits', category: 'Intelligence', routeFn: () => auditsRoute.value, icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="7" cy="7" r="5"/><line x1="11" y1="11" x2="14" y2="14"/></svg>' },
  { name: 'heatmaps', label: 'Heatmaps', description: 'Visual click and scroll behavior', category: 'Intelligence', routeFn: () => heatmapRoute.value, icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="1" width="14" height="14" rx="2"/><circle cx="6" cy="6" r="2" fill="currentColor" opacity="0.6"/><circle cx="10" cy="10" r="2.5" fill="currentColor" opacity="0.8"/></svg>' },
  { name: 'keywords', label: 'Keywords', description: 'Keyword ranking and tracking', category: 'Intelligence', routeFn: () => keywordsRoute.value, icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 12l4-4 3 3 5-7"/><circle cx="14" cy="4" r="1.5" fill="currentColor"/></svg>' },
  { name: 'strategy', label: 'Strategy', description: 'AI-powered growth recommendations', category: 'Intelligence', routeFn: () => strategyRoute.value, icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 1l2 4h4l-3 3 1 4-4-2-4 2 1-4-3-3h4z"/></svg>' },
  { name: 'agents', label: 'Agents', description: 'AI agents for automation tasks', category: 'Intelligence', routeFn: () => agentsRoute.value, icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="6" r="3"/><path d="M3 14c0-3 2.2-5 5-5s5 2 5 5"/><path d="M12 4l2-2M4 4L2 2" stroke-linecap="round"/></svg>' },
  { name: 'campaigns', label: 'Campaigns', description: 'Email campaigns and outreach', category: 'Intelligence', routeFn: () => campaignsRoute.value, icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 3h12c.6 0 1 .4 1 1v8c0 .6-.4 1-1 1H2c-.6 0-1-.4-1-1V4c0-.6.4-1 1-1z"/><polyline points="14,4 8,9 2,4"/></svg>' },
  { name: 'llm-ranking', label: 'LLM Ranking', description: 'AI visibility scoring across LLMs', category: 'Intelligence', routeFn: () => llmRankingRoute.value, icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M8 4v4l3 2"/></svg>' },
  { name: 'billing', label: 'Billing', description: 'Subscription plans and payment', category: 'Account', route: '/billing', icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="3" width="14" height="10" rx="2"/><line x1="1" y1="7" x2="15" y2="7"/></svg>' },
  { name: 'settings', label: 'Settings', description: 'Account settings and preferences', category: 'Account', route: '/settings', icon: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="2.5"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.3 3.3l1.4 1.4M11.3 11.3l1.4 1.4M12.7 3.3l-1.4 1.4M4.7 11.3l-1.4 1.4"/></svg>' },
]

const filteredSearchPages = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return searchPages
  return searchPages.filter(p =>
    p.label.toLowerCase().includes(q) ||
    p.description.toLowerCase().includes(q) ||
    p.category.toLowerCase().includes(q)
  )
})

const groupedResults = computed(() => {
  const groups = {}
  let flatIdx = 0
  for (const item of filteredSearchPages.value) {
    if (!groups[item.category]) groups[item.category] = { label: item.category, items: [] }
    groups[item.category].items.push({ ...item, _flatIdx: flatIdx++ })
  }
  return Object.values(groups)
})

function openSearch() {
  showSearch.value = true
  searchQuery.value = ''
  highlightIdx.value = 0
  nextTick(() => searchInputRef.value?.focus())
}

function moveHighlight(dir) {
  const total = filteredSearchPages.value.length
  if (!total) return
  highlightIdx.value = (highlightIdx.value + dir + total) % total
}

function selectHighlighted() {
  const item = filteredSearchPages.value[highlightIdx.value]
  if (item) navigateToPage(item)
}

function navigateToPage(item) {
  showSearch.value = false
  const target = item.routeFn ? item.routeFn() : item.route
  router.push(target)
}

function handleGlobalKeydown(e) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    openSearch()
  }
}

watch(searchQuery, () => {
  highlightIdx.value = 0
})
// Onboarding steps for first-time users
const onboardingSteps = [
  {
    target: '.project-select',
    title: 'Your Projects',
    message: 'This is the project selector. Each project tracks one website. Switch between them or add new ones with the + button.',
    position: 'right',
  },
  {
    target: '.nav-link[href*="analytics"], a.nav-link.active',
    title: 'Analytics Dashboard',
    message: 'View real-time visitor data, traffic sources, and engagement. Install the tracking pixel to start collecting data.',
    position: 'right',
  },
  {
    target: '.nav-link[href*="audits"], a[href*="audits"]',
    title: 'Run Site Audits',
    message: 'Click "Run Audit" to scan your website for SEO, performance, mobile, security, and content issues — with actionable recommendations.',
    position: 'right',
  },
  {
    target: '.help-trigger',
    title: 'Need Help?',
    message: 'Click the ? button anytime for quick start guides, page-specific help, and setup instructions.',
    position: 'bottom',
  },
]

const userInitials = computed(() => {
  const name = authStore.user?.full_name || ''
  return name.split(' ').map(n => n[0]).filter(Boolean).join('').toUpperCase().slice(0, 2)
})

const websiteId = computed(() => appStore.activeWebsite?.id)

// Cache key: one keep-alive instance per page type + website.
// Same page + same website = instant (no reload). Different website = fresh instance.
const pageKey = computed(() => `${route.name || 'page'}-${route.params.websiteId || ''}`)
const analyticsRoute = computed(() => websiteId.value ? `/analytics/${websiteId.value}` : '/websites')
const leadsRoute = computed(() => websiteId.value ? `/leads/${websiteId.value}` : '/websites')

const auditsRoute = computed(() => websiteId.value ? `/audits/${websiteId.value}` : '/websites')
const heatmapRoute = computed(() => websiteId.value ? `/heatmap/${websiteId.value}` : '/websites')
const keywordsRoute = computed(() => websiteId.value ? `/keywords/${websiteId.value}` : '/websites')
const strategyRoute = computed(() => websiteId.value ? `/strategy/${websiteId.value}` : '/websites')
const agentsRoute = computed(() => websiteId.value ? `/agents/${websiteId.value}` : '/websites')
const campaignsRoute = computed(() => websiteId.value ? `/campaigns/${websiteId.value}` : '/websites')
const llmRankingRoute = computed(() => websiteId.value ? `/llm-ranking/${websiteId.value}` : '/websites')



function switchWebsite(id) {
  const website = appStore.websites.find(w => w.id === id)
  if (!website) return
  appStore.setActiveWebsite(website)

  // Re-route current page to use the new project ID
  const path = route.path
  const routeMap = [
    { prefix: '/analytics/', target: `/analytics/${id}` },
    { prefix: '/leads/', target: `/leads/${id}` },

    { prefix: '/audits/', target: `/audits/${id}` },
    { prefix: '/heatmap/', target: `/heatmap/${id}` },
    { prefix: '/keywords/', target: `/keywords/${id}` },
    { prefix: '/strategy/', target: `/strategy/${id}` },
    { prefix: '/websites/', target: `/websites/${id}` },
    { prefix: '/campaigns/', target: `/campaigns/${id}` },
    { prefix: '/llm-ranking/', target: `/llm-ranking/${id}` },
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
    toast.success('Project created successfully!')
    router.push(`/websites/${project.id}`)
  } catch (err) {
    const msg = err.displayMessage || 'We couldn\'t create the project. Please check the URL and try again.'
    createError.value = msg
    toast.error(msg)
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
    const { data } = await websitesApi.list({ _silentError: true })
    appStore.setWebsites(data?.results || data || [])
  } catch {}
  // Fetch plan info for project limits
  try {
    const { data } = await billingApi.getCurrent({ _silentError: true })
    const plan = data?.plan || data?.data?.plan || 'starter'
    const limits = { starter: 1, growth: 5, scale: -1 }
    appStore.setPlanInfo(plan, limits[plan] ?? 1)
  } catch {}
  // Search keyboard shortcut
  document.addEventListener('keydown', handleGlobalKeydown)
  // Gamification progress
  try {
    const { data } = await gamificationApi.progress()
    const p = data?.data || data
    userPoints.value = p?.total_points || 0
    userLevel.value = p?.current_level || 1
  } catch {}
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleGlobalKeydown)
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

.brand-logo {
  width: 36px;
  height: 36px;
  object-fit: contain;
  flex-shrink: 0;
}

.brand-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
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
  border-radius: var(--radius-sm);
  font-size: var(--font-base);
  font-weight: 500;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  text-decoration: none;
}

.nav-link .nav-icon {
  color: var(--nav-color, var(--text-secondary));
  transition: all var(--transition-fast);
}

.nav-link:hover {
  color: var(--text-primary);
  background: rgba(0, 0, 0, 0.04);
}

.nav-link:hover .nav-icon {
  color: var(--nav-color, var(--text-primary));
  filter: drop-shadow(0 0 4px var(--nav-color, transparent));
}

[data-theme="dark"] .nav-link:hover { background: rgba(255, 255, 255, 0.06); }

.nav-link.active {
  color: var(--nav-color, var(--text-primary));
  background: color-mix(in srgb, var(--nav-color, var(--bg-surface)) 8%, transparent);
  font-weight: 600;
}

.nav-link.active .nav-icon {
  color: var(--nav-color, var(--text-primary));
  filter: drop-shadow(0 0 6px var(--nav-color, transparent));
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

.points-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  color: #92400e;
  font-size: 0.7rem;
  font-weight: 700;
  text-decoration: none;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.points-badge:hover {
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.4);
  transform: translateY(-1px);
}

.points-badge svg { color: #f59e0b; flex-shrink: 0; }
.points-value { letter-spacing: 0.02em; }
.points-level {
  padding-left: 6px;
  border-left: 1px solid rgba(146, 64, 14, 0.2);
  opacity: 0.7;
}

[data-theme="dark"] .points-badge {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(217, 119, 6, 0.1));
  color: #fbbf24;
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
  padding: 32px;
  background: var(--bg-root);
  min-height: calc(100vh - var(--topbar-height));
}

/* Page transition — smooth slide-up + fade (Framer-like) */
.page-fade-leave-active {
  transition: opacity 120ms ease, transform 120ms ease;
}
.page-fade-enter-active {
  transition: opacity 280ms cubic-bezier(0.23, 1, 0.32, 1), transform 280ms cubic-bezier(0.23, 1, 0.32, 1);
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
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

/* Search Trigger */
.search-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all 0.15s ease;
  min-width: 220px;
}
.search-trigger:hover {
  border-color: var(--color-primary);
  background: var(--bg-base);
}
.search-trigger svg {
  color: var(--text-muted);
  flex-shrink: 0;
}
.search-placeholder {
  font-size: var(--font-sm);
  color: var(--text-muted);
  flex: 1;
}
.search-shortcut {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--bg-base);
  border: 1px solid var(--border-color);
  padding: 2px 6px;
  border-radius: 4px;
  letter-spacing: 0.5px;
}
</style>

<!-- Command palette styles (unscoped for Teleport) -->
<style>
.cmd-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 9999;
  display: flex;
  justify-content: center;
  padding-top: 15vh;
  animation: cmdFadeIn 0.15s ease;
}
@keyframes cmdFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.cmd-palette {
  width: 560px;
  max-height: 480px;
  background: var(--bg-card, #fff);
  border-radius: 12px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: cmdSlideUp 0.2s ease;
}
@keyframes cmdSlideUp {
  from { transform: translateY(12px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
.cmd-input-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-color, #e5e5e5);
}
.cmd-search-icon {
  color: var(--text-muted, #888);
  flex-shrink: 0;
}
.cmd-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 15px;
  color: var(--text-primary, #111);
  outline: none;
}
.cmd-input::placeholder {
  color: var(--text-muted, #999);
}
.cmd-results {
  overflow-y: auto;
  padding: 8px;
  flex: 1;
}
.cmd-group-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted, #888);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 8px 10px 4px;
}
.cmd-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.1s;
}
.cmd-item:hover,
.cmd-item-active {
  background: var(--bg-surface, #f5f5f5);
}
.cmd-item-icon {
  color: var(--text-muted, #888);
  flex-shrink: 0;
  width: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cmd-item-text {
  flex: 1;
  min-width: 0;
}
.cmd-item-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #111);
}
.cmd-item-desc {
  font-size: 12px;
  color: var(--text-muted, #888);
  margin-left: 8px;
}
.cmd-item-shortcut {
  font-size: 10px;
  color: var(--text-muted, #888);
  background: var(--bg-base, #f0f0f0);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--border-color, #e5e5e5);
}
.cmd-empty {
  padding: 24px;
  text-align: center;
  color: var(--text-muted, #888);
  font-size: 14px;
}
</style>
