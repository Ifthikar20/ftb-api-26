<template>
  <div class="stats-grid">
    <div class="stat-card" v-for="stat in stats" :key="stat.label">
      <div class="stat-label">{{ stat.label }}</div>
      <div class="stat-value">{{ stat.value }}</div>
      <span class="stat-change" :class="stat.direction">
        {{ stat.direction === 'up' ? '+' : '-' }} {{ stat.change }}
      </span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  stats: { type: Array, required: true },
})
</script>

<style scoped>
/* Stats grid inherits from global .stats-grid, .stat-card styles */
</style>
