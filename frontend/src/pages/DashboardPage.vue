<template>
  <div class="dashboard-page fade-in">
    <div v-if="loading" class="loading-state">Loading dashboard...</div>
    <template v-else>
      <GreetingHeader :timeOfDay="timeOfDay" :firstName="firstName" />
      <StatsGrid :stats="stats" class="stagger-enter" />

      <div class="content-grid stagger-enter">
        <MorningBrief :brief="brief" class="tint-blue" />
        <QuickActions :actions="quickActions" />
        <WeeklyTasks :tasks="actions" class="tint-green" />
        <RecentActivity :activity="activity" />
        <AgentActivity :runs="agentRuns" />
        <TrendInsights class="tint-lavender" />
        <IntegrationStatus :integrations="integrations" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import dashboardApi from '@/api/dashboard'
import agentsApi from '@/api/agents'

import GreetingHeader from '@/components/dashboard/GreetingHeader.vue'
import StatsGrid from '@/components/dashboard/StatsGrid.vue'
import MorningBrief from '@/components/dashboard/MorningBrief.vue'
import QuickActions from '@/components/dashboard/QuickActions.vue'
import WeeklyTasks from '@/components/dashboard/WeeklyTasks.vue'
import RecentActivity from '@/components/dashboard/RecentActivity.vue'
import AgentActivity from '@/components/dashboard/AgentActivity.vue'
import IntegrationStatus from '@/components/dashboard/IntegrationStatus.vue'
import TrendInsights from '@/components/dashboard/TrendInsights.vue'

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
const agentRuns = ref([])
const DEFAULT_INTEGRATIONS = {
  pixel: { installed: false, verified: false, verified_at: null, pixel_key: null },
  services: [
    { type: 'ga', label: 'Google Analytics', connected: false, connected_at: null },
    { type: 'gsc', label: 'Google Search Console', connected: false, connected_at: null },
    { type: 'facebook', label: 'Facebook Ads', connected: false, connected_at: null },
  ],
}
const integrations = ref({ ...DEFAULT_INTEGRATIONS })

onMounted(async () => {
  try {
    const [dashRes, agentRes] = await Promise.all([
      dashboardApi.get(),
      agentsApi.activity().catch(() => ({ data: [] })),
    ])
    const d = dashRes.data?.data || dashRes.data
    stats.value = d.stats || []
    brief.value = d.brief || ''
    actions.value = d.actions || []
    activity.value = d.activity || []
    quickActions.value = d.quick_actions || []
    integrations.value = d.integrations
      ? {
          pixel: { ...DEFAULT_INTEGRATIONS.pixel, ...d.integrations.pixel },
          services: d.integrations.services?.length
            ? d.integrations.services
            : DEFAULT_INTEGRATIONS.services,
        }
      : { ...DEFAULT_INTEGRATIONS }
    agentRuns.value = (agentRes.data || agentRes || []).slice(0, 3)
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

/* Subtle card color tints */
.tint-blue {
  background: linear-gradient(135deg, #f0f7ff 0%, #ffffff 60%) !important;
}

.tint-green {
  background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 60%) !important;
}

.tint-lavender {
  background: linear-gradient(135deg, #f5f3ff 0%, #ffffff 60%) !important;
}

[data-theme="dark"] .tint-blue {
  background: linear-gradient(135deg, rgba(91, 141, 239, 0.06) 0%, var(--bg-card) 60%) !important;
}

[data-theme="dark"] .tint-green {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.06) 0%, var(--bg-card) 60%) !important;
}

[data-theme="dark"] .tint-lavender {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.06) 0%, var(--bg-card) 60%) !important;
}
</style>
