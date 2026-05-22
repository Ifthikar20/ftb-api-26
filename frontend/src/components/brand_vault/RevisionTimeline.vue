<template>
  <div class="rt">
    <div class="rt-head">
      <h3>Revision history</h3>
      <p>Every approval, edit, supersede, and rejection — who, when, and what changed.</p>
    </div>

    <div v-if="loading" class="rt-skeleton">
      <div v-for="i in 4" :key="i" class="rt-skel" />
    </div>

    <div v-else-if="!revisions.length" class="rt-empty">
      <p>No changes recorded yet.</p>
    </div>

    <ol v-else class="rt-list">
      <li v-for="rev in revisions" :key="rev.id" class="rt-row">
        <span class="rt-dot" :class="`is-${rev.action}`" aria-hidden="true"></span>
        <div class="rt-row-body">
          <div class="rt-row-head">
            <span class="rt-action">{{ actionLabel(rev.action) }}</span>
            <span class="rt-actor" v-if="rev.actor_email">by {{ rev.actor_email }}</span>
            <span class="rt-when">{{ formatDate(rev.created_at) }}</span>
          </div>
          <div v-if="changeSummary(rev)" class="rt-row-change">
            {{ changeSummary(rev) }}
          </div>
        </div>
      </li>
    </ol>
  </div>
</template>

<script setup>
defineProps({
  revisions: { type: Array, required: true },
  loading: { type: Boolean, default: false },
})

const ACTION_LABELS = {
  created: 'Fact created',
  approved: 'Approved',
  rejected: 'Rejected',
  edited: 'Edited',
  superseded: 'Superseded',
}
function actionLabel(a) { return ACTION_LABELS[a] || a }

function changeSummary(rev) {
  const before = rev.before || {}
  const after = rev.after || {}
  // For supersede / edit, surface the meaningful object/subject delta.
  if (before.object && after.object && before.object !== after.object) {
    return `"${truncate(before.object)}" → "${truncate(after.object)}"`
  }
  if (after.subject && after.predicate && after.object) {
    return `${after.subject} · ${after.predicate} · ${truncate(after.object)}`
  }
  return ''
}
function truncate(s) {
  if (!s) return ''
  return s.length > 80 ? s.slice(0, 80) + '…' : s
}
function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.rt { display: flex; flex-direction: column; gap: 14px; }
.rt-head h3 { margin: 0 0 4px; font-size: 1.05rem; color: var(--text-primary); }
.rt-head p { margin: 0; font-size: 0.88rem; color: var(--text-secondary); line-height: 1.5; }

.rt-list { list-style: none; margin: 0; padding: 0; position: relative; }
.rt-list::before {
  content: '';
  position: absolute;
  left: 9px;
  top: 12px;
  bottom: 12px;
  width: 1px;
  background: var(--border-color, #e5e7eb);
}
.rt-row {
  display: grid;
  grid-template-columns: 20px 1fr;
  gap: 14px;
  padding: 10px 0;
  position: relative;
}
.rt-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--text-muted);
  margin-top: 6px;
  margin-left: 4px;
  border: 2px solid var(--bg-card, #fff);
  z-index: 1;
}
.rt-dot.is-approved { background: #10b981; }
.rt-dot.is-rejected { background: #ef4444; }
.rt-dot.is-superseded { background: #6366f1; }
.rt-dot.is-edited { background: #f59e0b; }
.rt-dot.is-created { background: #94a3b8; }

.rt-row-head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
}
.rt-action { font-size: 0.88rem; font-weight: 600; color: var(--text-primary); }
.rt-actor { font-size: 0.8rem; color: var(--text-secondary); }
.rt-when { font-size: 0.78rem; color: var(--text-muted); margin-left: auto; }
.rt-row-change { font-size: 0.82rem; color: var(--text-secondary); margin-top: 4px; line-height: 1.45; }

.rt-skeleton { display: flex; flex-direction: column; gap: 8px; }
.rt-skel {
  height: 56px;
  border-radius: 10px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.rt-empty {
  text-align: center;
  padding: 40px 20px;
  border: 1px dashed var(--border-color, #e5e7eb);
  border-radius: 14px;
  color: var(--text-muted);
  font-size: 0.88rem;
}
[data-theme="dark"] .rt-dot { border-color: var(--bg-card); }
[data-theme="dark"] .rt-skel { background: var(--bg-card); border-color: var(--border-color); }
</style>
