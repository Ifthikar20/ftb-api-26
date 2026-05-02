<template>
  <!--
    Funnel-stage radar.

    Five axes (Bottom / Mid / Top / Niche / Custom — pruned to whichever
    the audit actually has). Two polygons:
      - You: mention rate per stage
      - Closest competitor: mention rate per stage, derived from how
        often that brand was named in the same prompt buckets

    Uses the same INTENT_FUNNEL_STAGE mapping the recommendations card
    already uses, so the numbers match between the two views.
  -->
  <div v-if="hasData" class="fr-card">
    <div class="fr-header">
      <h3 class="fr-title">Funnel coverage</h3>
      <p class="fr-sub">
        How often {{ targetName }} appears at each buyer-journey stage,
        compared with <strong>{{ competitorName }}</strong>.
      </p>
    </div>
    <div class="fr-body">
      <Radar :data="chartData" :options="chartOptions" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Radar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend,
} from 'chart.js'

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

const props = defineProps({
  results: { type: Array, default: () => [] },
  prompts: { type: Array, default: () => [] },
  targetName: { type: String, default: 'You' },
  // Closest competitor name for the comparison polygon. Optional;
  // when absent we just plot the target's coverage.
  competitorName: { type: String, default: '' },
})

// Same mapping used server-side in services.prompt_library and in
// LLMRankingPage.vue so the three views stay consistent.
const INTENT_TO_FUNNEL = {
  recommendation: 'bottom',
  alternatives: 'bottom',
  review: 'bottom',
  comparison: 'mid',
  use_case: 'mid',
  category: 'mid',
  persona: 'top',
  local: 'niche',
  custom: 'niche',
}
const STAGE_LABELS = {
  bottom: 'Bottom — Intent',
  mid: 'Mid — Comparison',
  top: 'Top — Awareness',
  niche: 'Niche / Long-tail',
}
const STAGE_ORDER = ['bottom', 'mid', 'top', 'niche']

// Map prompt text → stage so we can bucket each result.
const promptStage = computed(() => {
  const m = {}
  for (const p of props.prompts || []) {
    if (!p) continue
    const text = (typeof p === 'string' ? p : p.text || '').trim().toLowerCase()
    if (!text) continue
    const explicit = typeof p === 'object' && p.funnel_stage
    if (explicit) {
      m[text] = explicit
      continue
    }
    const intent = (typeof p === 'object' && p.type) || 'custom'
    m[text] = INTENT_TO_FUNNEL[intent] || 'niche'
  }
  return m
})

function bucketStats(filterFn) {
  // For each stage: how many succeeded queries matched filterFn.
  const stats = {}
  for (const stage of STAGE_ORDER) stats[stage] = { mentioned: 0, total: 0 }
  for (const r of props.results) {
    if (!r.query_succeeded) continue
    const stage = promptStage.value[(r.prompt || '').trim().toLowerCase()] || 'niche'
    if (!stats[stage]) continue
    stats[stage].total += 1
    if (filterFn(r)) stats[stage].mentioned += 1
  }
  return stats
}

const targetStats = computed(() => bucketStats(r => r.is_mentioned))
const competitorStats = computed(() => {
  if (!props.competitorName) return null
  const cn = props.competitorName.toLowerCase()
  return bucketStats(r =>
    (r.competitors_mentioned || []).some(
      c => c && (c.name || '').toLowerCase() === cn,
    ),
  )
})

const hasData = computed(() => {
  // At least one stage with > 0 total — otherwise the chart is meaningless.
  return STAGE_ORDER.some(s => (targetStats.value[s]?.total || 0) > 0)
})

function pct(s) { return s.total ? Math.round(s.mentioned / s.total * 100) : 0 }

const chartData = computed(() => {
  const targetSeries = STAGE_ORDER.map(s => pct(targetStats.value[s]))
  const datasets = [
    {
      label: props.targetName,
      data: targetSeries,
      borderColor: 'rgba(255, 106, 44, 1)',
      backgroundColor: 'rgba(255, 106, 44, 0.18)',
      pointBackgroundColor: 'rgba(255, 106, 44, 1)',
      pointRadius: 4,
      borderWidth: 2,
    },
  ]
  if (competitorStats.value) {
    datasets.push({
      label: props.competitorName,
      data: STAGE_ORDER.map(s => pct(competitorStats.value[s])),
      borderColor: 'rgba(99, 102, 241, 0.85)',
      backgroundColor: 'rgba(99, 102, 241, 0.12)',
      pointBackgroundColor: 'rgba(99, 102, 241, 1)',
      pointRadius: 4,
      borderWidth: 2,
    })
  }
  return { labels: STAGE_ORDER.map(s => STAGE_LABELS[s]), datasets }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } },
    tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.r}%` } },
  },
  scales: {
    r: {
      min: 0,
      max: 100,
      ticks: { stepSize: 25, backdropColor: 'transparent', font: { size: 10 } },
      grid: { circular: true },
      pointLabels: { font: { size: 11 } },
    },
  },
}))
</script>

<style scoped>
.fr-card {
  background: var(--bg-secondary, #fff);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.fr-header { margin-bottom: 12px; }
.fr-title {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
.fr-sub {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
}
.fr-body {
  position: relative;
  flex: 1;
  min-height: 280px;
}
</style>
