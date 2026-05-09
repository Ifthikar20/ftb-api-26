<template>
  <div class="w-full">
    <div class="mb-1.5 flex items-center justify-between">
      <span class="text-xs font-medium text-zinc-700">{{ label }}</span>
      <span class="text-xs tabular-nums text-zinc-500">{{ pctLabel }}</span>
    </div>
    <div class="h-2 w-full overflow-hidden rounded-full bg-zinc-100">
      <div
        class="h-full rounded-full transition-all duration-300"
        :class="barColor"
        :style="{ width: pct + '%' }"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  score: { type: Number, default: 0 },
  label: { type: String, default: 'Score' },
})

const safeScore = computed(() => {
  const n = Number(props.score)
  if (Number.isNaN(n)) return 0
  return Math.max(0, Math.min(1, n))
})

const pct = computed(() => Math.round(safeScore.value * 100))
const pctLabel = computed(() => `${pct.value}%`)

const barColor = computed(() => {
  const s = safeScore.value
  if (s < 0.5) return 'bg-amber-500'
  if (s < 0.8) return 'bg-blue-500'
  return 'bg-emerald-500'
})
</script>
