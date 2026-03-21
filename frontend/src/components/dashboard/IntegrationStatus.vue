<template>
  <div class="card integration-card">
    <div class="card-header">
      <h3 class="card-title">
        <svg class="title-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
          <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
        </svg>
        Integration Status
      </h3>
      <router-link to="/settings" class="settings-link">Manage</router-link>
    </div>

    <!-- Pixel Health -->
    <div class="integration-section">
      <div class="section-label">Tracking Pixel</div>
      <div class="integration-row">
        <span class="status-dot" :class="pixelStatusClass"></span>
        <div class="integration-info">
          <div class="integration-name">FetchBot Pixel</div>
          <div class="integration-meta">
            <template v-if="integrations.pixel?.verified">
              Verified {{ integrations.pixel.verified_at || '' }}
            </template>
            <template v-else>
              Not installed — <router-link to="/websites" class="setup-link">Set up now</router-link>
            </template>
          </div>
        </div>
        <span class="badge" :class="integrations.pixel?.verified ? 'badge-success' : 'badge-warning'">
          {{ integrations.pixel?.verified ? 'Active' : 'Pending' }}
        </span>
      </div>
    </div>

    <!-- Connected Services -->
    <div class="integration-section">
      <div class="section-label">Connected Services</div>
      <div v-for="service in integrations.services" :key="service.type" class="integration-row">
        <span class="status-dot" :class="service.connected ? 'dot-success' : 'dot-idle'"></span>
        <div class="integration-info">
          <div class="integration-name">{{ service.label }}</div>
          <div class="integration-meta">
            <template v-if="service.connected">
              Connected {{ service.connected_at || '' }}
            </template>
            <template v-else>
              Not connected
            </template>
          </div>
        </div>
        <span class="badge" :class="service.connected ? 'badge-success' : 'badge-neutral'">
          {{ service.connected ? 'Connected' : 'Available' }}
        </span>
      </div>
    </div>

    <!-- Summary -->
    <div class="integration-summary">
      <div class="summary-stat">
        <span class="summary-value">{{ connectedCount }}</span>
        <span class="summary-label">Connected</span>
      </div>
      <div class="summary-divider"></div>
      <div class="summary-stat">
        <span class="summary-value">{{ totalCount }}</span>
        <span class="summary-label">Available</span>
      </div>
      <div class="summary-divider"></div>
      <div class="summary-stat">
        <span class="summary-value" :class="integrations.pixel?.verified ? 'text-success' : 'text-warning'">
          {{ integrations.pixel?.verified ? '✓' : '!' }}
        </span>
        <span class="summary-label">Pixel</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  integrations: { type: Object, required: true },
})

const pixelStatusClass = computed(() =>
  props.integrations.pixel?.verified ? 'dot-success' : 'dot-warning'
)

const connectedCount = computed(() =>
  (props.integrations.services || []).filter(s => s.connected).length
)

const totalCount = computed(() =>
  (props.integrations.services || []).length
)
</script>

<style scoped>
.integration-card {
  position: relative;
  overflow: hidden;
}

.integration-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--color-success), var(--brand-accent, #6366f1), var(--color-warning));
  opacity: 0.7;
}

.title-icon {
  vertical-align: -3px;
  margin-right: 6px;
  opacity: 0.7;
}

.settings-link {
  font-size: var(--font-xs);
  color: var(--text-muted);
  text-decoration: none;
  font-weight: 500;
  transition: color var(--transition-fast);
}
.settings-link:hover { color: var(--text-primary); }

.integration-section {
  margin-top: 16px;
}

.section-label {
  font-size: var(--font-xs);
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 10px;
}

.integration-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}

.integration-row:last-child { border-bottom: none; }

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-success { background: #22c55e; box-shadow: 0 0 6px rgba(34, 197, 94, 0.4); }
.dot-warning { background: #f59e0b; box-shadow: 0 0 6px rgba(245, 158, 11, 0.4); }
.dot-idle { background: var(--text-muted); opacity: 0.4; }

.integration-info { flex: 1; min-width: 0; }
.integration-name { font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); }
.integration-meta { font-size: var(--font-xs); color: var(--text-muted); margin-top: 2px; }

.setup-link {
  color: var(--brand-accent, #6366f1);
  text-decoration: none;
  font-weight: 600;
}
.setup-link:hover { text-decoration: underline; }

.integration-summary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.summary-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.summary-value {
  font-size: var(--font-xl);
  font-weight: 700;
  color: var(--text-primary);
}

.summary-label {
  font-size: var(--font-xs);
  color: var(--text-muted);
}

.summary-divider {
  width: 1px;
  height: 32px;
  background: var(--border-color);
}

.text-success { color: #22c55e; }
.text-warning { color: #f59e0b; }
</style>
