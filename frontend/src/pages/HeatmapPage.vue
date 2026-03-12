<template>
  <div class="heatmap-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Click Heatmap</h1>
        <p class="page-subtitle">See where visitors click on your pages.</p>
      </div>
      <div class="header-controls">
        <select v-model="selectedPage" class="form-input" style="min-width:280px" @change="onPageChange">
          <option v-for="p in pages" :key="p.url" :value="p.url">{{ cleanUrl(p.url) }} ({{ p.click_count }} clicks)</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="loading-state">Loading heatmap data...</div>
    <template v-else>
      <!-- Empty State -->
      <div v-if="!pages.length" class="empty-guide">
        <div class="empty-guide-icon">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="var(--brand-accent)" stroke-width="1.5">
            <rect x="6" y="6" width="36" height="36" rx="4"/>
            <circle cx="18" cy="20" r="4" fill="rgba(91,141,239,0.3)"/>
            <circle cx="30" cy="16" r="6" fill="rgba(239,68,68,0.3)"/>
            <circle cx="24" cy="32" r="5" fill="rgba(234,179,8,0.3)"/>
            <circle cx="36" cy="28" r="3" fill="rgba(34,197,94,0.3)"/>
          </svg>
        </div>
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

        <div class="heatmap-viewport" ref="viewportRef">
          <!-- Iframe of the actual page -->
          <iframe
            v-if="selectedPage"
            :src="selectedPage"
            class="heatmap-iframe"
            sandbox="allow-same-origin"
            loading="lazy"
            tabindex="-1"
            @load="onIframeLoad"
          ></iframe>
          <div v-if="iframeLoading" class="iframe-loader">Loading page preview...</div>

          <!-- Canvas heat overlay -->
          <canvas ref="heatCanvas" class="heat-overlay"></canvas>

          <!-- Click markers for detail -->
          <div v-if="showMarkers" class="click-markers">
            <div
              v-for="(p, i) in points.slice(0, 30)" :key="i"
              class="click-marker"
              :style="{
                left: p.x + '%',
                top: p.y + '%',
                '--dot-size': (6 + p.intensity * 14) + 'px',
                '--dot-color': dotColor(p.intensity),
              }"
              :title="'Clicks: ' + p.count"
            >{{ p.count }}</div>
          </div>
        </div>

        <!-- Toolbar -->
        <div class="heatmap-toolbar">
          <label class="hm-toggle">
            <input type="checkbox" v-model="showMarkers" /> Show click counts
          </label>
          <label class="hm-toggle">
            <input type="checkbox" v-model="heatOpacity" :true-value="0.65" :false-value="0.4" @change="drawHeatmap" /> More visible
          </label>
        </div>
      </div>

      <!-- Top Click Zones Table -->
      <div class="card" style="margin-top:20px">
        <div class="card-header">
          <h3 class="card-title">Top Click Zones</h3>
          <span class="text-xs text-muted">{{ points.length }} aggregated points</span>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>Position (X%, Y%)</th>
              <th>Zone</th>
              <th>Clicks</th>
              <th>Intensity</th>
              <th>Heat</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(p, i) in points.slice(0, 20)" :key="i">
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
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import analyticsApi from '@/api/analytics'

const props = defineProps({ websiteId: String })

const loading = ref(true)
const pages = ref([])
const selectedPage = ref('')
const points = ref([])
const totalClicks = ref(0)
const fetchError = ref(null)
const showMarkers = ref(false)
const heatOpacity = ref(0.4)
const iframeLoading = ref(true)

const viewportRef = ref(null)
const heatCanvas = ref(null)

const hottestZone = computed(() => {
  if (!points.value.length) return '--'
  const top = points.value[0]
  return zoneLabel(top.y)
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

// ── Gaussian Heatmap Rendering ──
function drawHeatmap() {
  const canvas = heatCanvas.value
  const viewport = viewportRef.value
  if (!canvas || !viewport || !points.value.length) return

  const w = viewport.offsetWidth
  const h = viewport.offsetHeight
  canvas.width = w
  canvas.height = h

  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, w, h)

  // Step 1: draw grayscale heat blobs (additive alpha)
  points.value.forEach(p => {
    const x = (p.x / 100) * w
    const y = (p.y / 100) * h
    const radius = 20 + p.intensity * 40
    const alpha = Math.min(1, 0.15 + p.intensity * 0.7)

    const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius)
    gradient.addColorStop(0, `rgba(0,0,0,${alpha})`)
    gradient.addColorStop(1, 'rgba(0,0,0,0)')

    ctx.globalCompositeOperation = 'lighter'
    ctx.fillStyle = gradient
    ctx.beginPath()
    ctx.arc(x, y, radius, 0, Math.PI * 2)
    ctx.fill()
  })

  // Step 2: colorize with gradient palette
  const imageData = ctx.getImageData(0, 0, w, h)
  const pixels = imageData.data
  const palette = buildPalette()

  for (let i = 0; i < pixels.length; i += 4) {
    const alpha = pixels[i + 3] // grayscale alpha = heat intensity
    if (alpha === 0) continue

    const idx = Math.min(255, alpha)
    pixels[i] = palette[idx * 4]       // R
    pixels[i + 1] = palette[idx * 4 + 1] // G
    pixels[i + 2] = palette[idx * 4 + 2] // B
    pixels[i + 3] = Math.round(alpha * heatOpacity.value) // final opacity
  }

  ctx.putImageData(imageData, 0, 0)
}

function buildPalette() {
  // blue → cyan → green → yellow → orange → red
  const colors = [
    { pos: 0, r: 0, g: 0, b: 0 },
    { pos: 45, r: 0, g: 0, b: 255 },
    { pos: 90, r: 0, g: 200, b: 255 },
    { pos: 130, r: 0, g: 255, b: 100 },
    { pos: 170, r: 255, g: 255, b: 0 },
    { pos: 210, r: 255, g: 165, b: 0 },
    { pos: 240, r: 255, g: 50, b: 0 },
    { pos: 255, r: 255, g: 0, b: 0 },
  ]

  const palette = new Uint8Array(256 * 4)
  for (let i = 0; i < 256; i++) {
    let lower = colors[0], upper = colors[colors.length - 1]
    for (let c = 0; c < colors.length - 1; c++) {
      if (i >= colors[c].pos && i <= colors[c + 1].pos) {
        lower = colors[c]
        upper = colors[c + 1]
        break
      }
    }
    const range = upper.pos - lower.pos || 1
    const t = (i - lower.pos) / range
    palette[i * 4] = Math.round(lower.r + (upper.r - lower.r) * t)
    palette[i * 4 + 1] = Math.round(lower.g + (upper.g - lower.g) * t)
    palette[i * 4 + 2] = Math.round(lower.b + (upper.b - lower.b) * t)
    palette[i * 4 + 3] = 255
  }
  return palette
}

function onIframeLoad() {
  iframeLoading.value = false
  nextTick(() => drawHeatmap())
}

async function onPageChange() {
  iframeLoading.value = true
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
    if (!selectedPage.value && d.selected_page) {
      selectedPage.value = d.selected_page
    }
  } catch (e) {
    console.error('Heatmap fetch error', e)
    fetchError.value = e?.response?.data?.detail || e?.message || 'Failed to load heatmap data'
  }
}

async function retryFetch() {
  loading.value = true
  await fetchHeatmap()
  loading.value = false
  nextTick(() => drawHeatmap())
}

// Redraw on window resize
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

watch(points, () => nextTick(() => drawHeatmap()))
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
  background: linear-gradient(90deg, #0000ff, #00c8ff, #00ff64, #ffff00, #ffa500, #ff3200, #ff0000);
}

/* Heatmap Viewport — page preview + heat overlay */
.heatmap-viewport {
  position: relative;
  width: 100%;
  height: 600px;
  overflow: hidden;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-surface);
}

.heatmap-iframe {
  position: absolute;
  top: 0; left: 0;
  width: 1440px;
  height: 900px;
  transform: scale(0.7);
  transform-origin: top left;
  border: none;
  pointer-events: none;
  opacity: 0.85;
}

.iframe-loader {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  font-size: var(--font-sm);
  color: var(--text-muted);
  z-index: 1;
}

.heat-overlay {
  position: absolute;
  top: 0; left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 5;
}

/* Click markers */
.click-markers {
  position: absolute;
  top: 0; left: 0;
  width: 100%;
  height: 100%;
  z-index: 10;
  pointer-events: none;
}

.click-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  width: var(--dot-size);
  height: var(--dot-size);
  border-radius: 50%;
  background: var(--dot-color);
  border: 2px solid rgba(255,255,255,0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 8px;
  font-weight: 700;
  color: white;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

/* Toolbar */
.heatmap-toolbar {
  display: flex; gap: 20px; padding: 12px 0 0; align-items: center;
}
.hm-toggle {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--text-secondary); cursor: pointer;
}
.hm-toggle input { accent-color: var(--brand-accent); }

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
  .heatmap-viewport { height: 400px; }
  .heatmap-iframe { width: 1024px; height: 768px; transform: scale(0.4); }
}
</style>
