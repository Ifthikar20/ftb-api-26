<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">Recent Activity</h3>
    </div>
    <div class="activity-list">
      <div v-for="item in activity" :key="item.text" class="activity-item">
        <span class="activity-dot" :style="{ background: item.color }"></span>
        <div>
          <div class="activity-text">{{ item.text }}</div>
          <div class="activity-time">{{ item.time }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  activity: { type: Array, required: true },
})
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

.activity-text {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.activity-time {
  font-size: var(--font-xs);
  color: var(--text-muted);
  margin-top: 2px;
}
</style>
