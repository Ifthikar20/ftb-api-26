<template>
  <AirCard
    size="md"
    interactive
    class="brief-card group relative h-full"
    @click="$emit('select', brief)"
  >
    <div class="flex h-full flex-col">
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <GapTypeBadge :gap="brief.gap_type" />
        <FormatBadge v-if="brief.target_format" :format="brief.target_format" />
      </div>

      <h3 class="text-[15px] font-medium leading-snug line-clamp-2" style="color: var(--text-primary)">
        {{ brief.headline || 'Untitled brief' }}
      </h3>

      <p
        v-if="brief.description"
        class="mt-2 text-[13px] leading-relaxed line-clamp-3"
        style="color: var(--text-secondary)"
      >
        {{ brief.description }}
      </p>

      <div
        class="mt-auto flex items-end justify-between gap-3 pt-5"
        style="border-top: 1px solid var(--border-color)"
      >
        <div class="flex flex-col gap-1">
          <span class="text-[10px] font-semibold uppercase tracking-wider" style="color: var(--text-muted)">
            Impact
          </span>
          <div class="flex items-end gap-1" aria-hidden="true">
            <span
              v-for="i in 3"
              :key="i"
              class="block w-1.5 rounded-sm transition-colors"
              :class="[i === 1 ? 'h-2' : i === 2 ? 'h-3' : 'h-4']"
              :style="{ background: i <= impactBars ? 'var(--brand-accent)' : 'var(--border-color)' }"
            ></span>
          </div>
        </div>

        <AirButton
          variant="primary"
          size="sm"
          @click.stop="$emit('select', brief)"
        >
          Create draft
          <template #iconRight>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M2.5 6h7" />
              <path d="M6.5 3l3 3-3 3" />
            </svg>
          </template>
        </AirButton>
      </div>
    </div>

    <button
      type="button"
      class="brief-card__skip"
      title="Skip this brief"
      @click.stop="$emit('skip', brief)"
    >
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
        <path d="M3 3l6 6M9 3l-6 6" />
      </svg>
    </button>
  </AirCard>
</template>

<script setup>
import { computed } from 'vue'
import GapTypeBadge from './GapTypeBadge.vue'
import FormatBadge from './FormatBadge.vue'
import AirCard from '@/components/ui/AirCard.vue'
import AirButton from '@/components/ui/AirButton.vue'

const props = defineProps({
  brief: { type: Object, required: true },
})

defineEmits(['select', 'skip'])

const impactBars = computed(() => {
  const s = Number(props.brief?.impact_score) || 0
  if (s >= 0.66) return 3
  if (s >= 0.33) return 2
  if (s > 0) return 1
  return 0
})
</script>

<style scoped>
.brief-card__skip {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  display: none;
  padding: 0.375rem;
  border-radius: 9999px;
  background: var(--bg-card);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
  transition: color 150ms ease-out, transform 150ms ease-out;
}
.brief-card:hover .brief-card__skip {
  display: inline-flex;
}
.brief-card__skip:hover {
  color: var(--text-primary);
  transform: scale(1.05);
}
</style>
