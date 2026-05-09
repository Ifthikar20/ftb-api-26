<template>
  <tr class="border-b border-gray-100 align-top">
    <td class="px-3 py-2 text-sm text-gray-900">{{ fact.subject }}</td>
    <td class="px-3 py-2 text-sm text-gray-700">{{ fact.predicate }}</td>
    <td class="px-3 py-2 text-sm text-gray-700">{{ fact.object }}</td>
    <td class="px-3 py-2">
      <div class="flex items-center gap-2">
        <div class="h-2 w-20 overflow-hidden rounded-full bg-gray-100">
          <div class="h-full bg-indigo-500" :style="{ width: pct + '%' }"></div>
        </div>
        <span class="text-xs text-gray-500">{{ pct }}%</span>
      </div>
    </td>
    <td class="px-3 py-2">
      <span
        class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
        :class="statusClass"
      >
        {{ statusLabel }}
      </span>
    </td>
    <td class="px-3 py-2 text-sm">
      <a
        v-if="fact.source_url"
        :href="fact.source_url"
        target="_blank"
        rel="noopener noreferrer"
        class="text-indigo-700 hover:underline"
      >
        Source
      </a>
      <span v-else class="text-xs text-gray-400">—</span>
    </td>
    <td class="px-3 py-2">
      <div v-if="isPending" class="flex flex-wrap gap-1">
        <button
          class="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-800 hover:bg-emerald-100"
          @click="$emit('approve', fact)"
        >
          Approve
        </button>
        <button
          class="rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-xs text-rose-800 hover:bg-rose-100"
          @click="$emit('reject', fact)"
        >
          Reject
        </button>
        <button
          class="rounded-md border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
          @click="$emit('edit-click', fact)"
        >
          Edit
        </button>
      </div>
      <span v-else class="text-xs text-gray-400">—</span>
    </td>
  </tr>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  fact: { type: Object, required: true },
})

defineEmits(['approve', 'reject', 'edit-click'])

const STATUS_STYLES = {
  pending: 'bg-amber-100 text-amber-800',
  approved: 'bg-emerald-100 text-emerald-800',
  rejected: 'bg-zinc-100 text-zinc-700',
  auto: 'bg-blue-100 text-blue-800',
}

const statusClass = computed(() => STATUS_STYLES[props.fact.status] || STATUS_STYLES.pending)

const statusLabel = computed(() => {
  const s = props.fact.status || 'pending'
  if (s === 'auto') return 'Auto-approved'
  return s.charAt(0).toUpperCase() + s.slice(1)
})

const isPending = computed(() => props.fact.status === 'pending')

const pct = computed(() => {
  const c = Number(props.fact.confidence) || 0
  const v = c <= 1 ? c * 100 : c
  return Math.max(0, Math.min(100, Math.round(v)))
})
</script>
