<script setup>
import { ref, computed, watch } from 'vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import AirButton from '@/components/ui/AirButton.vue'
import AirChip from '@/components/ui/AirChip.vue'
import promptLibrary from '@/api/promptLibrary'
import { useToast } from '@/composables/useToast'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  websiteId: { type: String, default: null },
  variables: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue', 'created'])

const toast = useToast()

const text = ref('')
const style = ref('question')
const intentBucket = ref('category')
const autoTemplating = ref(false)
const saving = ref(false)
const detectedVars = ref([])

const styles = [
  { value: 'question', label: 'Question' },
  { value: 'story', label: 'Story' },
  { value: 'comparison', label: 'Comparison' },
  { value: 'local', label: 'Local' },
  { value: 'how_to', label: 'How-to' },
  { value: 'listicle', label: 'Listicle' },
]
const intents = [
  { value: 'category', label: 'Category' },
  { value: 'comparison', label: 'Comparison' },
  { value: 'problem', label: 'Problem' },
  { value: 'local', label: 'Local' },
]

const TEMPLATE_RE = /\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}/g
function detect(t) {
  const out = []
  TEMPLATE_RE.lastIndex = 0
  let m
  while ((m = TEMPLATE_RE.exec(t || '')) !== null) {
    if (!out.includes(m[1])) out.push(m[1])
  }
  return out
}

watch(text, (v) => { detectedVars.value = detect(v) })

const filledPreview = computed(() => {
  let body = text.value || ''
  return body.replace(TEMPLATE_RE, (_, name) => {
    const v = props.variables?.[name]
    return v != null && String(v).length ? String(v) : `{{ ${name} }}`
  })
})

watch(() => props.modelValue, (open) => {
  if (open) {
    text.value = ''
    style.value = 'question'
    intentBucket.value = 'category'
    detectedVars.value = []
  }
})

function close() { emit('update:modelValue', false) }

async function autoTemplate() {
  if (!text.value.trim()) return
  autoTemplating.value = true
  try {
    const { data } = await promptLibrary.autoTemplate(text.value)
    const payload = data?.data || data || {}
    if (payload.template_text) {
      text.value = payload.template_text
      if (payload.style) style.value = payload.style
    }
  } catch (e) {
    toast.error(e.displayMessage || 'Auto-template failed.')
  } finally {
    autoTemplating.value = false
  }
}

async function save() {
  if (!props.websiteId) {
    toast.error('Pick an active website first.')
    return
  }
  if (!text.value.trim()) return
  saving.value = true
  try {
    const payload = {
      template_text: text.value,
      style: style.value,
      intent_bucket: intentBucket.value,
    }
    const { data } = await promptLibrary.createWebsitePrompt(props.websiteId, payload)
    const created = data?.data || data
    toast.success('Prompt created.')
    emit('created', created)
    close()
  } catch (e) {
    toast.error(e.displayMessage || 'Could not create prompt.')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <BaseModal
    :model-value="modelValue"
    title="Create a prompt"
    subtitle="Write a question your customers ask, or paste a real one. We will detect variables and let you fill them per-website."
    wide
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="np-grid">
      <div class="np-col">
        <label class="np-label">Prompt text or template</label>
        <textarea
          v-model="text"
          rows="6"
          class="np-textarea"
          placeholder="E.g. What is the best {{ industry }} agency in {{ location }}?"
        ></textarea>

        <div v-if="detectedVars.length" class="np-vars">
          <span class="np-vars-label">Detected:</span>
          <AirChip v-for="v in detectedVars" :key="v" variant="info" size="xs">{{ v }}</AirChip>
        </div>

        <div class="np-row">
          <div class="np-field">
            <label class="np-label">Style</label>
            <select v-model="style" class="np-select">
              <option v-for="s in styles" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </div>
          <div class="np-field">
            <label class="np-label">Intent</label>
            <select v-model="intentBucket" class="np-select">
              <option v-for="i in intents" :key="i.value" :value="i.value">{{ i.label }}</option>
            </select>
          </div>
        </div>
      </div>

      <div class="np-col">
        <label class="np-label">Live preview</label>
        <div class="np-preview">{{ filledPreview || 'Start typing — preview shows here.' }}</div>
      </div>
    </div>

    <template #footer>
      <div class="np-footer">
        <AirButton variant="outline" :loading="autoTemplating" :disabled="!text.trim()" @click="autoTemplate">
          Auto-template this
        </AirButton>
        <div class="np-spacer"></div>
        <AirButton variant="ghost" @click="close">Cancel</AirButton>
        <AirButton variant="primary" :loading="saving" :disabled="!text.trim()" @click="save">Save</AirButton>
      </div>
    </template>
  </BaseModal>
</template>

<style scoped>
.np-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 720px) { .np-grid { grid-template-columns: 1fr; } }
.np-col { display: flex; flex-direction: column; gap: 8px; }
.np-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); }
.np-textarea {
  width: 100%; padding: 10px 12px;
  border-radius: 10px; border: 1px solid var(--border-color);
  background: var(--bg-card); color: var(--text-primary);
  font-size: 14px; line-height: 1.5; resize: vertical;
}
.np-vars { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.np-vars-label { font-size: 11px; color: var(--text-muted); }
.np-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.np-field { display: flex; flex-direction: column; gap: 4px; }
.np-select {
  height: 34px; padding: 0 10px;
  border-radius: 9999px; border: 1px solid var(--border-color);
  background: var(--bg-card); color: var(--text-primary);
  font-size: 12px;
}
.np-preview {
  border: 1px dashed var(--border-color); border-radius: 10px;
  padding: 12px; background: var(--bg-card-hover, transparent);
  color: var(--text-primary); font-size: 14px; line-height: 1.55;
  min-height: 140px; white-space: pre-wrap;
}
.np-footer { display: flex; align-items: center; gap: 8px; width: 100%; }
.np-spacer { flex: 1; }
</style>
