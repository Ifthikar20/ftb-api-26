<template>
  <div class="tov">
    <div class="tov-intro">
      <h3>Tone of voice</h3>
      <p>
        Real samples of your brand's writing. Content Studio reads these when
        generating drafts so the output sounds like you, not a generic LLM.
      </p>
    </div>

    <form class="tov-add" @submit.prevent="onAdd">
      <textarea
        v-model="text"
        rows="3"
        maxlength="4000"
        placeholder="Paste a paragraph from a blog post, sales email, or product page…"
        class="tov-input"
      />
      <div class="tov-add-foot">
        <span class="tov-counter">{{ (text || '').length }} / 4000</span>
        <AirButton type="submit" variant="primary" size="sm" :disabled="!text.trim() || saving">
          {{ saving ? 'Saving…' : 'Add sample' }}
        </AirButton>
      </div>
    </form>

    <div v-if="loading" class="tov-skeleton">
      <div v-for="i in 3" :key="i" class="tov-skel" />
    </div>

    <div v-else-if="!samples.length" class="tov-empty">
      <p>No tone samples yet. Add a paragraph above to teach the agents your voice.</p>
    </div>

    <ul v-else class="tov-list">
      <li v-for="sample in samples" :key="sample.id" class="tov-row">
        <p class="tov-row-text">{{ sample.text }}</p>
        <div class="tov-row-meta">
          <span>{{ sample.word_count || 0 }} words</span>
          <span>·</span>
          <span>{{ formatDate(sample.created_at) }}</span>
          <button class="tov-remove" type="button" @click="onRemove(sample)">Remove</button>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useToast } from '@/composables/useToast'
import brandVaultApi from '@/api/brandVault'
import AirButton from '@/components/ui/AirButton.vue'

const props = defineProps({
  websiteId: { type: String, required: true },
  samples: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['refresh'])

const toast = useToast()
const text = ref('')
const saving = ref(false)

async function onAdd() {
  const t = text.value.trim()
  if (!t) return
  saving.value = true
  try {
    await brandVaultApi.addToneSample(props.websiteId, t)
    text.value = ''
    toast.success('Sample added.')
    emit('refresh')
  } catch (e) {
    toast.error(e.displayMessage || 'Could not add sample.')
  } finally {
    saving.value = false
  }
}

async function onRemove(sample) {
  try {
    await brandVaultApi.deleteToneSample(sample.id)
    toast.success('Sample removed.')
    emit('refresh')
  } catch (e) {
    toast.error(e.displayMessage || 'Could not remove sample.')
  }
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}
</script>

<style scoped>
.tov { display: flex; flex-direction: column; gap: 16px; }
.tov-intro h3 { margin: 0 0 4px; font-size: 1.05rem; color: var(--text-primary); }
.tov-intro p { margin: 0; font-size: 0.88rem; color: var(--text-secondary); line-height: 1.5; }

.tov-add {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
}
.tov-input {
  width: 100%;
  border: 1px solid var(--border-color, #e5e7eb);
  background: var(--bg-input, #fff);
  border-radius: 8px;
  padding: 10px 12px;
  font: inherit;
  font-size: 0.9rem;
  color: var(--text-primary);
  resize: vertical;
}
.tov-input:focus {
  outline: none;
  border-color: var(--brand-accent, #ff6b35);
  box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.18);
}
.tov-add-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.tov-counter { font-size: 0.78rem; color: var(--text-muted); }

.tov-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.tov-row {
  padding: 14px 16px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
}
.tov-row-text {
  margin: 0 0 8px;
  font-size: 0.9rem;
  color: var(--text-primary);
  line-height: 1.55;
  white-space: pre-wrap;
}
.tov-row-meta {
  display: flex;
  gap: 8px;
  font-size: 0.78rem;
  color: var(--text-muted);
  align-items: center;
}
.tov-remove {
  appearance: none;
  background: transparent;
  border: none;
  color: #b91c1c;
  font: inherit;
  font-size: 0.78rem;
  margin-left: auto;
  cursor: pointer;
}
.tov-remove:hover { text-decoration: underline; }

.tov-skeleton { display: flex; flex-direction: column; gap: 8px; }
.tov-skel {
  height: 88px;
  border-radius: 12px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.tov-empty {
  text-align: center;
  padding: 40px 20px;
  border: 1px dashed var(--border-color, #e5e7eb);
  border-radius: 14px;
  color: var(--text-muted);
  font-size: 0.88rem;
}

[data-theme="dark"] .tov-add,
[data-theme="dark"] .tov-row,
[data-theme="dark"] .tov-skel { background: var(--bg-card); border-color: var(--border-color); }
[data-theme="dark"] .tov-input { background: var(--bg-input); color: var(--text-primary); border-color: var(--border-color); }
</style>
