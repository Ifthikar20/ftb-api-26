<template>
  <div class="bvs-grid">
    <div class="bvs-card">
      <div class="bvs-label">Pending</div>
      <div class="bvs-val" :class="{ 'is-warn': stats.pending > 0 }">{{ stats.pending || 0 }}</div>
      <div class="bvs-sub">Needs review</div>
    </div>
    <div class="bvs-card">
      <div class="bvs-label">Approved</div>
      <div class="bvs-val is-good">{{ approvedTotal }}</div>
      <div class="bvs-sub">{{ stats.auto || 0 }} auto · {{ stats.approved || 0 }} manual</div>
    </div>
    <div class="bvs-card">
      <div class="bvs-label">Stale</div>
      <div class="bvs-val" :class="{ 'is-warn': staleCount > 0 }">{{ staleCount || 0 }}</div>
      <div class="bvs-sub">Older than 6 months</div>
    </div>
    <div class="bvs-card bvs-card-cov">
      <div class="bvs-label">Coverage</div>
      <div class="bvs-val">{{ coverageScore }}%</div>
      <div class="bvs-bar">
        <div class="bvs-bar-fill" :style="{ width: coverageScore + '%' }"></div>
      </div>
      <div class="bvs-sub">Standard B2B facts covered</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: { type: Object, required: true },
  coverageScore: { type: Number, default: 0 },
  staleCount: { type: Number, default: 0 },
})

const approvedTotal = computed(
  () => (props.stats.approved || 0) + (props.stats.auto || 0),
)
</script>

<style scoped>
.bvs-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}
@media (max-width: 900px) { .bvs-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 540px) { .bvs-grid { grid-template-columns: 1fr; } }

.bvs-card {
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
  padding: 16px 18px;
}
.bvs-label {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 8px;
}
.bvs-val {
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  line-height: 1.05;
  font-variant-numeric: tabular-nums;
}
.bvs-val.is-warn { color: #b45309; }
.bvs-val.is-good { color: #047857; }
.bvs-sub { font-size: 0.78rem; color: var(--text-muted); margin-top: 6px; }
.bvs-bar {
  height: 4px;
  border-radius: 999px;
  background: var(--border-color, #e5e7eb);
  margin: 8px 0 6px;
  overflow: hidden;
}
.bvs-bar-fill {
  height: 100%;
  background: var(--brand-accent, #ff6b35);
  border-radius: 999px;
  transition: width 0.3s ease;
}
</style>
