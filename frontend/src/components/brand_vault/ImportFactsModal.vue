<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
    @click.self="close"
  >
    <div class="w-full max-w-lg rounded-lg bg-white shadow-xl">
      <header class="flex items-center justify-between border-b px-4 py-3">
        <h2 class="text-base font-semibold text-gray-900">Import facts</h2>
        <button class="text-gray-400 hover:text-gray-700" @click="close">Close</button>
      </header>

      <div class="border-b px-4 pt-3">
        <div class="inline-flex overflow-hidden rounded-md border border-gray-200">
          <button
            class="px-3 py-1.5 text-xs"
            :class="tab === 'json' ? 'bg-indigo-600 text-white' : 'text-gray-700 hover:bg-gray-50'"
            @click="tab = 'json'"
          >
            Paste JSON
          </button>
          <button
            class="px-3 py-1.5 text-xs"
            :class="tab === 'csv' ? 'bg-indigo-600 text-white' : 'text-gray-700 hover:bg-gray-50'"
            @click="tab = 'csv'"
          >
            Upload CSV
          </button>
        </div>
      </div>

      <div v-if="tab === 'json'" class="space-y-3 px-4 py-3">
        <p class="text-xs text-gray-500">
          Paste a JSON array of facts. Each must have subject, predicate, object.
        </p>
        <textarea
          v-model="jsonText"
          rows="10"
          class="w-full rounded-md border border-gray-200 p-2 font-mono text-xs"
          :placeholder="jsonPlaceholder"
        ></textarea>
      </div>

      <div v-else class="space-y-3 px-4 py-3">
        <p class="text-xs text-gray-500">
          CSV columns: subject, predicate, object, product_line, topic, confidence, source_url.
        </p>
        <input
          ref="fileInput"
          type="file"
          accept=".csv,text/csv"
          class="block w-full text-sm"
          @change="onFileChange"
        />
      </div>

      <footer class="flex items-center justify-end gap-2 border-t px-4 py-3">
        <button
          class="rounded-md border px-3 py-1.5 text-sm hover:bg-gray-50"
          @click="close"
        >
          Cancel
        </button>
        <button
          class="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          :disabled="submitting || !canSubmit"
          @click="submit"
        >
          {{ submitting ? 'Importing...' : 'Import' }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import brandVaultApi from '@/api/brandVault'
import { useToast } from '@/composables/useToast'

const props = defineProps({
  open: { type: Boolean, default: false },
  websiteId: { type: String, required: true },
})
const emit = defineEmits(['update:open', 'imported'])
const toast = useToast()

const tab = ref('json')
const jsonText = ref('')
const file = ref(null)
const submitting = ref(false)
const fileInput = ref(null)

const jsonPlaceholder = `[
  {"subject": "Acme", "predicate": "supports", "object": "Webhooks", "confidence": 0.95}
]`

watch(() => props.open, (v) => {
  if (v) {
    tab.value = 'json'
    jsonText.value = ''
    file.value = null
  }
})

const canSubmit = computed(() => {
  if (tab.value === 'json') return jsonText.value.trim().length > 0
  return !!file.value
})

function close() {
  emit('update:open', false)
}

function onFileChange(e) {
  file.value = e.target.files?.[0] || null
}

async function submit() {
  submitting.value = true
  try {
    let resp
    if (tab.value === 'json') {
      let facts
      try {
        facts = JSON.parse(jsonText.value)
      } catch (e) {
        toast.error('Invalid JSON.')
        return
      }
      if (!Array.isArray(facts)) {
        toast.error('JSON must be an array of facts.')
        return
      }
      resp = await brandVaultApi.importJson(props.websiteId, facts)
    } else {
      resp = await brandVaultApi.importCsv(props.websiteId, file.value)
    }
    const body = resp.data?.data || resp.data || {}
    const created = body.created || 0
    const skipped = body.skipped || 0
    const errs = (body.errors || []).length
    toast.success(`Imported ${created} fact(s); ${skipped} skipped; ${errs} error(s).`)
    emit('imported', body)
    emit('update:open', false)
  } catch (e) {
    toast.error(e.displayMessage || 'Import failed.')
  } finally {
    submitting.value = false
  }
}
</script>
