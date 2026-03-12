<template>
  <div class="heatmap-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Click Heatmap</h1>
        <p class="page-subtitle">See where visitors click on your pages.</p>
      </div>
      <div class="header-controls">
        <select v-model="selectedPage" class="form-input" style="min-width:260px;max-width:360px" @change="onPageChange">
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
        <button v-if="fetchError" class="btn btn-secondary" style="margin-top:12px" @click="retryFetch">Retry</button>
        <p v-if="fetchError" class="text-danger text-sm" style="margin-top:8px">{{ fetchError }}</p>
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

      <!-- Heatmap Visualization -->
      <div class="card heatmap-card">
        <div class="heatmap-header">
          <h3 class="card-title">{{ cleanUrl(selectedPage) }}</h3>
          <div class="header-right">
            <div class="heat-legend">
              <span class="legend-label">Low</span>
              <div class="legend-gradient"></div>
              <span class="legend-label">High</span>
            </div>
          </div>
        </div>

        <div class="heatmap-viewport" ref="viewportRef">
          <!-- Page wireframe background -->
          <svg class="wireframe-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
            <!-- Navigation bar -->
            <rect x="2" y="1" width="96" height="6" rx="0.5" class="wf-section"/>
            <text x="50" y="4.5" text-anchor="middle" class="wf-label">Navigation</text>
            <!-- Hero section -->
            <rect x="5" y="10" width="90" height="20" rx="0.8" class="wf-section"/>
            <text x="50" y="21" text-anchor="middle" class="wf-label">Hero / CTA</text>
            <!-- Content cards -->
            <rect x="5" y="34" width="28" height="14" rx="0.5" class="wf-section"/>
            <rect x="36" y="34" width="28" height="14" rx="0.5" class="wf-section"/>
            <rect x="67" y="34" width="28" height="14" rx="0.5" class="wf-section"/>
            <text x="50" y="42" text-anchor="middle" class="wf-label">Content</text>
            <!-- Mid section -->
            <rect x="5" y="52" width="90" height="16" rx="0.5" class="wf-section"/>
            <text x="50" y="61" text-anchor="middle" class="wf-label">Mid Section</text>
            <!-- Lower content -->
            <rect x="5" y="72" width="44" height="14" rx="0.5" class="wf-section"/>
            <rect x="51" y="72" width="44" height="14" rx="0.5" class="wf-section"/>
            <text x="50" y="80" text-anchor="middle" class="wf-label">Lower Content</text>
            <!-- Footer -->
            <rect x="2" y="90" width="96" height="9" rx="0.5" class="wf-section"/>
            <text x="50" y="95.5" text-anchor="middle" class="wf-label">Footer</text>
          </svg>

          <!-- Canvas heat overlay -->
          <canvas ref="heatCanvas" class="heat-overlay"></canvas>

          <!-- Click markers -->
          <div v-if="showMarkers" class="click-markers">
            <div
              v-for="(p, i) in points.slice(0, 30)" :key="i"
              class="click-marker"
              :style="{
                left: p.x + '%',
                top: p.y + '%',
                '--dot-size': (8 + p.intensity * 12) + 'px',
                '--dot-color': dotColor(p.intensity),
              }"
            >{{ p.count }}</div>
          </div>
        </div>

        <div class="heatmap-toolbar">
          <label class="hm-toggle">
            <input type="checkbox" v-model="showMarkers" /> Show click counts
          </label>
          <label class="hm-toggle">
            <input type="checkbox" v-model="highOpacity" @change="drawHeatmap" /> More visible
          </label>
        </div>
      </div>

      <!-- Zone + Elements Row -->
      <div class="hm-grid">
        <!-- Zone Distribution -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">🗺️ Zone Distribution</h3>
            <span class="text-xs text-muted">Where clicks concentrate</span>
          </div>
          <div class="zone-bars">
            <div v-for="z in zones" :key="z.zone" class="zone-row">
              <span class="zone-name">{{ z.zone }}</span>
              <div class="zone-bar-wrap">
                <div class="zone-bar-fill" :style="{ width: Math.max(z.pct, 1) + '%', background: zoneColor(z.pct) }"></div>
              </div>
              <span class="zone-pct">{{ z.pct }}%</span>
              <span class="zone-count">{{ z.clicks }}</span>
            </div>
          </div>
        </div>

        <!-- Top Clicked Elements -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">🖱️ Top Clicked Elements</h3>
            <span class="text-xs text-muted">{{ topElements.length }} elements</span>
          </div>
          <div v-if="topElements.length" class="element-list">
            <div v-for="(el, i) in topElements.slice(0, 8)" :key="i" class="element-row">
              <span class="element-rank">#{{ i + 1 }}</span>
              <div class="element-info">
                <code class="element-selector">{{ el.selector }}</code>
                <span v-if="el.text" class="element-text">{{ el.text }}</span>
              </div>
              <span class="element-clicks">{{ el.count }}</span>
            </div>
          </div>
          <div v-else class="empty-inline">No element data yet.</div>
        </div>
      </div>

      <!-- AI Insights -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">🧠 AI Insights</h3>
          <button v-if="!aiInsights.length" class="btn btn-primary btn-sm" @click="fetchInsights" :disabled="insightsLoading">
            {{ insightsLoading ? 'Analyzing...' : 'Generate AI Insights' }}
          </button>
          <button v-else class="btn btn-secondary btn-sm" @click="fetchInsights" :disabled="insightsLoading">
            {{ insightsLoading ? 'Analyzing...' : 'Refresh' }}
          </button>
        </div>

        <div v-if="insightsLoading" class="insights-shimmer">
          <div class="shimmer-card" v-for="n in 3" :key="n">
            <div class="shimmer-line w70"></div>
            <div class="shimmer-line w100"></div>
            <div class="shimmer-line w50"></div>
          </div>
        </div>

        <div v-else-if="aiInsights.length" class="insights-grid">
          <div v-for="(ins, i) in aiInsights" :key="i" class="insight-card" :class="'insight-' + (ins.type || 'info')">
            <div class="insight-icon">
              <span v-if="ins.type === 'success'">✅</span>
              <span v-else-if="ins.type === 'warning'">⚠️</span>
              <span v-else-if="ins.type === 'danger'">🔴</span>
              <span v-else-if="ins.type === 'opportunity'">💡</span>
              <span v-else>📊</span>
            </div>
            <div class="insight-body">
              <div class="insight-title">{{ ins.title }}</div>
              <div class="insight-text">{{ ins.insight }}</div>
              <div v-if="ins.action" class="insight-action">→ {{ ins.action }}</div>
            </div>
          </div>
        </div>

        <div v-else class="empty-inline">Click <strong>Generate AI Insights</strong> to get actionable recommendations based on your click data.</div>
      </div>

      <!-- Click Points Table -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">📍 Click Points</h3>
          <span class="text-xs text-muted">{{ points.length }} points</span>
        </div>
        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th>Position</th>
                <th>Zone</th>
                <th>Clicks</th>
                <th>Intensity</th>
                <th>Heat</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(p, i) in points.slice(0, 15)" :key="i">
                <td class="font-mono">{{ p.x }}%, {{ p.y }}%</td>
                <td class="text-muted">{{ zoneLabel(p.y) }}</td>
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
      </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import analyticsApi from '@/api/analytics'

const props = defineProps({ websiteId: String })

const loading = ref(true)
const pages = ref([])
const selectedPage = ref('')
const points = ref([])
const totalClicks = ref(0)
const fetchError = ref(null)
const showMarkers = ref(false)
const highOpacity = ref(false)
const zones = ref([])
const topElements = ref([])
const aiInsights = ref([])
const insightsLoading = ref(false)

const viewportRef = ref(null)
const heatCanvas = ref(null)

const hottestZone = computed(() => {
  if (!points.value.length) return '--'
  return zoneLabel(points.value[0].y)
})

function zoneLabel(yPct) {
  if (yPct < 8) return 'Navigation'
  if (yPct < 25) return 'Hero / CTA'
  if (yPct < 50) return 'Content Area'
  if (yPct < 75) return 'Mid Section'
  if (yPct < 90) return 'Lower Content'
  return 'Footer'
}

function cleanUrl(url) {
  if (!url) return '--'
  try { return new URL(url).pathname } catch { return url }
}

function dotColor(intensity) {
  if (intensity < 0.2) return 'rgba(59,130,246,0.7)'
  if (intensity < 0.4) return 'rgba(34,197,94,0.7)'
  if (intensity < 0.6) return 'rgba(234,179,8,0.8)'
  if (intensity < 0.8) return 'rgba(249,115,22,0.8)'
  return 'rgba(239,68,68,0.9)'
}

function zoneColor(pct) {
  if (pct >= 40) return '#ef4444'
  if (pct >= 25) return '#f59e0b'
  if (pct >= 10) return '#22c55e'
  return '#6366f1'
}

// ── Canvas Heatmap ──
function drawHeatmap() {
  const canvas = heatCanvas.value
  const vp = viewportRef.value
  if (!canvas || !vp || !points.value.length) return

  const w = vp.offsetWidth
  const h = vp.offsetHeight
  canvas.width = w
  canvas.height = h

  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, w, h)

  // Draw radial heat blobs
  points.value.forEach(p => {
    const x = (p.x / 100) * w
    const y = (p.y / 100) * h
    const radius = 16 + p.intensity * 50
    const alpha = Math.min(1, 0.15 + p.intensity * 0.75)

    const grad = ctx.createRadialGradient(x, y, 0, x, y, radius)
    grad.addColorStop(0, `rgba(0,0,0,${alpha})`)
    grad.addColorStop(1, 'rgba(0,0,0,0)')

    ctx.globalCompositeOperation = 'lighter'
    ctx.fillStyle = grad
    ctx.beginPath()
    ctx.arc(x, y, radius, 0, Math.PI * 2)
    ctx.fill()
  })

  // Colorize
  const imgData = ctx.getImageData(0, 0, w, h)
  const px = imgData.data
  const pal = buildPalette()
  const opacity = highOpacity.value ? 0.7 : 0.45

  for (let i = 0; i < px.length; i += 4) {
    const a = px[i + 3]
    if (a === 0) continue
    const idx = Math.min(255, a)
    px[i]     = pal[idx * 4]
    px[i + 1] = pal[idx * 4 + 1]
    px[i + 2] = pal[idx * 4 + 2]
    px[i + 3] = Math.round(a * opacity)
  }
  ctx.putImageData(imgData, 0, 0)
}

function buildPalette() {
  const stops = [
    { pos: 0, r: 0, g: 0, b: 0 },
    { pos: 40, r: 0, g: 0, b: 255 },
    { pos: 85, r: 0, g: 200, b: 255 },
    { pos: 130, r: 0, g: 255, b: 100 },
    { pos: 170, r: 255, g: 255, b: 0 },
    { pos: 210, r: 255, g: 160, b: 0 },
    { pos: 240, r: 255, g: 50, b: 0 },
    { pos: 255, r: 255, g: 0, b: 0 },
  ]
  const pal = new Uint8Array(256 * 4)
  for (let i = 0; i < 256; i++) {
    let lo = stops[0], hi = stops[stops.length - 1]
    for (let c = 0; c < stops.length - 1; c++) {
      if (i >= stops[c].pos && i <= stops[c + 1].pos) { lo = stops[c]; hi = stops[c + 1]; break }
    }
    const t = (i - lo.pos) / (hi.pos - lo.pos || 1)
    pal[i * 4]     = Math.round(lo.r + (hi.r - lo.r) * t)
    pal[i * 4 + 1] = Math.round(lo.g + (hi.g - lo.g) * t)
    pal[i * 4 + 2] = Math.round(lo.b + (hi.b - lo.b) * t)
    pal[i * 4 + 3] = 255
  }
  return pal
}

async function onPageChange() {
  await fetchHeatmap()
  nextTick(() => drawHeatmap())
}

async function fetchHeatmap() {
  try {
    fetchError.value = null
    const { data } = await analyticsApi.heatmap(props.websiteId, { page: selectedPage.value })
    const d = data?.data || data
    pages.value = d.pages || []
    points.value = d.points || []
    totalClicks.value = d.total_clicks || 0
    zones.value = d.zones || []
    topElements.value = d.top_elements || []
    if (!selectedPage.value && d.selected_page) {
      selectedPage.value = d.selected_page
    }
  } catch (e) {
    console.error('Heatmap fetch error', e)
    fetchError.value = e?.response?.data?.detail || e?.message || 'Failed to load heatmap data'
  }
}

async function fetchInsights() {
  insightsLoading.value = true
  try {
    const { data } = await analyticsApi.heatmap(props.websiteId, { page: selectedPage.value, insights: 1 })
    const d = data?.data || data
    aiInsights.value = d.ai_insights || []
  } catch (e) {
    console.error('Insights fetch error', e)
  } finally {
    insightsLoading.value = false
  }
}

async function retryFetch() {
  loading.value = true
  await fetchHeatmap()
  loading.value = false
  nextTick(() => drawHeatmap())
}

let resizeTimer = null
function onResize() {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => drawHeatmap(), 200)
}

onMounted(async () => {
  await fetchHeatmap()
  loading.value = false
  nextTick(() => drawHeatmap())
  window.addEventListener('resize', onResize)
})
onUnmounted(() => window.removeEventListener('resize', onResize))
watch(points, () => nextTick(() => drawHeatmap()))
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }
.header-controls { display: flex; gap: 12px; align-items: center; flex-shrink: 0; }

/* Stats */
.heatmap-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
.stat-pill {
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg);
  padding: 14px 16px; display: flex; flex-direction: column; gap: 4px;
}
.stat-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; }
.stat-value { font-size: 20px; font-weight: 700; color: var(--text-primary); }

/* Heatmap Card */
.heatmap-card { overflow: hidden; margin-bottom: 20px; }
.heatmap-header { display: flex; align-items: center; justify-content: space-between; padding: 0 0 12px; flex-wrap: wrap; gap: 8px; }
.header-right { display: flex; align-items: center; gap: 12px; }
.heat-legend { display: flex; align-items: center; gap: 6px; }
.legend-label { font-size: 10px; color: var(--text-muted); }
.legend-gradient {
  width: 100px; height: 6px; border-radius: 20px;
  background: linear-gradient(90deg, #0000ff, #00c8ff, #00ff64, #ffff00, #ffa500, #ff3200, #ff0000);
}

/* Heatmap Viewport */
.heatmap-viewport {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-surface);
}

.wireframe-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.wf-section {
  fill: none;
  stroke: var(--text-muted);
  stroke-width: 0.3;
  stroke-dasharray: 1.5 1;
  opacity: 0.25;
}
.wf-label {
  fill: var(--text-muted);
  font-size: 2.5px;
  opacity: 0.3;
  font-family: system-ui, sans-serif;
}

.heat-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 5;
}

/* Click markers */
.click-markers { position: absolute; inset: 0; z-index: 10; pointer-events: none; }
.click-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  width: var(--dot-size);
  height: var(--dot-size);
  border-radius: 50%;
  background: var(--dot-color);
  border: 2px solid rgba(255,255,255,0.95);
  display: flex; align-items: center; justify-content: center;
  font-size: 8px; font-weight: 700; color: white;
  text-shadow: 0 1px 2px rgba(0,0,0,0.6);
  box-shadow: 0 2px 6px rgba(0,0,0,0.35);
}

/* Toolbar */
.heatmap-toolbar { display: flex; gap: 20px; padding: 10px 0 0; align-items: center; }
.hm-toggle { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--text-secondary); cursor: pointer; }
.hm-toggle input { accent-color: var(--brand-accent); }

/* Grid layout */
.hm-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }

/* Zones */
.zone-bars { display: flex; flex-direction: column; gap: 8px; }
.zone-row { display: flex; align-items: center; gap: 8px; }
.zone-name { width: 90px; font-size: 11px; font-weight: 500; color: var(--text-primary); flex-shrink: 0; }
.zone-bar-wrap { flex: 1; height: 8px; background: var(--bg-input); border-radius: 4px; overflow: hidden; }
.zone-bar-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease; min-width: 2px; }
.zone-pct { width: 34px; text-align: right; font-size: 11px; font-weight: 700; color: var(--text-primary); }
.zone-count { width: 30px; text-align: right; font-size: 10px; color: var(--text-muted); }

/* Elements */
.element-list { display: flex; flex-direction: column; }
.element-row { display: flex; align-items: center; gap: 8px; padding: 7px 0; border-bottom: 1px solid var(--border-color); }
.element-row:last-child { border-bottom: none; }
.element-rank { flex-shrink: 0; width: 26px; height: 26px; border-radius: 50%; background: var(--bg-surface); display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; color: var(--text-muted); }
.element-row:nth-child(-n+3) .element-rank { background: rgba(99,102,241,0.12); color: var(--brand-accent); }
.element-info { flex: 1; min-width: 0; overflow: hidden; }
.element-selector { font-size: 10px; font-family: 'SF Mono', 'Fira Code', monospace; color: var(--brand-accent); background: rgba(99,102,241,0.06); padding: 1px 5px; border-radius: 3px; display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.element-text { display: block; font-size: 10px; color: var(--text-muted); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.element-clicks { flex-shrink: 0; font-size: 14px; font-weight: 700; color: var(--text-primary); }

/* AI Insights */
.insights-grid { display: flex; flex-direction: column; gap: 10px; }
.insight-card { display: flex; gap: 10px; padding: 12px; border-radius: var(--radius-md); border-left: 4px solid var(--border-color); background: var(--bg-surface); }
.insight-success { border-left-color: #22c55e; }
.insight-warning { border-left-color: #f59e0b; }
.insight-danger { border-left-color: #ef4444; }
.insight-opportunity { border-left-color: #6366f1; }
.insight-info { border-left-color: #3b82f6; }
.insight-icon { font-size: 18px; flex-shrink: 0; line-height: 1; }
.insight-body { flex: 1; min-width: 0; }
.insight-title { font-size: 12px; font-weight: 700; color: var(--text-primary); margin-bottom: 3px; }
.insight-text { font-size: 11px; color: var(--text-secondary); line-height: 1.5; }
.insight-action { font-size: 10px; font-weight: 600; color: var(--brand-accent); margin-top: 4px; }

/* Shimmer */
.insights-shimmer { display: flex; flex-direction: column; gap: 10px; }
.shimmer-card { padding: 12px; border-radius: var(--radius-md); background: var(--bg-surface); display: flex; flex-direction: column; gap: 6px; }
.shimmer-line { height: 10px; border-radius: 4px; background: linear-gradient(90deg, var(--bg-input) 25%, var(--bg-surface) 50%, var(--bg-input) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
.w70 { width: 70%; } .w100 { width: 100%; } .w50 { width: 50%; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* Table */
.table-responsive { overflow-x: auto; }
.font-mono { font-family: 'SF Mono', 'Fira Code', monospace; font-size: var(--font-xs); }
.heat-bar { width: 100%; height: 6px; background: var(--bg-input); border-radius: 20px; overflow: hidden; }
.heat-bar-fill { height: 100%; border-radius: 20px; transition: width 0.5s ease; }

/* Empty */
.empty-guide { text-align: center; padding: 50px 30px; background: var(--bg-card); border: 2px dashed var(--border-color); border-radius: var(--radius-lg); }
.empty-guide-icon { font-size: 48px; margin-bottom: 12px; }
.empty-guide h3 { font-size: var(--font-lg); color: var(--text-primary); margin: 0 0 8px; }
.empty-guide p { font-size: var(--font-sm); color: var(--text-secondary); max-width: 440px; margin: 0 auto 12px; line-height: 1.5; }
.empty-guide-snippet { background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 10px 16px; display: inline-block; margin-bottom: 10px; }
.empty-guide-snippet code { font-size: var(--font-xs); color: var(--brand-accent); font-family: 'SF Mono', monospace; }
.empty-guide-hint { font-size: var(--font-xs); color: var(--text-muted); }
.empty-inline { font-size: 12px; color: var(--text-muted); padding: 16px 0; }

/* Responsive */
@media (max-width: 900px) {
  .heatmap-stats { grid-template-columns: repeat(2, 1fr); }
  .hm-grid { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .heatmap-stats { grid-template-columns: 1fr; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 12px; }
  .header-controls select { min-width: 100% !important; max-width: 100% !important; }
  .heatmap-viewport { aspect-ratio: 4 / 3; }
}
</style>
