<template>
  <svg
    :viewBox="`0 0 ${vbWidth} ${vbHeight}`"
    :width="width"
    :height="height"
    preserveAspectRatio="none"
    aria-hidden="true"
  >
    <path
      v-if="path"
      :d="path"
      fill="none"
      :stroke="stroke"
      stroke-width="1.6"
      stroke-linejoin="round"
      stroke-linecap="round"
    />
    <path
      v-if="area"
      :d="area"
      :fill="fill"
      stroke="none"
    />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  width: { type: Number, default: 110 },
  height: { type: Number, default: 28 },
  stroke: { type: String, default: '#5b8def' },
  fill: { type: String, default: 'rgba(91, 141, 239, 0.14)' },
})

const vbWidth = 100
const vbHeight = 28

const points = computed(() => {
  const values = (props.data || []).map((v) => Number(v) || 0)
  if (!values.length) return []
  const max = Math.max(1, ...values)
  const n = values.length
  return values.map((v, i) => {
    const x = (i / Math.max(1, n - 1)) * vbWidth
    const y = vbHeight - (v / max) * (vbHeight - 4) - 2
    return [x, y]
  })
})

const path = computed(() => {
  if (!points.value.length) return ''
  return points.value
    .map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`)
    .join(' ')
})

const area = computed(() => {
  if (!points.value.length) return ''
  const head = points.value
    .map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`)
    .join(' ')
  const lastX = points.value[points.value.length - 1][0].toFixed(2)
  return `${head} L${lastX},${vbHeight} L0,${vbHeight} Z`
})
</script>
