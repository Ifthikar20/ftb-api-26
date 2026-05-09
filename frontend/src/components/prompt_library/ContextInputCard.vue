<script setup>
import { computed, ref } from 'vue'
import AirCard from '@/components/ui/AirCard.vue'
import AirChip from '@/components/ui/AirChip.vue'
import AirButton from '@/components/ui/AirButton.vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  minWords: { type: Number, default: 5 },
  examples: {
    type: Array,
    default: () => [
      "Local dental clinic in Dallas, weekend walk-ins, near Lakewood",
      "B2B SaaS in NYC for marketing teams managing newsletters",
      "Boutique hotel in Austin near 6th Street, popular with musicians",
      "Health podcast on Broadway NY at 6pm for working professionals",
    ],
  },
})

const emit = defineEmits(['update:modelValue', 'generate'])

const internal = ref(props.modelValue || '')

function sync(v) {
  internal.value = v
  emit('update:modelValue', v)
}

const wordCount = computed(() => {
  const v = (internal.value || '').trim()
  if (!v) return 0
  return v.split(/\s+/).filter(Boolean).length
})

const valid = computed(() => wordCount.value >= props.minWords)

function pickExample(text) {
  sync(text)
}

function onGenerate() {
  if (!valid.value || props.loading) return
  emit('generate', internal.value.trim())
}
</script>

<template>
  <AirCard size="lg" class="cic-card mx-auto" style="max-width: 48rem">
    <div class="cic-eyebrow">Step 1</div>
    <h2 class="cic-title">What's the scenario?</h2>
    <p class="cic-subtitle">
      Describe a moment, place, or context where someone might ask AI about you.
      The more vivid, the better.
    </p>

    <textarea
      class="cic-textarea"
      :value="internal"
      rows="3"
      placeholder='Good fellow&apos;s podcast about health, Broadway NY at 6pm'
      @input="sync($event.target.value)"
    />

    <div class="cic-meta">
      <span :class="['cic-counter', valid ? 'is-ok' : 'is-warn']">
        {{ wordCount }} / {{ minWords }} words
      </span>
      <span v-if="!valid" class="cic-hint">Add a few more words for better prompts.</span>
    </div>

    <div class="cic-examples">
      <span class="cic-examples-label">Try a seed:</span>
      <AirChip
        v-for="(ex, i) in examples"
        :key="i"
        as="button"
        size="sm"
        variant="neutral"
        @click="pickExample(ex)"
      >{{ ex }}</AirChip>
    </div>

    <div class="cic-actions">
      <AirButton
        variant="primary"
        size="lg"
        :loading="loading"
        :disabled="!valid || loading"
        @click="onGenerate"
      >
        <template v-if="loading">Generating 20 prompts…</template>
        <template v-else>Generate prompts</template>
      </AirButton>
    </div>
  </AirCard>
</template>

<style scoped>
.cic-eyebrow {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 4px;
}
.cic-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}
.cic-subtitle {
  margin-top: 6px;
  margin-bottom: 16px;
  font-size: 14px;
  color: var(--text-secondary);
}
.cic-textarea {
  width: 100%;
  border-radius: 16px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-primary);
  padding: 14px 16px;
  font-size: 15px;
  line-height: 1.5;
  outline: none;
  resize: vertical;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.cic-textarea:focus-visible {
  border-color: var(--brand-accent);
  box-shadow: 0 0 0 4px var(--brand-accent-glow);
}
.cic-meta {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}
.cic-counter { color: var(--text-muted); font-variant-numeric: tabular-nums; }
.cic-counter.is-ok { color: var(--text-secondary); }
.cic-counter.is-warn { color: var(--color-warning, #b45309); }
.cic-hint { color: var(--text-muted); }
.cic-examples {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.cic-examples-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-right: 4px;
}
.cic-actions {
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
}
</style>
