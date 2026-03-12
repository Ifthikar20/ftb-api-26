<template>
  <div class="keywords-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Keyword Intelligence</h1>
        <p class="page-subtitle">AI-powered keyword scoring, Google Trends, and rank tracking.</p>
      </div>
      <button class="btn btn-primary" @click="showAddModal = true">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Track Keyword
      </button>
    </div>

    <!-- Tabs -->
    <div class="kw-tabs">
      <button class="kw-tab" :class="{ active: activeTab === 'tracker' }" @click="activeTab = 'tracker'">📊 Rank Tracker</button>
      <button class="kw-tab" :class="{ active: activeTab === 'scores' }" @click="switchTab('scores')">🧠 AI Scores</button>
      <button class="kw-tab" :class="{ active: activeTab === 'trending' }" @click="switchTab('trending')">🔥 Trending Now</button>
      <button class="kw-tab" :class="{ active: activeTab === 'scanner' }" @click="switchTab('scanner')">🤖 Keyword Agents</button>
    </div>

    <div v-if="loading" class="loading-state">Loading keywords...</div>
    <template v-else>

      <!-- ═══ TAB 1: Rank Tracker ═══ -->
      <div v-show="activeTab === 'tracker'">
        <!-- Summary Stats -->
        <div class="kw-stats">
          <div class="stat-pill"><span class="stat-label">Keywords Tracked</span><span class="stat-value">{{ keywords.length }}</span></div>
          <div class="stat-pill"><span class="stat-label">Avg. Position</span><span class="stat-value">{{ avgPosition }}</span></div>
          <div class="stat-pill"><span class="stat-label pill-up">Improved</span><span class="stat-value" style="color:var(--color-success)">{{ improved }}</span></div>
          <div class="stat-pill"><span class="stat-label pill-down">Declined</span><span class="stat-value" style="color:var(--color-danger)">{{ declined }}</span></div>
        </div>

        <div class="card">
          <table class="data-table">
            <thead>
              <tr><th>Keyword</th><th class="text-center">Position</th><th class="text-center">Change</th><th class="text-center">Best</th><th class="text-center">Volume</th><th class="text-center">Difficulty</th><th class="text-center">30d Trend</th></tr>
            </thead>
            <tbody>
              <tr v-for="kw in keywords" :key="kw.id" class="kw-row" @click="toggleHistory(kw)">
                <td>
                  <div class="kw-name">{{ kw.keyword }}</div>
                  <div class="kw-url">{{ cleanUrl(kw.target_url) }}</div>
                </td>
                <td class="text-center"><span class="rank-badge" :class="rankClass(kw.current_rank)">{{ kw.current_rank || '--' }}</span></td>
                <td class="text-center">
                  <span v-if="kw.rank_change > 0" class="change-up">+{{ kw.rank_change }}</span>
                  <span v-else-if="kw.rank_change < 0" class="change-down">{{ kw.rank_change }}</span>
                  <span v-else class="change-flat">--</span>
                </td>
                <td class="text-center font-semibold">{{ kw.best_rank || '--' }}</td>
                <td class="text-center">{{ (kw.search_volume || 0).toLocaleString() }}</td>
                <td class="text-center">
                  <div class="diff-bar-wrap"><div class="diff-bar" :style="{ width: kw.difficulty + '%' }" :class="diffClass(kw.difficulty)"></div><span class="diff-num">{{ kw.difficulty }}</span></div>
                </td>
                <td class="text-center">
                  <svg v-if="kw._history" width="100" height="28" class="sparkline"><polyline :points="sparklinePoints(kw._history)" fill="none" stroke="var(--brand-accent)" stroke-width="1.5"/></svg>
                  <span v-else class="text-muted text-sm">Click to load</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!keywords.length" class="empty-inline">No keywords being tracked yet. Click "Track Keyword" to start.</div>
        </div>

        <!-- Expanded Chart -->
        <div v-if="expandedKw" class="card" style="margin-top:20px">
          <div class="card-header"><h3 class="card-title">Rank History: {{ expandedKw.keyword }}</h3><span class="text-sm text-muted">Last 30 days</span></div>
          <div class="rank-chart-wrap">
            <svg :viewBox="`0 0 ${chartW} ${chartH}`" class="rank-chart">
              <text v-for="r in yLabels" :key="r" x="30" :y="rankToY(r) + 4" class="chart-label">{{ r }}</text>
              <line v-for="r in yLabels" :key="'g'+r" x1="45" :y1="rankToY(r)" :x2="chartW-10" :y2="rankToY(r)" class="grid-line"/>
              <path :d="areaPath" class="chart-area"/>
              <polyline :points="chartLine" fill="none" stroke="var(--brand-accent)" stroke-width="2"/>
              <circle v-for="(pt, i) in chartPoints" :key="i" :cx="pt.x" :cy="pt.y" r="3" fill="var(--brand-accent)" stroke="var(--bg-card)" stroke-width="1.5" class="chart-dot"/>
              <text v-for="(pt, i) in chartPoints" :key="'x'+i" :x="pt.x" :y="chartH - 2" class="chart-label" text-anchor="middle" v-if="i % 5 === 0">{{ pt.label }}</text>
            </svg>
          </div>
        </div>
      </div>

      <!-- ═══ TAB 2: AI Scores ═══ -->
      <div v-show="activeTab === 'scores'">
        <!-- How It Works -->
        <div class="card explainer-card" v-if="scoreExplanation">
          <div class="card-header">
            <h3 class="card-title">🧠 {{ scoreExplanation.method }}</h3>
            <button class="btn btn-secondary btn-sm" @click="showExplainer = !showExplainer">{{ showExplainer ? 'Hide' : 'How it works' }}</button>
          </div>
          <div v-if="showExplainer" class="explainer-body">
            <div class="explainer-grid">
              <div v-for="c in scoreExplanation.components" :key="c.name" class="explainer-item">
                <div class="explainer-weight">{{ c.weight }}</div>
                <div class="explainer-name">{{ c.name }}</div>
                <div class="explainer-desc">{{ c.desc }}</div>
              </div>
            </div>
            <div class="disclaimer">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="7" cy="7" r="6"/><line x1="7" y1="4" x2="7" y2="7.5"/><circle cx="7" cy="9.5" r="0.5" fill="currentColor"/></svg>
              {{ scoreExplanation.disclaimer }}
            </div>
          </div>
        </div>

        <!-- Scored Keywords -->
        <div class="card" style="margin-top:16px">
          <table class="data-table" v-if="scoredKeywords.length">
            <thead>
              <tr><th>Keyword</th><th class="text-center">AI Score</th><th class="text-center">Grade</th><th class="text-center">Rank</th><th class="text-center">Volume</th><th>Recommendation</th></tr>
            </thead>
            <tbody>
              <tr v-for="kw in scoredKeywords" :key="kw.id">
                <td class="font-semibold">{{ kw.keyword }}</td>
                <td class="text-center">
                  <div class="score-ring">
                    <svg viewBox="0 0 36 36">
                      <circle cx="18" cy="18" r="15.5" fill="none" stroke="var(--bg-surface)" stroke-width="3"/>
                      <circle cx="18" cy="18" r="15.5" fill="none" :stroke="kw.grade.color" stroke-width="3" :stroke-dasharray="kw.ai_score + ' ' + (100 - kw.ai_score)" stroke-dashoffset="25" stroke-linecap="round"/>
                    </svg>
                    <span class="score-num">{{ kw.ai_score }}</span>
                  </div>
                </td>
                <td class="text-center"><span class="grade-badge" :style="{ color: kw.grade.color, background: kw.grade.color + '15' }">{{ kw.grade.label }}</span></td>
                <td class="text-center"><span class="rank-badge" :class="rankClass(kw.current_rank)">{{ kw.current_rank || '--' }}</span></td>
                <td class="text-center">{{ (kw.search_volume || 0).toLocaleString() }}</td>
                <td class="text-sm" style="max-width:300px;line-height:1.5">{{ kw.recommendation }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-inline">Track keywords first to see AI scores and recommendations.</div>
        </div>
      </div>

      <!-- ═══ TAB 3: Trending Now ═══ -->
      <div v-show="activeTab === 'trending'">
        <div class="analytics-row">
          <!-- Trending Searches -->
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">🔥 Trending on Google</h3>
              <span class="text-xs text-muted" v-if="trendingData.updated_at">Updated {{ formatTime(trendingData.updated_at) }}</span>
            </div>
            <div v-if="trendingData.source === 'unavailable'" class="pytrends-notice">
              <p><strong>Google Trends not connected</strong></p>
              <p>Install pytrends to get real-time trending data:</p>
              <code>pip install pytrends</code>
              <p class="text-xs text-muted" style="margin-top:12px">This is optional — keyword tracking works without it.</p>
            </div>
            <div v-else-if="trendingData.keywords && trendingData.keywords.length" class="trending-list">
              <div v-for="(kw, i) in trendingData.keywords" :key="i" class="trending-item">
                <span class="trending-rank">{{ i + 1 }}</span>
                <span class="trending-kw">{{ kw }}</span>
                <button class="btn btn-secondary btn-xs" @click="quickTrack(kw)">+ Track</button>
              </div>
            </div>
            <div v-else class="empty-inline">No trending data available</div>
          </div>

          <!-- Suggestions -->
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">💡 Suggested for You</h3>
              <span class="text-xs text-muted">Based on your website</span>
            </div>
            <div v-if="suggestions.length" class="suggestion-list">
              <div v-for="s in suggestions" :key="s.keyword" class="suggestion-item">
                <div>
                  <span class="font-semibold text-sm">{{ s.keyword }}</span>
                  <span class="suggestion-badge" :class="'sb-' + s.trend">{{ s.source }}</span>
                </div>
                <button class="btn btn-secondary btn-xs" @click="quickTrack(s.keyword)">+ Track</button>
              </div>
            </div>
            <div v-else class="empty-inline">Add keywords or install pytrends for suggestions</div>
          </div>
        </div>

        <!-- How to Use Panel -->
        <div class="card tips-card">
          <div class="card-header"><h3 class="card-title">📌 How to Use Keyword Intelligence</h3></div>
          <div class="tips-grid">
            <div class="tip-item">
              <div class="tip-num">1</div>
              <div><strong>Track keywords</strong> your website should rank for. Start with your core pages and key terms.</div>
            </div>
            <div class="tip-item">
              <div class="tip-num">2</div>
              <div><strong>Check AI Scores</strong> to find quick-win opportunities. Keywords ranked #11-20 with low difficulty are your best bets.</div>
            </div>
            <div class="tip-item">
              <div class="tip-num">3</div>
              <div><strong>Monitor trends</strong> to discover rising topics. If a trending keyword matches your expertise, create content before competitors.</div>
            </div>
            <div class="tip-item">
              <div class="tip-num">4</div>
              <div><strong>Follow recommendations</strong> for each keyword. The AI suggests specific actions based on your current position and competition.</div>
            </div>
          </div>
          <div class="disclaimer" style="margin-top:16px">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="7" cy="7" r="6"/><line x1="7" y1="4" x2="7" y2="7.5"/><circle cx="7" cy="9.5" r="0.5" fill="currentColor"/></svg>
            Rankings are checked periodically. Search volume and difficulty are estimates. Google Trends data is sourced from Google and may not reflect exact search counts. Use all metrics as directional guidance for your SEO strategy.
          </div>
        </div>
      </div>

      <!-- ═══ TAB 4: Keyword Agents ═══ -->
      <div v-show="activeTab === 'scanner'">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">🤖 Keyword Agents</h3>
            <button class="btn btn-primary btn-sm" @click="runKeywordScan" :disabled="scanLoading">
              {{ scanLoading ? 'Agents working...' : (scanData.score != null ? 'Re-scan' : 'Run Agents') }}
            </button>
          </div>

          <div v-if="scanData.score != null" class="seo-scanner-results">
            <!-- Score Gauge -->
            <div class="seo-score-row">
              <div class="seo-score-gauge" :class="scanData.score >= 70 ? 'sg-good' : scanData.score >= 40 ? 'sg-mid' : 'sg-bad'">
                <span class="seo-score-num">{{ scanData.score }}</span>
                <span class="seo-score-lbl">/ 100</span>
              </div>
              <div class="seo-score-meta">
                <div class="seo-verdict" :class="scanData.score >= 70 ? 'sv-good' : scanData.score >= 40 ? 'sv-mid' : 'sv-bad'">
                  {{ scanData.score >= 70 ? 'Good' : scanData.score >= 40 ? 'Needs Work' : 'Poor' }}
                </div>
                <div class="text-xs text-muted">{{ scanData.page_meta?.word_count || 0 }} words • {{ scanData.keywords?.length || 0 }} keywords extracted</div>
                <div v-if="scanData.scanned_at" class="text-xs text-muted">Scanned {{ new Date(scanData.scanned_at).toLocaleString() }}</div>
              </div>
            </div>

            <!-- Score Breakdown -->
            <div class="seo-breakdown">
              <h4 class="seo-sec-title">Score Breakdown</h4>
              <div v-for="(comp, key) in scanData.score_breakdown" :key="key" v-if="comp && comp.label" class="seo-br-row">
                <div class="seo-br-name">{{ comp.label }} <span class="text-xs text-muted">({{ comp.weight }}%)</span></div>
                <div class="seo-br-track"><div class="seo-br-fill" :style="{ width: comp.score + '%' }" :class="comp.score >= 70 ? 'bf-good' : comp.score >= 40 ? 'bf-mid' : 'bf-bad'"></div></div>
                <span class="seo-br-num">{{ comp.score }}</span>
              </div>
            </div>

            <!-- AI Engine Visibility -->
            <div v-if="scanData.ai_rankings && Object.keys(scanData.ai_rankings).length" class="ai-engines-section">
              <h4 class="seo-sec-title">🤖 AI Engine Visibility
                <span v-if="scanData.ai_rankings.overall_score != null" class="ai-overall-badge" :class="scanData.ai_rankings.overall_score >= 40 ? 'aob-good' : scanData.ai_rankings.overall_score > 0 ? 'aob-mid' : 'aob-none'">
                  Overall: {{ scanData.ai_rankings.overall_score }}/100
                </span>
              </h4>
              <p class="text-xs text-muted" style="margin-bottom:14px">Do AI search engines recommend your site when users ask about your keywords?</p>
              <div class="ai-engine-grid">
                <!-- Claude -->
                <div v-if="scanData.ai_rankings.claude" class="ai-engine-card" :class="scanData.ai_rankings.claude.mentioned ? 'aec-found' : 'aec-missing'">
                  <div class="aec-header">
                    <div class="aec-name">Claude</div>
                    <div class="aec-score-circle" :class="scanData.ai_rankings.claude.score >= 40 ? 'asc-good' : scanData.ai_rankings.claude.score > 0 ? 'asc-mid' : 'asc-none'">
                      {{ scanData.ai_rankings.claude.score }}
                    </div>
                  </div>
                  <div class="aec-status" :class="scanData.ai_rankings.claude.mentioned ? 'ast-found' : scanData.ai_rankings.claude.status === 'not_configured' ? 'ast-na' : 'ast-missing'">
                    {{ scanData.ai_rankings.claude.mentioned ? '✓ Found' : scanData.ai_rankings.claude.status === 'not_configured' ? 'Not configured' : scanData.ai_rankings.claude.status === 'error' ? 'Error' : '✗ Not mentioned' }}
                  </div>
                  <div v-if="scanData.ai_rankings.claude.excerpt" class="aec-excerpt">{{ scanData.ai_rankings.claude.excerpt }}</div>
                  <div v-if="scanData.ai_rankings.claude.mentioned_keywords?.length" class="aec-kws">
                    <span v-for="kw in scanData.ai_rankings.claude.mentioned_keywords" :key="kw" class="aec-kw-tag">{{ kw }}</span>
                  </div>
                </div>

                <!-- ChatGPT -->
                <div v-if="scanData.ai_rankings.chatgpt" class="ai-engine-card" :class="scanData.ai_rankings.chatgpt.mentioned ? 'aec-found' : 'aec-missing'">
                  <div class="aec-header">
                    <div class="aec-name">ChatGPT</div>
                    <div class="aec-score-circle" :class="scanData.ai_rankings.chatgpt.score >= 40 ? 'asc-good' : scanData.ai_rankings.chatgpt.score > 0 ? 'asc-mid' : 'asc-none'">
                      {{ scanData.ai_rankings.chatgpt.score }}
                    </div>
                  </div>
                  <div class="aec-status" :class="scanData.ai_rankings.chatgpt.mentioned ? 'ast-found' : scanData.ai_rankings.chatgpt.status === 'not_configured' ? 'ast-na' : 'ast-missing'">
                    {{ scanData.ai_rankings.chatgpt.mentioned ? '✓ Found' : scanData.ai_rankings.chatgpt.status === 'not_configured' ? 'Not configured' : scanData.ai_rankings.chatgpt.status === 'error' ? 'Error' : '✗ Not mentioned' }}
                  </div>
                  <div v-if="scanData.ai_rankings.chatgpt.excerpt" class="aec-excerpt">{{ scanData.ai_rankings.chatgpt.excerpt }}</div>
                  <div v-if="scanData.ai_rankings.chatgpt.mentioned_keywords?.length" class="aec-kws">
                    <span v-for="kw in scanData.ai_rankings.chatgpt.mentioned_keywords" :key="kw" class="aec-kw-tag">{{ kw }}</span>
                  </div>
                </div>

                <!-- Perplexity -->
                <div v-if="scanData.ai_rankings.perplexity" class="ai-engine-card" :class="scanData.ai_rankings.perplexity.mentioned ? 'aec-found' : 'aec-missing'">
                  <div class="aec-header">
                    <div class="aec-name">Perplexity</div>
                    <div class="aec-score-circle" :class="scanData.ai_rankings.perplexity.score >= 40 ? 'asc-good' : scanData.ai_rankings.perplexity.score > 0 ? 'asc-mid' : 'asc-none'">
                      {{ scanData.ai_rankings.perplexity.score }}
                    </div>
                  </div>
                  <div class="aec-status" :class="scanData.ai_rankings.perplexity.mentioned ? 'ast-found' : scanData.ai_rankings.perplexity.status === 'not_configured' ? 'ast-na' : 'ast-missing'">
                    {{ scanData.ai_rankings.perplexity.mentioned ? '✓ Found' : scanData.ai_rankings.perplexity.status === 'not_configured' ? 'Not configured' : scanData.ai_rankings.perplexity.status === 'error' ? 'Error' : '✗ Not mentioned' }}
                  </div>
                  <div v-if="scanData.ai_rankings.perplexity.excerpt" class="aec-excerpt">{{ scanData.ai_rankings.perplexity.excerpt }}</div>
                  <div v-if="scanData.ai_rankings.perplexity.mentioned_keywords?.length" class="aec-kws">
                    <span v-for="kw in scanData.ai_rankings.perplexity.mentioned_keywords" :key="kw" class="aec-kw-tag">{{ kw }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Extracted Keywords -->
            <div v-if="scanData.keywords?.length" class="seo-kw-section">
              <h4 class="seo-sec-title">Extracted Keywords</h4>
              <table class="data-table">
                <thead><tr><th>Keyword</th><th class="text-center">Trend Interest</th><th class="text-center">Density</th><th>Found In</th></tr></thead>
                <tbody>
                  <tr v-for="(k, i) in scanData.keywords.slice(0, 12)" :key="i">
                    <td class="font-semibold">{{ k.keyword }}</td>
                    <td class="text-center">
                      <span class="seo-trend-chip" :class="(scanData.trends?.[k.keyword]?.trend || 'unknown') === 'rising' ? 'stc-up' : (scanData.trends?.[k.keyword]?.trend || 'unknown') === 'declining' ? 'stc-down' : 'stc-flat'">
                        {{ scanData.trends?.[k.keyword]?.interest || 0 }}
                      </span>
                    </td>
                    <td class="text-center">
                      <span :class="k.density_status === 'optimal' ? 'text-success' : k.density_status === 'high' ? 'text-danger' : 'text-warning'">{{ k.density }}%</span>
                    </td>
                    <td>
                      <span v-for="l in k.locations" :key="l" class="seo-loc-tag">{{ l }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Synonym Suggestions -->
            <div v-if="scanData.suggestions?.length" class="seo-syn-section">
              <h4 class="seo-sec-title">💡 Better Keyword Alternatives</h4>
              <p class="text-xs text-muted" style="margin-bottom:12px">These keywords have higher Google Trends interest than what you currently use.</p>
              <table class="data-table">
                <thead><tr><th>Your Keyword</th><th></th><th>Suggested Alternative</th><th class="text-center">Improvement</th></tr></thead>
                <tbody>
                  <tr v-for="(s, i) in scanData.suggestions.slice(0, 8)" :key="i">
                    <td class="text-muted">{{ s.original }}</td>
                    <td style="text-align:center;color:var(--text-muted)">→</td>
                    <td class="font-semibold" style="color:var(--brand-accent)">{{ s.suggested }}</td>
                    <td class="text-center"><span class="seo-delta">+{{ s.improvement }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-else-if="scanData.error" class="empty-inline">{{ scanData.error }}</div>
          <div v-else class="empty-inline">Click <strong>Run Agents</strong> to scan your site's keywords, check AI engine rankings (Claude, ChatGPT, Perplexity), and get optimization suggestions.</div>
        </div>
      </div>
    </template>

    <!-- Add Keyword Modal -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal-card">
        <h3 class="card-title" style="margin-bottom:16px">Track New Keyword</h3>
        <div style="margin-bottom:12px"><label class="form-label">Keyword</label><input v-model="newKw.keyword" class="form-input" placeholder="e.g. growth hacking tools" /></div>
        <div style="margin-bottom:12px"><label class="form-label">Target URL (optional)</label><input v-model="newKw.target_url" class="form-input" placeholder="https://..." /></div>
        <div class="flex gap-8" style="justify-content:flex-end">
          <button class="btn btn-secondary" @click="showAddModal = false">Cancel</button>
          <button class="btn btn-primary" @click="addKeyword" :disabled="!newKw.keyword.trim() || adding">{{ adding ? 'Adding...' : 'Track Keyword' }}</button>
        </div>
        <p v-if="addError" class="text-sm" style="color:var(--color-danger);margin-top:12px">{{ addError }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import analyticsApi from '@/api/analytics'

const props = defineProps({ websiteId: String })

const activeTab = ref('tracker')
const loading = ref(true)
const keywords = ref([])
const expandedKw = ref(null)
const showAddModal = ref(false)
const adding = ref(false)
const addError = ref('')
const newKw = ref({ keyword: '', target_url: '' })
const showExplainer = ref(false)

// AI scores
const scoredKeywords = ref([])
const scoreExplanation = ref(null)

// Trending
const trendingData = ref({})

// SEO Scanner
const scanData = ref({})
const scanLoading = ref(false)
const suggestions = ref([])

const chartW = 700; const chartH = 200; const chartPadLeft = 50; const chartPadTop = 15; const chartPadBottom = 25

const avgPosition = computed(() => {
  const ranked = keywords.value.filter(k => k.current_rank)
  if (!ranked.length) return '--'
  return Math.round(ranked.reduce((s, k) => s + k.current_rank, 0) / ranked.length)
})
const improved = computed(() => keywords.value.filter(k => k.rank_change > 0).length)
const declined = computed(() => keywords.value.filter(k => k.rank_change < 0).length)

const yLabels = computed(() => {
  if (!expandedKw.value?._history?.length) return [1, 10, 20, 30]
  const ranks = expandedKw.value._history.map(h => h.rank).filter(Boolean)
  const min = Math.max(1, Math.min(...ranks) - 2)
  const max = Math.max(...ranks) + 2
  const step = Math.max(1, Math.round((max - min) / 4))
  const labels = []; for (let r = min; r <= max; r += step) labels.push(r); return labels
})

function rankToY(rank) {
  const ranks = expandedKw.value?._history?.map(h => h.rank).filter(Boolean) || [1, 50]
  const min = Math.max(1, Math.min(...ranks) - 2); const max = Math.max(...ranks) + 2
  return chartPadTop + ((rank - min) / (max - min)) * (chartH - chartPadTop - chartPadBottom)
}

const chartPoints = computed(() => {
  if (!expandedKw.value?._history?.length) return []
  const h = expandedKw.value._history; const w = chartW - chartPadLeft - 20
  return h.map((r, i) => ({ x: chartPadLeft + (i / Math.max(h.length - 1, 1)) * w, y: rankToY(r.rank), label: new Date(r.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }))
})
const chartLine = computed(() => chartPoints.value.map(p => `${p.x},${p.y}`).join(' '))
const areaPath = computed(() => {
  const pts = chartPoints.value; if (!pts.length) return ''
  const b = chartH - chartPadBottom; let d = `M ${pts[0].x} ${b}`; pts.forEach(p => { d += ` L ${p.x} ${p.y}` }); d += ` L ${pts[pts.length - 1].x} ${b} Z`; return d
})

function cleanUrl(url) { if (!url) return ''; try { return new URL(url).pathname } catch { return url } }
function rankClass(rank) { if (!rank) return ''; if (rank <= 3) return 'rank-top3'; if (rank <= 10) return 'rank-top10'; if (rank <= 20) return 'rank-top20'; return 'rank-low' }
function diffClass(d) { if (d < 30) return 'diff-easy'; if (d < 60) return 'diff-medium'; return 'diff-hard' }
function sparklinePoints(history) {
  if (!history?.length) return ''; const ranks = history.map(h => h.rank).filter(Boolean); if (!ranks.length) return ''
  const min = Math.min(...ranks) - 1; const max = Math.max(...ranks) + 1; const range = max - min || 1
  return ranks.map((r, i) => `${(i / Math.max(ranks.length - 1, 1)) * 96 + 2},${2 + ((r - min) / range) * 24}`).join(' ')
}
function formatTime(d) { if (!d) return ''; return new Date(d).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) }

function switchTab(tab) {
  activeTab.value = tab
  if (tab === 'scores' && !scoredKeywords.value.length) fetchScores()
  if (tab === 'trending' && !trendingData.value.keywords) fetchTrending()
}

async function runKeywordScan() {
  scanLoading.value = true
  try {
    const res = await analyticsApi.keywordScanTrigger(props.websiteId)
    scanData.value = res.data?.data || res.data || {}
  } catch (e) {
    scanData.value = { error: 'Scan failed — ensure your site URL is accessible.' }
  } finally {
    scanLoading.value = false
  }
}

async function toggleHistory(kw) {
  if (expandedKw.value?.id === kw.id) { expandedKw.value = null; return }
  if (!kw._history) {
    try { const { data } = await analyticsApi.keywordHistory(props.websiteId, kw.id); kw._history = data?.data?.history || data?.history || [] }
    catch { kw._history = [] }
  }
  expandedKw.value = kw
}

async function addKeyword() {
  adding.value = true; addError.value = ''
  try {
    const { data } = await analyticsApi.addKeyword(props.websiteId, newKw.value)
    const kw = data?.data || data
    keywords.value.unshift({ ...kw, rank_change: null, _history: null })
    newKw.value = { keyword: '', target_url: '' }; showAddModal.value = false
  } catch (e) { addError.value = e.response?.data?.error || 'Failed to add keyword.' }
  finally { adding.value = false }
}

async function quickTrack(keyword) {
  try {
    const { data } = await analyticsApi.addKeyword(props.websiteId, { keyword })
    const kw = data?.data || data
    keywords.value.unshift({ ...kw, rank_change: null, _history: null })
  } catch {}
}

async function fetchScores() {
  try {
    const { data } = await analyticsApi.keywordScores(props.websiteId)
    const d = data?.data || data
    scoredKeywords.value = d.keywords || []
    scoreExplanation.value = d.explanation || null
  } catch (e) { console.error('Scores fetch error', e) }
}

async function fetchTrending() {
  try {
    const [tRes, sRes] = await Promise.all([
      analyticsApi.keywordTrending(props.websiteId).catch(() => ({ data: {} })),
      analyticsApi.keywordSuggestions(props.websiteId).catch(() => ({ data: [] })),
    ])
    trendingData.value = tRes.data?.data || tRes.data || {}
    suggestions.value = sRes.data?.data || sRes.data || []
  } catch (e) { console.error('Trending fetch error', e) }
}

onMounted(async () => {
  try {
    const { data } = await analyticsApi.keywords(props.websiteId)
    keywords.value = (data?.data || data || []).map(k => ({ ...k, _history: null }))
  } catch (e) { console.error('Keywords fetch error', e) }
  finally { loading.value = false }
})
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }

/* Tabs */
.kw-tabs { display: flex; gap: 4px; margin-bottom: 24px; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 4px; }
.kw-tab { display: flex; align-items: center; gap: 6px; padding: 10px 16px; border: none; background: transparent; border-radius: var(--radius-md); font-size: var(--font-sm); font-weight: 600; color: var(--text-muted); cursor: pointer; transition: all 0.15s; font-family: var(--font-family); white-space: nowrap; }
.kw-tab:hover { color: var(--text-primary); background: var(--bg-surface); }
.kw-tab.active { background: var(--text-primary); color: var(--text-inverse); }

/* Stats */
.kw-stats { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.stat-pill { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 14px 20px; display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 120px; }
.stat-label { font-size: var(--font-xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.stat-value { font-size: var(--font-xl); font-weight: 700; color: var(--text-primary); }

/* Keywords table */
.kw-row { cursor: pointer; transition: background 0.15s; }
.kw-row:hover { background: var(--bg-surface); }
.kw-name { font-weight: 600; color: var(--text-primary); }
.kw-url { font-size: var(--font-xs); color: var(--text-muted); margin-top: 2px; }

.rank-badge { display: inline-block; min-width: 32px; padding: 4px 10px; border-radius: var(--radius-full); font-weight: 700; font-size: var(--font-sm); text-align: center; }
.rank-top3 { background: rgba(34,197,94,0.15); color: var(--color-success); }
.rank-top10 { background: rgba(59,130,246,0.12); color: #3b82f6; }
.rank-top20 { background: rgba(234,179,8,0.12); color: #ca8a04; }
.rank-low { background: rgba(239,68,68,0.1); color: var(--color-danger); }

.change-up { color: var(--color-success); font-weight: 700; }
.change-down { color: var(--color-danger); font-weight: 700; }
.change-flat { color: var(--text-muted); }

.diff-bar-wrap { display: flex; align-items: center; gap: 8px; }
.diff-bar { height: 5px; border-radius: var(--radius-full); min-width: 2px; }
.diff-easy { background: var(--color-success); }
.diff-medium { background: #eab308; }
.diff-hard { background: var(--color-danger); }
.diff-num { font-size: var(--font-xs); color: var(--text-muted); min-width: 20px; }

.sparkline { cursor: pointer; }

/* Chart */
.rank-chart-wrap { overflow-x: auto; }
.rank-chart { width: 100%; min-height: 200px; display: block; }
.chart-area { fill: var(--brand-accent); opacity: 0.08; }
.chart-label { fill: var(--text-muted); font-size: 10px; }
.grid-line { stroke: var(--border-color); stroke-width: 0.5; opacity: 0.4; }
.chart-dot { transition: r 0.2s; }
.chart-dot:hover { r: 5; }

/* Score Ring */
.score-ring { position: relative; width: 40px; height: 40px; display: inline-block; }
.score-ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.score-num { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: var(--text-primary); }

.grade-badge { display: inline-block; padding: 3px 10px; border-radius: var(--radius-full); font-size: var(--font-xs); font-weight: 700; }

/* Explainer */
.explainer-card { border-left: 3px solid var(--brand-accent); }
.explainer-body { margin-top: 16px; }
.explainer-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.explainer-item { text-align: center; }
.explainer-weight { font-size: var(--font-xl); font-weight: 700; color: var(--brand-accent); }
.explainer-name { font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); margin: 4px 0; }
.explainer-desc { font-size: var(--font-xs); color: var(--text-secondary); line-height: 1.4; }

.disclaimer { display: flex; align-items: flex-start; gap: 8px; padding: 14px 16px; background: var(--bg-surface); border-radius: var(--radius-md); font-size: var(--font-xs); color: var(--text-muted); line-height: 1.5; margin-top: 16px; }
.disclaimer svg { flex-shrink: 0; margin-top: 2px; }

/* Trending */
.analytics-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
.trending-list { display: flex; flex-direction: column; gap: 8px; }
.trending-item { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--border-color); }
.trending-item:last-child { border-bottom: none; }
.trending-rank { width: 24px; height: 24px; background: var(--bg-surface); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: var(--text-muted); }
.trending-kw { flex: 1; font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); }

.suggestion-list { display: flex; flex-direction: column; gap: 10px; }
.suggestion-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border-color); }
.suggestion-item:last-child { border-bottom: none; }
.suggestion-badge { font-size: 10px; padding: 2px 8px; border-radius: var(--radius-full); margin-left: 8px; }
.sb-rising { background: rgba(39,174,96,0.12); color: var(--color-success); }
.sb-stable { background: rgba(52,152,219,0.12); color: var(--color-info); }

.btn-xs { font-size: 11px; padding: 3px 10px; }

.pytrends-notice { padding: 24px; text-align: center; color: var(--text-secondary); font-size: var(--font-sm); }
.pytrends-notice code { display: block; margin-top: 10px; padding: 10px 16px; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); font-family: 'SF Mono', monospace; font-size: var(--font-xs); color: var(--brand-accent); }

/* Tips */
.tips-card { }
.tips-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.tip-item { display: flex; gap: 14px; font-size: var(--font-sm); color: var(--text-secondary); line-height: 1.5; }
.tip-num { width: 28px; height: 28px; background: var(--brand-accent); color: #1a1a2e; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: var(--font-sm); flex-shrink: 0; }

.empty-inline { text-align: center; padding: 40px 20px; color: var(--text-muted); font-size: var(--font-sm); }

/* Modal */
.modal-overlay { position: fixed; inset: 0; z-index: 200; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; }
.modal-card { background: var(--bg-card); border-radius: var(--radius-lg); padding: 28px; width: 440px; max-width: 90vw; box-shadow: var(--shadow-lg); }
.form-label { display: block; font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }

/* SEO Scanner */
.seo-scanner-results { display: flex; flex-direction: column; gap: 24px; margin-top: 8px; }
.seo-sec-title { font-size: 13px; font-weight: 700; color: var(--text-primary); margin: 0 0 12px; padding-bottom: 6px; border-bottom: 1px solid var(--border-color); }

.seo-score-row { display: flex; align-items: center; gap: 24px; padding: 16px; background: var(--bg-surface); border-radius: var(--radius-lg); }
.seo-score-gauge { width: 88px; height: 88px; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 4px solid; flex-shrink: 0; }
.sg-good { border-color: #22c55e; background: rgba(34,197,94,0.06); }
.sg-mid { border-color: #f59e0b; background: rgba(245,158,11,0.06); }
.sg-bad { border-color: #ef4444; background: rgba(239,68,68,0.06); }
.seo-score-num { font-size: 28px; font-weight: 800; color: var(--text-primary); line-height: 1; }
.seo-score-lbl { font-size: 10px; color: var(--text-muted); font-weight: 600; }
.seo-score-meta { flex: 1; }
.seo-verdict { font-size: 18px; font-weight: 700; margin-bottom: 6px; }
.sv-good { color: #22c55e; }
.sv-mid { color: #f59e0b; }
.sv-bad { color: #ef4444; }

.seo-breakdown { display: flex; flex-direction: column; gap: 8px; }
.seo-br-row { display: flex; align-items: center; gap: 12px; }
.seo-br-name { width: 180px; font-size: 12px; color: var(--text-primary); flex-shrink: 0; }
.seo-br-track { flex: 1; height: 8px; background: var(--bg-surface); border-radius: 4px; overflow: hidden; }
.seo-br-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease; }
.bf-good { background: #22c55e; }
.bf-mid { background: #f59e0b; }
.bf-bad { background: #ef4444; }
.seo-br-num { width: 30px; text-align: right; font-size: 12px; font-weight: 700; color: var(--text-primary); }

.seo-trend-chip { display: inline-block; padding: 2px 10px; border-radius: var(--radius-full); font-size: 11px; font-weight: 700; }
.stc-up { background: rgba(34,197,94,0.12); color: #22c55e; }
.stc-down { background: rgba(239,68,68,0.1); color: #ef4444; }
.stc-flat { background: rgba(245,158,11,0.1); color: #f59e0b; }

.text-success { color: #22c55e; font-weight: 600; }
.text-danger { color: #ef4444; font-weight: 600; }
.text-warning { color: #f59e0b; font-weight: 600; }

.seo-loc-tag { display: inline-block; padding: 1px 7px; margin: 1px 3px; border-radius: var(--radius-full); font-size: 9px; font-weight: 700; text-transform: uppercase; background: rgba(99,102,241,0.1); color: var(--brand-accent); }

.seo-delta { color: #22c55e; font-weight: 700; font-size: 13px; }

/* AI Engine Visibility */
.ai-engines-section { margin-top: 4px; }
.ai-overall-badge { display: inline-block; margin-left: 10px; padding: 2px 10px; border-radius: var(--radius-full); font-size: 11px; font-weight: 700; vertical-align: middle; }
.aob-good { background: rgba(34,197,94,0.12); color: #22c55e; }
.aob-mid { background: rgba(245,158,11,0.1); color: #f59e0b; }
.aob-none { background: rgba(100,100,100,0.1); color: var(--text-muted); }

.ai-engine-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.ai-engine-card { background: var(--bg-surface); border-radius: var(--radius-lg); padding: 18px; border: 1px solid var(--border-color); transition: border-color 0.2s; }
.aec-found { border-color: #22c55e; border-left: 3px solid #22c55e; }
.aec-missing { border-style: dashed; opacity: 0.85; }

.aec-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.aec-name { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.aec-score-circle { width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 800; border: 3px solid; }
.asc-good { border-color: #22c55e; color: #22c55e; background: rgba(34,197,94,0.06); }
.asc-mid { border-color: #f59e0b; color: #f59e0b; background: rgba(245,158,11,0.06); }
.asc-none { border-color: var(--border-color); color: var(--text-muted); background: transparent; }

.aec-status { font-size: 12px; font-weight: 700; margin-bottom: 8px; }
.ast-found { color: #22c55e; }
.ast-missing { color: #ef4444; }
.ast-na { color: var(--text-muted); font-style: italic; }

.aec-excerpt { font-size: 11px; color: var(--text-secondary); line-height: 1.5; padding: 8px 10px; background: var(--bg-card); border-radius: var(--radius-md); border-left: 2px solid var(--brand-accent); margin-bottom: 8px; font-style: italic; word-break: break-word; }

.aec-kws { display: flex; flex-wrap: wrap; gap: 4px; }
.aec-kw-tag { display: inline-block; padding: 2px 8px; border-radius: var(--radius-full); font-size: 10px; font-weight: 700; background: rgba(99,102,241,0.1); color: var(--brand-accent); }

@media (max-width: 900px) { .analytics-row { grid-template-columns: 1fr; } .explainer-grid { grid-template-columns: repeat(2, 1fr); } .tips-grid { grid-template-columns: 1fr; } .seo-br-name { width: 140px; } }
@media (max-width: 768px) { .kw-stats { flex-direction: column; } .seo-score-row { flex-direction: column; text-align: center; } }
</style>
