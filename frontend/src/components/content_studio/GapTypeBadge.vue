<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
    :class="palette.classes"
  >
    <svg
      class="h-3.5 w-3.5"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      stroke-width="1.6"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <template v-if="gap === 'visibility'">
        <circle cx="8" cy="8" r="3" />
        <path d="M1.5 8c2-3.5 4.5-5 6.5-5s4.5 1.5 6.5 5c-2 3.5-4.5 5-6.5 5s-4.5-1.5-6.5-5z" />
      </template>
      <template v-else-if="gap === 'accuracy'">
        <path d="M8 1.5l2 4.5 5 .5-3.7 3.4 1.1 5L8 12.3 3.6 14.9 4.7 9.9 1 6.5l5-.5z" />
      </template>
      <template v-else-if="gap === 'citation'">
        <path d="M3 4.5h7M3 8h7M3 11.5h5" />
        <path d="M12 3.5v9l1.5-1 1.5 1v-9z" fill="currentColor" stroke="none" opacity="0.25" />
        <path d="M12 3.5v9l1.5-1 1.5 1v-9z" />
      </template>
      <template v-else>
        <circle cx="8" cy="8" r="6" />
        <path d="M8 5v3l2 1.5" />
      </template>
    </svg>
    <span>{{ palette.label }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  gap: { type: String, default: 'generic' },
})

const PALETTE = {
  visibility: { classes: 'bg-blue-50 text-blue-700', label: 'Visibility' },
  accuracy: { classes: 'bg-amber-50 text-amber-700', label: 'Accuracy' },
  citation: { classes: 'bg-emerald-50 text-emerald-700', label: 'Citation' },
  generic: { classes: 'bg-zinc-100 text-zinc-700', label: 'General' },
}

const palette = computed(() => PALETTE[props.gap] || PALETTE.generic)
</script>
