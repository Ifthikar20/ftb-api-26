<script setup>
import { ref, computed } from 'vue'
import AirChip from '@/components/ui/AirChip.vue'
import AirButton from '@/components/ui/AirButton.vue'

const props = defineProps({
  result: { type: Object, required: true },
})

defineEmits(['try-provider'])

const expanded = ref(false)
const r = computed(() => props.result || {})

const providers = ['claude', 'gpt4', 'gemini', 'perplexity']
</script>

<template>
  <div class="str-wrap">
    <div class="str-meta">
      <AirChip variant="info" size="xs">{{ r.provider || 'unknown' }}</AirChip>
      <span v-if="r.latency_ms" class="str-stat">{{ r.latency_ms }}ms</span>
      <span v-if="r.cost_usd" class="str-stat">${{ Number(r.cost_usd).toFixed(4) }}</span>
      <AirChip :variant="r.mentioned ? 'success' : 'neutral'" size="xs">
        {{ r.mentioned ? 'Mentioned' : 'Not mentioned' }}
      </AirChip>
      <AirChip variant="neutral" size="xs">{{ r.citations_count || 0 }} citations</AirChip>
      <AirChip v-if="r.claims_count !== undefined" variant="neutral" size="xs">{{ r.claims_count }} claims</AirChip>
    </div>

    <div v-if="r.error" class="str-error">{{ r.error }}</div>

    <div class="str-section">
      <div class="str-label">Filled prompt</div>
      <pre class="str-pre">{{ r.filled_prompt }}</pre>
    </div>

    <div class="str-section">
      <div class="str-label">LLM response</div>
      <div class="str-response" :class="{ 'str-collapsed': !expanded }">
        <pre class="str-pre">{{ r.response_text }}</pre>
      </div>
      <button type="button" class="str-toggle" @click="expanded = !expanded">
        {{ expanded ? 'Show less' : 'Show more' }}
      </button>
    </div>

    <div class="str-section str-try">
      <span class="str-label">Try another provider:</span>
      <AirButton
        v-for="p in providers"
        :key="p"
        size="sm"
        :variant="p === r.provider ? 'primary' : 'ghost'"
        @click="$emit('try-provider', p)"
      >{{ p }}</AirButton>
    </div>
  </div>
</template>

<style scoped>
.str-wrap { display: flex; flex-direction: column; gap: 12px; }
.str-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.str-stat { font-size: 11px; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.str-error { color: var(--color-danger, #dc2626); font-size: 12px; }
.str-section { display: flex; flex-direction: column; gap: 4px; }
.str-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); }
.str-pre {
  margin: 0;
  padding: 10px 12px;
  background: var(--bg-card-hover);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.55;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 600px;
  overflow: auto;
}
.str-response.str-collapsed .str-pre { max-height: 200px; }
.str-toggle {
  align-self: flex-start;
  background: transparent; border: 0; padding: 0;
  color: var(--brand-accent); font-size: 12px; cursor: pointer;
}
.str-try { flex-direction: row; align-items: center; flex-wrap: wrap; gap: 6px; }
</style>
