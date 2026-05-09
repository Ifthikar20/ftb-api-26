<script setup>
import { computed, ref } from 'vue'

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

function onSubmit() {
  if (!valid.value || props.loading) return
  emit('generate', internal.value.trim())
}

function clear() {
  sync('')
}
</script>

<template>
  <div class="cic-shell mx-auto">
    <div class="cic-bar" :class="{ 'is-focused': false, 'is-loading': loading }">
      <span class="cic-leading-icon" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="7" stroke-linecap="round"/>
          <path d="M21 21l-4.35-4.35" stroke-linecap="round"/>
        </svg>
      </span>

      <textarea
        ref="textareaEl"
        class="cic-textarea"
        :value="internal"
        rows="1"
        placeholder="Try: fresh bagels in Dallas, indie coffee on the Lower East Side, family dentist in Austin…"
        @input="sync($event.target.value)"
        @keydown.enter.prevent="onSubmit"
      />

      <button
        v-if="internal"
        type="button"
        class="cic-clear"
        aria-label="Clear search"
        @click="clear"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">
          <path d="M18 6L6 18M6 6l12 12" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>

      <button
        type="button"
        class="cic-submit"
        :disabled="!valid || loading"
        :aria-busy="loading || undefined"
        @click="onSubmit"
      >
        <span v-if="loading" class="cic-spinner" aria-hidden="true"></span>
        <span v-else class="cic-submit-icon" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M5 12h14M13 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </span>
        <span class="cic-submit-text">{{ loading ? 'Searching' : 'Search' }}</span>
      </button>
    </div>

    <div v-if="!valid && internal" class="cic-hint">
      Add a few more words for better prompts.
    </div>
  </div>
</template>

<style scoped>
.cic-shell {
  width: 100%;
  max-width: 44rem;
}

.cic-bar {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 9999px;
  padding: 6px 6px 6px 18px;
  gap: 10px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 8px 24px rgba(15, 23, 42, 0.05);
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}
.cic-bar:hover {
  border-color: var(--text-muted);
}
.cic-bar:focus-within {
  border-color: var(--brand-accent);
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 12px 32px rgba(15, 23, 42, 0.10),
    0 0 0 4px var(--brand-accent-glow, rgba(91, 141, 239, 0.18));
}

.cic-leading-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  flex-shrink: 0;
}

.cic-textarea {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  padding: 12px 4px;
  font-size: 15px;
  line-height: 1.5;
  outline: none;
  resize: none;
  font-family: inherit;
  letter-spacing: 0;
}
.cic-textarea::placeholder {
  color: var(--text-muted);
  font-weight: 400;
}

.cic-clear {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 9999px;
  border: 0;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s, color 0.15s;
}
.cic-clear:hover {
  background: var(--bg-surface, rgba(0, 0, 0, 0.04));
  color: var(--text-primary);
}

.cic-submit {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px 10px 16px;
  border: 0;
  border-radius: 9999px;
  background: var(--brand-accent);
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  flex-shrink: 0;
  transition: filter 0.15s ease, transform 0.15s ease, opacity 0.15s ease, box-shadow 0.15s ease;
  box-shadow: 0 4px 12px var(--brand-accent-glow, rgba(91, 141, 239, 0.25));
}
.cic-submit:hover:not(:disabled) {
  filter: brightness(0.96);
  transform: translateY(-0.5px);
}
.cic-submit:active:not(:disabled) {
  transform: translateY(0);
}
.cic-submit:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

.cic-submit-icon { display: inline-flex; align-items: center; }
.cic-submit-text { letter-spacing: 0.01em; }

.cic-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: cic-spin 0.7s linear infinite;
}
@keyframes cic-spin { to { transform: rotate(360deg); } }

.cic-hint {
  margin-top: 8px;
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
}
</style>
