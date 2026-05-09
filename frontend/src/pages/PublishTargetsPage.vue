<template>
  <div class="cs-page mx-auto max-w-5xl px-6 py-12 sm:px-8 lg:px-12">
    <header class="mb-10 flex flex-wrap items-end justify-between gap-4">
      <div class="max-w-2xl">
        <div class="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-rose-500">
          Content Studio
        </div>
        <h1 class="text-3xl font-semibold tracking-tight text-zinc-900">
          Publish targets
        </h1>
        <p class="mt-2 text-sm leading-relaxed text-zinc-500">
          Where approved drafts land. Configure a webhook, your CMS, an editor inbox,
          or a GitHub repo — pick a default and you can publish in one click.
        </p>
      </div>
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-full bg-rose-500 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-rose-600"
        @click="openCreate"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M7 2v10M2 7h10" />
        </svg>
        Add target
      </button>
    </header>

    <div v-if="loading" class="grid gap-4">
      <div v-for="i in 3" :key="i" class="h-20 animate-pulse rounded-2xl border border-zinc-200 bg-white"></div>
    </div>

    <div
      v-else-if="!targets.length"
      class="flex flex-col items-center justify-center rounded-3xl border border-dashed border-zinc-200 bg-white px-8 py-20 text-center"
    >
      <div class="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-rose-50 text-rose-500">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 7h16M4 12h16M4 17h10" />
        </svg>
      </div>
      <h3 class="text-lg font-semibold text-zinc-900">No publish targets yet.</h3>
      <p class="mt-2 max-w-md text-sm text-zinc-500">
        Add a target so approved drafts can leave the studio. We support webhooks, WordPress,
        Ghost, email, and GitHub.
      </p>
      <button
        type="button"
        class="mt-6 rounded-full bg-rose-500 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-rose-600"
        @click="openCreate"
      >
        Add your first target
      </button>
    </div>

    <div v-else class="grid gap-4">
      <PublishTargetCard
        v-for="t in targets"
        :key="t.id"
        :target="t"
        @edit="openEdit"
        @delete="confirmDelete = $event"
      />
    </div>

    <PublishTargetForm
      v-model="formOpen"
      :target="editing"
      :saving="saving"
      @submit="onSubmit"
    />

    <Teleport to="body">
      <div
        v-if="confirmDelete"
        class="fixed inset-0 z-[200] flex items-center justify-center bg-zinc-900/60 px-4"
        @click.self="confirmDelete = null"
      >
        <div class="w-full max-w-md rounded-3xl bg-white p-8 shadow-lg">
          <h3 class="text-lg font-semibold text-zinc-900">Remove this target?</h3>
          <p class="mt-2 text-sm text-zinc-500">
            Drafts will no longer publish to <strong>{{ confirmDelete.label || confirmDelete.provider }}</strong>.
            You can re-add it any time.
          </p>
          <div class="mt-6 flex justify-end gap-2">
            <button
              type="button"
              class="rounded-full px-4 py-2 text-sm font-semibold text-zinc-700 hover:bg-zinc-100"
              @click="confirmDelete = null"
            >
              Cancel
            </button>
            <button
              type="button"
              class="rounded-full bg-rose-500 px-5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-rose-600 disabled:opacity-50"
              :disabled="deleting"
              @click="onDelete"
            >
              {{ deleting ? 'Removing...' : 'Remove target' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from '@/composables/useToast'
import contentStudioApi from '@/api/contentStudio'
import PublishTargetCard from '@/components/content_studio/PublishTargetCard.vue'
import PublishTargetForm from '@/components/content_studio/PublishTargetForm.vue'

const route = useRoute()
const toast = useToast()

const websiteId = computed(() => route.params.websiteId)

const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const targets = ref([])
const formOpen = ref(false)
const editing = ref(null)
const confirmDelete = ref(null)

async function load() {
  if (!websiteId.value) return
  loading.value = true
  try {
    const { data } = await contentStudioApi.publishTargets(websiteId.value)
    const body = data?.data || data || {}
    const list = body.results || body || []
    targets.value = Array.isArray(list) ? list : []
  } catch {
    targets.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  formOpen.value = true
}

function openEdit(t) {
  editing.value = t
  formOpen.value = true
}

async function onSubmit(payload) {
  saving.value = true
  try {
    if (editing.value) {
      await contentStudioApi.updatePublishTarget(editing.value.id, payload)
      toast.success('Target updated.')
    } else {
      await contentStudioApi.createPublishTarget(websiteId.value, payload)
      toast.success('Target added.')
    }
    formOpen.value = false
    editing.value = null
    await load()
  } catch {
    // handled
  } finally {
    saving.value = false
  }
}

async function onDelete() {
  if (!confirmDelete.value) return
  deleting.value = true
  try {
    await contentStudioApi.deletePublishTarget(confirmDelete.value.id)
    toast.success('Target removed.')
    confirmDelete.value = null
    await load()
  } catch {
    // handled
  } finally {
    deleting.value = false
  }
}

onMounted(load)
</script>
