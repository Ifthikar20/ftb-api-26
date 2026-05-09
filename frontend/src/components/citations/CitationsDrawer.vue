<template>
  <div
    v-if="open"
    class="fixed inset-0 z-40 flex justify-end bg-black/30"
    @click.self="close"
  >
    <div class="flex h-full w-full max-w-xl flex-col bg-white shadow-xl">
      <header class="flex items-start justify-between gap-3 border-b px-4 py-3">
        <div class="min-w-0">
          <h2 class="text-base font-semibold text-gray-900">Citations</h2>
          <p v-if="provider" class="text-xs text-gray-500">{{ provider }}</p>
          <p
            v-if="prompt"
            class="mt-1 text-sm text-gray-700 line-clamp-2"
            :title="prompt"
          >
            {{ prompt }}
          </p>
        </div>
        <button
          class="rounded text-gray-400 hover:text-gray-700"
          @click="close"
          aria-label="Close"
        >
          Close
        </button>
      </header>

      <div class="flex items-center justify-between border-b px-4 py-2 text-xs text-gray-600">
        <span>{{ citations.length }} citation{{ citations.length === 1 ? '' : 's' }}</span>
        <button
          v-if="citations.length"
          class="rounded-md border px-2 py-1 text-xs hover:bg-gray-50"
          @click="openAll"
        >
          Open all in new tabs
        </button>
      </div>

      <div class="flex-1 overflow-auto px-4 py-3">
        <div v-if="!citations.length" class="py-12 text-center text-sm text-gray-500">
          No citations were extracted for this response.
        </div>
        <div v-else>
          <div v-for="group in groups" :key="group.source_class" class="mb-5">
            <div class="mb-2 flex items-center gap-2">
              <SourceClassBadge :source_class="group.source_class" />
              <span class="text-xs text-gray-500">{{ group.items.length }}</span>
            </div>
            <ul class="space-y-2">
              <li
                v-for="c in group.items"
                :key="c.id"
                class="rounded-md border border-gray-100 px-3 py-2"
              >
                <div class="flex items-start gap-2 text-sm">
                  <span
                    v-if="c.position != null"
                    class="mt-0.5 inline-block min-w-[1.25rem] text-xs text-gray-400"
                  >
                    #{{ c.position }}
                  </span>
                  <div class="min-w-0 flex-1">
                    <a
                      :href="c.url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="block truncate font-medium text-indigo-700 hover:underline"
                      :title="c.title || c.url"
                    >
                      {{ c.title || c.url }}
                    </a>
                    <div class="text-xs text-gray-500">{{ c.apex_domain || c.domain }}</div>
                    <p
                      v-if="c.snippet"
                      class="mt-1 line-clamp-3 text-xs text-gray-600"
                    >
                      {{ c.snippet }}
                    </p>
                    <div class="mt-1 flex flex-wrap gap-1">
                      <span
                        v-if="c.is_target"
                        class="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800"
                      >
                        Your site
                      </span>
                      <span
                        v-if="c.is_competitor"
                        class="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
                      >
                        Competitor
                      </span>
                    </div>
                  </div>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SourceClassBadge from './SourceClassBadge.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  citations: { type: Array, default: () => [] },
  provider: { type: String, default: '' },
  prompt: { type: String, default: '' },
})

const emit = defineEmits(['update:open'])

function close() {
  emit('update:open', false)
}

function openAll() {
  for (const c of props.citations) {
    if (c.url) window.open(c.url, '_blank', 'noopener')
  }
}

const groups = computed(() => {
  const buckets = new Map()
  for (const c of props.citations || []) {
    const key = c.source_class || 'other'
    if (!buckets.has(key)) buckets.set(key, [])
    buckets.get(key).push(c)
  }
  return Array.from(buckets.entries())
    .map(([source_class, items]) => ({ source_class, items }))
    .sort((a, b) => b.items.length - a.items.length)
})
</script>
