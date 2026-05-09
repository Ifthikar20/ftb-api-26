<template>
  <div class="p-6">
    <header class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold">Prompt Library</h1>
        <p class="text-sm text-gray-500">
          Demand-side prompts mined from real users — pick which ones to include in your audits.
        </p>
      </div>
      <IndustryTypeahead
        v-model="industryId"
        placeholder="Filter by industry"
        class="w-64"
      />
    </header>

    <section class="mb-4 flex flex-wrap gap-2">
      <button
        v-for="bucket in buckets"
        :key="bucket.value"
        class="rounded-full border px-3 py-1 text-sm"
        :class="bucket.value === intent ? 'border-indigo-600 bg-indigo-50 text-indigo-700' : 'border-gray-200 text-gray-600'"
        @click="intent = bucket.value"
      >
        {{ bucket.label }}
      </button>
    </section>

    <div v-if="loading" class="text-sm text-gray-500">Loading...</div>
    <ul v-else class="space-y-2">
      <li
        v-for="p in prompts"
        :key="p.id"
        class="flex items-start justify-between rounded-md border border-gray-100 px-3 py-2"
      >
        <div>
          <div class="text-sm text-gray-900">{{ p.text }}</div>
          <div class="text-xs text-gray-500">
            {{ p.intent_bucket }} · {{ p.source_label }} · score {{ p.demand_score?.toFixed?.(0) || 0 }}
          </div>
        </div>
      </li>
      <li v-if="!prompts.length" class="rounded-md border border-dashed p-6 text-center text-sm text-gray-500">
        No prompts yet for this industry. The daily miner will populate this list.
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import promptLibrary from '@/api/promptLibrary'
import IndustryTypeahead from '@/components/IndustryTypeahead.vue'

const industryId = ref(null)
const intent = ref('')
const prompts = ref([])
const loading = ref(false)

const buckets = [
  { value: '', label: 'All' },
  { value: 'category', label: 'Category' },
  { value: 'comparison', label: 'Comparison' },
  { value: 'problem', label: 'Problem' },
  { value: 'local', label: 'Local' },
]

async function load() {
  loading.value = true
  try {
    const params = { limit: 100 }
    if (intent.value) params.intent_bucket = intent.value
    // industryId is a UUID; the list endpoint filters by slug. The
    // typeahead emits the id — we look up the slug from the loaded list
    // via a side-effect on selection in a later iteration. For now, omit
    // the filter when no slug is known to keep the page responsive.
    const { data } = await promptLibrary.getPrompts(params)
    const rows = data?.data?.results || data?.results || data?.data || data || []
    prompts.value = Array.isArray(rows) ? rows : []
  } catch {
    prompts.value = []
  } finally {
    loading.value = false
  }
}

watch([industryId, intent], load, { immediate: true })
</script>
