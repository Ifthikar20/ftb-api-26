<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">Quick Actions</h3>
    </div>
    <div class="actions-list">
      <router-link v-for="action in actions" :key="action.label" :to="action.to" class="action-row">
        <div>
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
</style>
