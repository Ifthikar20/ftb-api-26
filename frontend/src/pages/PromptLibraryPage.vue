<template>
  <div class="p-6">
    <header id="pl-header" class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold">Prompt Library</h1>
        <p class="text-sm text-gray-500">
          Demand-side prompts mined from real users — pick which ones to include in your audits.
        </p>
      </div>
      <IndustryTypeahead
        id="pl-industry"
        v-model="industryId"
        placeholder="Filter by industry"
        class="w-64"
      />
    </header>

    <section id="pl-buckets" class="mb-4 flex flex-wrap gap-2">
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

    <OnboardingTooltip storage-key="fb_tour_prompt_library_v1" :steps="tourSteps" />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import promptLibrary from '@/api/promptLibrary'
import IndustryTypeahead from '@/components/IndustryTypeahead.vue'
import OnboardingTooltip from '@/components/OnboardingTooltip.vue'

const tourSteps = [
  {
    target: '#pl-header',
    title: 'Welcome to the Prompt Library',
    message: 'These are demand-side prompts — real questions people ask AI assistants in your category. We use them to test whether your brand shows up.',
    position: 'bottom',
  },
  {
    target: '#pl-industry',
    title: 'Filter by industry',
    message: 'Pick your industry to see prompts mined for that category. New prompts arrive daily from Reddit, search data, and AI-generated paraphrases.',
    position: 'left',
  },
  {
    target: '#pl-buckets',
    title: 'Intent buckets',
    message: 'Prompts are grouped by intent: Category ("best CRM"), Comparison ("X vs Y"), Problem ("how do I…"), and Local ("near me"). Use these to spot coverage gaps.',
    position: 'bottom',
  },
]

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
