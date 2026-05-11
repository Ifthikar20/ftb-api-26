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
    <div class="cic-box" :class="{ 'is-loading': loading }">
      <textarea
        ref="textareaEl"
        class="cic-textarea"
        :value="internal"
        rows="4"
        placeholder="Describe a scenario in your own words. Try: fresh bagels in Dallas, indie coffee on the Lower East Side, family dentist in Austin…"
        @input="sync($event.target.value)"
        @keydown.meta.enter.prevent="onSubmit"
        @keydown.ctrl.enter.prevent="onSubmit"
      />

      <div class="cic-footer">
        <div class="cic-meta">
          <span class="cic-count" :class="{ 'is-ok': valid }">
            {{ wordCount }} word{{ wordCount === 1 ? '' : 's' }}
          </span>
          <span class="cic-sep" aria-hidden="true">·</span>
          <span class="cic-hint-inline">{{ valid ? 'Ready to search' : `Need ${Math.max(0, minWords - wordCount)} more` }}</span>
          <span class="cic-sep cic-sep-light" aria-hidden="true">·</span>
          <kbd class="cic-kbd">⌘</kbd><kbd class="cic-kbd">↵</kbd>
          <span class="cic-kbd-hint">to search</span>
        </div>
        <div class="cic-footer-actions">
          <button
            v-if="internal"
            type="button"
            class="cic-clear"
            aria-label="Clear"
            @click="clear"
          >Clear</button>
          <button
            type="button"
            class="cic-submit"
            :disabled="!valid || loading"
            :aria-busy="loading || undefined"
            @click="onSubmit"
          >
            <span v-if="loading" class="cic-spinner" aria-hidden="true"></span>
            <span v-else class="cic-submit-icon" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M5 12h14M13 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
            <span class="cic-submit-text">{{ loading ? 'Searching' : 'Search' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cic-shell {
  width: 100%;
  max-width: 56rem;
}

.cic-box {
  position: relative;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 16px 18px 12px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 10px 28px rgba(15, 23, 42, 0.06);
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
.cic-box:focus-within {
  border-color: var(--brand-accent);
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 14px 36px rgba(15, 23, 42, 0.10),
    0 0 0 4px var(--brand-accent-glow, rgba(91, 141, 239, 0.18));
}

.cic-textarea {
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  padding: 4px 2px;
  font-size: 16px;
  line-height: 1.55;
  outline: none;
  resize: vertical;
  min-height: 100px;
  max-height: 360px;
  font-family: inherit;
  letter-spacing: 0;
}
.cic-textarea::placeholder {
  color: var(--text-muted);
  font-weight: 400;
}

.cic-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 10px;
  margin-top: 8px;
  border-top: 1px solid var(--border-color);
}
.cic-meta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
  min-width: 0;
  flex-wrap: wrap;
}
.cic-count { font-variant-numeric: tabular-nums; }
.cic-count.is-ok { color: var(--brand-accent); font-weight: 600; }
.cic-sep { color: var(--text-muted); opacity: 0.6; }
.cic-sep-light { opacity: 0.35; }
.cic-hint-inline { font-style: italic; }
.cic-kbd {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 18px; height: 18px;
  padding: 0 4px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-surface, rgba(15, 23, 42, 0.03));
  font-size: 10.5px;
  color: var(--text-secondary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.cic-kbd + .cic-kbd { margin-left: 2px; }
.cic-kbd-hint { margin-left: 2px; }

.cic-footer-actions { display: inline-flex; align-items: center; gap: 8px; }

.cic-clear {
  border: 0;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 9999px;
  font-size: 12.5px;
  font-weight: 500;
  font-family: inherit;
}
.cic-clear:hover {
  background: var(--bg-surface, rgba(15, 23, 42, 0.04));
  color: var(--text-primary);
}

.cic-submit {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 18px 9px 16px;
  border: 0;
  border-radius: 9999px;
  background: var(--brand-accent);
  color: #ffffff;
  font-size: 13.5px;
  font-weight: 600;
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
.cic-submit:active:not(:disabled) { transform: translateY(0); }
.cic-submit:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}
.cic-submit-icon { display: inline-flex; align-items: center; }

.cic-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: cic-spin 0.7s linear infinite;
}
@keyframes cic-spin { to { transform: rotate(360deg); } }
</style>
