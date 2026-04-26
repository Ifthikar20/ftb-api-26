<template>
  <div class="settings-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Settings</h1>
        <p class="page-subtitle">Manage your account, preferences, and AI usage.</p>
      </div>
    </div>

    <div class="content-grid" style="grid-template-columns: 1fr">
      <!-- Profile -->
      <div class="card" style="margin-bottom:20px">
        <div class="card-header"><h3 class="card-title">Profile</h3></div>
        <form @submit.prevent="saveProfile" class="settings-form">
          <div class="form-group">
            <label class="form-label">Full Name</label>
            <input v-model="profile.full_name" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Email</label>
            <input v-model="profile.email" class="form-input" disabled />
          </div>
          <div class="form-group">
            <label class="form-label">Company</label>
            <input v-model="profile.company_name" class="form-input" />
          </div>
          <button type="submit" class="btn btn-primary btn-sm" :disabled="saving">{{ saving ? 'Saving...' : 'Save Changes' }}</button>
        </form>
      </div>

      <!-- AI Usage & Token Tracking -->
      <div class="card" style="margin-bottom:20px">
        <div class="card-header" style="display:flex;justify-content:space-between;align-items:center">
          <h3 class="card-title" style="display:flex;align-items:center;gap:8px">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z"/><path d="M12 6v6l4 2"/></svg>
            AI Usage & Tokens
          </h3>
          <select v-model="usagePeriod" @change="loadUsage" class="usage-period-select">
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
          </select>
        </div>

        <div v-if="usageLoading" class="usage-loading">
          <div class="spinner"></div>
          <span>Loading usage data...</span>
        </div>

        <div v-else-if="usage" class="usage-content">
          <!-- Monthly Cap Progress -->
          <div v-if="usage.cap_status && usage.cap_status.cap_usd > 0" class="cap-bar-wrap">
            <div class="cap-bar-header">
              <span class="cap-bar-label">Monthly AI spend</span>
              <span class="cap-bar-value">
                ${{ usage.cap_status.spent_usd.toFixed(2) }} / ${{ usage.cap_status.cap_usd.toFixed(2) }}
                ({{ usage.cap_status.pct }}%)
              </span>
            </div>
            <div class="cap-bar">
              <div
                class="cap-bar-fill"
                :class="{ 'cap-bar-warn': usage.cap_status.pct >= 80, 'cap-bar-exceeded': usage.cap_status.exceeded }"
                :style="{ width: Math.min(100, usage.cap_status.pct) + '%' }"
              ></div>
            </div>
            <p v-if="usage.cap_status.exceeded" class="cap-bar-msg">
              Cap reached. New AI runs will be blocked until next month or until you raise the cap.
            </p>
          </div>
          <div v-else-if="usage.cap_status" class="cap-bar-wrap cap-bar-none">
            No monthly spend cap set. Add one to control runaway AI cost.
          </div>

          <!-- Totals Row -->
          <div class="usage-totals">
            <div class="usage-stat">
              <div class="usage-stat-value">{{ formatNum(usage.totals.calls) }}</div>
              <div class="usage-stat-label">API Calls</div>
            </div>
            <div class="usage-stat">
              <div class="usage-stat-value">{{ formatTokens(usage.totals.total_tokens) }}</div>
              <div class="usage-stat-label">Total Tokens</div>
            </div>
            <div class="usage-stat">
              <div class="usage-stat-value">{{ formatTokens(usage.totals.input_tokens) }}</div>
              <div class="usage-stat-label">Input Tokens</div>
            </div>
            <div class="usage-stat">
              <div class="usage-stat-value">{{ formatTokens(usage.totals.output_tokens) }}</div>
              <div class="usage-stat-label">Output Tokens</div>
            </div>
            <div class="usage-stat cost">
              <div class="usage-stat-value">${{ usage.totals.estimated_cost_usd.toFixed(4) }}</div>
              <div class="usage-stat-label">Est. Cost</div>
            </div>
          </div>

          <!-- Module Breakdown -->
          <div class="usage-section" v-if="usage.by_module.length">
            <h4 class="usage-section-title">Usage by Module</h4>
            <div class="usage-table">
              <div class="usage-table-header">
                <span>Module</span>
                <span>Calls</span>
                <span>Tokens</span>
                <span>Cost</span>
              </div>
              <div v-for="m in usage.by_module" :key="m.module" class="usage-table-row">
                <span class="module-name">
                  <span class="module-dot" :class="m.module"></span>
                  {{ moduleLabels[m.module] || m.module }}
                </span>
                <span>{{ formatNum(m.calls) }}</span>
                <span>{{ formatTokens(m.tokens) }}</span>
                <span class="cost-cell">${{ m.cost.toFixed(4) }}</span>
              </div>
            </div>
          </div>

          <!-- Provider Breakdown -->
          <div class="usage-section" v-if="usage.by_provider && usage.by_provider.length">
            <h4 class="usage-section-title">Usage by Provider</h4>
            <div class="usage-table">
              <div class="usage-table-header">
                <span>Provider</span>
                <span>Calls</span>
                <span>Tokens</span>
                <span>Cost</span>
              </div>
              <div v-for="p in usage.by_provider" :key="p.provider" class="usage-table-row">
                <span class="model-name">{{ providerLabels[p.provider] || p.provider }}</span>
                <span>{{ formatNum(p.calls) }}</span>
                <span>{{ formatTokens(p.tokens) }}</span>
                <span class="cost-cell">${{ p.cost.toFixed(4) }}</span>
              </div>
            </div>
          </div>

          <!-- Role Split -->
          <div class="usage-section" v-if="usage.by_role && usage.by_role.length">
            <h4 class="usage-section-title">Upstream vs Internal Parsing</h4>
            <div class="usage-table">
              <div class="usage-table-header">
                <span>Role</span>
                <span>Calls</span>
                <span>Tokens</span>
                <span>Cost</span>
              </div>
              <div v-for="r in usage.by_role" :key="r.role" class="usage-table-row">
                <span class="model-name">{{ roleLabels[r.role] || r.role }}</span>
                <span>{{ formatNum(r.calls) }}</span>
                <span>{{ formatTokens(r.tokens) }}</span>
                <span class="cost-cell">${{ r.cost.toFixed(4) }}</span>
              </div>
            </div>
          </div>

          <!-- Model Breakdown -->
          <div class="usage-section" v-if="usage.by_model.length">
            <h4 class="usage-section-title">Usage by Model</h4>
            <div class="usage-table">
              <div class="usage-table-header">
                <span>Model</span>
                <span>Calls</span>
                <span>Tokens</span>
                <span>Cost</span>
              </div>
              <div v-for="m in usage.by_model" :key="m.model_name" class="usage-table-row">
                <span class="model-name">{{ m.model_name }}</span>
                <span>{{ formatNum(m.calls) }}</span>
                <span>{{ formatTokens(m.tokens) }}</span>
                <span class="cost-cell">${{ m.cost.toFixed(4) }}</span>
              </div>
            </div>
          </div>

          <!-- Daily Chart -->
          <div class="usage-section" v-if="usage.daily.length">
            <h4 class="usage-section-title">Daily Token Usage</h4>
            <div class="usage-chart">
              <div v-for="d in usage.daily" :key="d.day" class="chart-bar-wrap" :title="`${d.day}: ${formatTokens(d.tokens)} tokens, ${d.calls} calls`">
                <div class="chart-bar" :style="{ height: barHeight(d.tokens) + '%' }"></div>
                <span class="chart-label">{{ formatDay(d.day) }}</span>
              </div>
            </div>
          </div>

          <!-- Empty state -->
          <div v-if="!usage.by_module.length" class="usage-empty">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.5"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z"/><path d="M12 6v6l4 2"/></svg>
            <p>No AI usage recorded yet. Token tracking starts automatically when you use AI features like Lead Finder, Agents, Messaging, or LLM Ranking.</p>
          </div>
        </div>
      </div>

      <!-- Notification Preferences -->
      <div class="card" style="margin-bottom:20px">
        <div class="card-header"><h3 class="card-title">Notification Preferences</h3></div>
        <div class="settings-form">
          <label class="toggle-row">
            <span>Hot lead email alerts</span>
            <input type="checkbox" v-model="notifPrefs.hot_lead_email" @change="saveNotifPrefs" />
          </label>
          <label class="toggle-row">
            <span>Weekly report</span>
            <input type="checkbox" v-model="notifPrefs.weekly_report" @change="saveNotifPrefs" />
          </label>
          <label class="toggle-row">
            <span>Competitor change alerts</span>
            <input type="checkbox" v-model="notifPrefs.competitor_changes" @change="saveNotifPrefs" />
          </label>
          <label class="toggle-row">
            <span>Audit complete alerts</span>
            <input type="checkbox" v-model="notifPrefs.audit_complete" @change="saveNotifPrefs" />
          </label>
        </div>
      </div>

      <!-- Theme -->
      <div class="card">
        <div class="card-header"><h3 class="card-title">Appearance</h3></div>
        <div class="settings-form">
          <label class="toggle-row">
            <span>Dark Mode</span>
            <input type="checkbox" :checked="appStore.theme === 'dark'" @change="appStore.toggleTheme()" />
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import notificationsApi from '@/api/notifications'

const authStore = useAuthStore()
const appStore = useAppStore()
const saving = ref(false)

const profile = ref({
  full_name: '',
  email: '',
  company_name: '',
})

const notifPrefs = ref({
  hot_lead_email: true,
  weekly_report: true,
  competitor_changes: true,
  audit_complete: true,
})

// ── AI Usage ──
const usage = ref(null)
const usageLoading = ref(false)
const usagePeriod = ref('30')

const moduleLabels = {
  lead_finder: 'AI Lead Finder',
  messaging: 'AI Messaging',
  llm_ranking: 'LLM Ranking',
  seo_keywords: 'SEO Keywords',
  analytics: 'AI Insights',
}

const providerLabels = {
  anthropic: 'Anthropic (Claude)',
  openai: 'OpenAI (GPT)',
  google: 'Google (Gemini)',
  perplexity: 'Perplexity',
}

const roleLabels = {
  upstream: 'Upstream LLM (ranking, lead finder, messaging)',
  extraction: 'Internal parsing (Haiku extraction)',
  prompt_generation: 'Prompt generation',
  context_inference: 'Audit context inference',
}

function formatNum(n) { return (n || 0).toLocaleString() }
function formatTokens(n) {
  if (!n) return '0'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return n.toLocaleString()
}

function formatDay(isoDate) {
  if (!isoDate) return ''
  const d = new Date(isoDate)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function barHeight(tokens) {
  if (!usage.value?.daily?.length) return 0
  const max = Math.max(...usage.value.daily.map(d => d.tokens || 0))
  return max > 0 ? Math.max(4, (tokens / max) * 100) : 4
}

async function loadUsage() {
  usageLoading.value = true
  try {
    const token = authStore.token || localStorage.getItem('access_token')
    const res = await fetch(`/api/v1/auth/me/ai-usage/?days=${usagePeriod.value}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) {
      usage.value = await res.json()
    }
  } catch (e) {
    console.error('Failed to load AI usage', e)
  } finally {
    usageLoading.value = false
  }
}

onMounted(async () => {
  if (authStore.user) {
    profile.value = {
      full_name: authStore.user.full_name || '',
      email: authStore.user.email || '',
      company_name: authStore.user.company_name || '',
    }
  }
  try {
    const { data } = await notificationsApi.getPreferences()
    const d = data?.data || data
    if (d) notifPrefs.value = { ...notifPrefs.value, ...d }
  } catch {}

  // Load AI usage
  loadUsage()
})

async function saveProfile() {
  saving.value = true
  try {
    // Would call auth API to update profile
    // For now, update local state
    if (authStore.user) {
      authStore.user.full_name = profile.value.full_name
      authStore.user.company_name = profile.value.company_name
    }
  } finally {
    saving.value = false
  }
}

async function saveNotifPrefs() {
  try {
    await notificationsApi.updatePreferences(notifPrefs.value)
  } catch {}
}
</script>

<style scoped>
.settings-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 480px;
}

.cap-bar-wrap {
  margin-bottom: 18px;
  padding: 12px 14px;
  background: var(--bg-soft, #f8fafc);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}
.cap-bar-header {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-sm);
  margin-bottom: 6px;
  color: var(--text-primary);
}
.cap-bar-label { font-weight: 600; }
.cap-bar-value { color: var(--text-secondary); }
.cap-bar {
  height: 8px;
  background: var(--border-color);
  border-radius: 4px;
  overflow: hidden;
}
.cap-bar-fill {
  height: 100%;
  background: #16a34a;
  transition: width 0.2s;
}
.cap-bar-warn { background: #f59e0b; }
.cap-bar-exceeded { background: #dc2626; }
.cap-bar-msg {
  margin: 8px 0 0;
  font-size: var(--font-xs);
  color: #dc2626;
}
.cap-bar-none {
  font-size: var(--font-xs);
  color: var(--text-secondary);
  font-style: italic;
}

.toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: var(--font-sm);
  color: var(--text-primary);
  cursor: pointer;
}

.toggle-row:last-child { border-bottom: none; }

.toggle-row input[type="checkbox"] {
  accent-color: var(--text-primary);
  width: 18px;
  height: 18px;
}

/* ── AI Usage Styles ── */
.usage-period-select {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
  background: var(--bg-surface);
  color: var(--text-primary);
  cursor: pointer;
}

.usage-loading {
  display: flex; align-items: center; gap: 10px;
  padding: 32px; color: var(--text-muted); font-size: 14px;
}

.spinner {
  width: 18px; height: 18px;
  border: 2px solid var(--border-color);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.usage-content { padding: 4px 0; }

.usage-totals {
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px;
  margin-bottom: 20px;
}

.usage-stat {
  background: var(--bg-surface); border: 1px solid var(--border-color);
  border-radius: 10px; padding: 14px; text-align: center;
}

.usage-stat.cost { background: linear-gradient(135deg, #eef2ff, #faf5ff); }
[data-theme="dark"] .usage-stat.cost { background: linear-gradient(135deg, #1e1b4b, #2e1065); }

.usage-stat-value {
  font-size: 20px; font-weight: 700; color: var(--text-primary);
  letter-spacing: -0.02em;
}

.usage-stat.cost .usage-stat-value { color: #6366f1; }

.usage-stat-label {
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px;
}

.usage-section { margin-bottom: 20px; }

.usage-section-title {
  font-size: 13px; font-weight: 700; color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.05em;
  margin: 0 0 10px; padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.usage-table { font-size: 13px; }

.usage-table-header {
  display: grid; grid-template-columns: 2fr 1fr 1fr 1fr;
  padding: 8px 0; font-size: 11px; font-weight: 700;
  color: var(--text-muted); text-transform: uppercase;
  letter-spacing: 0.05em; border-bottom: 1px solid var(--border-color);
}

.usage-table-row {
  display: grid; grid-template-columns: 2fr 1fr 1fr 1fr;
  padding: 10px 0; align-items: center;
  border-bottom: 1px solid var(--bg-surface);
  transition: background 0.1s;
}

.usage-table-row:hover { background: var(--bg-surface); }

.module-name {
  display: flex; align-items: center; gap: 8px;
  font-weight: 600; color: var(--text-primary);
}

.module-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}

.module-dot.lead_finder { background: #22c55e; }
.module-dot.messaging { background: #8b5cf6; }
.module-dot.llm_ranking { background: #ec4899; }
.module-dot.seo_keywords { background: #eab308; }
.module-dot.analytics { background: #f97316; }

.model-name {
  font-family: 'SF Mono', 'Cascadia Mono', 'Consolas', monospace;
  font-size: 12px; font-weight: 500; color: var(--text-secondary);
}

.cost-cell { color: #6366f1; font-weight: 600; }

/* Daily chart */
.usage-chart {
  display: flex; align-items: flex-end; gap: 3px;
  height: 120px; padding: 8px 0;
}

.chart-bar-wrap {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; height: 100%; justify-content: flex-end;
  cursor: pointer;
}

.chart-bar {
  width: 100%; min-width: 4px; max-width: 32px;
  background: linear-gradient(180deg, #6366f1, #8b5cf6);
  border-radius: 3px 3px 0 0; transition: height 0.3s ease;
}

.chart-bar-wrap:hover .chart-bar { background: #4f46e5; }

.chart-label {
  font-size: 9px; color: var(--text-muted); margin-top: 4px;
  writing-mode: vertical-rl; text-orientation: mixed;
  transform: rotate(180deg); white-space: nowrap;
}

.usage-empty {
  display: flex; flex-direction: column; align-items: center;
  padding: 32px; gap: 10px; text-align: center;
}

.usage-empty p { font-size: 13px; color: var(--text-muted); max-width: 400px; margin: 0; }

/* Responsive */
@media (max-width: 768px) {
  .usage-totals { grid-template-columns: repeat(2, 1fr); }
}
</style>
