<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">This Week's Actions</h3>
      <span class="text-sm text-muted">{{ completedCount }} of {{ tasks.length }} done</span>
    </div>
    <div class="task-list">
      <div v-for="task in tasks" :key="task.id || task.text" class="task-item" :class="{ done: task.done }">
        <span class="task-check">{{ task.done ? '\u25CF' : '\u25CB' }}</span>
        <span class="task-text">{{ task.text }}</span>
        <span class="badge" :class="priorityClass(task.priority)">{{ task.priority }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  tasks: { type: Array, required: true },
})

const completedCount = computed(() => props.tasks.filter(a => a.done).length)

function priorityClass(p) {
  if (p === 'High') return 'badge-danger'
  if (p === 'Medium') return 'badge-warning'
  return 'badge-neutral'
}
</script>

<style scoped>
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
</style>
