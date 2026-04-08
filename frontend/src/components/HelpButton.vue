<template>
  <div class="help-wrapper">
    <button class="help-trigger" @click="open = !open" title="Help & Support">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="8" cy="8" r="7"/>
        <path d="M6 6a2 2 0 1 1 2.5 1.94c-.32.14-.5.43-.5.78V10"/>
        <circle cx="8" cy="12" r="0.5" fill="currentColor"/>
      </svg>
    </button>

    <Teleport to="body">
      <div v-if="open" class="help-overlay" @click.self="open = false">
        <div class="help-panel">
          <div class="help-header">
            <h3>Help & Setup</h3>
            <button class="help-close" @click="open = false">&times;</button>
          </div>

          <div class="help-content">
            <!-- Quick Start -->
            <div class="help-section">
              <h4>Quick Start</h4>
              <div class="help-step">
                <span class="step-num">1</span>
                <div>
                  <strong>Add your project</strong>
                  <p>Click the + button in the sidebar to add your website URL.</p>
                </div>
              </div>
              <div class="help-step">
                <span class="step-num">2</span>
                <div>
                  <strong>Install the tracking pixel</strong>
                  <p>Go to your project settings and copy the embed snippet into your website's &lt;head&gt; tag.</p>
                </div>
              </div>
              <div class="help-step">
                <span class="step-num">3</span>
                <div>
                  <strong>Run your first audit</strong>
                  <p>Go to Audits and click "Run Audit" to scan your site for SEO, performance, and security issues.</p>
                </div>
              </div>
              <div class="help-step">
                <span class="step-num">4</span>
                <div>
                  <strong>Track keywords</strong>
                  <p>Go to Keywords and add the search terms you want to monitor.</p>
                </div>
              </div>
            </div>

            <!-- Contextual Help -->
            <div class="help-section">
              <h4>Page Guide</h4>
              <div v-for="item in pageHelp" :key="item.page" class="help-item" :class="{ active: isCurrentPage(item.page) }">
                <div class="help-item-header" @click="expandedItem = expandedItem === item.page ? '' : item.page">
                  <span>{{ item.icon }} {{ item.label }}</span>
                  <span class="chevron" :class="{ expanded: expandedItem === item.page }">›</span>
                </div>
                <div v-if="expandedItem === item.page" class="help-item-body">{{ item.help }}</div>
              </div>
            </div>

            <!-- Reset Onboarding -->
            <div class="help-section">
              <button class="help-reset-btn" @click="resetOnboarding">Replay Onboarding Tour</button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const open = ref(false)
const expandedItem = ref('')

const pageHelp = [
  { page: 'analytics', icon: '', label: 'Analytics', help: 'See real-time visitor data, traffic sources, top pages, and device breakdown. Data appears once you install the tracking pixel on your website.' },
  { page: 'heatmap', icon: '', label: 'Heatmaps', help: 'Visualize where visitors click on your pages. Requires the tracking pixel to capture click coordinates. Hotter colors = more clicks.' },
  { page: 'keywords', icon: '', label: 'Keywords', help: 'Track your search engine rankings for specific keywords. Add keywords manually and monitor their position over time.' },
  { page: 'leads', icon: '', label: 'Leads', help: 'Captured visitor and form submission data. Leads are created when visitors interact with forms on your tracked site.' },


  { page: 'billing', icon: '', label: 'Billing', help: 'Manage your subscription, view usage, and compare plan features.' },
]

function isCurrentPage(page) {
  return route.path.startsWith('/' + page)
}

function resetOnboarding() {
  localStorage.removeItem('fb_onboarding_done')
  open.value = false
  window.location.reload()
}
</script>

<style scoped>
.help-trigger {
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  transition: color 0.15s;
}
.help-trigger:hover { color: var(--text-primary); }

.help-overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  background: rgba(0,0,0,0.3);
  display: flex;
  justify-content: flex-end;
}

.help-panel {
  width: 380px;
  max-width: 90vw;
  height: 100vh;
  background: var(--bg-card);
  border-left: 1px solid var(--border-color);
  box-shadow: -8px 0 30px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.help-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}
.help-header h3 { margin: 0; font-size: var(--font-lg); color: var(--text-primary); }

.help-close {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--text-muted);
  cursor: pointer;
  line-height: 1;
}
.help-close:hover { color: var(--text-primary); }

.help-content { padding: 20px 24px; }

.help-section {
  margin-bottom: 28px;
}
.help-section h4 {
  font-size: var(--font-sm);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 16px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.help-step {
  display: flex;
  gap: 14px;
  margin-bottom: 16px;
}

.step-num {
  width: 26px;
  height: 26px;
  background: var(--text-primary);
  color: var(--text-inverse);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 2px;
}

.help-step p {
  font-size: var(--font-sm);
  color: var(--text-secondary);
  margin: 4px 0 0;
  line-height: 1.4;
}

.help-item {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  margin-bottom: 8px;
  overflow: hidden;
}

.help-item.active { border-color: var(--brand-accent); }

.help-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
  transition: background 0.15s;
}

.help-item-header:hover { background: var(--bg-surface); }

.chevron { transition: transform 0.2s; font-size: 18px; color: var(--text-muted); }
.chevron.expanded { transform: rotate(90deg); }

.help-item-body {
  padding: 0 16px 14px;
  font-size: var(--font-sm);
  color: var(--text-secondary);
  line-height: 1.5;
}

.help-reset-btn {
  width: 100%;
  padding: 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}
.help-reset-btn:hover {
  background: var(--bg-card);
  border-color: var(--text-primary);
  color: var(--text-primary);
}
</style>
