<template>
  <div class="dashboard-page fade-in">
    <div v-if="loading" class="loading-state">Loading dashboard...</div>
    <template v-else>
      <!-- Greeting -->
      <div class="greeting-section">
        <div>
          <h1 class="greeting-title">Good {{ timeOfDay }}, {{ firstName }}</h1>
          <p class="greeting-sub">Here's what's happening with your marketing today.</p>
        </div>
        <router-link to="/websites" class="btn btn-primary">+ Add Project</router-link>
      </div>

      <!-- Stats -->
      <div class="stats-grid">
        <div class="stat-card" v-for="stat in stats" :key="stat.label">
          <div class="stat-label">{{ stat.label }}</div>
          <div class="stat-value">{{ stat.value }}</div>
          <span class="stat-change" :class="stat.direction">
            {{ stat.direction === 'up' ? '+' : '-' }} {{ stat.change }}
          </span>
        </div>
      </div>

      <div class="content-grid">
        <!-- Morning Brief -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Morning Brief</h3>
            <span class="badge badge-neutral">Today</span>
          </div>
          <p class="brief-text">{{ brief }}</p>
        </div>

        <!-- Quick Actions -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Quick Actions</h3>
          </div>
          <div class="actions-list">
            <router-link v-for="action in quickActions" :key="action.label" :to="action.to" class="action-row">
              <div>
                <div class="action-label">{{ action.label }}</div>
                <div class="action-desc">{{ action.desc }}</div>
              </div>
              <span class="action-arrow">&rarr;</span>
            </router-link>
          </div>
        </div>

        <!-- Weekly Tasks -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">This Week's Actions</h3>
            <span class="text-sm text-muted">{{ completedActions }} of {{ actions.length }} done</span>
          </div>
          <div class="task-list">
            <div v-for="task in actions" :key="task.id || task.text" class="task-item" :class="{ done: task.done }">
              <span class="task-check">{{ task.done ? '\u25CF' : '\u25CB' }}</span>
              <span class="task-text">{{ task.text }}</span>
              <span class="badge" :class="priorityClass(task.priority)">{{ task.priority }}</span>
            </div>
          </div>
        </div>

        <!-- Recent Activity -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Recent Activity</h3>
          </div>
          <div class="activity-list">
            <div v-for="item in activity" :key="item.text" class="activity-item">
              <span class="activity-dot" :style="{ background: item.color }"></span>
              <div>
                <div class="text-sm">{{ item.text }}</div>
                <div class="text-xs text-muted">{{ item.time }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import dashboardApi from '@/api/dashboard'

const authStore = useAuthStore()
const firstName = computed(() => (authStore.user?.full_name || 'there').split(' ')[0])

const hour = new Date().getHours()
const timeOfDay = computed(() => hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening')

const loading = ref(true)
const stats = ref([])
const brief = ref('')
const actions = ref([])
const activity = ref([])
const quickActions = ref([])

const completedActions = computed(() => actions.value.filter(a => a.done).length)

function priorityClass(p) {
  if (p === 'High') return 'badge-danger'
  if (p === 'Medium') return 'badge-warning'
  return 'badge-neutral'
}

onMounted(async () => {
  try {
    const { data } = await dashboardApi.get()
    const d = data.data || data
    stats.value = d.stats || []
    brief.value = d.brief || ''
    actions.value = d.actions || []
    activity.value = d.activity || []
    quickActions.value = d.quick_actions || []
  } catch (e) {
    console.error('Dashboard load error', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.loading-state {
  text-align: center;
  padding: 80px 20px;
  font-size: var(--font-md);
  color: var(--text-muted);
}

.greeting-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32px;
  flex-wrap: wrap;
  gap: 16px;
}

.greeting-title {
  font-family: var(--font-display);
  font-size: var(--font-3xl);
  font-weight: 400;
  color: var(--text-primary);
}

.greeting-sub {
  font-size: var(--font-base);
  color: var(--text-secondary);
  margin-top: 4px;
}

.brief-text {
  font-size: var(--font-base);
  color: var(--text-secondary);
  line-height: 1.8;
}

.actions-list { display: flex; flex-direction: column; }

.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 4px;
  border-bottom: 1px solid var(--border-color);
  text-decoration: none;
  color: inherit;
  transition: all var(--transition-fast);
}

.action-row:hover { padding-left: 8px; }
.action-row:last-child { border-bottom: none; }

.action-label { font-size: var(--font-base); font-weight: 600; color: var(--text-primary); }
.action-desc { font-size: var(--font-xs); color: var(--text-muted); }
.action-arrow { color: var(--text-muted); font-size: var(--font-lg); }

.task-list { display: flex; flex-direction: column; gap: 4px; }

.task-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 4px;
}

.task-item.done .task-text { text-decoration: line-through; color: var(--text-muted); }
.task-check { font-size: 14px; color: var(--color-success); }
.task-item:not(.done) .task-check { color: var(--text-muted); }
.task-text { flex: 1; font-size: var(--font-sm); color: var(--text-primary); }

.activity-list { display: flex; flex-direction: column; gap: 6px; }

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}

.activity-item:last-child { border-bottom: none; }

.activity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}
</style>
