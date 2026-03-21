<template>
  <div class="pipeline-node" :class="[`type-${data.nodeType}`, { selected: selected }]">
    <Handle v-if="data.nodeType !== 'source'" type="target" :position="Position.Left" />
    <div class="pn-emoji" v-html="data.icon || ''"></div>
    <div class="pn-label">{{ data.label }}</div>
    <div class="pn-count" v-if="data.count !== undefined">{{ data.count }}</div>
    <span v-if="data.badge" class="badge" :class="data.badgeClass || 'badge-neutral'" style="margin-top:4px;font-size:10px">{{ data.badge }}</span>
    <Handle type="source" :position="Position.Right" />
  </div>
</template>

<script setup>
import { Handle, Position } from '@vue-flow/core'

defineProps({
  data: { type: Object, required: true },
  selected: { type: Boolean, default: false },
})
</script>

<style scoped>
.pipeline-node {
  background: var(--bg-card);
  border: 1.5px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 14px 20px;
  min-width: 145px;
  transition: all var(--transition-base);
  cursor: grab;
}

.pipeline-node:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--border-hover);
}

.pipeline-node.selected {
  border-color: var(--brand-accent);
  box-shadow: 0 0 0 3px var(--brand-accent-glow);
}

/* Type variants */
.pipeline-node.type-hot       { background: var(--color-danger-bg);  border-color: rgba(196,77,77,0.2); }
.pipeline-node.type-warm      { background: var(--color-warning-bg); border-color: rgba(212,129,58,0.2); }
.pipeline-node.type-cold      { background: var(--bg-card); }
.pipeline-node.type-saas      { background: var(--color-info-bg);    border-color: rgba(74,142,194,0.15); }
.pipeline-node.type-health    { background: var(--color-success-bg); border-color: rgba(61,153,112,0.15); }
.pipeline-node.type-action    { background: var(--brand-accent-glow); border-color: rgba(212,149,106,0.2); }
.pipeline-node.type-connector { background: var(--bg-card); border-color: var(--border-hover); border-style: dashed; }

.pn-emoji  { font-size: 20px; margin-bottom: 4px; }
.pn-label  { font-size: var(--font-xs); font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.04em; }
.pn-count  { font-family: var(--font-display); font-size: var(--font-2xl); color: var(--text-primary); line-height: 1.2; }

/* Handle styling */
:deep(.vue-flow__handle) {
  width: 8px;
  height: 8px;
  background: var(--brand-accent);
  border: 2px solid var(--bg-card);
}
</style>
