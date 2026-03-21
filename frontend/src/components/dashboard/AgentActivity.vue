<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">Agent Activity</h3>
      <span class="text-sm text-muted">Latest runs</span>
    </div>
    <div v-if="runs.length" class="activity-list">
      <div v-for="run in runs" :key="run.id" class="activity-item">
        <span class="activity-dot" :style="{ background: agentColor(run.status) }"></span>
        <div style="flex:1">
          <div class="text-sm font-semibold">{{ run.agent_type_display }}</div>
          <div class="text-xs text-muted">{{ run.website_name }} · {{ run.status_display || run.status }}</div>
        </div>
        <span v-if="run.status === 'paused'" class="badge badge-warning" style="font-size:10px">Needs Approval</span>
      </div>
    </div>
    <div v-else class="text-sm text-muted" style="padding:16px 0">No agent runs yet.</div>
  </div>
</template>

<script setup>
defineProps({
  runs: { type: Array, required: true },
})

function agentColor(status) {
  const map = { completed: '#22c55e', running: '#3b82f6', paused: '#f59e0b', failed: '#ef4444' }
  return map[status] || '#94a3b8'
}
</script>

<style scoped>
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
