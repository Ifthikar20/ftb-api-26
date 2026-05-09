<script setup>
defineProps({
  state: { type: String, default: null }, // 'asc' | 'desc' | null
})
</script>

<template>
  <svg
    width="12"
    height="12"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    class="pl-sort-icon"
    :class="{ 'is-active': !!state, 'is-asc': state === 'asc', 'is-desc': state === 'desc' }"
    aria-hidden="true"
  >
    <path d="M8 9l4-4 4 4" stroke-linecap="round" stroke-linejoin="round" :class="{ 'is-dim': state === 'desc' }"/>
    <path d="M8 15l4 4 4-4" stroke-linecap="round" stroke-linejoin="round" :class="{ 'is-dim': state === 'asc' }"/>
  </svg>
</template>

<style scoped>
.pl-sort-icon {
  flex-shrink: 0;
  color: var(--text-muted);
  transition: color 0.15s;
}
.pl-sort-icon.is-active {
  color: var(--text-primary);
}
.pl-sort-icon path { transition: opacity 0.15s; }
.pl-sort-icon.is-asc path:nth-child(2),
.pl-sort-icon.is-desc path:nth-child(1) {
  opacity: 0.3;
}
</style>
