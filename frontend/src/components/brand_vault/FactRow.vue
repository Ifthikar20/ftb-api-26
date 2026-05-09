<template>
  <AirCard size="md" interactive class="fact-card flex h-full flex-col">
    <div class="mb-3 flex items-start justify-between gap-3">
      <div class="min-w-0">
        <div class="text-[15px] font-semibold leading-snug" style="color: var(--text-primary)">
          {{ fact.subject }}
        </div>
        <div class="mt-1 text-[13px] leading-relaxed" style="color: var(--text-secondary)">
          <span class="font-medium" style="color: var(--text-primary)">{{ fact.predicate }}</span>
          <span class="mx-1.5" style="color: var(--text-muted)">·</span>
          <span>{{ fact.object }}</span>
        </div>
      </div>
      <AirChip :variant="statusVariant" size="xs">{{ statusLabel }}</AirChip>
    </div>

    <div class="mt-auto flex flex-col gap-3 pt-4" style="border-top: 1px solid var(--border-color)">
      <div class="flex items-center gap-2">
        <span class="text-[10px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)">
          Confidence
        </span>
        <div class="h-1.5 flex-1 overflow-hidden rounded-full" style="background: var(--border-color)">
          <div class="h-full rounded-full" :style="{ width: pct + '%', background: 'var(--brand-accent)' }"></div>
        </div>
        <span class="tabular-nums text-xs" style="color: var(--text-secondary)">{{ pct }}%</span>
      </div>

      <div class="flex items-center justify-between gap-2">
        <a
          v-if="fact.source_url"
          :href="fact.source_url"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1 text-xs font-medium hover:underline"
          style="color: var(--brand-accent)"
          @click.stop
        >
          Source
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
            <path d="M3 7l4-4M4 3h3v3" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </a>
        <span v-else class="text-xs" style="color: var(--text-muted)">No source</span>

        <div v-if="isPending" class="flex flex-wrap gap-2">
          <AirButton variant="outline" size="xs" @click.stop="$emit('edit-click', fact)">Edit</AirButton>
          <AirButton variant="ghost" size="xs" @click.stop="$emit('reject', fact)">Reject</AirButton>
          <AirButton variant="primary" size="xs" @click.stop="$emit('approve', fact)">Approve</AirButton>
        </div>
      </div>
    </div>
  </AirCard>
</template>

<script setup>
import { computed } from 'vue'
import AirCard from '@/components/ui/AirCard.vue'
import AirButton from '@/components/ui/AirButton.vue'
import AirChip from '@/components/ui/AirChip.vue'

const props = defineProps({
  fact: { type: Object, required: true },
})

defineEmits(['approve', 'reject', 'edit-click'])

const STATUS_VARIANT = {
  pending: 'warning',
  approved: 'success',
  rejected: 'neutral',
  auto: 'info',
}

const statusVariant = computed(() => STATUS_VARIANT[props.fact.status] || 'warning')

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
