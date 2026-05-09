<template>
  <div class="cs-page mx-auto max-w-7xl px-6 py-10 sm:px-8 lg:px-12">
    <!-- Top bar -->
    <header class="mb-8 flex flex-wrap items-center gap-4">
      <button
        type="button"
        class="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
        @click="goBack"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M9 3l-4 4 4 4" />
        </svg>
        Back
      </button>
      <nav class="flex flex-wrap items-center gap-1.5 text-sm text-zinc-500" aria-label="Breadcrumb">
        <router-link :to="`/llm-ranking/${websiteId}/content`" class="hover:text-zinc-800">
          Content Studio
        </router-link>
        <span class="text-zinc-300">/</span>
        <span class="truncate text-zinc-800">{{ briefHeadline }}</span>
      </nav>
      <div class="ml-auto text-xs text-zinc-500">
        <span v-if="draft">Revision {{ draft.revision || 1 }} ·</span>
        <span>{{ savedLabel }}</span>
      </div>
    </header>

    <!-- Loading -->
    <div v-if="loading" class="grid gap-6 lg:grid-cols-[3fr,2fr]">
      <div class="h-[600px] animate-pulse rounded-2xl border border-zinc-200 bg-white"></div>
      <div class="h-[600px] animate-pulse rounded-2xl border border-zinc-200 bg-white"></div>
    </div>

    <div v-else-if="draft" class="grid gap-6 lg:grid-cols-[3fr,2fr]">
      <!-- LEFT: editor -->
      <section>
        <DraftEditor
          v-model:title="form.title"
          v-model:body="form.body"
        />
      </section>

      <!-- RIGHT: brief & guards -->
      <aside class="flex flex-col gap-4">
        <AirCard size="sm">
          <div class="mb-3 flex flex-wrap items-center gap-2">
            <GapTypeBadge v-if="brief?.gap_type" :gap="brief.gap_type" />
            <FormatBadge v-if="brief?.target_format" :format="brief.target_format" />
          </div>
          <h3 class="text-[15px] font-medium" style="color: var(--text-primary)">
            {{ brief?.headline || 'Brief' }}
          </h3>
          <p
            v-if="brief?.description"
            class="mt-2 text-sm leading-relaxed"
            style="color: var(--text-secondary)"
          >
            {{ brief.description }}
          </p>
        </AirCard>

        <AirCard size="sm">
          <div class="mb-4">
            <QualityScoreBar :score="Number(draft.voice_score) || 0" label="Voice match" />
            <p v-if="draft.voice_notes" class="mt-1.5 text-xs" style="color: var(--text-secondary)">{{ draft.voice_notes }}</p>
          </div>
          <div>
            <QualityScoreBar :score="Number(draft.accuracy_score) || 0" label="Accuracy" />
            <p v-if="draft.accuracy_notes" class="mt-1.5 text-xs" style="color: var(--text-secondary)">{{ draft.accuracy_notes }}</p>
          </div>
        </AirCard>

        <AirCard size="sm">
          <button
            type="button"
            class="flex w-full items-center justify-between text-left"
            @click="factsOpen = !factsOpen"
          >
            <span class="text-[13px] font-semibold text-zinc-900">
              Grounded facts ({{ groundedFactIds.length }})
            </span>
            <svg
              :class="['h-4 w-4 text-zinc-400 transition-transform', factsOpen ? 'rotate-180' : '']"
              viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"
            >
              <path d="M4 6l4 4 4-4" />
            </svg>
          </button>
          <div v-if="factsOpen" class="mt-3 flex flex-col gap-2">
            <div
              v-if="!groundedFactIds.length"
              class="rounded-xl bg-zinc-50 px-4 py-3 text-xs text-zinc-500"
            >
              No facts were attached to this draft.
            </div>
            <div
              v-for="id in groundedFactIds"
              :key="id"
              class="rounded-xl bg-zinc-50 px-4 py-2.5 text-xs text-zinc-600"
            >
              <span class="font-mono text-[11px] text-zinc-400">{{ String(id).slice(0, 8) }}</span>
              <span class="ml-2">grounded fact reference</span>
            </div>
          </div>
        </AirCard>

        <AirButton
          variant="outline"
          size="md"
          :loading="regenerating"
          :disabled="regenerating"
          @click="regenerate"
        >
          {{ regenerating ? 'Regenerating...' : 'Regenerate draft' }}
        </AirButton>
      </aside>
    </div>

    <div v-else class="rounded-3xl border border-dashed border-zinc-200 bg-white px-8 py-20 text-center text-zinc-500">
      Draft not found.
    </div>

    <!-- Sticky footer action bar -->
    <div
      v-if="draft"
      class="sticky bottom-4 z-30 mt-8 flex flex-wrap items-center justify-end gap-2 rounded-full border border-zinc-200 bg-white/95 px-4 py-2.5 shadow-md backdrop-blur"
    >
      <AirButton variant="ghost" size="md" :loading="saving" :disabled="saving" @click="save">
        {{ saving ? 'Saving...' : 'Save draft' }}
      </AirButton>
      <AirButton
        variant="outline"
        size="md"
        :loading="approving"
        :disabled="approving || draft.status === 'approved' || draft.status === 'published'"
        @click="approve"
      >
        {{ draft.status === 'approved' ? 'Approved' : (approving ? 'Approving...' : 'Approve') }}
      </AirButton>

      <div class="relative">
        <AirButton variant="primary" size="md" @click="publishMenuOpen = !publishMenuOpen">
          Publish
          <template #iconRight>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 5l3 3 3-3" />
            </svg>
          </template>
        </AirButton>
        <div
          v-if="publishMenuOpen"
          class="absolute bottom-full right-0 mb-2 w-72 rounded-2xl border border-zinc-200 bg-white p-2 shadow-lg"
          @click.stop
        >
          <div class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
            Publish to
          </div>
          <div v-if="!publishTargets.length" class="px-3 py-3 text-xs text-zinc-500">
            No targets configured yet.
            <router-link
              :to="`/llm-ranking/${websiteId}/content/publish-targets`"
              class="mt-2 block font-semibold text-rose-600"
            >
              Add a publish target →
            </router-link>
          </div>
          <button
            v-for="t in publishTargets"
            :key="t.id"
            type="button"
            class="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm text-zinc-700 hover:bg-zinc-50"
            @click="confirmPublish(t)"
          >
            <span>{{ t.label || t.provider }}</span>
            <span v-if="t.is_default" class="text-[10px] font-semibold uppercase tracking-wider text-rose-500">Default</span>
          </button>
        </div>
      </div>

      <div class="relative">
        <AirButton variant="ghost" size="md" @click="exportMenuOpen = !exportMenuOpen">
          Export
          <template #iconRight>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 5l3 3 3-3" />
            </svg>
          </template>
        </AirButton>
        <div
          v-if="exportMenuOpen"
          class="absolute bottom-full right-0 mb-2 w-44 rounded-2xl border border-zinc-200 bg-white p-2 shadow-lg"
        >
          <button
            v-for="fmt in ['md', 'html', 'json']"
            :key="fmt"
            type="button"
            class="block w-full rounded-xl px-3 py-2 text-left text-sm text-zinc-700 hover:bg-zinc-50"
            @click="exportAs(fmt)"
          >
            Download .{{ fmt }}
          </button>
        </div>
      </div>
    </div>

    <!-- Publish modal -->
    <Teleport to="body">
      <div
        v-if="publishConfirm"
        class="fixed inset-0 z-[200] flex items-center justify-center bg-zinc-900/60 px-4"
        @click.self="publishConfirm = null"
      >
        <div class="w-full max-w-md rounded-3xl bg-white p-8 shadow-lg">
          <h3 class="text-lg font-semibold text-zinc-900">
            Publish to {{ publishConfirm.label || publishConfirm.provider }}?
          </h3>
          <p class="mt-2 text-sm leading-relaxed text-zinc-500">
            We'll send this approved draft to <strong>{{ publishConfirm.label || publishConfirm.provider }}</strong>.
            You can change targets later.
          </p>
          <div class="mt-6 flex justify-end gap-2">
            <AirButton variant="ghost" size="md" @click="publishConfirm = null">
              Cancel
            </AirButton>
            <AirButton
              variant="primary"
              size="md"
              :loading="publishing"
              :disabled="publishing"
              @click="doPublish"
            >
              {{ publishing ? 'Publishing...' : 'Confirm publish' }}
            </AirButton>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import contentStudioApi from '@/api/contentStudio'
import DraftEditor from '@/components/content_studio/DraftEditor.vue'
import GapTypeBadge from '@/components/content_studio/GapTypeBadge.vue'
import FormatBadge from '@/components/content_studio/FormatBadge.vue'
import QualityScoreBar from '@/components/content_studio/QualityScoreBar.vue'
import AirButton from '@/components/ui/AirButton.vue'
import AirCard from '@/components/ui/AirCard.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const websiteId = computed(() => route.params.websiteId)
const draftId = computed(() => route.params.draftId)

const loading = ref(true)
const saving = ref(false)
const approving = ref(false)
const regenerating = ref(false)
const publishing = ref(false)
const lastSavedAt = ref(null)

const draft = ref(null)
const brief = ref(null)
const publishTargets = ref([])
const publishConfirm = ref(null)
const publishMenuOpen = ref(false)
const exportMenuOpen = ref(false)
const factsOpen = ref(false)

const form = reactive({ title: '', body: '' })

const briefHeadline = computed(() => brief.value?.headline || 'Draft')

const groundedFactIds = computed(() => brief.value?.grounded_fact_ids || [])

const savedLabel = computed(() => {
  if (saving.value) return 'saving...'
  if (!lastSavedAt.value) return 'unsaved changes'
  const diff = Math.round((Date.now() - lastSavedAt.value) / 60000)
  if (diff <= 0) return 'last saved just now'
  if (diff === 1) return 'last saved 1 min ago'
  return `last saved ${diff} min ago`
})

async function loadDraft() {
  loading.value = true
  try {
    const { data } = await contentStudioApi.draftDetail(draftId.value)
    const body = data?.data || data
    draft.value = body
    form.title = body?.title || ''
    form.body = body?.body_markdown || ''
    if (body?.brief) {
      try {
        const { data: bData } = await contentStudioApi.briefDetail(body.brief)
        brief.value = bData?.data || bData
      } catch {
        // soft fail
      }
    }
  } catch {
    draft.value = null
  } finally {
    loading.value = false
  }
}

async function loadTargets() {
  try {
    const { data } = await contentStudioApi.publishTargets(websiteId.value)
    const body = data?.data || data || {}
    const list = body.results || body || []
    publishTargets.value = (Array.isArray(list) ? list : []).filter((t) => t.is_active !== false)
  } catch {
    publishTargets.value = []
  }
}

async function save() {
  if (!draft.value) return
  saving.value = true
  try {
    const { data } = await contentStudioApi.updateDraft(draft.value.id, {
      title: form.title,
      body_markdown: form.body,
    })
    const body = data?.data || data
    draft.value = body || draft.value
    lastSavedAt.value = Date.now()
    toast.success('Draft saved.')
  } catch {
    // handled
  } finally {
    saving.value = false
  }
}

async function approve() {
  approving.value = true
  try {
    // Save first to persist any edits.
    if (saving.value === false) {
      await contentStudioApi.updateDraft(draft.value.id, {
        title: form.title,
        body_markdown: form.body,
      })
    }
    const { data } = await contentStudioApi.approveDraft(draft.value.id)
    const body = data?.data || data
    draft.value = body || draft.value
    toast.success('Draft approved. Choose a target to publish.')
  } catch {
    // handled
  } finally {
    approving.value = false
  }
}

async function regenerate() {
  if (!confirm('Regenerate this draft? Your unsaved edits will be replaced.')) return
  regenerating.value = true
  try {
    const { data } = await contentStudioApi.regenerateDraft(draft.value.id)
    const body = data?.data || data
    if (body?.id) {
      router.replace(`/llm-ranking/${websiteId.value}/content/drafts/${body.id}`)
      await loadDraft()
    }
    toast.success('A fresh draft is on the way.')
  } catch {
    // handled
  } finally {
    regenerating.value = false
  }
}

function confirmPublish(target) {
  publishMenuOpen.value = false
  publishConfirm.value = target
}

async function doPublish() {
  if (!publishConfirm.value) return
  publishing.value = true
  try {
    await contentStudioApi.publishDraft(draft.value.id, publishConfirm.value.id)
    toast.success(`Sent to ${publishConfirm.value.label || publishConfirm.value.provider}.`)
    publishConfirm.value = null
    router.push(`/llm-ranking/${websiteId.value}/content`)
  } catch {
    // handled
  } finally {
    publishing.value = false
  }
}

async function exportAs(fmt) {
  exportMenuOpen.value = false
  try {
    const { data } = await contentStudioApi.exportDraft(draft.value.id, fmt)
    const blob = data instanceof Blob ? data : new Blob([data], { type: 'application/octet-stream' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${(draft.value.title || 'draft').replace(/\s+/g, '-').toLowerCase()}.${fmt}`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch {
    // handled
  }
}

function goBack() {
  router.push(`/llm-ranking/${websiteId.value}/content`)
}

onMounted(() => {
  loadDraft()
  loadTargets()
})
</script>
