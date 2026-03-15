<template>
  <div class="dashboard-page fade-in">
    <div v-if="loading" class="loading-state">Loading dashboard...</div>
    <template v-else>
      <GreetingHeader :timeOfDay="timeOfDay" :firstName="firstName" />
      <StatsGrid :stats="stats" />

      <div class="content-grid">
        <MorningBrief :brief="brief" />
        <QuickActions :actions="quickActions" />
        <WeeklyTasks :tasks="actions" />
        <RecentActivity :activity="activity" />
        <AgentActivity :runs="agentRuns" />
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
const integrations = ref({ pixel: {}, services: [] })

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
    integrations.value = d.integrations || { pixel: {}, services: [] }
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
</style>
