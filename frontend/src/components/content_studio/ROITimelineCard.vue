<template>
  <article
    class="flex flex-col gap-4 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm transition-all duration-150 ease-out hover:-translate-y-0.5 hover:shadow-md sm:flex-row sm:items-center sm:justify-between"
  >
    <div class="min-w-0 flex-1">
      <h3 class="truncate text-[15px] font-medium text-zinc-900">
        {{ title }}
      </h3>
      <p class="mt-1 text-xs text-zinc-500">
        {{ daysLabel }} · measured {{ measuredLabel }}
      </p>
    </div>

    <div class="flex flex-wrap items-center gap-6 sm:gap-8">
      <Metric
        label="Visibility"
        :delta="visibilityLift"
        :unit="'pts'"
      />
      <Metric
        label="Citations"
        :delta="citationDelta"
        :unit="''"
        integer
      />
      <Metric
        label="Accuracy"
        :delta="accuracyLift"
        :unit="'pts'"
      />
    </div>
  </article>
</template>

<script setup>
import { computed, h } from 'vue'

const props = defineProps({
  row: { type: Object, required: true },
})

const Metric = (mp) => {
  const d = Number(mp.delta) || 0
  const positive = d > 0
  const negative = d < 0
  const color = positive ? 'text-emerald-600' : negative ? 'text-rose-600' : 'text-zinc-400'
  const arrow = positive ? '↑' : negative ? '↓' : '·'
  const formatted = mp.integer ? Math.round(d) : (Math.round(d * 10) / 10).toFixed(1)
  const sign = d > 0 ? '+' : ''
  return h('div', { class: 'flex flex-col items-start gap-0.5' }, [
    h('span', { class: 'text-[10px] font-semibold uppercase tracking-wider text-zinc-400' }, mp.label),
    h('span', { class: `text-sm font-semibold tabular-nums ${color}` }, [
      `${arrow} ${sign}${formatted}${mp.unit ? ' ' + mp.unit : ''}`,
    ]),
  ])
}

const title = computed(() => props.row.draft_title || props.row.title || 'Published draft')

const daysLabel = computed(() => {
  const d = props.row.days_since_publish
  if (d == null) return 'Recently published'
  if (d === 0) return 'Published today'
  if (d === 1) return 'Published 1 day ago'
  return `Published ${d} days ago`
})

const measuredLabel = computed(() => {
  const ts = props.row.measured_at
  if (!ts) return '—'
  try {
    return new Date(ts).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return ts
  }
})

const visibilityLift = computed(() => Number(props.row.visibility_lift) || 0)
const accuracyLift = computed(() => Number(props.row.accuracy_lift) || 0)
const citationDelta = computed(() => {
  const before = Number(props.row.citation_count_before) || 0
  const after = Number(props.row.citation_count_after) || 0
  return after - before
})
</script>
