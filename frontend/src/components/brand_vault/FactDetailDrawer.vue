<template>
  <Transition name="fd-fade">
    <div v-if="open" class="fd-mask" @click.self="close">
      <Transition name="fd-slide">
        <aside v-if="open" class="fd-drawer" role="dialog" aria-label="Fact detail">
          <header class="fd-head">
            <span class="fd-eyebrow">Fact</span>
            <h3 class="fd-title">{{ fact?.subject }}</h3>
            <button class="fd-close" type="button" aria-label="Close" @click="close">×</button>
          </header>

          <section class="fd-section">
            <div class="fd-text">
              <strong>{{ fact?.subject }}</strong>
              <span class="fd-pred">{{ fact?.predicate }}</span>
              <span>{{ fact?.object }}</span>
            </div>
            <div class="fd-meta">
              <span class="fd-pill" :class="`is-${fact?.status}`">{{ fact?.status }}</span>
              <span v-if="fact?.product_line" class="fd-tag">{{ fact.product_line }}</span>
              <span v-if="fact?.topic" class="fd-tag">{{ fact.topic }}</span>
              <span class="fd-conf">{{ confidencePct }}% confidence</span>
            </div>
            <a v-if="fact?.source_url" :href="fact.source_url" target="_blank" rel="noopener" class="fd-source">
              View source ↗
            </a>
          </section>

          <section class="fd-section">
            <h4>Usage</h4>
            <div v-if="loadingUsage" class="fd-usage-loading">Loading usage…</div>
            <div v-else class="fd-usage">
              <div class="fd-usage-cell">
                <div class="fd-usage-val">{{ usage.audit_count || 0 }}</div>
                <div class="fd-usage-label">audits since added</div>
              </div>
              <div class="fd-usage-cell">
                <div class="fd-usage-val">{{ usage.draft_count || 0 }}</div>
                <div class="fd-usage-label">content drafts</div>
              </div>
              <div class="fd-usage-cell">
                <div class="fd-usage-val">{{ usage.revision_count || 0 }}</div>
                <div class="fd-usage-label">revisions</div>
              </div>
            </div>
          </section>

          <section class="fd-section">
            <h4>Provenance</h4>
            <dl class="fd-prov">
              <dt>Added</dt>
              <dd>{{ formatDate(fact?.created_at) }}</dd>
              <dt>Extracted by</dt>
              <dd>{{ fact?.extracted_by || 'manual' }}</dd>
              <dt>Version from</dt>
              <dd>{{ formatDate(fact?.version_from) }}</dd>
              <dt v-if="fact?.version_to">Superseded at</dt>
              <dd v-if="fact?.version_to">{{ formatDate(fact?.version_to) }}</dd>
            </dl>
          </section>
        </aside>
      </Transition>
    </div>
  </Transition>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import brandVaultApi from '@/api/brandVault'

const props = defineProps({
  open: { type: Boolean, default: false },
  fact: { type: Object, default: null },
})
const emit = defineEmits(['update:open'])

const usage = ref({})
const loadingUsage = ref(false)

watch(() => [props.open, props.fact?.id], async ([open, id]) => {
  if (!open || !id) return
  loadingUsage.value = true
  try {
    const { data } = await brandVaultApi.factUsage(id)
    usage.value = data?.data || data || {}
  } catch (_) {
    usage.value = {}
  } finally {
    loadingUsage.value = false
  }
})

const confidencePct = computed(() => {
  const c = Number(props.fact?.confidence) || 0
  const v = c <= 1 ? c * 100 : c
  return Math.max(0, Math.min(100, Math.round(v)))
})

function close() { emit('update:open', false) }
function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}
</script>

<style scoped>
.fd-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  z-index: 1100;
  display: flex;
  justify-content: flex-end;
}
.fd-drawer {
  width: 100%;
  max-width: 480px;
  background: var(--bg-card, #fff);
  height: 100%;
  overflow-y: auto;
  border-left: 1px solid var(--border-color, #e5e7eb);
  display: flex;
  flex-direction: column;
}
.fd-head {
  position: sticky;
  top: 0;
  background: var(--bg-card, #fff);
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  padding: 16px 22px;
  z-index: 1;
}
.fd-eyebrow {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
}
.fd-title { margin: 4px 0 0; font-size: 1.1rem; font-weight: 700; color: var(--text-primary); letter-spacing: -0.01em; }
.fd-close {
  position: absolute;
  top: 12px;
  right: 14px;
  appearance: none;
  background: transparent;
  border: none;
  font-size: 1.4rem;
  line-height: 1;
  color: var(--text-muted);
  cursor: pointer;
}
.fd-close:hover { color: var(--text-primary); }

.fd-section {
  padding: 18px 22px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
}
.fd-section h4 {
  margin: 0 0 10px;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
}
.fd-text {
  font-size: 0.95rem;
  line-height: 1.55;
  color: var(--text-primary);
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}
.fd-text strong { font-weight: 600; }
.fd-pred { color: var(--text-secondary); }

.fd-meta { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; font-size: 0.78rem; color: var(--text-muted); margin-bottom: 10px; }
.fd-pill { font-size: 0.66rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; padding: 2px 8px; border-radius: 999px; }
.fd-pill.is-approved { background: rgba(16,185,129,0.14); color: #047857; }
.fd-pill.is-auto { background: rgba(91,141,239,0.14); color: #1d4ed8; }
.fd-pill.is-pending { background: rgba(245,158,11,0.18); color: #b45309; }
.fd-pill.is-rejected { background: var(--bg-subtle, #fafafa); color: var(--text-muted); }
.fd-tag {
  background: var(--bg-subtle, #fafafa);
  padding: 1px 7px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-size: 0.7rem;
}
.fd-conf { font-variant-numeric: tabular-nums; }
.fd-source {
  display: inline-block;
  color: var(--brand-accent, #ff6b35);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 500;
}
.fd-source:hover { text-decoration: underline; }

.fd-usage {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.fd-usage-cell {
  padding: 12px 14px;
  background: var(--bg-subtle, #fafafa);
  border-radius: 10px;
  text-align: center;
}
.fd-usage-val { font-size: 1.25rem; font-weight: 700; color: var(--text-primary); }
.fd-usage-label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; margin-top: 2px; }
.fd-usage-loading { font-size: 0.85rem; color: var(--text-muted); }

.fd-prov { display: grid; grid-template-columns: max-content 1fr; gap: 6px 14px; margin: 0; font-size: 0.85rem; }
.fd-prov dt { color: var(--text-muted); }
.fd-prov dd { margin: 0; color: var(--text-primary); }

.fd-fade-enter-active, .fd-fade-leave-active { transition: opacity 0.2s ease; }
.fd-fade-enter-from, .fd-fade-leave-to { opacity: 0; }
.fd-slide-enter-active, .fd-slide-leave-active { transition: transform 0.22s ease; }
.fd-slide-enter-from, .fd-slide-leave-to { transform: translateX(100%); }

[data-theme="dark"] .fd-drawer,
[data-theme="dark"] .fd-head { background: var(--bg-card); border-color: var(--border-color); }
[data-theme="dark"] .fd-section { border-color: var(--border-color); }
[data-theme="dark"] .fd-usage-cell,
[data-theme="dark"] .fd-tag { background: var(--bg-card-hover); }
</style>
