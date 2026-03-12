<template>
  <div class="keywords-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Keyword Intelligence</h1>
        <p class="page-subtitle">AI-powered keyword scanning, ranking, and SEO insights.</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-primary" @click="runScan" :disabled="scanLoading">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.22-8.56"/><path d="M21 3v5h-5"/></svg>
          {{ scanLoading ? 'Scanning...' : 'Scan Website' }}
        </button>
        <button class="btn-add-card" @click="showCardPicker = true" title="Add a card">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">Loading...</div>
    <template v-else>

    <!-- Empty State -->
    <div v-if="!activeCards.length && !scanData.score && !keywords.length" class="empty-guide">
      <div class="empty-guide-icon">📊</div>
      <h3>Build your SEO dashboard</h3>
      <p>Click the <strong>+</strong> button to add feature cards, or <strong>Scan Website</strong> to start analyzing your SEO.</p>
    </div>

    <!-- Active Cards -->
    <div class="cards-grid">
      <template v-for="cardId in activeCards" :key="cardId">

        <!-- Site Audit -->
        <div v-if="cardId === 'site_audit'" class="card feature-card">
          <div class="fc-head">
            <div class="fc-icon">🔍</div>
            <div class="fc-title-wrap"><h3 class="fc-title">Site Audit</h3><p class="fc-sub">Audit your site for visibility blockers</p></div>
            <button class="fc-remove" @click="removeCard(cardId)" title="Remove">×</button>
          </div>
          <div v-if="scanData.score != null" class="fc-body">
            <div class="fc-stat-row">
              <div class="fc-stat"><span class="fc-stat-val" :style="{color: scanData.score >= 70 ? '#22c55e' : scanData.score >= 40 ? '#f59e0b' : '#ef4444'}">{{ scanData.score }}/100</span><span class="fc-stat-lbl">Health Score</span></div>
              <div class="fc-stat"><span class="fc-stat-val">{{ scanData.pages_scanned || 1 }}</span><span class="fc-stat-lbl">Pages Scanned</span></div>
              <div class="fc-stat"><span class="fc-stat-val">{{ scanData.page_meta?.word_count?.toLocaleString() || 0 }}</span><span class="fc-stat-lbl">Total Words</span></div>
            </div>
            <div class="fc-breakdown" v-if="scanData.score_breakdown">
              <div v-for="(comp, key) in scanData.score_breakdown" :key="key" v-if="comp && comp.label" class="fc-br-row">
                <span class="fc-br-name">{{ comp.label }}</span>
                <div class="fc-br-bar"><div class="fc-br-fill" :style="{ width: comp.score + '%' }" :class="comp.score >= 70 ? 'b-good' : comp.score >= 40 ? 'b-mid' : 'b-bad'"></div></div>
                <span class="fc-br-num">{{ comp.score }}</span>
              </div>
            </div>
          </div>
          <div v-else class="fc-empty">Click <strong>Scan Website</strong> to audit your site for 140+ SEO issues and get your health score.</div>
        </div>

        <!-- Keyword Research -->
        <div v-if="cardId === 'keyword_research'" class="card feature-card">
          <div class="fc-head">
            <div class="fc-icon">🔑</div>
            <div class="fc-title-wrap"><h3 class="fc-title">Keyword Research</h3><p class="fc-sub">Target the best keywords with AI</p></div>
            <button class="fc-remove" @click="removeCard(cardId)" title="Remove">×</button>
          </div>
          <div v-if="scanData.keywords?.length" class="fc-body">
            <div class="split-screen">
              <div class="split-left">
                <div class="split-label">Page Content <span class="text-xs text-muted">— keywords highlighted</span></div>
                <div class="page-preview" v-html="highlightedContent"></div>
              </div>
              <div class="split-right">
                <div class="split-label">Detected Keywords</div>
                <div class="kw-found-list">
                  <div v-for="(k, i) in scanData.keywords.slice(0, 10)" :key="i" class="kw-found-item">
                    <span class="kw-found-rank">#{{ i + 1 }}</span>
                    <div class="kw-found-info">
                      <span class="kw-found-word" :class="'kw-hl-' + (i < 3 ? 'hot' : i < 7 ? 'warm' : 'cool')">{{ k.keyword }}</span>
                      <div class="kw-found-meta">
                        <span>{{ k.density }}%</span>
                        <span v-if="scanData.trends?.[k.keyword]">{{ scanData.trends[k.keyword].interest }}/100</span>
                        <span v-for="l in k.locations" :key="l" class="seo-loc-tag">{{ l }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="fc-empty">Discover keyword ideas your site can win. Analyze search volume, difficulty, and intent.</div>
        </div>

        <!-- AI Analysis -->
        <div v-if="cardId === 'ai_analysis'" class="card feature-card">
          <div class="fc-head">
            <div class="fc-icon">🤖</div>
            <div class="fc-title-wrap"><h3 class="fc-title">AI Analysis</h3><p class="fc-sub">Measure and grow your AI visibility</p></div>
            <button class="fc-remove" @click="removeCard(cardId)" title="Remove">×</button>
          </div>
          <div v-if="scanData.ai_rankings && Object.keys(scanData.ai_rankings).length" class="fc-body">
            <div class="ai-engine-grid">
              <div v-for="engine in ['claude', 'chatgpt', 'perplexity']" :key="engine" v-if="scanData.ai_rankings[engine]" class="ai-engine-card" :class="scanData.ai_rankings[engine].mentioned ? 'aec-found' : 'aec-missing'">
                <div class="aec-header">
                  <div class="aec-name">{{ engine === 'chatgpt' ? 'ChatGPT' : engine.charAt(0).toUpperCase() + engine.slice(1) }}</div>
                  <div class="aec-score-circle" :class="scanData.ai_rankings[engine].score >= 40 ? 'asc-good' : scanData.ai_rankings[engine].score > 0 ? 'asc-mid' : 'asc-none'">{{ scanData.ai_rankings[engine].score }}</div>
                </div>
                <div class="aec-status" :class="scanData.ai_rankings[engine].mentioned ? 'ast-found' : 'ast-missing'">
                  {{ scanData.ai_rankings[engine].mentioned ? '✓ Found' : '✗ Not mentioned' }}
                </div>
                <div v-if="scanData.ai_rankings[engine].excerpt" class="aec-excerpt">{{ scanData.ai_rankings[engine].excerpt }}</div>
              </div>
            </div>
          </div>
          <div v-else class="fc-empty">Track AI Visibility Scores across Claude, ChatGPT, and Perplexity. See which prompts mention your brand.</div>
        </div>

        <!-- Competitive Research -->
        <div v-if="cardId === 'competitive'" class="card feature-card">
          <div class="fc-head">
            <div class="fc-icon">⚔️</div>
            <div class="fc-title-wrap"><h3 class="fc-title">Competitive Research</h3><p class="fc-sub">Outperform your competitors</p></div>
            <button class="fc-remove" @click="removeCard(cardId)" title="Remove">×</button>
          </div>
          <div v-if="scanData.dataforseo?.some(e => e.top_competitors?.length)" class="fc-body">
            <div class="comp-grid">
              <div v-for="e in scanData.dataforseo.filter(x => x.top_competitors?.length).slice(0, 4)" :key="e.keyword" class="comp-kw-section">
                <div class="comp-kw-name">{{ e.keyword }}</div>
                <div v-for="c in e.top_competitors.slice(0, 3)" :key="c.position" class="comp-row">
                  <span class="comp-pos">#{{ c.position }}</span>
                  <span class="comp-domain">{{ c.domain }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="fc-empty">Compare your site against top competitors. Claim keywords and topics driving their traffic.</div>
        </div>

        <!-- Content Ideas -->
        <div v-if="cardId === 'content_ideas'" class="card feature-card">
          <div class="fc-head">
            <div class="fc-icon">💡</div>
            <div class="fc-title-wrap"><h3 class="fc-title">Content Ideas</h3><p class="fc-sub">Optimize content for full search coverage</p></div>
            <button class="fc-remove" @click="removeCard(cardId)" title="Remove">×</button>
          </div>
          <div v-if="scanData.suggestions?.length" class="fc-body">
            <div class="alt-grid">
              <div v-for="(s, i) in scanData.suggestions.slice(0, 6)" :key="i" class="alt-card">
                <div class="alt-original">{{ s.original }}</div>
                <div class="alt-arrow">→</div>
                <div class="alt-new">{{ s.suggested }}</div>
                <div class="alt-delta">+{{ s.improvement }}</div>
              </div>
            </div>
          </div>
          <div v-else class="fc-empty">Uncover trending topics and real user questions. Strengthen your copy with actionable ideas.</div>
        </div>

        <!-- Position Tracking -->
        <div v-if="cardId === 'position_tracking'" class="card feature-card">
          <div class="fc-head">
            <div class="fc-icon">📍</div>
            <div class="fc-title-wrap"><h3 class="fc-title">Position Tracking</h3><p class="fc-sub">Monitor visibility in Google and AI</p></div>
            <button class="fc-remove" @click="removeCard(cardId)" title="Remove">×</button>
          </div>
          <div class="fc-body">
            <div class="fc-stat-row" style="margin-bottom:12px">
              <div class="fc-stat"><span class="fc-stat-val">{{ keywords.length }}</span><span class="fc-stat-lbl">Tracked</span></div>
              <div class="fc-stat"><span class="fc-stat-val">{{ avgPosition }}</span><span class="fc-stat-lbl">Avg Position</span></div>
              <div class="fc-stat"><span class="fc-stat-val" style="color:#22c55e">{{ improved }}</span><span class="fc-stat-lbl">Improved</span></div>
              <div class="fc-stat"><span class="fc-stat-val" style="color:#ef4444">{{ declined }}</span><span class="fc-stat-lbl">Declined</span></div>
            </div>
            <div v-if="keywords.length" class="table-responsive">
              <table class="data-table data-table-sm">
                <thead><tr><th>Keyword</th><th class="text-center">Pos</th><th class="text-center">Vol</th><th class="text-center">Diff</th></tr></thead>
                <tbody>
                  <tr v-for="kw in keywords.slice(0, 8)" :key="kw.id">
                    <td><div class="kw-name">{{ kw.keyword }}</div></td>
                    <td class="text-center"><span class="rank-badge" :class="rankClass(kw.current_rank)">{{ kw.current_rank || '--' }}</span></td>
                    <td class="text-center">{{ (kw.search_volume || 0).toLocaleString() }}</td>
                    <td class="text-center">{{ kw.difficulty || '--' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <button class="btn btn-secondary btn-sm" style="margin-top:8px" @click="showAddModal = true">+ Track Keyword</button>
          </div>
        </div>

        <!-- SERP Data (DataForSEO) -->
        <div v-if="cardId === 'serp_data'" class="card feature-card">
          <div class="fc-head">
            <div class="fc-icon">🔎</div>
            <div class="fc-title-wrap"><h3 class="fc-title">Google SERP Data</h3><p class="fc-sub">Real-time rankings via DataForSEO</p></div>
            <button class="fc-remove" @click="removeCard(cardId)" title="Remove">×</button>
          </div>
          <div v-if="scanData.dataforseo?.length" class="fc-body">
            <div class="serp-grid">
              <div v-for="e in scanData.dataforseo.slice(0, 6)" :key="e.keyword" class="serp-card">
                <div class="serp-card-head">
                  <div class="serp-kw">{{ e.keyword }}</div>
                  <span v-if="e.position" class="rank-badge" :class="rankClass(e.position)">#{{ e.position }}</span>
                  <span v-else class="rank-badge rank-low">—</span>
                </div>
                <div class="serp-metrics">
                  <div class="serp-metric"><span class="sm-label">Vol</span><span class="sm-value">{{ (e.volume || 0).toLocaleString() }}</span></div>
                  <div class="serp-metric"><span class="sm-label">CPC</span><span class="sm-value">${{ (e.cpc || 0).toFixed(2) }}</span></div>
                  <div class="serp-metric"><span class="sm-label">Diff</span><span class="sm-value">{{ e.difficulty || 0 }}</span></div>
                </div>
                <div v-if="e.serp_features?.length" class="serp-features">
                  <span v-for="f in e.serp_features.slice(0, 5)" :key="f" class="serp-feat-tag">{{ formatFeature(f) }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="fc-body">
            <div class="setup-steps">
              <p class="setup-intro">Connect <strong>DataForSEO</strong> for real Google rankings, volume, CPC, and difficulty:</p>
              <div class="setup-step"><span class="step-num">1</span><div class="step-text">Sign up at <a href="https://dataforseo.com" target="_blank">dataforseo.com</a></div></div>
              <div class="setup-step"><span class="step-num">2</span><div class="step-text">Dashboard → API Access → get login & password</div></div>
              <div class="setup-step"><span class="step-num">3</span><div class="step-text">Add <code>DATAFORSEO_LOGIN</code> and <code>DATAFORSEO_PASSWORD</code> to <code>.env.prod</code></div></div>
              <div class="setup-step"><span class="step-num">4</span><div class="step-text">Restart server & re-scan</div></div>
            </div>
          </div>
        </div>

        <!-- Geo SEO -->
        <div v-if="cardId === 'geo_seo'" class="card feature-card">
          <div class="fc-head">
            <div class="fc-icon">🌍</div>
            <div class="fc-title-wrap"><h3 class="fc-title">Geo SEO & Tagging</h3><p class="fc-sub">Regional optimization</p></div>
            <button class="fc-remove" @click="removeCard(cardId)" title="Remove">×</button>
          </div>
          <div v-if="scanData.geo_data" class="fc-body">
            <div class="geo-tag-status" :class="scanData.geo_data.has_geo_tags ? 'gts-found' : 'gts-missing'">
              {{ scanData.geo_data.has_geo_tags ? '✓ Geo Tags Found' : '✗ No Geo Tags Detected' }}
            </div>
            <div v-for="(tip, i) in (scanData.geo_data.tips || [])" :key="i" class="geo-tip-card" :class="'gt-' + tip.type" style="margin-top:6px">
              <span class="gt-icon">{{ tip.type === 'success' ? '✅' : tip.type === 'warning' ? '⚠️' : 'ℹ️' }}</span>
              <div class="gt-body">
                <div class="gt-text">{{ tip.tip }}</div>
                <code v-if="tip.tag" class="gt-tag">{{ tip.tag }}</code>
              </div>
            </div>
          </div>
          <div v-else class="fc-empty">Scan your site to detect hreflang, og:locale, and geo meta tags.</div>
        </div>

        <!-- Pages Scanned -->
        <div v-if="cardId === 'pages_scanned'" class="card feature-card">
          <div class="fc-head">
            <div class="fc-icon">📑</div>
            <div class="fc-title-wrap"><h3 class="fc-title">Pages Scanned</h3><p class="fc-sub">Per-page keyword breakdown</p></div>
            <button class="fc-remove" @click="removeCard(cardId)" title="Remove">×</button>
          </div>
          <div v-if="scanData.per_page?.length" class="fc-body">
            <div class="pages-list">
              <div v-for="(pg, i) in scanData.per_page" :key="i" class="page-row">
                <div class="page-row-left">
                  <span class="page-num">{{ i + 1 }}</span>
                  <div class="page-info">
                    <a :href="pg.url" target="_blank" class="page-url">{{ cleanPagePath(pg.url) }}</a>
                    <div class="page-title-text">{{ pg.title || 'Untitled' }}</div>
                  </div>
                </div>
                <div class="page-row-right">
                  <span class="page-stat">{{ pg.word_count }} words</span>
                  <span class="page-stat">{{ pg.keyword_count }} kw</span>
                </div>
                <div class="page-kws">
                  <span v-for="kw in pg.top_keywords.slice(0, 4)" :key="kw" class="page-kw-chip">{{ kw }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="fc-empty">Scan your website to see which pages were crawled and what keywords each page targets.</div>
        </div>

        <!-- Dynamic SEO Optimizer -->
        <div v-if="cardId === 'seo_optimizer'" class="card feature-card fc-highlight">
          <div class="fc-head">
            <div class="fc-icon">⚡</div>
            <div class="fc-title-wrap"><h3 class="fc-title">Dynamic SEO Optimizer</h3><p class="fc-sub">Auto-optimize your live website</p></div>
            <button class="fc-remove" @click="removeCard(cardId)" title="Remove">×</button>
          </div>
          <div class="fc-body">
            <div v-if="embedCode" class="embed-section">
              <div class="embed-label">Paste this in your website's <code>&lt;head&gt;</code>:</div>
              <div class="embed-code-wrap">
                <pre class="embed-code">{{ embedCode }}</pre>
                <button class="embed-copy" @click="copyEmbed" :class="{ copied: embedCopied }">{{ embedCopied ? '✓ Copied' : 'Copy' }}</button>
              </div>
              <div class="embed-features">
                <div class="ef-title">What it auto-optimizes:</div>
                <div class="ef-list">
                  <span class="ef-item">✓ Schema markup (JSON-LD)</span>
                  <span class="ef-item">✓ Open Graph tags</span>
                  <span class="ef-item">✓ Canonical URLs</span>
                  <span class="ef-item">✓ hreflang tags</span>
                  <span class="ef-item">✓ Geo meta tags</span>
                  <span class="ef-item">✓ Title & meta optimization</span>
                </div>
              </div>
            </div>
            <div v-else class="fc-empty">Loading embed code...</div>
          </div>
        </div>

      </template>
    </div>

    </template>

    <!-- Card Picker Modal -->
    <Teleport to="body">
      <div v-if="showCardPicker" class="modal-overlay" @click.self="showCardPicker = false">
        <div class="modal-card modal-picker">
          <h3 class="modal-title">Add a Card</h3>
          <div class="picker-grid">
            <div v-for="card in availableCards" :key="card.id" class="picker-item" :class="{ 'pi-active': activeCards.includes(card.id) }" @click="toggleCard(card.id)">
              <div class="pi-icon">{{ card.icon }}</div>
              <div class="pi-info">
                <div class="pi-name">{{ card.name }}</div>
                <div class="pi-desc">{{ card.desc }}</div>
              </div>
              <div class="pi-check">{{ activeCards.includes(card.id) ? '✓' : '+' }}</div>
            </div>
          </div>
          <div class="modal-actions"><button class="btn btn-primary" @click="showCardPicker = false">Done</button></div>
        </div>
      </div>
    </Teleport>

    <!-- Add Keyword Modal -->
    <Teleport to="body">
      <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
        <div class="modal-card">
          <h3 class="modal-title">Track Keyword</h3>
          <div class="modal-body">
            <label class="form-label">Keyword</label>
            <input v-model="newKw.keyword" class="form-input" placeholder="e.g. modest fashion" autofocus />
            <label class="form-label" style="margin-top:12px">Target URL (optional)</label>
            <input v-model="newKw.target_url" class="form-input" placeholder="https://..." />
            <p v-if="addError" class="text-danger text-sm" style="margin-top:8px">{{ addError }}</p>
          </div>
          <div class="modal-actions">
            <button class="btn btn-secondary" @click="showAddModal = false">Cancel</button>
            <button class="btn btn-primary" @click="addKeyword" :disabled="adding">{{ adding ? 'Adding...' : 'Add' }}</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import analyticsApi from '@/api/analytics'

const props = defineProps({ websiteId: String })

const loading = ref(true)
const keywords = ref([])
const showAddModal = ref(false)
const showCardPicker = ref(false)
const adding = ref(false)
const addError = ref('')
const newKw = ref({ keyword: '', target_url: '' })
const scanData = ref({})
const scanLoading = ref(false)

// Card system
const STORAGE_KEY = 'ftb_kw_cards'
const availableCards = [
  { id: 'site_audit', name: 'Site Audit', desc: 'Scan for SEO issues and get your health score', icon: '🔍' },
  { id: 'keyword_research', name: 'Keyword Research', desc: 'Discover keyword ideas with search volume and difficulty', icon: '🔑' },
  { id: 'ai_analysis', name: 'AI Analysis', desc: 'Track your visibility across AI engines', icon: '🤖' },
  { id: 'competitive', name: 'Competitive Research', desc: 'Compare your site against top competitors', icon: '⚔️' },
  { id: 'content_ideas', name: 'Content Ideas', desc: 'Find trending topics and keyword alternatives', icon: '💡' },
  { id: 'position_tracking', name: 'Position Tracking', desc: 'Monitor keyword rankings in Google and AI', icon: '📍' },
  { id: 'serp_data', name: 'Google SERP Data', desc: 'Real rankings, volume, CPC via DataForSEO', icon: '🔎' },
  { id: 'geo_seo', name: 'Geo SEO & Tagging', desc: 'Regional optimization and geo tag detection', icon: '🌍' },
  { id: 'seo_optimizer', name: 'Dynamic SEO Optimizer', desc: 'Auto-optimize schema, OG, canonical on your live site', icon: '⚡' },
  { id: 'pages_scanned', name: 'Pages Scanned', desc: 'Per-page keyword breakdown', icon: '📑' },
]

const defaultCards = ['site_audit', 'keyword_research', 'position_tracking', 'ai_analysis']
const activeCards = ref([...defaultCards])

const embedCode = ref('')
const embedCopied = ref(false)

function loadCards() {
  try { const saved = localStorage.getItem(STORAGE_KEY); if (saved) activeCards.value = JSON.parse(saved) } catch {}
}
function saveCards() { localStorage.setItem(STORAGE_KEY, JSON.stringify(activeCards.value)) }
function toggleCard(id) {
  const idx = activeCards.value.indexOf(id)
  if (idx >= 0) activeCards.value.splice(idx, 1)
  else activeCards.value.push(id)
  saveCards()
}
function removeCard(id) { activeCards.value = activeCards.value.filter(c => c !== id); saveCards() }
watch(activeCards, saveCards, { deep: true })

const avgPosition = computed(() => {
  const ranked = keywords.value.filter(k => k.current_rank)
  if (!ranked.length) return '--'
  return Math.round(ranked.reduce((s, k) => s + k.current_rank, 0) / ranked.length)
})
const improved = computed(() => keywords.value.filter(k => k.rank_change > 0).length)
const declined = computed(() => keywords.value.filter(k => k.rank_change < 0).length)

function cleanUrl(url) { if (!url) return ''; try { return new URL(url).pathname } catch { return url } }
function cleanPagePath(url) { if (!url) return url; try { const u = new URL(url); return u.pathname === '/' ? '/ (Homepage)' : u.pathname } catch { return url } }
function rankClass(rank) { if (!rank) return ''; if (rank <= 3) return 'rank-top3'; if (rank <= 10) return 'rank-top10'; if (rank <= 20) return 'rank-top20'; return 'rank-low' }
function diffClass(d) { if (d < 30) return 'diff-easy'; if (d < 60) return 'diff-medium'; return 'diff-hard' }
function formatFeature(f) {
  const map = { organic: 'Organic', paid: 'Ads', featured_snippet: 'Featured', people_also_ask: 'PAA', local_pack: 'Local', images: 'Images', video: 'Video', knowledge_graph: 'KG', carousel: 'Carousel', shopping: 'Shopping' }
  return map[f] || f.replace(/_/g, ' ')
}

const highlightedContent = computed(() => {
  const meta = scanData.value?.page_meta
  if (!meta) return ''
  const kws = (scanData.value.keywords || []).map(k => k.keyword)
  let html = ''
  if (meta.title) html += `<div class="pv-section"><span class="pv-tag">TITLE</span> ${highlightWords(meta.title, kws)}</div>`
  if (meta.meta_description) html += `<div class="pv-section"><span class="pv-tag">META</span> ${highlightWords(meta.meta_description, kws)}</div>`
  if (meta.h1?.length) meta.h1.forEach(h => { html += `<div class="pv-section"><span class="pv-tag">H1</span> <strong>${highlightWords(h, kws)}</strong></div>` })
  if (meta.h2?.length) meta.h2.slice(0, 4).forEach(h => { html += `<div class="pv-section"><span class="pv-tag">H2</span> ${highlightWords(h, kws)}</div>` })
  return html || '<div class="text-muted">No page content extracted.</div>'
})

function highlightWords(text, keywords) {
  if (!text || !keywords.length) return text
  const escaped = keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const regex = new RegExp(`\\b(${escaped.join('|')})\\b`, 'gi')
  return text.replace(regex, '<mark class="kw-highlight">$1</mark>')
}

async function fetchKeywords() {
  try { const { data } = await analyticsApi.keywords(props.websiteId); keywords.value = (data?.data || data || []).map(k => ({ ...k, _history: null })) } catch (e) { console.error('Keywords fetch error', e) }
}

async function runScan() {
  scanLoading.value = true
  try { const res = await analyticsApi.keywordScanTrigger(props.websiteId); scanData.value = res.data?.data || res.data || {}; await fetchKeywords() } catch (e) { scanData.value = { error: 'Scan failed.' } }
  finally { scanLoading.value = false }
}

async function addKeyword() {
  if (!newKw.value.keyword.trim()) return
  adding.value = true; addError.value = ''
  try { await analyticsApi.addKeyword(props.websiteId, { keyword: newKw.value.keyword.trim(), target_url: newKw.value.target_url }); await fetchKeywords(); showAddModal.value = false; newKw.value = { keyword: '', target_url: '' } }
  catch (e) { addError.value = e?.response?.data?.error || 'Failed to add keyword' }
  finally { adding.value = false }
}

onMounted(async () => {
  loadCards()
  await fetchKeywords()
  try { const res = await analyticsApi.keywordScan(props.websiteId); const d = res.data?.data || res.data || {}; if (d.score != null) scanData.value = d } catch (e) {}
  // Fetch embed code
  try { const res = await analyticsApi.seoEmbed(props.websiteId); embedCode.value = res.data?.data?.embed_code || '' } catch (e) {}
  loading.value = false
})

function copyEmbed() {
  navigator.clipboard.writeText(embedCode.value)
  embedCopied.value = true
  setTimeout(() => embedCopied.value = false, 2000)
}
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }

.header-actions { display: flex; gap: 8px; align-items: center; }
.btn-add-card { width: 36px; height: 36px; border-radius: 50%; border: 2px solid var(--border-color); background: var(--bg-card); color: var(--text-primary); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.15s; }
.btn-add-card:hover { border-color: var(--brand-accent); color: var(--brand-accent); background: rgba(99,102,241,0.06); }

/* Cards Grid */
.cards-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.feature-card { overflow: hidden; }
.fc-head { display: flex; align-items: flex-start; gap: 10px; padding-bottom: 12px; border-bottom: 1px solid var(--border-color); margin-bottom: 12px; }
.fc-icon { font-size: 20px; flex-shrink: 0; margin-top: 2px; }
.fc-title-wrap { flex: 1; min-width: 0; }
.fc-title { font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 0; }
.fc-sub { font-size: 11px; color: var(--text-muted); margin: 2px 0 0; }
.fc-remove { width: 24px; height: 24px; border: none; background: transparent; color: var(--text-muted); font-size: 18px; cursor: pointer; border-radius: 4px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.fc-remove:hover { background: rgba(239,68,68,0.1); color: #ef4444; }
.fc-body { min-height: 60px; }
.fc-empty { font-size: 12px; color: var(--text-muted); line-height: 1.5; padding: 16px 0; }

/* Feature Card Stats */
.fc-stat-row { display: flex; gap: 8px; flex-wrap: wrap; }
.fc-stat { flex: 1; min-width: 60px; text-align: center; padding: 8px 4px; background: var(--bg-surface); border-radius: var(--radius-md); }
.fc-stat-val { display: block; font-size: 18px; font-weight: 800; color: var(--text-primary); line-height: 1.2; }
.fc-stat-lbl { display: block; font-size: 9px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.03em; margin-top: 2px; }

/* Breakdown bars */
.fc-breakdown { margin-top: 12px; display: flex; flex-direction: column; gap: 4px; }
.fc-br-row { display: flex; align-items: center; gap: 6px; }
.fc-br-name { width: 100px; font-size: 10px; color: var(--text-secondary); flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fc-br-bar { flex: 1; height: 5px; background: var(--bg-input); border-radius: 3px; overflow: hidden; }
.fc-br-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
.b-good { background: #22c55e; } .b-mid { background: #f59e0b; } .b-bad { background: #ef4444; }
.fc-br-num { width: 20px; text-align: right; font-size: 10px; font-weight: 700; color: var(--text-primary); }

/* Split Screen */
.split-screen { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.split-left, .split-right { background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 10px; overflow: hidden; }
.split-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-primary); margin-bottom: 8px; }
.page-preview { font-size: 11px; color: var(--text-secondary); line-height: 1.6; max-height: 250px; overflow-y: auto; }
.page-preview :deep(.pv-section) { padding: 5px 8px; margin-bottom: 4px; background: var(--bg-card); border-radius: var(--radius-md); border-left: 3px solid var(--border-color); }
.page-preview :deep(.pv-tag) { display: inline-block; font-size: 8px; font-weight: 800; color: white; background: var(--brand-accent); padding: 1px 4px; border-radius: 2px; margin-right: 4px; }
.page-preview :deep(.kw-highlight) { background: rgba(250,204,21,0.35); color: var(--text-primary); font-weight: 700; padding: 0 2px; border-radius: 2px; }

/* Keyword Found List */
.kw-found-list { display: flex; flex-direction: column; gap: 4px; max-height: 250px; overflow-y: auto; }
.kw-found-item { display: flex; align-items: flex-start; gap: 6px; padding: 4px 6px; border-radius: var(--radius-md); background: var(--bg-card); }
.kw-found-rank { flex-shrink: 0; width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 8px; font-weight: 800; color: var(--text-muted); background: var(--bg-surface); }
.kw-found-info { flex: 1; min-width: 0; }
.kw-found-word { font-size: 12px; font-weight: 700; }
.kw-hl-hot { color: #ef4444; } .kw-hl-warm { color: #f59e0b; } .kw-hl-cool { color: #6366f1; }
.kw-found-meta { font-size: 9px; color: var(--text-muted); display: flex; gap: 5px; flex-wrap: wrap; }
.seo-loc-tag { padding: 0 4px; border-radius: 2px; font-size: 8px; font-weight: 700; background: rgba(99,102,241,0.08); color: var(--brand-accent); }

/* Tracked Keywords Table */
.table-responsive { overflow-x: auto; }
.data-table-sm th, .data-table-sm td { padding: 6px 8px; font-size: 11px; }
.kw-name { font-weight: 600; color: var(--text-primary); font-size: 12px; }
.rank-badge { display: inline-block; padding: 2px 6px; border-radius: var(--radius-full); font-size: 11px; font-weight: 700; }
.rank-top3 { background: rgba(34,197,94,0.12); color: #16a34a; }
.rank-top10 { background: rgba(59,130,246,0.12); color: #2563eb; }
.rank-top20 { background: rgba(245,158,11,0.12); color: #d97706; }
.rank-low { background: rgba(239,68,68,0.08); color: #dc2626; }

/* AI Engine */
.ai-engine-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.ai-engine-card { background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 10px; }
.aec-found { border-left: 3px solid #22c55e; } .aec-missing { border-left: 3px solid #ef4444; }
.aec-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.aec-name { font-size: 12px; font-weight: 700; } .aec-score-circle { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 800; border: 2px solid; }
.asc-good { border-color: #22c55e; color: #22c55e; } .asc-mid { border-color: #f59e0b; color: #f59e0b; } .asc-none { border-color: var(--border-color); color: var(--text-muted); }
.aec-status { font-size: 10px; font-weight: 700; } .ast-found { color: #22c55e; } .ast-missing { color: #ef4444; }
.aec-excerpt { font-size: 10px; color: var(--text-secondary); line-height: 1.3; padding: 4px 6px; background: var(--bg-card); border-radius: var(--radius-md); border-left: 2px solid var(--brand-accent); margin-top: 6px; font-style: italic; word-break: break-word; }

/* SERP Data */
.serp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
.serp-card { background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 10px; }
.serp-card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.serp-kw { font-size: 12px; font-weight: 700; }
.serp-metrics { display: flex; gap: 10px; margin-bottom: 6px; }
.serp-metric { text-align: center; }
.sm-label { display: block; font-size: 8px; color: var(--text-muted); text-transform: uppercase; }
.sm-value { display: block; font-size: 12px; font-weight: 700; color: var(--text-primary); }
.serp-features { display: flex; flex-wrap: wrap; gap: 3px; }
.serp-feat-tag { font-size: 8px; padding: 1px 5px; border-radius: 2px; background: rgba(99,102,241,0.08); color: var(--brand-accent); font-weight: 600; }

/* Competitive */
.comp-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.comp-kw-section { background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 10px; }
.comp-kw-name { font-size: 12px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px; }
.comp-row { display: flex; gap: 6px; font-size: 11px; padding: 2px 0; }
.comp-pos { font-weight: 700; color: var(--text-primary); } .comp-domain { color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Alternatives */
.alt-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; }
.alt-card { display: flex; align-items: center; gap: 6px; padding: 8px 10px; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); }
.alt-original { font-size: 11px; color: var(--text-muted); flex-shrink: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.alt-arrow { color: var(--text-muted); flex-shrink: 0; font-size: 11px; }
.alt-new { font-size: 11px; font-weight: 700; color: var(--brand-accent); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.alt-delta { font-size: 9px; font-weight: 700; color: #22c55e; background: rgba(34,197,94,0.08); padding: 1px 5px; border-radius: 3px; }

/* Geo SEO */
.geo-tag-status { font-size: 13px; font-weight: 700; margin-bottom: 8px; }
.gts-found { color: #22c55e; } .gts-missing { color: #ef4444; }
.geo-tip-card { display: flex; gap: 6px; padding: 8px; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); }
.gt-success { border-left: 3px solid #22c55e; } .gt-warning { border-left: 3px solid #f59e0b; } .gt-info { border-left: 3px solid #6366f1; }
.gt-icon { font-size: 14px; flex-shrink: 0; }
.gt-body { flex: 1; }
.gt-text { font-size: 10px; color: var(--text-secondary); line-height: 1.4; }
.gt-tag { display: block; margin-top: 3px; font-size: 9px; padding: 2px 5px; background: var(--bg-card); border-radius: 3px; color: var(--brand-accent); word-break: break-all; }

/* Pages */
.pages-list { display: flex; flex-direction: column; gap: 6px; }
.page-row { display: grid; grid-template-columns: 1fr auto; gap: 6px; padding: 8px 10px; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); align-items: center; }
.page-row-left { display: flex; align-items: center; gap: 6px; min-width: 0; }
.page-num { flex-shrink: 0; width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: 800; background: var(--brand-accent); color: white; }
.page-info { min-width: 0; }
.page-url { font-size: 11px; font-weight: 600; color: var(--brand-accent); text-decoration: none; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.page-url:hover { text-decoration: underline; }
.page-title-text { font-size: 9px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.page-row-right { display: flex; gap: 6px; }
.page-stat { font-size: 9px; font-weight: 600; color: var(--text-secondary); background: var(--bg-card); padding: 1px 5px; border-radius: 3px; }
.page-kws { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 3px; }
.page-kw-chip { font-size: 9px; padding: 1px 5px; border-radius: var(--radius-full); background: rgba(99,102,241,0.08); color: var(--brand-accent); font-weight: 600; }

/* Setup Steps */
.setup-steps { padding: 4px 0; }
.setup-intro { font-size: 12px; color: var(--text-secondary); margin: 0 0 10px; line-height: 1.5; }
.setup-step { display: flex; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border-color); align-items: flex-start; }
.setup-step:last-child { border-bottom: none; }
.step-num { flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 800; background: var(--brand-accent); color: white; }
.step-text { font-size: 12px; color: var(--text-primary); line-height: 1.4; }
.step-text a { color: var(--brand-accent); font-weight: 600; }
.step-text code { font-size: 10px; background: var(--bg-surface); border: 1px solid var(--border-color); padding: 0 4px; border-radius: 2px; color: var(--brand-accent); }

/* Card Picker */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 20px; }
.modal-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 20px; width: 100%; max-width: 400px; }
.modal-picker { max-width: 500px; max-height: 80vh; overflow-y: auto; }
.modal-title { font-size: var(--font-lg); font-weight: 700; color: var(--text-primary); margin: 0 0 14px; }
.modal-body { display: flex; flex-direction: column; gap: 4px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.form-label { display: block; font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }

.picker-grid { display: flex; flex-direction: column; gap: 6px; }
.picker-item { display: flex; align-items: center; gap: 10px; padding: 12px; border: 1px solid var(--border-color); border-radius: var(--radius-md); cursor: pointer; transition: all 0.15s; }
.picker-item:hover { border-color: var(--brand-accent); background: rgba(99,102,241,0.03); }
.picker-item.pi-active { border-color: var(--brand-accent); background: rgba(99,102,241,0.06); }
.pi-icon { font-size: 22px; flex-shrink: 0; }
.pi-info { flex: 1; }
.pi-name { font-size: 13px; font-weight: 700; color: var(--text-primary); }
.pi-desc { font-size: 11px; color: var(--text-muted); margin-top: 1px; }
.pi-check { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; flex-shrink: 0; }
.pi-active .pi-check { background: var(--brand-accent); color: white; }

/* Empty */
.empty-guide { text-align: center; padding: 50px 30px; background: var(--bg-card); border: 2px dashed var(--border-color); border-radius: var(--radius-lg); }
.empty-guide-icon { font-size: 44px; margin-bottom: 10px; }
.empty-guide h3 { font-size: var(--font-lg); color: var(--text-primary); margin: 0 0 8px; }
.empty-guide p { font-size: var(--font-sm); color: var(--text-secondary); max-width: 400px; margin: 0 auto; line-height: 1.5; }

/* Dynamic SEO Optimizer */
.fc-highlight { border-left: 3px solid var(--brand-accent); }
.embed-section { display: flex; flex-direction: column; gap: 10px; }
.embed-label { font-size: 12px; color: var(--text-secondary); }
.embed-label code { font-size: 11px; background: var(--bg-surface); padding: 1px 4px; border-radius: 2px; }
.embed-code-wrap { position: relative; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); overflow: hidden; }
.embed-code { font-size: 10px; padding: 10px 12px; padding-right: 60px; margin: 0; overflow-x: auto; white-space: pre-wrap; word-break: break-all; color: var(--brand-accent); font-family: 'SF Mono', 'Fira Code', monospace; line-height: 1.5; }
.embed-copy { position: absolute; top: 6px; right: 6px; font-size: 10px; padding: 3px 10px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-card); color: var(--text-primary); cursor: pointer; font-weight: 600; transition: all 0.15s; }
.embed-copy:hover { border-color: var(--brand-accent); color: var(--brand-accent); }
.embed-copy.copied { background: #22c55e; color: white; border-color: #22c55e; }
.embed-features { padding: 8px 10px; background: var(--bg-surface); border-radius: var(--radius-md); }
.ef-title { font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 6px; }
.ef-list { display: flex; flex-wrap: wrap; gap: 4px; }
.ef-item { font-size: 10px; padding: 2px 8px; background: rgba(34,197,94,0.08); color: #16a34a; border-radius: var(--radius-full); font-weight: 600; }

/* Responsive */
@media (max-width: 900px) { .cards-grid { grid-template-columns: 1fr; } .split-screen { grid-template-columns: 1fr; } .ai-engine-grid { grid-template-columns: 1fr; } .alt-grid { grid-template-columns: 1fr; } .comp-grid { grid-template-columns: 1fr; } }
@media (max-width: 600px) { .page-header { flex-direction: column; align-items: flex-start; gap: 10px; } .fc-stat-row { flex-direction: column; } }
</style>
