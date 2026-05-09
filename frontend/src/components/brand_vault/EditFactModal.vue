<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
    @click.self="close"
  >
    <div class="w-full max-w-md rounded-lg bg-white p-5 shadow-xl">
      <h3 class="mb-3 text-base font-semibold text-gray-900">Edit fact</h3>
      <p class="mb-4 text-xs text-gray-500">
        Saving creates a new version that supersedes the original.
      </p>

      <div class="space-y-3">
        <div>
          <label class="mb-1 block text-xs font-medium text-gray-700">Subject</label>
          <input
            v-model="form.subject"
            class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          />
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-gray-700">Predicate</label>
          <input
            v-model="form.predicate"
            class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          />
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-gray-700">Object</label>
          <textarea
            v-model="form.object"
            rows="2"
            class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          ></textarea>
        </div>
        <div>
          <label class="mb-1 block text-xs font-medium text-gray-700">
            Reason (optional)
          </label>
          <textarea
            v-model="form.reason"
            rows="2"
            placeholder="Why are you editing this fact?"
            class="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          ></textarea>
        </div>
      </div>

      <div class="mt-5 flex justify-end gap-2">
        <button
          class="rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
          :disabled="saving"
          @click="close"
        >
          Cancel
        </button>
        <button
          class="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          :disabled="saving || !canSave"
          @click="save"
        >
          {{ saving ? 'Saving...' : 'Save' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import brandVaultApi from '@/api/brandVault'
import { useToast } from '@/composables/useToast'

const props = defineProps({
  open: { type: Boolean, default: false },
  fact: { type: Object, default: null },
})

const emit = defineEmits(['update:open', 'saved'])
const toast = useToast()

const saving = ref(false)
const form = ref({ subject: '', predicate: '', object: '', reason: '' })

watch(
  () => props.fact,
  (f) => {
    form.value = {
      subject: f?.subject || '',
      predicate: f?.predicate || '',
      object: f?.object || '',
      reason: '',
    }
  },
  { immediate: true },
)

const canSave = computed(
  () =>
    form.value.subject.trim() &&
    form.value.predicate.trim() &&
    form.value.object.trim(),
)

function close() {
  if (saving.value) return
  emit('update:open', false)
}

async function save() {
  if (!props.fact?.id || !canSave.value) return
  saving.value = true
  try {
    const { data } = await brandVaultApi.edit(props.fact.id, {
      subject: form.value.subject.trim(),
      predicate: form.value.predicate.trim(),
      object: form.value.object.trim(),
    })
    const newFact = data?.data || data
    toast.success('Fact updated.')
    emit('saved', newFact)
    emit('update:open', false)
  } catch (e) {
    toast.error(e.displayMessage || 'Could not save fact.')
  } finally {
    saving.value = false
  }
}
</script>
