<template>
  <div class="heatmap-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Click Heatmap</h1>
        <p class="page-subtitle">See where visitors click on your pages.</p>
      </div>
      <div class="header-controls">
        <select v-model="selectedPage" class="form-input" style="min-width:280px" @change="fetchHeatmap">
          <option v-for="p in pages" :key="p.url" :value="p.url">{{ cleanUrl(p.url) }} ({{ p.click_count }} clicks)</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="loading-state">Loading heatmap data...</div>
    <template v-else>
      <!-- Empty State -->
      <div v-if="!pages.length" class="empty-guide">
        <div class="empty-guide-icon">🔥</div>
        <h3>No click data yet</h3>
        <p>Once visitors interact with your tracked website, click positions will appear here as a heatmap. Install the tracking pixel to start collecting data.</p>
        <div class="empty-guide-snippet">
          <code>&lt;script src="/fetchbot-pixel.js" data-site="YOUR_PIXEL_KEY" async&gt;&lt;/script&gt;</code>
        </div>
        <p class="empty-guide-hint">The pixel automatically captures click coordinates — no extra setup needed.</p>
      </div>

      <template v-if="pages.length">
      <!-- Stats Row -->
      <div class="heatmap-stats">
        <div class="stat-pill">
          <span class="stat-label">Total Clicks</span>
          <span class="stat-value">{{ totalClicks.toLocaleString() }}</span>
        </div>
        <div class="stat-pill">
          <span class="stat-label">Hottest Zone</span>
          <span class="stat-value">{{ hottestZone }}</span>
        </div>
        <div class="stat-pill">
          <span class="stat-label">Click Points</span>
          <span class="stat-value">{{ points.length }}</span>
        </div>
        <div class="stat-pill">
          <span class="stat-label">Pages Tracked</span>
          <span class="stat-value">{{ pages.length }}</span>
        </div>
      </div>

      <!-- Heatmap Canvas -->
      <div class="card heatmap-card">
        <div class="heatmap-header">
          <h3 class="card-title">{{ cleanUrl(selectedPage) }}</h3>
          <div class="heat-legend">
            <span class="legend-label">Low</span>
            <div class="legend-gradient"></div>
            <span class="legend-label">High</span>
          </div>
        </div>
        <div class="heatmap-canvas" ref="canvasRef">
          <svg :viewBox="`0 0 ${canvasW} ${canvasH}`" class="heatmap-svg">
            <!-- Grid lines -->
            <line v-for="i in 9" :key="'gx'+i" :x1="(canvasW/10)*i" y1="0" :x2="(canvasW/10)*i" :y2="canvasH" class="grid-line"/>
            <line v-for="i in 9" :key="'gy'+i" x1="0" :y1="(canvasH/10)*i" :x2="canvasW" :y2="(canvasH/10)*i" class="grid-line"/>

            <!-- Page layout overlay (decorative wireframe) -->
            <rect x="20" y="10" :width="canvasW-40" height="40" rx="4" class="wireframe" />
            <text :x="canvasW/2" y="35" text-anchor="middle" class="wireframe-text">Navigation Bar</text>
            <rect x="60" y="80" :width="canvasW-120" height="120" rx="6" class="wireframe" />
            <text :x="canvasW/2" y="145" text-anchor="middle" class="wireframe-text">Hero Section</text>
            <rect x="40" y="230" :width="(canvasW-100)/3" height="80" rx="4" class="wireframe" />
            <rect :x="40+(canvasW-100)/3+10" y="230" :width="(canvasW-100)/3" height="80" rx="4" class="wireframe" />
            <rect :x="40+2*((canvasW-100)/3+10)" y="230" :width="(canvasW-100)/3" height="80" rx="4" class="wireframe" />
            <rect x="20" y="340" :width="canvasW-40" height="60" rx="4" class="wireframe" />
            <text :x="canvasW/2" y="375" text-anchor="middle" class="wireframe-text">Footer</text>

            <!-- Heat dots -->
            <circle
              v-for="(p, i) in points" :key="i"
              :cx="p.x / 100 * canvasW"
              :cy="p.y / 100 * canvasH"
              :r="dotRadius(p.intensity)"
              :fill="dotColor(p.intensity)"
              :opacity="0.5 + p.intensity * 0.4"
              class="heat-dot"
            />
          </svg>
        </div>
      </div>

      <!-- Top Click Zones Table -->
      <div class="card" style="margin-top:20px">
        <div class="card-header">
          <h3 class="card-title">Top Click Zones</h3>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>Position (X%, Y%)</th>
              <th>Clicks</th>
              <th>Intensity</th>
              <th>Heat</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(p, i) in points.slice(0, 15)" :key="i">
              <td class="font-mono">{{ p.x }}%, {{ p.y }}%</td>
              <td class="font-semibold">{{ p.count }}</td>
              <td>{{ Math.round(p.intensity * 100) }}%</td>
              <td>
                <div class="heat-bar">
                  <div class="heat-bar-fill" :style="{ width: (p.intensity * 100) + '%', background: dotColor(p.intensity) }"></div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import analyticsApi from '@/api/analytics'

const props = defineProps({ websiteId: String })

const loading = ref(true)
const pages = ref([])
const selectedPage = ref('')
const points = ref([])
const totalClicks = ref(0)

const canvasW = 720
const canvasH = 420

const hottestZone = computed(() => {
  if (!points.value.length) return '--'
  const top = points.value[0]
  if (top.y < 10) return 'Navigation'
  if (top.y < 40) return 'Hero / CTA'
  if (top.y < 65) return 'Content Area'
  if (top.y < 85) return 'Mid Section'
  return 'Footer'
})

function cleanUrl(url) {
  if (!url) return '--'
  try { return new URL(url).pathname } catch { return url }
}

function dotRadius(intensity) {
  return 6 + intensity * 16
}

function dotColor(intensity) {
  // blue → green → yellow → orange → red
  if (intensity < 0.2) return 'rgba(59,130,246,0.7)'
  if (intensity < 0.4) return 'rgba(34,197,94,0.7)'
  if (intensity < 0.6) return 'rgba(234,179,8,0.8)'
  if (intensity < 0.8) return 'rgba(249,115,22,0.8)'
  return 'rgba(239,68,68,0.9)'
}

async function fetchHeatmap() {
  try {
    const { data } = await analyticsApi.heatmap(props.websiteId, { page: selectedPage.value })
    const d = data?.data || data
    pages.value = d.pages || []
    points.value = d.points || []
    totalClicks.value = d.total_clicks || 0
    if (!selectedPage.value && d.selected_page) {
      selectedPage.value = d.selected_page
    }
  } catch (e) {
    console.error('Heatmap fetch error', e)
  }
}

onMounted(async () => {
  await fetchHeatmap()
  loading.value = false
})
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }
.header-controls { display: flex; gap: 12px; align-items: center; }

.heatmap-stats {
  display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap;
}
.stat-pill {
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg);
  padding: 14px 20px; display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 140px;
}
.stat-label { font-size: var(--font-xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.stat-value { font-size: var(--font-xl); font-weight: 700; color: var(--text-primary); }

.heatmap-card { overflow: hidden; }
.heatmap-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 0 16px;
}

.heat-legend { display: flex; align-items: center; gap: 8px; }
.legend-label { font-size: var(--font-xs); color: var(--text-muted); }
.legend-gradient {
  width: 120px; height: 8px; border-radius: var(--radius-full);
  background: linear-gradient(90deg, rgba(59,130,246,0.7), rgba(34,197,94,0.7), rgba(234,179,8,0.8), rgba(249,115,22,0.8), rgba(239,68,68,0.9));
}

.heatmap-canvas {
  background: var(--bg-surface); border-radius: var(--radius-md);
  border: 1px solid var(--border-color); overflow: hidden;
}

.heatmap-svg { width: 100%; display: block; }

.grid-line { stroke: var(--border-color); stroke-width: 0.5; opacity: 0.3; }
.wireframe { fill: none; stroke: var(--text-muted); stroke-width: 1; opacity: 0.15; stroke-dasharray: 4 4; }
.wireframe-text { fill: var(--text-muted); font-size: 11px; opacity: 0.3; }

.heat-dot { transition: all 0.3s ease; }
.heat-dot:hover { filter: brightness(1.3); }

.font-mono { font-family: 'SF Mono', 'Fira Code', monospace; font-size: var(--font-sm); }

.heat-bar { width: 100%; height: 6px; background: var(--bg-input); border-radius: var(--radius-full); overflow: hidden; }
.heat-bar-fill { height: 100%; border-radius: var(--radius-full); transition: width 0.5s ease; }

/* Empty Guide */
.empty-guide { text-align: center; padding: 60px 40px; background: var(--bg-card); border: 2px dashed var(--border-color); border-radius: var(--radius-lg); }
.empty-guide-icon { font-size: 48px; margin-bottom: 16px; }
.empty-guide h3 { font-size: var(--font-lg); color: var(--text-primary); margin: 0 0 10px; }
.empty-guide p { font-size: var(--font-sm); color: var(--text-secondary); max-width: 480px; margin: 0 auto 16px; line-height: 1.6; }
.empty-guide-snippet { background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px 20px; display: inline-block; margin-bottom: 12px; }
.empty-guide-snippet code { font-size: var(--font-xs); color: var(--brand-accent); font-family: 'SF Mono', 'Fira Code', monospace; }
.empty-guide-hint { font-size: var(--font-xs); color: var(--text-muted); }

@media (max-width: 768px) {
  .heatmap-stats { flex-direction: column; }
}
</style>
