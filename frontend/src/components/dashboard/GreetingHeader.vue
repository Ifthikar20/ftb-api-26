<template>
  <div class="greeting-section">
    <div>
      <h1 class="greeting-title">Good {{ timeOfDay }}, {{ firstName }}</h1>
      <p class="greeting-sub">Here's what's happening with your marketing today.</p>
    </div>
    <router-link to="/websites" class="btn btn-primary">+ Add Project</router-link>
  </div>
</template>

<script setup>
defineProps({
  timeOfDay: { type: String, required: true },
  firstName: { type: String, required: true },
})
</script>

<style scoped>
.greeting-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32px;
  flex-wrap: wrap;
  gap: 16px;
}

.greeting-title {
  font-family: var(--font-display);
  font-size: var(--font-3xl);
  font-weight: 400;
  color: var(--text-primary);
}

.greeting-sub {
  font-size: var(--font-base);
  color: var(--text-secondary);
  margin-top: 4px;
}
</style>
