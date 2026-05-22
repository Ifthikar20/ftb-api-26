<template>
  <section class="kw-widget" :class="{ 'is-clickable': items.length }">
    <header class="kw-head">
      <div>
        <h3 class="kw-title">Keyword repository</h3>
        <p class="kw-sub">
          <template v-if="totalMentions">
            {{ totalMentions }} mentions across {{ items.length }} {{ items.length === 1 ? 'topic' : 'topics' }}
          </template>
          <template v-else>
            Topics extracted from your approved facts.
          </template>
        </p>
      </div>
      <button
        v-if="items.length"
        type="button"
        class="kw-expand"
        @click="$emit('expand')"
      >View all →</button>
    </header>

    <div v-if="loading" class="kw-list">
      <div v-for="i in 4" :key="i" class="kw-skel" />
    </div>

    <div v-else-if="!items.length" class="kw-empty">
      Approve some facts with a topic to fill the repository.
    </div>

    <ul v-else class="kw-list" @click="$emit('expand')">
      <li v-for="row in top" :key="row.topic" class="kw-row">
        <span class="kw-rank">{{ row.rank }}</span>
        <span class="kw-name">{{ row.topic }}</span>
        <span class="kw-spark" aria-hidden="true">
          <KeywordSparkline :data="row.timeline" />
        </span>
        <span class="kw-count">{{ row.mention_count }}</span>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import KeywordSparkline from './KeywordSparkline.vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  totalMentions: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
})
defineEmits(['expand'])

const top = computed(() =>
  props.items.slice(0, 5).map((row, i) => ({ ...row, rank: i + 1 })),
)
</script>

<style scoped>
.kw-widget {
  background: var(--bg-card, #ffffff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 16px;
  padding: 20px 24px;
}
.kw-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.kw-title { margin: 0 0 4px; font-size: 1.1rem; font-weight: 700; color: var(--text-primary); letter-spacing: -0.01em; }
.kw-sub { margin: 0; font-size: 0.85rem; color: var(--text-secondary); }
.kw-expand {
  appearance: none;
  background: transparent;
  border: none;
  color: var(--brand-accent, #ff6b35);
  font: inherit;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.kw-expand:hover { text-decoration: underline; }

.kw-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
}
.kw-widget.is-clickable .kw-list:hover { border-color: var(--text-muted); }
.kw-row {
  display: grid;
  grid-template-columns: 24px 1fr 110px 64px;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: var(--bg-card, #fff);
  border-bottom: 1px solid var(--border-color, #e5e7eb);
}
.kw-row:last-child { border-bottom: none; }
.kw-rank { font-size: 0.78rem; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.kw-name { font-size: 0.92rem; color: var(--text-primary); font-weight: 500; text-transform: capitalize; }
.kw-spark { display: flex; align-items: center; justify-content: flex-end; opacity: 0.85; }
.kw-count {
  font-size: 0.92rem;
  color: var(--text-primary);
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.kw-skel {
  height: 42px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  background: linear-gradient(90deg, transparent 32%, rgba(255,255,255,0.45) 50%, transparent 68%), var(--bg-subtle, #fafafa);
  background-size: 200% 100%;
  animation: kw-shimmer 1.4s linear infinite;
}
.kw-skel:last-child { border-bottom: none; }
@keyframes kw-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.kw-empty {
  padding: 28px 16px;
  text-align: center;
  font-size: 0.85rem;
  color: var(--text-muted);
  border: 1px dashed var(--border-color, #e5e7eb);
  border-radius: 12px;
}

[data-theme="dark"] .kw-widget,
[data-theme="dark"] .kw-list,
[data-theme="dark"] .kw-row { background: var(--bg-card); border-color: var(--border-color); }
</style>
