<template>
  <div
    v-if="open"
    class="fixed inset-0 z-40 flex justify-end bg-black/30"
    @click.self="close"
  >
    <div class="flex h-full w-full max-w-2xl flex-col bg-white shadow-xl">
      <header class="flex items-start justify-between gap-3 border-b px-4 py-3">
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2">
            <SeverityBadge :severity="mismatch?.severity || 'info'" />
            <span v-if="provider" class="text-xs text-gray-500">{{ provider }}</span>
            <span v-if="auditDate" class="text-xs text-gray-400">· {{ auditDate }}</span>
          </div>
          <h2 class="mt-1 text-base font-semibold text-gray-900">
            Mismatch detail
          </h2>
        </div>
        <button
          class="rounded text-gray-400 hover:text-gray-700"
          @click="close"
          aria-label="Close"
        >
          Close
        </button>
      </header>

      <div v-if="!mismatch" class="flex-1 p-6 text-sm text-gray-500">
        No mismatch selected.
      </div>

      <div v-else class="flex-1 overflow-auto px-4 py-4">
        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <section class="rounded-md border border-gray-100 p-3">
            <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
              What the LLM said
            </h3>
            <p class="mb-3 text-sm text-gray-800">{{ mismatch.claim?.text || '—' }}</p>
            <dl class="space-y-1 text-xs text-gray-600">
              <div><dt class="inline font-medium">Subject:</dt> {{ mismatch.claim?.subject || '—' }}</div>
              <div><dt class="inline font-medium">Predicate:</dt> {{ mismatch.claim?.predicate || '—' }}</div>
              <div><dt class="inline font-medium">Object:</dt> {{ mismatch.claim?.object || '—' }}</div>
            </dl>
          </section>

          <section class="rounded-md border border-gray-100 p-3">
            <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
              What we know
            </h3>
            <div v-if="mismatch.matched_fact" class="space-y-1 text-xs text-gray-700">
              <dl class="space-y-1">
                <div><dt class="inline font-medium">Subject:</dt> {{ mismatch.matched_fact.subject }}</div>
                <div><dt class="inline font-medium">Predicate:</dt> {{ mismatch.matched_fact.predicate }}</div>
                <div><dt class="inline font-medium">Object:</dt> {{ mismatch.matched_fact.object }}</div>
              </dl>
              <div v-if="mismatch.matched_fact.source_url" class="pt-1">
                <a
                  :href="mismatch.matched_fact.source_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-indigo-700 hover:underline"
                >
                  Source
                </a>
              </div>
            </div>
            <div v-else class="text-xs text-gray-500 italic">
              No matching fact in the Brand Vault.
            </div>
          </section>
        </div>

        <section v-if="mismatch.explanation" class="mt-4 rounded-md border border-gray-100 p-3">
          <h3 class="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Explanation
          </h3>
          <p class="text-sm text-gray-700">{{ mismatch.explanation }}</p>
        </section>

        <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div class="rounded-md border border-gray-100 p-3">
            <div class="text-xs text-gray-500">Mismatch type</div>
            <div class="text-sm font-medium text-gray-800">{{ mismatch.mismatch_type || '—' }}</div>
          </div>
          <div class="rounded-md border border-gray-100 p-3">
            <div class="text-xs text-gray-500">Severity</div>
            <div class="text-sm font-medium capitalize text-gray-800">{{ mismatch.severity }}</div>
          </div>
        </div>

        <div class="mt-4 space-y-3">
          <div>
            <div class="mb-1 flex items-center justify-between text-xs text-gray-600">
              <span>Factual divergence</span>
              <span>{{ pct(mismatch.factual_divergence) }}%</span>
            </div>
            <div class="h-2 w-full overflow-hidden rounded-full bg-gray-100">
              <div class="h-full bg-red-400" :style="{ width: pct(mismatch.factual_divergence) + '%' }"></div>
            </div>
          </div>
          <div>
            <div class="mb-1 flex items-center justify-between text-xs text-gray-600">
              <span>Audience reach</span>
              <span>{{ pct(mismatch.audience_reach) }}%</span>
            </div>
            <div class="h-2 w-full overflow-hidden rounded-full bg-gray-100">
              <div class="h-full bg-blue-400" :style="{ width: pct(mismatch.audience_reach) + '%' }"></div>
            </div>
          </div>
        </div>

        <div v-if="showPrompt && mismatch.claim?.prompt" class="mt-4 rounded-md border border-gray-100 p-3">
          <h3 class="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Prompt
          </h3>
          <pre class="whitespace-pre-wrap text-xs text-gray-700">{{ mismatch.claim.prompt }}</pre>
        </div>

        <div v-if="showRaw && rawResponse" class="mt-4 rounded-md border border-gray-100 p-3">
          <h3 class="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Raw response
          </h3>
          <pre class="whitespace-pre-wrap text-xs text-gray-700">{{ rawResponse }}</pre>
        </div>
      </div>

      <footer v-if="mismatch" class="flex flex-wrap items-center justify-end gap-2 border-t px-4 py-3">
        <button
          class="rounded-md border px-3 py-1.5 text-xs hover:bg-gray-50"
          @click="showPrompt = !showPrompt"
        >
          {{ showPrompt ? 'Hide prompt' : 'View prompt' }}
        </button>
        <button
          class="rounded-md border px-3 py-1.5 text-xs hover:bg-gray-50"
          @click="showRaw = !showRaw"
        >
          {{ showRaw ? 'Hide raw response' : 'View raw response' }}
        </button>
        <button
          class="rounded-md bg-rose-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-700 disabled:opacity-50"
          :disabled="dismissing || mismatch.dismissed"
          @click="onDismiss"
        >
          {{ mismatch.dismissed ? 'Dismissed' : (dismissing ? 'Dismissing...' : 'Dismiss as false positive') }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import SeverityBadge from './SeverityBadge.vue'
import claimVerifierApi from '@/api/claimVerifier'
import { useToast } from '@/composables/useToast'

const props = defineProps({
  open: { type: Boolean, default: false },
  mismatch: { type: Object, default: null },
})

const emit = defineEmits(['update:open', 'dismissed'])
const toast = useToast()

const dismissing = ref(false)
const showPrompt = ref(false)
const showRaw = ref(false)
const rawResponse = ref('')

watch(() => props.mismatch, () => {
  showPrompt.value = false
  showRaw.value = false
  rawResponse.value = ''
})

const provider = computed(() => props.mismatch?.claim?.provider || '')
const auditDate = computed(() => {
  const c = props.mismatch?.created_at
  if (!c) return ''
  try {
    return new Date(c).toLocaleString()
  } catch {
    return c
  }
})

function pct(v) {
  const n = Number(v) || 0
  if (n <= 1) return Math.round(n * 1000) / 10
  return Math.min(100, Math.round(n * 10) / 10)
}

function close() {
  emit('update:open', false)
}

async function onDismiss() {
  if (!props.mismatch?.id) return
  dismissing.value = true
  try {
    const { data } = await claimVerifierApi.dismiss(props.mismatch.id)
    const updated = data?.data || data
    toast.success('Mismatch dismissed.')
    emit('dismissed', updated)
    emit('update:open', false)
  } catch (e) {
    toast.error(e.displayMessage || 'Could not dismiss mismatch.')
  } finally {
    dismissing.value = false
  }
}
</script>
