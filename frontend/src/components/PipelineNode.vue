<template>
  <div class="pipeline-node" :class="[`type-${data.nodeType}`, `status-${data.status || 'idle'}`, { selected }]">
    <Handle v-if="data.nodeType !== 'source'" type="target" :position="Position.Left" />

    <!-- Status dot -->
    <div class="pn-status" :class="data.status || 'idle'"></div>

    <!-- Icon -->
    <div class="pn-icon" v-html="data.icon || ''"></div>

    <!-- Label -->
    <div class="pn-label">{{ data.label }}</div>

    <!-- Lead count -->
    <div class="pn-count" v-if="data.leadCount !== undefined">
      {{ data.leadCount }} <span class="pn-count-unit">{{ data.leadCount === 1 ? 'lead' : 'leads' }}</span>
    </div>

    <!-- Badge -->
    <span v-if="data.badge" class="pn-badge" :class="data.badgeClass || 'badge-neutral'">{{ data.badge }}</span>

    <!-- Primary output handle (right) -->
    <Handle type="source" :position="Position.Right" id="out" />

    <!-- Secondary output handle (bottom — for split nodes) -->
    <Handle v-if="data.hasSplit" type="source" :position="Position.Bottom" id="split" class="handle-split" />
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
  border-radius: 10px;
  padding: 14px 18px;
  min-width: 152px;
  max-width: 200px;
  transition: all 0.15s ease;
  cursor: grab;
  position: relative;
}
.pipeline-node:hover {
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  border-color: var(--border-hover);
}
.pipeline-node.selected {
  border-color: var(--brand-accent);
  box-shadow: 0 0 0 2px rgba(91,141,239,0.15);
}

/* Status ring */
.pn-status {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  transition: background 0.2s;
}
.pn-status.idle      { background: var(--border-color); }
.pn-status.ready     { background: var(--color-warning, #f59e0b); }
.pn-status.running   { background: var(--brand-accent); animation: pulse-status 1s ease infinite; }
.pn-status.done      { background: var(--color-success, #22c55e); }

@keyframes pulse-status {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.35; }
}

/* Type variants */
.pipeline-node.type-source    { background: var(--bg-surface); border-color: var(--border-hover); }
.pipeline-node.type-action    { background: var(--bg-card); }
.pipeline-node.type-splitter  { background: var(--bg-card); border-style: dashed; border-color: var(--border-hover); }
.pipeline-node.type-outreach  { background: color-mix(in srgb, var(--brand-accent) 4%, var(--bg-card)); border-color: color-mix(in srgb, var(--brand-accent) 18%, transparent); }
.pipeline-node.type-linkedin  { background: color-mix(in srgb, #0a66c2 4%, var(--bg-card)); border-color: color-mix(in srgb, #0a66c2 18%, transparent); }

.pn-icon   { font-size: 18px; margin-bottom: 6px; line-height: 1; }
.pn-label  { font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; line-height: 1.3; }
.pn-count  { font-family: var(--font-display, 'Inter', sans-serif); font-size: 22px; font-weight: 700; color: var(--text-primary); line-height: 1.2; margin-top: 2px; }
.pn-count-unit { font-size: 11px; font-weight: 500; color: var(--text-muted); }

.pn-badge {
  display: inline-block;
  margin-top: 5px;
  font-size: 9px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 4px;
  letter-spacing: 0.03em;
}
.badge-neutral { background: var(--bg-surface); color: var(--text-muted); }
.badge-accent  { background: rgba(91,141,239,0.08); color: var(--brand-accent); }
.badge-success { background: rgba(34,197,94,0.08); color: #22c55e; }
.badge-info    { background: rgba(59,130,246,0.08); color: #3b82f6; }
.badge-warning { background: rgba(245,158,11,0.08); color: #f59e0b; }
.badge-danger  { background: rgba(239,68,68,0.08); color: #ef4444; }

/* Handle styling */
:deep(.vue-flow__handle) {
  width: 8px;
  height: 8px;
  background: var(--brand-accent);
  border: 2px solid var(--bg-card);
}
:deep(.vue-flow__handle.handle-split) {
  background: var(--color-warning, #f59e0b);
}
</style>
