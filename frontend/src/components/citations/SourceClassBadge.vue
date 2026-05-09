<template>
  <span
    class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
    :class="classes"
    :title="label"
  >
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  source_class: { type: String, default: 'other' },
})

// Tailwind utility classes per source_class.
const COLOR_MAP = {
  reddit: 'bg-orange-100 text-orange-700',
  quora: 'bg-red-100 text-red-700',
  stackoverflow: 'bg-orange-100 text-orange-700',
  wikipedia: 'bg-gray-100 text-gray-700',
  news: 'bg-blue-100 text-blue-700',
  blog: 'bg-purple-100 text-purple-700',
  forum: 'bg-teal-100 text-teal-700',
  docs: 'bg-slate-100 text-slate-700',
  social: 'bg-sky-100 text-sky-700',
  youtube: 'bg-red-100 text-red-700',
  podcast: 'bg-fuchsia-100 text-fuchsia-700',
  gov: 'bg-green-100 text-green-700',
  edu: 'bg-indigo-100 text-indigo-700',
  your_site: 'bg-emerald-100 text-emerald-800',
  competitor_site: 'bg-amber-100 text-amber-800',
  other: 'bg-zinc-100 text-zinc-700',
}

const classes = computed(() => COLOR_MAP[props.source_class] || COLOR_MAP.other)

const label = computed(() => {
  const v = props.source_class || 'other'
  return v
    .split('_')
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(' ')
})
</script>
