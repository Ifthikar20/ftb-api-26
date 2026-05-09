<template>
  <div v-if="hasData" class="w-full">
    <div
      class="flex w-full overflow-hidden rounded-md border border-gray-100"
      :style="{ height: height + 'px' }"
    >
      <div
        v-for="seg in segments"
        :key="seg.source_class"
        class="h-full"
        :class="seg.bg"
        :style="{ width: seg.percent + '%' }"
        :title="`${seg.label}: ${seg.count} (${seg.percent}%)`"
      ></div>
    </div>
    <div class="mt-2 flex flex-wrap gap-2">
      <span
        v-for="seg in segments"
        :key="seg.source_class + '-legend'"
        class="inline-flex items-center gap-1 text-xs"
      >
        <SourceClassBadge :source_class="seg.source_class" />
        <span class="text-gray-500">{{ seg.count }}</span>
      </span>
    </div>
  </div>
  <div v-else class="text-xs text-gray-500">No source breakdown available.</div>
</template>

<script setup>
import { computed } from 'vue'
import SourceClassBadge from './SourceClassBadge.vue'

const props = defineProps({
  breakdown: { type: Object, default: () => ({}) },
  height: { type: Number, default: 12 },
})

// Same color map as the badge — bg-only here since the bar segments are filled.
const BG_MAP = {
  reddit: 'bg-orange-400',
  quora: 'bg-red-400',
  stackoverflow: 'bg-orange-500',
  wikipedia: 'bg-gray-400',
  news: 'bg-blue-400',
  blog: 'bg-purple-400',
  forum: 'bg-teal-400',
  docs: 'bg-slate-400',
  social: 'bg-sky-400',
  youtube: 'bg-red-500',
  podcast: 'bg-fuchsia-400',
  gov: 'bg-green-400',
  edu: 'bg-indigo-400',
  your_site: 'bg-emerald-500',
  competitor_site: 'bg-amber-500',
  other: 'bg-zinc-400',
}

function labelFor(value) {
  return (value || 'other')
    .split('_')
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(' ')
}

const segments = computed(() => {
  const entries = Object.entries(props.breakdown || {})
  return entries
    .map(([source_class, info]) => {
      const count = info?.count ?? 0
      const share = info?.share ?? 0
      return {
        source_class,
        count,
        share,
        percent: Math.round(share * 1000) / 10,
        label: labelFor(source_class),
        bg: BG_MAP[source_class] || BG_MAP.other,
      }
    })
    .filter((s) => s.count > 0)
    .sort((a, b) => b.count - a.count)
})

const hasData = computed(() => segments.value.length > 0)
</script>
