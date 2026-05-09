<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-700"
  >
    <svg
      class="h-3.5 w-3.5 text-zinc-500"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      stroke-width="1.6"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <template v-if="format === 'blog'">
        <rect x="2" y="2.5" width="12" height="11" rx="1.5" />
        <path d="M5 6h6M5 9h6M5 12h4" />
      </template>
      <template v-else-if="format === 'faq'">
        <circle cx="8" cy="8" r="6" />
        <path d="M6.2 6.5c.1-1 .9-1.7 1.9-1.7 1.1 0 1.9.7 1.9 1.7 0 1.5-2 1.5-2 3" />
        <circle cx="8" cy="11.4" r="0.4" fill="currentColor" />
      </template>
      <template v-else-if="format === 'reddit'">
        <circle cx="8" cy="9" r="5" />
        <circle cx="6" cy="9" r="0.7" fill="currentColor" />
        <circle cx="10" cy="9" r="0.7" fill="currentColor" />
        <path d="M6 11.5c1.2.7 2.8.7 4 0" />
      </template>
      <template v-else-if="format === 'json_ld'">
        <path d="M5.5 2.5c-1.5 0-2.5 1-2.5 2.5v1.5c0 1-.7 1.5-1.5 1.5.8 0 1.5.5 1.5 1.5V11c0 1.5 1 2.5 2.5 2.5" />
        <path d="M10.5 2.5c1.5 0 2.5 1 2.5 2.5v1.5c0 1 .7 1.5 1.5 1.5-.8 0-1.5.5-1.5 1.5V11c0 1.5-1 2.5-2.5 2.5" />
      </template>
      <template v-else-if="format === 'landing'">
        <rect x="2" y="2.5" width="12" height="11" rx="1.5" />
        <path d="M2 6h12" />
        <path d="M5 9h6M5 11.5h4" />
      </template>
      <template v-else>
        <rect x="2" y="2.5" width="12" height="11" rx="1.5" />
        <path d="M5 6h6M5 9h4" />
      </template>
    </svg>
    <span>{{ label }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  format: { type: String, default: '' },
})

const LABELS = {
  blog: 'Blog',
  faq: 'FAQ',
  reddit: 'Reddit',
  json_ld: 'JSON-LD',
  landing: 'Landing',
}

const label = computed(() => LABELS[props.format] || (props.format ? props.format : 'Format'))
</script>
