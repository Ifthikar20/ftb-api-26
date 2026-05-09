<script setup>
import { computed, ref } from 'vue'
import AirButton from '@/components/ui/AirButton.vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  minWords: { type: Number, default: 5 },
})

const emit = defineEmits(['update:modelValue', 'generate'])

const internal = ref(props.modelValue || '')

function sync(v) {
  internal.value = v
  emit('update:modelValue', v)
}

const wordCount = computed(() => {
  const v = (internal.value || '').trim()
  return v ? v.split(/\s+/).filter(Boolean).length : 0
})

const valid = computed(() => wordCount.value >= props.minWords)

function onGenerate() {
  if (!valid.value || props.loading) return
  emit('generate', internal.value.trim())
}
</script>

<template>
  <div class="cic-bar mx-auto" style="max-width: 48rem">
    <textarea
      class="cic-textarea"
      :value="internal"
      rows="2"
      placeholder="Search prompts by scenario, brand, or category"
      @input="sync($event.target.value)"
      @keydown.enter.prevent="onGenerate"
    />
    <AirButton
      variant="primary"
      size="md"
      :loading="loading"
      :disabled="!valid || loading"
      class="cic-search-btn"
      @click="onGenerate"
    >
      <template v-if="loading">Searching…</template>
      <template v-else>Search</template>
    </AirButton>
  </div>
</template>

<style scoped>
.cic-bar {
  display: flex;
  align-items: stretch;
  gap: 8px;
  width: 100%;
  padding: 6px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 9999px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.cic-bar:focus-within {
  border-color: var(--brand-accent);
  box-shadow: 0 0 0 4px var(--brand-accent-glow);
}
.cic-textarea {
  flex: 1;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  padding: 10px 16px;
  font-size: 15px;
  line-height: 1.45;
  outline: none;
  resize: none;
  min-height: 44px;
  font-family: inherit;
}
.cic-textarea::placeholder {
  color: var(--text-muted);
}
.cic-search-btn {
  flex-shrink: 0;
  align-self: stretch;
}
</style>
