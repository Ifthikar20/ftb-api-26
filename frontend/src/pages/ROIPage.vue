<template>
  <div class="cs-page mx-auto max-w-5xl px-6 py-12 sm:px-8 lg:px-12">
    <header class="mb-10 max-w-3xl">
      <div class="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-rose-500">
        Content Studio
      </div>
      <h1 class="text-3xl font-semibold tracking-tight text-zinc-900">
        Did the content move the needle?
      </h1>
      <p class="mt-2 text-sm leading-relaxed text-zinc-500">
        Every published draft is measured against your visibility, citations, and accuracy
        a few weeks later. Here's the story so far.
      </p>
    </header>

    <!-- Aggregate -->
    <section
      v-if="!loading && rows.length"
      class="mb-10 rounded-3xl border border-zinc-200 bg-white p-8 shadow-sm"
    >
      <p class="text-xl font-medium leading-snug text-zinc-900">
        Drafts published have lifted your visibility by
        <span :class="aggregateLift >= 0 ? 'text-emerald-600' : 'text-rose-600'">
          {{ aggregateLift >= 0 ? '+' : '' }}{{ aggregateLift.toFixed(1) }} pts
        </span>
        this quarter.
      </p>
      <p class="mt-2 text-sm text-zinc-500">
        Across {{ rows.length }} {{ rows.length === 1 ? 'measured draft' : 'measured drafts' }}.
      </p>
    </section>

    <div v-if="loading" class="grid gap-4">
      <div v-for="i in 4" :key="i" class="h-24 animate-pulse rounded-2xl border border-zinc-200 bg-white"></div>
    </div>

    <div
      v-else-if="!rows.length"
      class="flex flex-col items-center justify-center rounded-3xl border border-dashed border-zinc-200 bg-white px-8 py-20 text-center"
    >
      <div class="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-rose-50 text-rose-500">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 17l6-6 4 4 8-8" />
          <path d="M14 7h6v6" />
        </svg>
      </div>
      <h3 class="text-lg font-semibold text-zinc-900">No measurements yet.</h3>
      <p class="mt-2 max-w-md text-sm text-zinc-500">
        Once you publish your first draft, we'll measure the lift here over the following
        weeks. Visibility, citation count, and accuracy — all in one place.
      </p>
    </div>

    <div v-else class="grid gap-4">
      <ROITimelineCard v-for="r in rows" :key="r.id" :row="r" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import contentStudioApi from '@/api/contentStudio'
import ROITimelineCard from '@/components/content_studio/ROITimelineCard.vue'

const route = useRoute()
const websiteId = computed(() => route.params.websiteId)

const loading = ref(false)
const rows = ref([])

const aggregateLift = computed(() => {
  if (!rows.value.length) return 0
  const sum = rows.value.reduce((acc, r) => acc + (Number(r.visibility_lift) || 0), 0)
  return sum / rows.value.length
})

async function load() {
  if (!websiteId.value) return
  loading.value = true
  try {
    const { data } = await contentStudioApi.roi(websiteId.value)
    const body = data?.data || data || {}
    const list = body.results || body || []
    rows.value = Array.isArray(list) ? list : []
  } catch {
    rows.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
