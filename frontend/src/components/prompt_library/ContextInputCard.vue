<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  minWords: { type: Number, default: 5 },
  count: { type: Number, default: 20 },
  minCount: { type: Number, default: 5 },
  maxCount: { type: Number, default: 50 },
})

const emit = defineEmits(['update:modelValue', 'update:count', 'generate'])

const internal = ref(props.modelValue || '')
const internalCount = ref(Math.min(props.maxCount, Math.max(props.minCount, props.count)))

watch(() => props.count, (v) => {
  const clamped = Math.min(props.maxCount, Math.max(props.minCount, Number(v) || 20))
  if (clamped !== internalCount.value) internalCount.value = clamped
})

function sync(v) {
  internal.value = v
  emit('update:modelValue', v)
}

function syncCount(v) {
  // Slider gives us a number; clamp + propagate.
  const n = Math.min(props.maxCount, Math.max(props.minCount, Number(v) || props.minCount))
  internalCount.value = n
  emit('update:count', n)
}

const wordCount = computed(() => {
  const v = (internal.value || '').trim()
  return v ? v.split(/\s+/).filter(Boolean).length : 0
})

const valid = computed(() => wordCount.value >= props.minWords)

const rangeFill = computed(() => {
  const span = (props.maxCount - props.minCount) || 1
  const pct = ((internalCount.value - props.minCount) / span) * 100
  return `${Math.max(0, Math.min(100, pct))}%`
})

function onSubmit() {
  if (!valid.value || props.loading) return
  emit('generate', internal.value.trim(), internalCount.value)
}

function clear() {
  sync('')
}
</script>

<template>
  <div class="cic-shell mx-auto">
    <div class="cic-glow" aria-hidden="true"></div>
    <div class="cic-box" :class="{ 'is-loading': loading }">
      <div class="cic-lead">
        <span class="cic-icon" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7"/>
            <path d="M21 21l-4.35-4.35"/>
          </svg>
        </span>
        <textarea
          ref="textareaEl"
          class="cic-textarea"
          :value="internal"
          rows="3"
          placeholder="Search the prompt library. Try: fresh bagels in Dallas, indie coffee on the Lower East Side, family dentist in Austin…"
          @input="sync($event.target.value)"
          @keydown.meta.enter.prevent="onSubmit"
          @keydown.ctrl.enter.prevent="onSubmit"
        />
      </div>

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
        <div class="cic-count-picker" :title="`Generate ${internalCount} prompts`">
          <label for="cic-count-range" class="cic-count-label">Prompts</label>
          <input
            id="cic-count-range"
            type="range"
            class="cic-range"
            :min="minCount"
            :max="maxCount"
            step="1"
            :value="internalCount"
            :disabled="loading"
            :style="{ '--cic-range-fill': rangeFill }"
            @input="syncCount($event.target.value)"
          />
          <span class="cic-count-val">{{ internalCount }}</span>
          <span class="cic-count-max">/ {{ maxCount }}</span>
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
/* ── Container + ambient glow ──────────────────────────────
   The whole input sits on a soft orange radial so the search
   feels like the focal point of the page. The glow tracks the
   spring easing the rest of the app uses (paywall / onboarding
   modal). */
.cic-shell {
  --cic-accent: #ff6a2c;
  --cic-accent-soft: rgba(255, 106, 44, 0.10);
  --cic-spring: cubic-bezier(0.22, 1, 0.36, 1);
  --cic-spring-strong: cubic-bezier(0.16, 1, 0.3, 1);

  position: relative;
  width: 100%;
  max-width: 56rem;
  animation: cic-rise 0.55s var(--cic-spring-strong) both;
}
.cic-glow {
  position: absolute;
  top: -32px;
  left: 50%;
  width: 520px;
  height: 320px;
  transform: translateX(-50%);
  background: radial-gradient(ellipse at center, var(--cic-accent-soft) 0%, transparent 60%);
  filter: blur(36px);
  pointer-events: none;
  opacity: 0.85;
  z-index: 0;
}

@keyframes cic-rise {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}

.cic-box {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  padding: 18px 22px 14px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 10px 28px rgba(15, 23, 42, 0.06);
  transition: border-color 0.22s var(--cic-spring),
              box-shadow 0.32s var(--cic-spring),
              transform 0.22s var(--cic-spring);
}
.cic-box:focus-within {
  border-color: var(--cic-accent);
  transform: translateY(-1px);
  box-shadow:
    0 2px 4px rgba(15, 23, 42, 0.04),
    0 18px 40px rgba(15, 23, 42, 0.10),
    0 0 0 4px var(--cic-accent-soft);
}

/* Magnifying glass + textarea share a row so the icon hugs the
   first line of text. */
.cic-lead {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}
.cic-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: var(--cic-accent-soft);
  color: var(--cic-accent);
  margin-top: 4px;
  transition: transform 0.4s var(--cic-spring);
}
.cic-box:focus-within .cic-icon { transform: scale(1.06); }

.cic-textarea {
  flex: 1;
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  padding: 6px 2px;
  font-size: 18px;
  line-height: 1.55;
  outline: none;
  resize: vertical;
  min-height: 80px;
  max-height: 360px;
  font-family: inherit;
  letter-spacing: -0.005em;
  font-weight: 500;
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
  padding-top: 12px;
  margin-top: 10px;
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
.cic-count { font-variant-numeric: tabular-nums; transition: color 0.2s var(--cic-spring); }
.cic-count.is-ok { color: var(--cic-accent); font-weight: 600; }
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

/* ── Count picker (slider) ─────────────────────────────────
   Sits in the middle of the footer between the word-count meta
   and the action buttons. The track flows orange up to the
   thumb so the size of the request feels visible. */
.cic-count-picker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
  margin-left: auto;
}
.cic-count-label {
  font-weight: 600;
  letter-spacing: 0.02em;
}
.cic-count-val {
  min-width: 22px;
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: var(--text-primary);
}
.cic-count-max {
  color: var(--text-muted);
  opacity: 0.65;
  font-variant-numeric: tabular-nums;
}

/* Native <input type=range> with custom track/thumb. The %-fill
   trick uses a CSS gradient that hits a transparent stop where the
   thumb sits; JS sets a custom property if we ever want to be
   precise, but the gradient + accent-color combo looks great in
   modern browsers as-is. */
.cic-range {
  -webkit-appearance: none;
  appearance: none;
  width: 110px;
  height: 4px;
  border-radius: 999px;
  background: linear-gradient(to right,
    var(--cic-accent) 0%,
    var(--cic-accent) var(--cic-range-fill, 30%),
    rgba(15, 23, 42, 0.08) var(--cic-range-fill, 30%),
    rgba(15, 23, 42, 0.08) 100%);
  outline: none;
  cursor: pointer;
  transition: opacity 0.2s var(--cic-spring);
  accent-color: var(--cic-accent);
}
.cic-range:disabled { opacity: 0.4; cursor: not-allowed; }
.cic-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--cic-accent);
  border: 2px solid #fff;
  box-shadow: 0 2px 6px rgba(255, 106, 44, 0.35);
  cursor: pointer;
  transition: transform 0.2s var(--cic-spring), box-shadow 0.2s var(--cic-spring);
}
.cic-range:hover:not(:disabled)::-webkit-slider-thumb { transform: scale(1.12); box-shadow: 0 4px 10px rgba(255, 106, 44, 0.45); }
.cic-range::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--cic-accent);
  border: 2px solid #fff;
  box-shadow: 0 2px 6px rgba(255, 106, 44, 0.35);
  cursor: pointer;
}

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
  transition: background 0.2s var(--cic-spring), color 0.2s var(--cic-spring);
}
.cic-clear:hover {
  background: var(--bg-surface, rgba(15, 23, 42, 0.04));
  color: var(--text-primary);
}

.cic-submit {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px 10px 18px;
  border: 0;
  border-radius: 9999px;
  background: var(--cic-accent);
  color: #ffffff;
  font-size: 13.5px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  flex-shrink: 0;
  transition: transform 0.2s var(--cic-spring), background 0.25s var(--cic-spring), box-shadow 0.25s var(--cic-spring), opacity 0.15s;
  box-shadow: 0 6px 16px rgba(255, 106, 44, 0.32);
}
.cic-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(255, 106, 44, 0.36);
}
.cic-submit:active:not(:disabled) { transform: translateY(0) scale(0.98); }
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
