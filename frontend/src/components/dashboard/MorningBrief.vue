<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">Morning Brief</h3>
      <span class="badge badge-neutral">Today</span>
    </div>
    <p class="brief-text">{{ brief }}</p>
  </div>
</template>

<script setup>
defineProps({
  brief: { type: String, required: true },
})
</script>

<style scoped>
.brief-text {
  font-size: var(--font-base);
  color: var(--text-secondary);
  line-height: 1.8;
}
</style>
