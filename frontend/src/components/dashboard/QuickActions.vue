<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">Quick Actions</h3>
    </div>
    <div class="actions-list">
      <router-link v-for="action in actions" :key="action.label" :to="action.to" class="action-row">
        <div class="action-content">
          <div class="action-label">{{ action.label }}</div>
          <div class="action-desc">{{ action.desc }}</div>
        </div>
        <span class="action-arrow">&rarr;</span>
      </router-link>
    </div>
  </div>
</template>

<script setup>
defineProps({
  actions: { type: Array, required: true },
})
</script>

<style scoped>
.actions-list { display: flex; flex-direction: column; }

.action-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 4px;
  border-bottom: 1px solid var(--border-color);
  text-decoration: none;
  color: inherit;
  transition: background var(--transition-fast);
}

.action-row:hover {
  background: var(--bg-surface);
}

.action-row:last-child { border-bottom: none; }

.action-content { flex: 1; }

.action-label { font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); }
.action-desc { font-size: var(--font-xs); color: var(--text-muted); margin-top: 1px; }
.action-arrow { color: var(--text-muted); font-size: var(--font-base); transition: transform var(--transition-fast); }
.action-row:hover .action-arrow { transform: translateX(3px); color: var(--text-secondary); }
</style>
