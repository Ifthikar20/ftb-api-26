<template>
  <article
    class="group relative flex h-full cursor-pointer flex-col rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm transition-all duration-150 ease-out hover:-translate-y-0.5 hover:shadow-md"
    @click="$emit('select', brief)"
  >
    <!-- Top row: badges -->
    <div class="mb-3 flex flex-wrap items-center gap-2">
      <GapTypeBadge :gap="brief.gap_type" />
      <FormatBadge v-if="brief.target_format" :format="brief.target_format" />
    </div>

    <!-- Headline -->
    <h3 class="text-[15px] font-medium leading-snug text-zinc-900 line-clamp-2">
      {{ brief.headline || 'Untitled brief' }}
    </h3>

    <!-- Description -->
    <p
      v-if="brief.description"
      class="mt-2 text-[13px] leading-relaxed text-zinc-500 line-clamp-3"
    >
      {{ brief.description }}
    </p>

    <!-- Footer -->
    <div class="mt-5 flex items-end justify-between gap-3 pt-4 border-t border-zinc-100">
      <div class="flex flex-col gap-1">
        <span class="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
          Impact
        </span>
        <div class="flex items-end gap-1" aria-hidden="true">
          <span
            v-for="i in 3"
            :key="i"
            class="block w-1.5 rounded-sm transition-colors"
            :class="[
              i === 1 ? 'h-2' : i === 2 ? 'h-3' : 'h-4',
              i <= impactBars ? 'bg-rose-500' : 'bg-zinc-200',
            ]"
          ></span>
        </div>
      </div>

      <button
        type="button"
        class="inline-flex items-center gap-1.5 rounded-full bg-rose-500 px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-rose-600"
        @click.stop="$emit('select', brief)"
      >
        Create draft
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M2.5 6h7" />
          <path d="M6.5 3l3 3-3 3" />
        </svg>
      </button>
    </div>

    <!-- Skip on hover -->
    <button
      type="button"
      class="absolute right-3 top-3 hidden rounded-full bg-white/95 p-1.5 text-zinc-400 shadow-sm ring-1 ring-zinc-200 transition-colors hover:text-zinc-700 group-hover:block"
      title="Skip this brief"
      @click.stop="$emit('skip', brief)"
    >
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
        <path d="M3 3l6 6M9 3l-6 6" />
      </svg>
    </button>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import GapTypeBadge from './GapTypeBadge.vue'
import FormatBadge from './FormatBadge.vue'

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
