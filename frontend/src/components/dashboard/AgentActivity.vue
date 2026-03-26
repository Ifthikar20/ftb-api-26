<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">Agent Activity</h3>
      <span class="badge badge-neutral">Latest runs</span>
    </div>
    <div v-if="runs.length" class="activity-list">
      <div v-for="run in runs" :key="run.id" class="activity-item">
        <span class="activity-dot" :style="{ background: agentColor(run.status) }"></span>
        <div style="flex:1">
          <div class="agent-name">{{ run.agent_type_display }}</div>
          <div class="agent-meta">{{ run.website_name }} · {{ run.status_display || run.status }}</div>
        </div>
        <span v-if="run.status === 'paused'" class="badge badge-warning" style="font-size:10px">Needs Approval</span>
      </div>
    </div>
    <div v-else class="empty-text">No agent runs yet.</div>
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
.activity-list { display: flex; flex-direction: column; gap: 4px; }

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}

.activity-item:last-child { border-bottom: none; }

.activity-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 5px;
  flex-shrink: 0;
}

.agent-name {
  font-size: var(--font-sm);
  font-weight: 700;
  color: var(--text-primary);
}

.agent-meta {
  font-size: var(--font-xs);
  color: var(--text-muted);
  margin-top: 2px;
}

.empty-text {
  font-size: var(--font-sm);
  color: var(--text-muted);
  padding: 16px 0;
  font-weight: 500;
}
</style>
