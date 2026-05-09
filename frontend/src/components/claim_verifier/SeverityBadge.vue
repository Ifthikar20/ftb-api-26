<template>
  <span
    class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
    :class="classes"
  >
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  severity: { type: String, default: 'info' },
})

const COLORS = {
  critical: 'bg-red-100 text-red-800',
  high: 'bg-orange-100 text-orange-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-blue-100 text-blue-800',
  info: 'bg-slate-100 text-slate-700',
}

const classes = computed(() => COLORS[props.severity] || COLORS.info)

const label = computed(() => {
  const v = props.severity || 'info'
  return v.charAt(0).toUpperCase() + v.slice(1)
})
</script>
