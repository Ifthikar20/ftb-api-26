<template>
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
</template>

<script setup>
defineProps({
  activity: { type: Array, required: true },
})
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
