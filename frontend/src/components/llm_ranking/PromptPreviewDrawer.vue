<template>
  <div v-if="open" class="fixed inset-0 z-40 flex justify-end bg-black/30" @click.self="close">
    <div class="flex h-full w-full max-w-xl flex-col bg-white shadow-xl">
      <header class="flex items-center justify-between border-b px-4 py-3">
        <h2 class="text-base font-semibold">Preview prompts</h2>
        <button class="text-gray-400 hover:text-gray-700" @click="close">Close</button>
      </header>

      <div class="flex-1 overflow-auto px-4 py-3">
        <p v-if="loading" class="text-sm text-gray-500">Loading...</p>
        <p v-else-if="error" class="text-sm text-red-600">{{ error }}</p>
        <div v-else>
          <div v-for="(group, bucket) in grouped" :key="bucket" class="mb-4">
            <h3 class="mb-2 text-xs font-semibold uppercase text-gray-500">{{ bucket }}</h3>
            <ul class="space-y-1">
              <li
                v-for="p in group"
                :key="p.id"
                class="flex items-start gap-2 rounded-md border border-gray-100 px-2 py-1 text-sm"
              >
                <input
                  type="checkbox"
                  :checked="!disabled.has(p.id)"
                  class="mt-1"
                  @change="toggle(p.id)"
                />
                <div>
                  <div class="text-gray-900">{{ p.text }}</div>
                  <div class="text-xs text-gray-500">{{ p.source_label }}</div>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <footer class="flex justify-end gap-2 border-t px-4 py-3">
        <button class="rounded-md border px-3 py-1 text-sm" @click="close">Cancel</button>
        <button
          class="rounded-md bg-indigo-600 px-3 py-1 text-sm text-white disabled:opacity-50"
          :disabled="loading"
          @click="confirm"
        >
          Use these prompts
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import promptLibrary from '@/api/promptLibrary'

const props = defineProps({
  open: { type: Boolean, default: false },
  industryId: { type: String, default: null },
  n: { type: Number, default: 20 },
})

const emit = defineEmits(['update:open', 'confirm'])

const prompts = ref([])
const disabled = ref(new Set())
const loading = ref(false)
const error = ref('')
const seed = ref(null)

const grouped = computed(() => {
  const out = {}
  for (const p of prompts.value) {
    const key = p.intent_bucket || 'other'
    if (!out[key]) out[key] = []
    out[key].push(p)
  }
  return out
})

function close() {
  emit('update:open', false)
}

function toggle(id) {
  if (disabled.value.has(id)) disabled.value.delete(id)
  else disabled.value.add(id)
  // trigger reactivity
  disabled.value = new Set(disabled.value)
}

function confirm() {
  const chosen = prompts.value.filter((p) => !disabled.value.has(p.id))
  emit('confirm', { prompts: chosen, seed: seed.value })
  close()
}

async function load() {
  if (!props.industryId) return
  loading.value = true
  error.value = ''
  try {
    const { data } = await promptLibrary.previewSample({
      industry_id: props.industryId,
      n: props.n,
    })
    prompts.value = data.prompts || []
    seed.value = data.seed
    disabled.value = new Set()
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Failed to load preview'
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  (v) => {
    if (v) load()
  },
)
</script>
