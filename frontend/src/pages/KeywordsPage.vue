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
      <div class="empty-guide-icon"><svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="var(--text-muted)" stroke-width="1.5"><rect x="8" y="6" width="32" height="36" rx="4"/><path d="M16 18h16M16 26h10M16 34h14"/></svg></div>
      <h3>Build your SEO dashboard</h3>
      <p>Click the <strong>+</strong> button to add feature cards, or <strong>Scan Website</strong> to start analyzing your SEO.</p>
    </div>

    <!-- Active Cards -->
    <div class="cards-grid">
      <template v-for="cardId in activeCards" :key="cardId">

        <!-- Site Audit -->
        <div v-if="cardId === 'site_audit'" class="card feature-card">
          <div class="fc-head">
            <div class="fc-icon"><svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="7" cy="7" r="5"/><path d="M11 11l3 3"/></svg></div>
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
              <template v-for="(comp, key) in scanData.score_breakdown" :key="key">
                <div v-if="comp && comp.label" class="fc-br-row">
                  <span class="fc-br-name">{{ comp.label }}</span>
                  <div class="fc-br-bar"><div class="fc-br-fill" :style="{ width: comp.score + '%' }" :class="comp.score >= 70 ? 'b-good' : comp.score >= 40 ? 'b-mid' : 'b-bad'"></div></div>
                  <span class="fc-br-num">{{ comp.score }}</span>
                </div>
              </template>
            </div>
          </div>
          <div v-else class="fc-empty">Click <strong>Scan Website</strong> to audit your site for 140+ SEO issues and get your health score.</div>
        </div>

        <!-- Keyword Research -->
        <div v-if="cardId === 'keyword_research'" class="card feature-card">
          <div class="fc-head">
            <div class="fc-icon"><svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 12V4l4 4 4-4v8"/></svg></div>
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
            <div class="fc-icon"><svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="2"/><circle cx="6" cy="7" r="2"/><circle cx="10" cy="7" r="2"/><path d="M5 11h6"/></svg></div>
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
            <div class="fc-icon"><svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 4l4 4-4 4M8 4l4 4-4 4"/></svg></div>
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
            <div class="fc-icon"><svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="5" r="3"/><path d="M5 10v1a3 3 0 006 0v-1"/><line x1="8" y1="14" x2="8" y2="15"/></svg></div>
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
            <div class="fc-icon"><svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="6" r="4"/><path d="M8 10v4M6 14h4"/></svg></div>
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
            <div class="fc-icon"><svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="7" cy="7" r="5"/><path d="M11 11l3 3"/><circle cx="7" cy="7" r="2"/></svg></div>
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
            <div class="fc-icon"><svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M2 8h12M8 2c-2 2-2 10 0 12M8 2c2 2 2 10 0 12"/></svg></div>
            <div class="fc-title-wrap"><h3 class="fc-title">Geo SEO & Tagging</h3><p class="fc-sub">Regional optimization</p></div>
            <button class="fc-remove" @click="removeCard(cardId)" title="Remove">×</button>
          </div>
          <div v-if="scanData.geo_data" class="fc-body">
            <div class="geo-tag-status" :class="scanData.geo_data.has_geo_tags ? 'gts-found' : 'gts-missing'">
              {{ scanData.geo_data.has_geo_tags ? '✓ Geo Tags Found' : '✗ No Geo Tags Detected' }}
            </div>
            <div v-for="(tip, i) in (scanData.geo_data.tips || [])" :key="i" class="geo-tip-card" :class="'gt-' + tip.type" style="margin-top:6px">
              <span class="gt-icon"><span :style="{ display:'inline-block', width:'8px', height:'8px', borderRadius:'50%', background: tip.type === 'success' ? '#22c55e' : tip.type === 'warning' ? '#f59e0b' : '#6366f1' }"></span></span>
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
            <div class="fc-icon"><svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="2"/><path d="M5 6h6M5 9h4M5 12h5"/></svg></div>
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

        <!-- Scan Schedule -->
        <div v-if="cardId === 'scan_schedule'" class="card feature-card">
          <div class="fc-head">
            <div class="fc-icon"><svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M8 5v3l2 2"/></svg></div>
            <div class="fc-title-wrap"><h3 class="fc-title">DOM Scan Schedule</h3><p class="fc-sub">Configure automatic keyword re-scanning</p></div>
            <button class="fc-remove" @click="removeCard(cardId)" title="Remove">x</button>
          </div>
          <div class="fc-body">
            <div class="scan-config-form">
              <div class="sc-row">
                <label class="sc-label">Auto-scan</label>
                <button class="toggle-btn" :class="{ 'toggle-on': scanConfig.is_auto_scan_enabled }" @click="toggleAutoScan">
                  {{ scanConfig.is_auto_scan_enabled ? 'Enabled' : 'Disabled' }}
                </button>
              </div>
              <div class="sc-row">
                <label class="sc-label">Interval</label>
                <div class="interval-grid">
                  <button v-for="opt in intervalOptions" :key="opt.value" class="interval-btn" :class="{ 'ib-active': scanConfig.scan_interval_hours === opt.value }" @click="setScanInterval(opt.value)">{{ opt.label }}</button>
                </div>
              </div>
              <div class="sc-row">
                <label class="sc-label">Max pages</label>
                <div class="depth-row">
                  <input type="range" min="1" max="20" v-model.number="scanConfig.scan_depth" @change="saveScanConfig" class="depth-slider" />
                  <span class="depth-val">{{ scanConfig.scan_depth }}</span>
                </div>
              </div>
              <div class="sc-meta">
                <span v-if="scanConfig.last_scanned_at">Last scanned: {{ formatDate(scanConfig.last_scanned_at) }}</span>
                <span v-if="scanConfig.next_scan_at"> · Next: {{ formatDate(scanConfig.next_scan_at) }}</span>
                <span v-if="!scanConfig.last_scanned_at" class="text-muted">Not yet scanned</span>
              </div>
              <div class="sc-stats">
                <div class="fc-stat"><span class="fc-stat-val">{{ scanConfig.total_scans || 0 }}</span><span class="fc-stat-lbl">Total Scans</span></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Platform Comparison -->
        <div v-if="cardId === 'platform_comparison'" class="card feature-card">
          <div class="fc-head">
            <div class="fc-icon"><svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="5" height="10" rx="1"/><rect x="9" y="3" width="5" height="10" rx="1"/></svg></div>
            <div class="fc-title-wrap"><h3 class="fc-title">Platform Comparison</h3><p class="fc-sub">Compare site keywords vs social posts</p></div>
            <button class="fc-remove" @click="removeCard(cardId)" title="Remove">x</button>
          </div>
          <div class="fc-body">
            <div class="pc-actions">
              <div class="pc-filter-row">
                <select v-model="pcFilter" class="form-select-sm">
                  <option value="">All platforms</option>
                  <option value="linkedin">LinkedIn</option>
                  <option value="x">X (Twitter)</option>
                  <option value="facebook">Facebook</option>
                  <option value="instagram">Instagram</option>
                  <option value="blog">Blog / Article</option>
                  <option value="other">Other</option>
                </select>
                <button class="btn btn-secondary btn-sm" @click="showAddPostModal = true">+ Add Post</button>
                <button class="btn btn-secondary btn-sm" @click="loadComparison" :disabled="comparisonLoading">{{ comparisonLoading ? 'Loading...' : 'Compare' }}</button>
                <button v-if="comparison" class="btn btn-secondary btn-sm" @click="exportComparison('csv')">CSV</button>
                <button v-if="comparison" class="btn btn-secondary btn-sm" @click="exportComparison('html')">Report</button>
              </div>
            </div>

            <!-- Posts list -->
            <div v-if="platformPosts.length" class="posts-list">
              <div v-for="post in filteredPosts.slice(0, 5)" :key="post.id" class="post-row">
                <div class="post-row-left">
                  <span class="platform-badge" :class="'pb-' + post.platform">{{ post.platform_display }}</span>
                  <span class="post-title">{{ post.title || post.content.slice(0, 60) }}</span>
                </div>
                <button class="btn-icon-danger" @click="deletePost(post.id)" title="Remove">x</button>
              </div>
            </div>
            <div v-else class="fc-empty">No platform posts added yet. Add posts from LinkedIn, X, or other platforms to compare keywords.</div>

            <!-- Comparison results -->
            <div v-if="comparison" class="comparison-results">
              <div class="cr-tabs">
                <button v-for="tab in ['overlap', 'gaps', 'opportunities']" :key="tab" class="cr-tab" :class="{ 'cr-tab-active': compTab === tab }" @click="compTab = tab">
                  {{ tab.charAt(0).toUpperCase() + tab.slice(1) }}
                  <span class="cr-count">{{ comparison[tab]?.length || 0 }}</span>
                </button>
              </div>
              <div class="cr-body">
                <div v-if="compTab === 'overlap'" class="cr-desc">Keywords present on your site AND in your posts</div>
                <div v-if="compTab === 'gaps'" class="cr-desc">Keywords on your site but missing from posts — consider adding to content</div>
                <div v-if="compTab === 'opportunities'" class="cr-desc">Keywords in your posts but not yet on your site — potential content gaps</div>
                <div class="cr-chips">
                  <template v-if="compTab !== 'opportunities'">
                    <span v-for="kw in (comparison[compTab] || [])" :key="kw" class="cr-chip" :class="'cr-' + compTab">{{ kw }}</span>
                  </template>
                  <template v-else>
                    <span v-for="item in (comparison.opportunities || [])" :key="item.keyword" class="cr-chip cr-opp" :title="'Found in: ' + item.platforms.join(', ')">{{ item.keyword }}</span>
                  </template>
                  <span v-if="!comparison[compTab]?.length && compTab !== 'opportunities'" class="text-muted text-sm">None</span>
                  <span v-if="!comparison.opportunities?.length && compTab === 'opportunities'" class="text-muted text-sm">None</span>
                </div>
              </div>
            </div>
          </div>
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
              <div class="embed-label">Paste this in your website's <code>&lt;head&gt;</code> — one snippet for everything:</div>
              <div class="embed-code-wrap">
                <pre class="embed-code">{{ embedCode }}</pre>
                <button class="embed-copy" @click="copyEmbed" :class="{ copied: embedCopied }">{{ embedCopied ? '✓ Copied' : 'Copy' }}</button>
              </div>
              <div class="embed-features">
                <div class="ef-title">What it does:</div>
                <div class="ef-list">
                  <span class="ef-item">✓ Tracks visitors & clicks</span>
                  <span class="ef-item">✓ Heatmap data</span>
                  <span class="ef-item">✓ Schema markup</span>
                  <span class="ef-item">✓ Open Graph tags</span>
                  <span class="ef-item">✓ Canonical URLs</span>
                  <span class="ef-item">✓ hreflang tags</span>
                  <span class="ef-item">✓ Geo meta tags</span>
                  <span class="ef-item">✓ Title optimization</span>
                </div>
              </div>
            </div>
            <div v-else class="fc-empty">Loading embed code...</div>
          </div>
        </div>

        <!-- Keyword Alerts -->
        <div v-if="cardId === 'keyword_alerts'" class="card feature-card kw-alert-card">
          <div class="fc-head">
            <div class="fc-icon alert-bell-icon">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2a5 5 0 015 5v2l1 2H2l1-2V7a5 5 0 015-5z"/><path d="M6.5 13.5a1.5 1.5 0 003 0"/></svg>
              <span v-if="alertEvents.length" class="bell-dot"></span>
            </div>
            <div class="fc-title-wrap">
              <h3 class="fc-title">Keyword Alerts</h3>
              <p class="fc-sub">Get notified when rankings move significantly</p>
            </div>
            <div style="display:flex;align-items:center;gap:6px">
              <button class="al-add-btn" @click="showInlineAlertForm = !showInlineAlertForm" :class="{ 'al-add-active': showInlineAlertForm }">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2"><line x1="6" y1="1" x2="6" y2="11"/><line x1="1" y1="6" x2="11" y2="6"/></svg>
                New rule
              </button>
              <button class="fc-remove" @click="removeCard(cardId)" title="Remove">×</button>
            </div>
          </div>

          <!-- Inline Create Form (slide-in) -->
          <transition name="alert-form-slide">
            <div v-if="showInlineAlertForm" class="al-inline-form">
              <div class="al-form-title">Create alert rule</div>
              <div class="al-form-grid">
                <div class="al-field">
                  <label class="al-label">Keyword</label>
                  <select v-model="newAlert.tracked_keyword_id" class="al-select">
                    <option value="">All tracked keywords</option>
                    <option v-for="kw in keywords" :key="kw.id" :value="kw.id">{{ kw.keyword }}</option>
                  </select>
                </div>
                <div class="al-field al-field-sm">
                  <label class="al-label">Threshold</label>
                  <div class="al-threshold-row">
                    <button class="al-step-btn" @click="newAlert.threshold = Math.max(1, newAlert.threshold - 1)">−</button>
                    <span class="al-threshold-val">{{ newAlert.threshold }}</span>
                    <button class="al-step-btn" @click="newAlert.threshold = Math.min(50, newAlert.threshold + 1)">+</button>
                    <span class="al-threshold-unit">positions</span>
                  </div>
                </div>
              </div>
              <div class="al-form-row2">
                <div class="al-pill-group">
                  <span class="al-pill-label">Direction</span>
                  <button v-for="opt in [{ v: 'any', l: 'Any' }, { v: 'improved', l: 'Improved' }, { v: 'declined', l: 'Declined' }]"
                    :key="opt.v"
                    class="al-pill" :class="{ 'al-pill-active': newAlert.direction === opt.v }"
                    @click="newAlert.direction = opt.v">{{ opt.l }}</button>
                </div>
                <div class="al-pill-group">
                  <span class="al-pill-label">Notify via</span>
                  <button v-for="opt in [{ v: 'email', l: 'Email' }, { v: 'in_app', l: 'In-app' }]"
                    :key="opt.v"
                    class="al-pill" :class="{ 'al-pill-active': newAlert.notification_method === opt.v }"
                    @click="newAlert.notification_method = opt.v">{{ opt.l }}</button>
                </div>
              </div>
              <div v-if="addAlertError" class="al-form-error">{{ addAlertError }}</div>
              <div class="al-form-actions">
                <button class="al-cancel-btn" @click="showInlineAlertForm = false; addAlertError = ''">Cancel</button>
                <button class="al-save-btn" @click="addAlert" :disabled="addingAlert">
                  <svg v-if="addingAlert" class="al-spinner" width="12" height="12" viewBox="0 0 12 12"><circle cx="6" cy="6" r="4" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="16" stroke-dashoffset="6" opacity="0.4"/></svg>
                  {{ addingAlert ? 'Saving…' : 'Create rule' }}
                </button>
              </div>
            </div>
          </transition>

          <div class="fc-body">

            <!-- Active Rules -->
            <div v-if="alerts.length" class="al-rules-section">
              <div class="al-section-label">
                <span>Active rules</span>
                <span class="al-count-badge">{{ alerts.filter(a => a.is_active).length }}</span>
              </div>
              <div class="al-rules-list">
                <div v-for="al in alerts" :key="al.id" class="al-rule-item" :class="{ 'al-rule-muted': !al.is_active }">
                  <div class="al-rule-left">
                    <div class="al-rule-kw">
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M5 1a3.5 3.5 0 013.5 3.5v1L10 7H0l1.5-2.5V4.5A3.5 3.5 0 015 1z"/><path d="M3.5 8.5a1.5 1.5 0 003 0"/></svg>
                      {{ al.keyword }}
                    </div>
                    <div class="al-rule-meta">
                      <span class="al-badge al-badge-threshold">{{ '>' }}{{ al.threshold }} pos</span>
                      <span class="al-badge" :class="{
                        'al-badge-any': al.direction === 'any',
                        'al-badge-up': al.direction === 'improved',
                        'al-badge-down': al.direction === 'declined'
                      }">{{ al.direction }}</span>
                      <span class="al-badge al-badge-method">
                        <svg v-if="al.notification_method === 'email'" width="9" height="9" viewBox="0 0 9 9" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="0.5" y="1.5" width="8" height="6" rx="1"/><path d="M0.5 2.5l4 3 4-3"/></svg>
                        <svg v-else width="9" height="9" viewBox="0 0 9 9" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4.5 1a3 3 0 013 3v1L9 7H0l1.5-2V4a3 3 0 013-3z"/></svg>
                        {{ al.notification_method === 'email' ? 'Email' : 'In-app' }}
                      </span>
                    </div>
                  </div>
                  <div class="al-rule-right">
                    <button class="al-toggle" :class="{ 'al-toggle-on': al.is_active }" @click="toggleAlert(al)" :title="al.is_active ? 'Disable' : 'Enable'">
                      <span class="al-toggle-knob"></span>
                    </button>
                    <button class="al-delete-btn" @click="deleteAlert(al.id)" title="Delete rule">
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5"><line x1="2" y1="2" x2="10" y2="10"/><line x1="10" y1="2" x2="2" y2="10"/></svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Recent Trigger Events -->
            <div v-if="alertEvents.length" class="al-events-section">
              <div class="al-section-label" style="margin-top:14px">
                <span>Recent triggers</span>
                <span class="al-count-badge al-count-orange">{{ alertEvents.length }}</span>
              </div>
              <div class="al-events-list">
                <div v-for="ev in alertEvents.slice(0, 6)" :key="ev.id" class="al-event-item">
                  <div class="al-event-icon" :class="ev.direction === 'improved' ? 'al-ei-up' : 'al-ei-down'">
                    <svg v-if="ev.direction === 'improved'" width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="2"><polyline points="2,7 5,3 8,7"/></svg>
                    <svg v-else width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="2"><polyline points="2,3 5,7 8,3"/></svg>
                  </div>
                  <div class="al-event-body">
                    <span class="al-event-kw">{{ ev.keyword }}</span>
                    <span class="al-event-detail">
                      {{ ev.direction === 'improved' ? 'climbed' : 'dropped' }}
                      <strong>{{ Math.abs(ev.change) }} positions</strong>
                      <span class="al-rank-change">
                        #{{ ev.old_rank }} → #{{ ev.new_rank }}
                      </span>
                    </span>
                  </div>
                  <span class="al-event-time">{{ formatDate(ev.triggered_at) }}</span>
                </div>
              </div>
            </div>

            <!-- Empty state -->
            <div v-if="!alerts.length && !alertEvents.length" class="al-empty-state">
              <div class="al-empty-icon">
                <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="var(--text-muted)" stroke-width="1.2"><path d="M14 4a8 8 0 018 8v3l2 3H4l2-3v-3a8 8 0 018-8z"/><path d="M11 22a3 3 0 006 0"/></svg>
              </div>
              <p class="al-empty-text">No alert rules yet.</p>
              <p class="al-empty-sub">Click <strong>New rule</strong> above to get notified when keywords move.</p>
            </div>

          </div>
        </div>

        <!-- Competitor Tracking -->
        <div v-if="cardId === 'competitor_tracking'" class="card feature-card ct-card">
          <div class="fc-head">
            <div class="fc-icon">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="5" cy="5.5" r="2.5"/><circle cx="11" cy="5.5" r="2.5"/><path d="M5 8v5M11 8v5M8 9v4"/></svg>
            </div>
            <div class="fc-title-wrap">
              <h3 class="fc-title">Competitor Tracking</h3>
              <p class="fc-sub">Rank comparison against competitor domains</p>
            </div>
            <div style="display:flex;align-items:center;gap:6px">
              <button class="al-add-btn" @click="showAddCompetitorModal = true">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2"><line x1="6" y1="1" x2="6" y2="11"/><line x1="1" y1="6" x2="11" y2="6"/></svg>
                Add
              </button>
              <button class="fc-remove" @click="removeCard(cardId)" title="Remove">×</button>
            </div>
          </div>
          <div class="fc-body">

            <!-- Competitors list -->
            <div v-if="competitors.length" class="ct-list">
              <div v-for="c in competitors" :key="c.id" class="ct-row">
                <div class="ct-favicon">
                  <img :src="`https://www.google.com/s2/favicons?domain=${c.domain}&sz=20`" width="16" height="16" :alt="c.domain" @error="$event.target.style.display='none'" />
                </div>
                <div class="ct-info">
                  <span class="ct-name">{{ c.name || c.domain }}</span>
                  <span class="ct-domain">{{ c.domain }}</span>
                </div>
                <div class="ct-status" v-if="c.last_checked_at">
                  <span class="ct-last-check">Checked {{ formatDate(c.last_checked_at) }}</span>
                </div>
                <div class="ct-actions">
                  <button class="ct-refresh-btn" @click="refreshCompetitor(c.id)" :disabled="competitorLoading === c.id" :class="{ 'ct-refreshing': competitorLoading === c.id }">
                    <svg width="11" height="11" viewBox="0 0 11 11" fill="none" stroke="currentColor" stroke-width="1.8" :class="{ 'ct-spin': competitorLoading === c.id }"><path d="M10 5.5a4.5 4.5 0 11-3.1-4.28"/><path d="M10 1v3H7"/></svg>
                    {{ competitorLoading === c.id ? 'Checking' : 'Refresh' }}
                  </button>
                  <button class="al-delete-btn" @click="deleteCompetitor(c.id)">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5"><line x1="2" y1="2" x2="10" y2="10"/><line x1="10" y1="2" x2="2" y2="10"/></svg>
                  </button>
                </div>
              </div>
            </div>

            <div v-if="!competitors.length" class="al-empty-state">
              <div class="al-empty-icon">
                <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="var(--text-muted)" stroke-width="1.2"><circle cx="10" cy="10" r="5"/><circle cx="20" cy="10" r="5"/><path d="M10 15v8M20 15v8M15 17v6"/></svg>
              </div>
              <p class="al-empty-text">No competitors tracked yet.</p>
              <p class="al-empty-sub">Click <strong>Add</strong> to compare your rankings side-by-side.</p>
            </div>

            <!-- Overlap comparison table -->
            <div v-if="competitors.length" class="ct-compare-row">
              <button class="ct-compare-btn" @click="loadCompetitorOverlap" :disabled="!competitors.length">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="1" width="4" height="10" rx="1"/><rect x="7" y="1" width="4" height="10" rx="1"/></svg>
                Compare rankings
              </button>
            </div>

            <div v-if="competitorOverlap" class="ct-overlap-table">
              <div class="al-section-label" style="margin-top:14px">
                <span>Side-by-side ranking comparison</span>
              </div>
              <div class="table-responsive">
                <table class="data-table data-table-sm">
                  <thead>
                    <tr>
                      <th>Keyword</th>
                      <th class="text-center ct-us-col">
                        <span class="ct-us-label">Us</span>
                      </th>
                      <th v-for="c in competitorOverlap.competitors" :key="c.id" class="text-center">{{ c.name }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in competitorOverlap.keywords" :key="row.keyword">
                      <td class="ct-kw-cell">{{ row.keyword }}</td>
                      <td class="text-center">
                        <span class="rank-badge" :class="rankClass(row.our_rank)">{{ row.our_rank || '--' }}</span>
                      </td>
                      <td v-for="c in row.competitors" :key="c.id" class="text-center">
                        <span class="rank-badge" :class="rankClass(c.rank)">{{ c.rank || '--' }}</span>
                        <span v-if="row.our_rank && c.rank" class="ct-rank-delta" :class="c.rank > row.our_rank ? 'ct-delta-win' : c.rank < row.our_rank ? 'ct-delta-lose' : ''">
                          {{ c.rank > row.our_rank ? 'ahead' : c.rank < row.our_rank ? 'behind' : 'tied' }}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        </div>

        <!-- Historical Trend Charts -->
        <div v-if="cardId === 'history_charts'" class="card feature-card hc-card" style="grid-column: span 2">
          <div class="fc-head">
            <div class="fc-icon">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><polyline points="2,12 5,7 9,9 13,4"/><circle cx="5" cy="7" r="1.5" fill="currentColor"/><circle cx="9" cy="9" r="1.5" fill="currentColor"/><circle cx="13" cy="4" r="1.5" fill="currentColor"/></svg>
            </div>
            <div class="fc-title-wrap">
              <h3 class="fc-title">Historical Rank Charts</h3>
              <p class="fc-sub">Track position changes over the last 30 days</p>
            </div>
            <button class="fc-remove" @click="removeCard(cardId)" title="Remove">×</button>
          </div>
          <div class="fc-body">
            <div v-if="!keywords.length" class="al-empty-state">
              <div class="al-empty-icon">
                <svg width="30" height="30" viewBox="0 0 30 30" fill="none" stroke="var(--text-muted)" stroke-width="1.2"><polyline points="3,22 8,13 14,16 20,8 27,4"/></svg>
              </div>
              <p class="al-empty-text">No tracked keywords.</p>
              <p class="al-empty-sub">Add keywords in Position Tracking, then scan to populate rank history.</p>
            </div>
            <template v-else>
              <!-- Keyword selector -->
              <div class="hc-controls">
                <span class="al-section-label" style="margin-bottom:0">Select up to 5 keywords</span>
                <div class="hc-kw-row">
                  <button
                    v-for="kw in keywords.slice(0, 12)"
                    :key="kw.id"
                    class="hc-kw-chip"
                    :class="{ 'hc-chip-active': selectedChartKws.includes(kw.id), 'hc-chip-disabled': !selectedChartKws.includes(kw.id) && selectedChartKws.length >= 5 }"
                    :style="selectedChartKws.includes(kw.id) ? { borderColor: chartColors[selectedChartKws.indexOf(kw.id) % chartColors.length], color: chartColors[selectedChartKws.indexOf(kw.id) % chartColors.length], background: chartColors[selectedChartKws.indexOf(kw.id) % chartColors.length] + '18' } : {}"
                    @click="toggleChartKw(kw.id)"
                  >
                    <span class="hc-chip-dot" v-if="selectedChartKws.includes(kw.id)" :style="{ background: chartColors[selectedChartKws.indexOf(kw.id) % chartColors.length] }"></span>
                    {{ kw.keyword }}
                    <span v-if="kw.current_rank" class="hc-chip-rank">#{{ kw.current_rank }}</span>
                  </button>
                </div>
              </div>

              <div v-if="chartLoading" class="hc-loading">
                <div class="hc-loading-bar"></div>
                <span>Loading history…</span>
              </div>

              <div v-else-if="chartDatasets.length" class="hc-chart-area">
                <div class="hc-note">Lower position number = better ranking. Y-axis: rank #1 (top) to #50 (bottom).</div>
                <svg class="rank-chart" :viewBox="`0 0 ${chartW} ${chartH}`" preserveAspectRatio="xMidYMid meet">
                  <!-- Y axis grid lines + labels -->
                  <g v-for="gridY in chartGridY" :key="gridY.rank">
                    <line :x1="chartPadL" :y1="gridY.y" :x2="chartW - chartPadR" :y2="gridY.y"
                      :stroke="gridY.rank === 1 ? 'var(--brand-accent)' : 'var(--border-color)'"
                      :stroke-width="gridY.rank === 1 ? 1 : 0.5"
                      stroke-dasharray="3,3"
                    />
                    <text :x="chartPadL - 5" :y="gridY.y + 4" text-anchor="end" font-size="9" fill="var(--text-muted)">#{{ gridY.rank }}</text>
                  </g>
                  <!-- X axis labels -->
                  <g v-for="(label, i) in chartXLabels" :key="i">
                    <text :x="label.x" :y="chartH - 4" text-anchor="middle" font-size="8" fill="var(--text-muted)">{{ label.text }}</text>
                  </g>
                  <!-- Area fills (subtle) -->
                  <g v-for="(ds, di) in chartDatasets" :key="'area-' + ds.id">
                    <polygon
                      v-if="ds.areaPoints"
                      :points="ds.areaPoints"
                      :fill="chartColors[di % chartColors.length]"
                      fill-opacity="0.06"
                    />
                  </g>
                  <!-- Lines -->
                  <g v-for="(ds, di) in chartDatasets" :key="'line-' + ds.id">
                    <polyline
                      :points="ds.points"
                      fill="none"
                      :stroke="chartColors[di % chartColors.length]"
                      stroke-width="2"
                      stroke-linejoin="round"
                      stroke-linecap="round"
                    />
                  </g>
                  <!-- Dots with hover tooltip -->
                  <g v-for="(ds, di) in chartDatasets" :key="'dots-' + ds.id">
                    <g v-for="(pt, pi) in ds.dots" :key="pi" class="chart-dot-group" @mouseenter="showChartTip(pt, ds, di)" @mouseleave="hideChartTip">
                      <circle :cx="pt.x" :cy="pt.y" r="5" :fill="chartColors[di % chartColors.length]" fill-opacity="0" />
                      <circle :cx="pt.x" :cy="pt.y" r="3" :fill="chartColors[di % chartColors.length]" />
                    </g>
                  </g>
                  <!-- Tooltip -->
                  <g v-if="chartTip" :transform="`translate(${Math.min(chartTip.x, chartW - 90)}, ${Math.max(chartTip.y - 36, chartPadT)})`">
                    <rect x="0" y="0" width="82" height="28" rx="4" fill="var(--bg-card)" stroke="var(--border-color)" stroke-width="1"/>
                    <text x="6" y="11" font-size="9" fill="var(--text-muted)">{{ chartTip.date }}</text>
                    <text x="6" y="23" font-size="11" font-weight="700" :fill="chartTip.color">#{{ chartTip.rank }} · {{ chartTip.keyword }}</text>
                  </g>
                </svg>
                <!-- Legend -->
                <div class="hc-legend">
                  <div v-for="(ds, di) in chartDatasets" :key="ds.id" class="hc-legend-item">
                    <span class="hc-legend-line" :style="{ background: chartColors[di % chartColors.length] }"></span>
                    <span class="hc-legend-kw">{{ ds.keyword }}</span>
                    <span v-if="ds.currentRank" class="hc-legend-rank" :style="{ color: chartColors[di % chartColors.length] }">#{{ ds.currentRank }}</span>
                  </div>
                </div>
              </div>

              <div v-else-if="!chartLoading && selectedChartKws.length" class="al-empty-state">
                <p class="al-empty-text">No rank history yet for selected keywords.</p>
                <p class="al-empty-sub">Run a site scan to populate data.</p>
              </div>
              <div v-else-if="!selectedChartKws.length" class="al-empty-state" style="padding:16px">
                <p class="al-empty-sub">Select one or more keywords above to see rank history.</p>
              </div>
            </template>
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

    <!-- Add Competitor Modal -->
    <Teleport to="body">
      <div v-if="showAddCompetitorModal" class="modal-overlay" @click.self="showAddCompetitorModal = false">
        <div class="modal-card">
          <h3 class="modal-title">Add Competitor</h3>
          <div class="modal-body">
            <label class="form-label">Domain</label>
            <input v-model="newCompetitor.domain" class="form-input" placeholder="e.g. competitor.com" autofocus />
            <label class="form-label" style="margin-top:12px">Label (optional)</label>
            <input v-model="newCompetitor.name" class="form-input" placeholder="e.g. Main rival" />
            <p v-if="addCompetitorError" class="text-danger text-sm" style="margin-top:8px">{{ addCompetitorError }}</p>
          </div>
          <div class="modal-actions">
            <button class="btn btn-secondary" @click="showAddCompetitorModal = false">Cancel</button>
            <button class="btn btn-primary" @click="addCompetitor" :disabled="addingCompetitor">{{ addingCompetitor ? 'Adding...' : 'Add' }}</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Add Platform Post Modal -->
    <Teleport to="body">
      <div v-if="showAddPostModal" class="modal-overlay" @click.self="showAddPostModal = false">
        <div class="modal-card">
          <h3 class="modal-title">Add Platform Post</h3>
          <div class="modal-body">
            <label class="form-label">Platform</label>
            <select v-model="newPost.platform" class="form-input">
              <option value="linkedin">LinkedIn</option>
              <option value="x">X (Twitter)</option>
              <option value="facebook">Facebook</option>
              <option value="instagram">Instagram</option>
              <option value="blog">Blog / Article</option>
              <option value="other">Other</option>
            </select>
            <label class="form-label" style="margin-top:12px">Title (optional)</label>
            <input v-model="newPost.title" class="form-input" placeholder="Post title or headline" />
            <label class="form-label" style="margin-top:12px">Content</label>
            <textarea v-model="newPost.content" class="form-input" rows="5" placeholder="Paste the post text here..." style="resize:vertical"></textarea>
            <label class="form-label" style="margin-top:12px">URL (optional)</label>
            <input v-model="newPost.url" class="form-input" placeholder="https://..." />
            <p v-if="addPostError" class="text-danger text-sm" style="margin-top:8px">{{ addPostError }}</p>
          </div>
          <div class="modal-actions">
            <button class="btn btn-secondary" @click="showAddPostModal = false">Cancel</button>
            <button class="btn btn-primary" @click="addPost" :disabled="addingPost">{{ addingPost ? 'Adding...' : 'Add Post' }}</button>
          </div>
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

// Scan config
const scanConfig = ref({ is_auto_scan_enabled: true, scan_interval_hours: 24, scan_depth: 5, last_scanned_at: null, next_scan_at: null, total_scans: 0 })
const intervalOptions = [
  { value: 1, label: 'Hourly' },
  { value: 6, label: 'Every 6h' },
  { value: 24, label: 'Daily' },
  { value: 168, label: 'Weekly' },
]

// Platform comparison
const platformPosts = ref([])
const pcFilter = ref('')
const comparison = ref(null)
const comparisonLoading = ref(false)
const compTab = ref('gaps')
const showAddPostModal = ref(false)
const newPost = ref({ platform: 'linkedin', title: '', content: '', url: '' })
const addingPost = ref(false)
const addPostError = ref('')

const filteredPosts = computed(() => {
  if (!pcFilter.value) return platformPosts.value
  return platformPosts.value.filter(p => p.platform === pcFilter.value)
})

// Alerts
const alerts = ref([])
const alertEvents = ref([])
const showInlineAlertForm = ref(false)
const addingAlert = ref(false)
const addAlertError = ref('')
const newAlert = ref({ tracked_keyword_id: '', threshold: 3, direction: 'any', notification_method: 'email' })

// Competitors
const competitors = ref([])
const competitorOverlap = ref(null)
const competitorLoading = ref(null)
const showAddCompetitorModal = ref(false)
const addingCompetitor = ref(false)
const addCompetitorError = ref('')
const newCompetitor = ref({ domain: '', name: '' })

// History chart
const selectedChartKws = ref([])
const chartLoading = ref(false)
const chartDatasets = ref([])
const chartTip = ref(null)
const chartW = 560
const chartH = 220
const chartPadL = 36
const chartPadR = 10
const chartPadB = 20
const chartPadT = 12
const chartColors = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4', '#a855f7', '#ec4899', '#14b8a6']

// Computed chart grid / axes
const chartGridY = computed(() => {
  const ranks = [1, 5, 10, 20, 50]
  const maxRank = 50
  return ranks.map(r => ({
    rank: r,
    y: chartPadT + ((r - 1) / (maxRank - 1)) * (chartH - chartPadT - chartPadB),
  }))
})
const chartXLabels = computed(() => {
  if (!chartDatasets.value.length) return []
  const dates = chartDatasets.value[0]?.dates || []
  if (!dates.length) return []
  const step = Math.max(1, Math.floor(dates.length / 5))
  return dates.reduce((acc, d, i) => {
    if (i % step === 0 || i === dates.length - 1) {
      const x = chartPadL + (i / (dates.length - 1 || 1)) * (chartW - chartPadL - chartPadR)
      acc.push({ x, text: d.slice(5) }) // MM-DD
    }
    return acc
  }, [])
})

// Card system
const STORAGE_KEY = 'ftb_kw_cards'
const availableCards = [
  { id: 'site_audit', name: 'Site Audit', desc: 'Scan for SEO issues and get your health score', icon: 'SA' },
  { id: 'keyword_research', name: 'Keyword Research', desc: 'Discover keyword ideas with search volume and difficulty', icon: 'KR' },
  { id: 'ai_analysis', name: 'AI Analysis', desc: 'Track your visibility across AI engines', icon: 'AI' },
  { id: 'competitive', name: 'Competitive Research', desc: 'Compare your site against top competitors', icon: 'CR' },
  { id: 'content_ideas', name: 'Content Ideas', desc: 'Find trending topics and keyword alternatives', icon: 'CI' },
  { id: 'position_tracking', name: 'Position Tracking', desc: 'Monitor keyword rankings in Google and AI', icon: 'PT' },
  { id: 'serp_data', name: 'Google SERP Data', desc: 'Real rankings, volume, CPC via DataForSEO', icon: 'SD' },
  { id: 'geo_seo', name: 'Geo SEO & Tagging', desc: 'Regional optimization and geo tag detection', icon: 'GS' },
  { id: 'seo_optimizer', name: 'Dynamic SEO Optimizer', desc: 'Auto-optimize schema, OG, canonical on your live site', icon: 'SO' },
  { id: 'pages_scanned', name: 'Pages Scanned', desc: 'Per-page keyword breakdown', icon: 'PS' },
  { id: 'scan_schedule', name: 'DOM Scan Schedule', desc: 'Configure automatic keyword re-scanning intervals', icon: 'SC' },
  { id: 'platform_comparison', name: 'Platform Comparison', desc: 'Compare site keywords vs LinkedIn, X, and other posts', icon: 'PC' },
  { id: 'keyword_alerts', name: 'Keyword Alerts', desc: 'Get notified when keywords move more than N positions', icon: 'AL' },
  { id: 'competitor_tracking', name: 'Competitor Tracking', desc: 'Track how competitors rank for your keywords', icon: 'CT' },
  { id: 'history_charts', name: 'Historical Charts', desc: 'Visualize keyword rank trends over time', icon: 'HC' },
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

function cleanPagePath(url) { if (!url) return url; try { const u = new URL(url); return u.pathname === '/' ? '/ (Homepage)' : u.pathname } catch { return url } }
function rankClass(rank) { if (!rank) return ''; if (rank <= 3) return 'rank-top3'; if (rank <= 10) return 'rank-top10'; if (rank <= 20) return 'rank-top20'; return 'rank-low' }
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

// Alert functions
async function loadAlerts() {
  try {
    const [ra, re] = await Promise.all([
      analyticsApi.getAlerts(props.websiteId),
      analyticsApi.getAlertEvents(props.websiteId),
    ])
    alerts.value = ra.data || []
    alertEvents.value = re.data || []
  } catch (e) {}
}
async function addAlert() {
  addingAlert.value = true; addAlertError.value = ''
  try {
    const payload = { ...newAlert.value }
    if (!payload.tracked_keyword_id) delete payload.tracked_keyword_id
    await analyticsApi.createAlert(props.websiteId, payload)
    await loadAlerts()
    showInlineAlertForm.value = false
    newAlert.value = { tracked_keyword_id: '', threshold: 3, direction: 'any', notification_method: 'email' }
  } catch (e) { addAlertError.value = e?.response?.data?.error || 'Failed to create alert' }
  finally { addingAlert.value = false }
}
async function toggleAlert(al) {
  try { await analyticsApi.updateAlert(props.websiteId, al.id, { is_active: !al.is_active }); await loadAlerts() } catch (e) {}
}
async function deleteAlert(aid) {
  try { await analyticsApi.deleteAlert(props.websiteId, aid); await loadAlerts() } catch (e) {}
}

// Competitor functions
async function loadCompetitors() {
  try { const res = await analyticsApi.getCompetitors(props.websiteId); competitors.value = res.data || [] } catch (e) {}
}
async function addCompetitor() {
  addingCompetitor.value = true; addCompetitorError.value = ''
  try {
    await analyticsApi.addCompetitor(props.websiteId, newCompetitor.value)
    await loadCompetitors()
    showAddCompetitorModal.value = false
    newCompetitor.value = { domain: '', name: '' }
  } catch (e) { addCompetitorError.value = e?.response?.data?.error || 'Failed to add competitor' }
  finally { addingCompetitor.value = false }
}
async function deleteCompetitor(cid) {
  try { await analyticsApi.deleteCompetitor(props.websiteId, cid); await loadCompetitors(); competitorOverlap.value = null } catch (e) {}
}
async function refreshCompetitor(cid) {
  competitorLoading.value = cid
  try { await analyticsApi.refreshCompetitor(props.websiteId, cid) } catch (e) {}
  finally { competitorLoading.value = null }
}
async function loadCompetitorOverlap() {
  try { const res = await analyticsApi.getCompetitorOverlap(props.websiteId); competitorOverlap.value = res.data } catch (e) {}
}

// Export comparison
function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 5000)
}
async function exportComparison(fmt) {
  try {
    const res = await analyticsApi.exportComparison(props.websiteId, fmt)
    downloadBlob(res.data, `keyword-gap-report.${fmt}`)
  } catch (e) {}
}

// History chart functions
async function toggleChartKw(kwId) {
  const idx = selectedChartKws.value.indexOf(kwId)
  if (idx >= 0) selectedChartKws.value.splice(idx, 1)
  else if (selectedChartKws.value.length < 5) selectedChartKws.value.push(kwId)
  await buildChartDatasets()
}
async function buildChartDatasets() {
  if (!selectedChartKws.value.length) { chartDatasets.value = []; return }
  chartLoading.value = true
  try {
    const results = await Promise.all(
      selectedChartKws.value.map(id => analyticsApi.keywordHistory(props.websiteId, id))
    )
    const maxRank = 50
    chartDatasets.value = results.map((res, i) => {
      const kwId = selectedChartKws.value[i]
      const kw = keywords.value.find(k => k.id === kwId)
      const history = (res.data?.history || []).slice(-30)
      const dates = history.map(h => h.date)
      const n = dates.length
      const bottom = chartPadT + chartH - chartPadB
      const dots = history.map((h, j) => {
        const rank = Math.min(h.rank || maxRank, maxRank)
        const x = chartPadL + (n > 1 ? (j / (n - 1)) : 0.5) * (chartW - chartPadL - chartPadR)
        const y = chartPadT + ((rank - 1) / (maxRank - 1)) * (chartH - chartPadT - chartPadB)
        return { x, y, rank: h.rank, date: h.date }
      })
      const points = dots.map(d => `${d.x},${d.y}`).join(' ')
      // Area: line points + bottom-right + bottom-left to close
      const areaPoints = dots.length
        ? `${points} ${dots[dots.length - 1].x},${bottom} ${dots[0].x},${bottom}`
        : ''
      return {
        id: kwId,
        keyword: kw?.keyword || kwId,
        currentRank: kw?.current_rank,
        dates,
        dots,
        points,
        areaPoints,
      }
    })
  } catch (e) { chartDatasets.value = [] }
  finally { chartLoading.value = false }
}

function showChartTip(pt, ds, di) {
  chartTip.value = { x: pt.x, y: pt.y, rank: pt.rank, date: pt.date, keyword: ds.keyword, color: chartColors[di % chartColors.length] }
}
function hideChartTip() { chartTip.value = null }

// Scan config functions
async function loadScanConfig() {
  try { const res = await analyticsApi.getScanConfig(props.websiteId); scanConfig.value = res.data } catch (e) {}
}
async function saveScanConfig() {
  try { const res = await analyticsApi.updateScanConfig(props.websiteId, scanConfig.value); scanConfig.value = res.data } catch (e) {}
}
async function toggleAutoScan() {
  scanConfig.value.is_auto_scan_enabled = !scanConfig.value.is_auto_scan_enabled
  await saveScanConfig()
}
async function setScanInterval(hours) {
  scanConfig.value.scan_interval_hours = hours
  await saveScanConfig()
}
function formatDate(iso) {
  if (!iso) return ''
  try { return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) } catch { return iso }
}

// Platform content functions
async function loadPlatformPosts() {
  try { const res = await analyticsApi.getPlatformContent(props.websiteId); platformPosts.value = res.data || [] } catch (e) {}
}
async function addPost() {
  if (!newPost.value.content.trim()) return
  addingPost.value = true; addPostError.value = ''
  try {
    await analyticsApi.addPlatformContent(props.websiteId, newPost.value)
    await loadPlatformPosts()
    showAddPostModal.value = false
    newPost.value = { platform: 'linkedin', title: '', content: '', url: '' }
  } catch (e) { addPostError.value = e?.response?.data?.error || 'Failed to add post' }
  finally { addingPost.value = false }
}
async function deletePost(pid) {
  try { await analyticsApi.deletePlatformContent(props.websiteId, pid); await loadPlatformPosts() } catch (e) {}
}
async function loadComparison() {
  comparisonLoading.value = true
  try { const res = await analyticsApi.keywordComparison(props.websiteId); comparison.value = res.data } catch (e) {}
  finally { comparisonLoading.value = false }
}

onMounted(async () => {
  loadCards()
  await fetchKeywords()
  try { const res = await analyticsApi.keywordScan(props.websiteId); const d = res.data?.data || res.data || {}; if (d.score != null) scanData.value = d } catch (e) {}
  // Fetch embed code
  try { const res = await analyticsApi.seoEmbed(props.websiteId); embedCode.value = res.data?.data?.embed_code || '' } catch (e) {}
  await Promise.all([loadScanConfig(), loadPlatformPosts(), loadAlerts(), loadCompetitors()])
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

/* Scan Schedule Card */
.scan-config-form { display: flex; flex-direction: column; gap: 12px; }
.sc-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.sc-label { font-size: 11px; font-weight: 700; color: var(--text-primary); width: 80px; flex-shrink: 0; text-transform: uppercase; letter-spacing: 0.03em; }
.toggle-btn { padding: 4px 14px; border-radius: var(--radius-full); border: 1px solid var(--border-color); font-size: 11px; font-weight: 700; cursor: pointer; background: var(--bg-surface); color: var(--text-muted); transition: all 0.15s; }
.toggle-on { background: rgba(99,102,241,0.12); border-color: var(--brand-accent); color: var(--brand-accent); }
.interval-grid { display: flex; gap: 4px; flex-wrap: wrap; }
.interval-btn { padding: 3px 10px; border-radius: var(--radius-full); border: 1px solid var(--border-color); font-size: 10px; font-weight: 600; cursor: pointer; background: var(--bg-surface); color: var(--text-muted); transition: all 0.15s; }
.ib-active { background: var(--brand-accent); border-color: var(--brand-accent); color: white; }
.depth-row { display: flex; align-items: center; gap: 8px; flex: 1; }
.depth-slider { flex: 1; accent-color: var(--brand-accent); }
.depth-val { font-size: 12px; font-weight: 700; color: var(--brand-accent); min-width: 20px; }
.sc-meta { font-size: 10px; color: var(--text-muted); }
.sc-stats { display: flex; gap: 8px; }

/* Platform Comparison Card */
.pc-actions { margin-bottom: 10px; }
.pc-filter-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.form-select-sm { height: 32px; padding: 0 8px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-surface); color: var(--text-primary); font-size: 12px; }
.posts-list { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
.post-row { display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); }
.post-row-left { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0; }
.platform-badge { font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: var(--radius-full); background: rgba(99,102,241,0.1); color: var(--brand-accent); flex-shrink: 0; text-transform: uppercase; }
.pb-linkedin { background: rgba(10,102,194,0.1); color: #0a66c2; }
.pb-x { background: rgba(0,0,0,0.06); color: var(--text-primary); }
.pb-facebook { background: rgba(24,119,242,0.1); color: #1877f2; }
.pb-instagram { background: rgba(225,48,108,0.1); color: #e1306c; }
.pb-blog { background: rgba(34,197,94,0.1); color: #16a34a; }
.post-title { font-size: 11px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.btn-icon-danger { width: 22px; height: 22px; border: none; background: transparent; color: var(--text-muted); font-size: 16px; cursor: pointer; border-radius: 4px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.btn-icon-danger:hover { background: rgba(239,68,68,0.1); color: #ef4444; }
.comparison-results { border-top: 1px solid var(--border-color); padding-top: 10px; margin-top: 8px; }
.cr-tabs { display: flex; gap: 4px; margin-bottom: 8px; }
.cr-tab { flex: 1; padding: 5px; font-size: 10px; font-weight: 700; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-surface); cursor: pointer; color: var(--text-muted); display: flex; align-items: center; justify-content: center; gap: 4px; }
.cr-tab-active { border-color: var(--brand-accent); background: rgba(99,102,241,0.08); color: var(--brand-accent); }
.cr-count { background: var(--bg-card); border-radius: 10px; padding: 0 5px; font-size: 9px; }
.cr-desc { font-size: 10px; color: var(--text-muted); margin-bottom: 8px; line-height: 1.4; }
.cr-chips { display: flex; flex-wrap: wrap; gap: 4px; }
.cr-chip { font-size: 10px; padding: 2px 8px; border-radius: var(--radius-full); font-weight: 600; }
.cr-overlap { background: rgba(99,102,241,0.1); color: var(--brand-accent); }
.cr-gaps { background: rgba(245,158,11,0.1); color: #d97706; }
.cr-opp { background: rgba(34,197,94,0.1); color: #16a34a; }

/* ── Keyword Alert Card ───────────────────────────────────────────────── */
.kw-alert-card { position: relative; overflow: visible; }

/* Bell icon with notification dot */
.alert-bell-icon { position: relative; display: flex; align-items: center; justify-content: center; }
.bell-dot { position: absolute; top: -2px; right: -2px; width: 7px; height: 7px; border-radius: 50%; background: #ef4444; border: 1.5px solid var(--bg-card); animation: bell-pulse 2s infinite; }
@keyframes bell-pulse { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.3); opacity: 0.7; } }

/* New rule button */
.al-add-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background: var(--bg-surface); color: var(--text-secondary);
  font-size: 11px; font-weight: 600; cursor: pointer;
  transition: all 0.15s;
}
.al-add-btn:hover { border-color: var(--brand-accent); color: var(--brand-accent); background: rgba(99,102,241,0.06); }
.al-add-active { border-color: var(--brand-accent); color: var(--brand-accent); background: rgba(99,102,241,0.08); }

/* Inline slide-in form */
.alert-form-slide-enter-active,
.alert-form-slide-leave-active { transition: max-height 0.22s ease, opacity 0.2s ease; overflow: hidden; }
.alert-form-slide-enter-from,
.alert-form-slide-leave-to { max-height: 0; opacity: 0; }
.alert-form-slide-enter-to,
.alert-form-slide-leave-from { max-height: 300px; opacity: 1; }

.al-inline-form {
  margin: 0 -1px;
  padding: 14px 16px;
  background: var(--bg-surface);
  border-top: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
}
.al-form-title { font-size: 11px; font-weight: 700; color: var(--text-primary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 12px; }
.al-form-grid { display: grid; grid-template-columns: 1fr auto; gap: 10px; margin-bottom: 10px; }
.al-field { display: flex; flex-direction: column; gap: 4px; }
.al-label { font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; }
.al-select {
  height: 32px; padding: 0 8px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-card); color: var(--text-primary);
  font-size: 12px; outline: none;
  transition: border-color 0.15s;
}
.al-select:focus { border-color: var(--brand-accent); }
.al-threshold-row { display: flex; align-items: center; gap: 4px; }
.al-step-btn {
  width: 26px; height: 26px; border-radius: 50%; border: 1px solid var(--border-color);
  background: var(--bg-card); color: var(--text-primary); font-size: 16px; font-weight: 400;
  cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.12s;
  line-height: 1;
}
.al-step-btn:hover { border-color: var(--brand-accent); color: var(--brand-accent); }
.al-threshold-val { font-size: 18px; font-weight: 800; color: var(--brand-accent); min-width: 26px; text-align: center; }
.al-threshold-unit { font-size: 10px; color: var(--text-muted); white-space: nowrap; }
.al-form-row2 { display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 12px; }
.al-pill-group { display: flex; align-items: center; gap: 4px; }
.al-pill-label { font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; margin-right: 2px; }
.al-pill {
  padding: 3px 10px; border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background: var(--bg-card); color: var(--text-muted);
  font-size: 11px; font-weight: 600; cursor: pointer; transition: all 0.12s;
}
.al-pill:hover { border-color: var(--brand-accent); color: var(--brand-accent); }
.al-pill-active { background: var(--brand-accent); border-color: var(--brand-accent); color: white; }
.al-form-error { font-size: 11px; color: #ef4444; margin-bottom: 8px; }
.al-form-actions { display: flex; justify-content: flex-end; gap: 8px; }
.al-cancel-btn {
  padding: 6px 14px; border-radius: var(--radius-md);
  border: 1px solid var(--border-color); background: transparent;
  color: var(--text-muted); font-size: 12px; font-weight: 600; cursor: pointer;
  transition: all 0.12s;
}
.al-cancel-btn:hover { color: var(--text-primary); border-color: var(--text-muted); }
.al-save-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 16px; border-radius: var(--radius-md);
  border: none; background: var(--brand-accent); color: white;
  font-size: 12px; font-weight: 700; cursor: pointer; transition: all 0.12s;
}
.al-save-btn:hover:not(:disabled) { background: var(--brand-hover, #4f46e5); }
.al-save-btn:disabled { opacity: 0.6; cursor: not-allowed; }
@keyframes spin { to { transform: rotate(360deg); } }
.al-spinner { animation: spin 0.8s linear infinite; }

/* Section labels */
.al-section-label {
  display: flex; align-items: center; gap: 6px;
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--text-muted);
  margin-bottom: 8px;
}
.al-count-badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 18px; height: 16px; padding: 0 5px;
  border-radius: var(--radius-full); background: rgba(99,102,241,0.12);
  color: var(--brand-accent); font-size: 9px; font-weight: 800;
}
.al-count-orange { background: rgba(245,158,11,0.12); color: #d97706; }

/* Rule items */
.al-rules-list { display: flex; flex-direction: column; gap: 5px; }
.al-rule-item {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 9px 11px; border: 1px solid var(--border-color);
  border-radius: var(--radius-md); background: var(--bg-surface);
  transition: border-color 0.15s;
}
.al-rule-item:hover { border-color: rgba(99,102,241,0.3); }
.al-rule-muted { opacity: 0.55; }
.al-rule-left { display: flex; flex-direction: column; gap: 5px; flex: 1; min-width: 0; }
.al-rule-kw {
  display: flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 700; color: var(--text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.al-rule-kw svg { color: var(--text-muted); flex-shrink: 0; }
.al-rule-meta { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.al-badge {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 1px 6px; border-radius: var(--radius-full);
  font-size: 9px; font-weight: 700; letter-spacing: 0.02em;
  border: 1px solid transparent;
}
.al-badge-threshold { background: rgba(99,102,241,0.08); color: var(--brand-accent); border-color: rgba(99,102,241,0.2); }
.al-badge-any { background: var(--bg-card); color: var(--text-muted); border-color: var(--border-color); }
.al-badge-up { background: rgba(34,197,94,0.1); color: #16a34a; border-color: rgba(34,197,94,0.25); }
.al-badge-down { background: rgba(239,68,68,0.08); color: #dc2626; border-color: rgba(239,68,68,0.2); }
.al-badge-method { background: var(--bg-card); color: var(--text-secondary); border-color: var(--border-color); }
.al-rule-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

/* Custom toggle switch */
.al-toggle {
  width: 30px; height: 16px; border-radius: 8px;
  border: none; cursor: pointer; padding: 0;
  background: var(--border-color); position: relative;
  transition: background 0.2s;
}
.al-toggle-on { background: var(--brand-accent); }
.al-toggle-knob {
  position: absolute; top: 2px; left: 2px;
  width: 12px; height: 12px; border-radius: 50%;
  background: white; transition: left 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}
.al-toggle-on .al-toggle-knob { left: 16px; }
.al-delete-btn {
  width: 22px; height: 22px; border-radius: 4px;
  border: none; background: transparent; color: var(--text-muted);
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all 0.12s;
}
.al-delete-btn:hover { background: rgba(239,68,68,0.1); color: #dc2626; }

/* Event list */
.al-events-section { }
.al-events-list { display: flex; flex-direction: column; gap: 4px; }
.al-event-item {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 10px; border-radius: var(--radius-md);
  background: var(--bg-surface); border: 1px solid var(--border-color);
}
.al-event-icon {
  width: 20px; height: 20px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.al-ei-up { background: rgba(34,197,94,0.12); color: #16a34a; }
.al-ei-down { background: rgba(239,68,68,0.1); color: #dc2626; }
.al-event-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.al-event-kw { font-size: 12px; font-weight: 700; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.al-event-detail { font-size: 10px; color: var(--text-muted); }
.al-event-detail strong { color: var(--text-secondary); }
.al-rank-change { font-size: 10px; color: var(--text-muted); margin-left: 4px; font-variant-numeric: tabular-nums; }
.al-event-time { font-size: 9px; color: var(--text-muted); flex-shrink: 0; white-space: nowrap; }

/* Empty state */
.al-empty-state { display: flex; flex-direction: column; align-items: center; padding: 24px 12px; text-align: center; }
.al-empty-icon { opacity: 0.35; margin-bottom: 10px; }
.al-empty-text { font-size: 13px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px; }
.al-empty-sub { font-size: 11px; color: var(--text-muted); margin: 0; line-height: 1.5; }
.al-empty-sub strong { color: var(--text-secondary); }

/* ── Competitor Tracking Card ─────────────────────────────────────────── */
.ct-card { }
.ct-list { display: flex; flex-direction: column; gap: 5px; margin-bottom: 10px; }
.ct-row {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 11px; border: 1px solid var(--border-color);
  border-radius: var(--radius-md); background: var(--bg-surface);
  transition: border-color 0.15s;
}
.ct-row:hover { border-color: rgba(99,102,241,0.3); }
.ct-favicon { width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.ct-info { flex: 1; min-width: 0; }
.ct-name { display: block; font-size: 12px; font-weight: 700; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ct-domain { font-size: 10px; color: var(--text-muted); }
.ct-status { font-size: 9px; color: var(--text-muted); flex-shrink: 0; display: none; }
@media (min-width: 500px) { .ct-status { display: block; } }
.ct-last-check { }
.ct-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.ct-refresh-btn {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 10px; border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background: var(--bg-card); color: var(--text-secondary);
  font-size: 10px; font-weight: 600; cursor: pointer; transition: all 0.15s;
}
.ct-refresh-btn:hover:not(:disabled) { border-color: var(--brand-accent); color: var(--brand-accent); }
.ct-refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.ct-refreshing { opacity: 0.7; pointer-events: none; }
.ct-spin { animation: spin 0.8s linear infinite; }
.ct-compare-row { margin: 6px 0; }
.ct-compare-btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 14px; border-radius: var(--radius-full);
  border: 1px solid var(--border-color); background: var(--bg-surface);
  color: var(--text-secondary); font-size: 11px; font-weight: 600;
  cursor: pointer; transition: all 0.15s;
}
.ct-compare-btn:hover:not(:disabled) { border-color: var(--brand-accent); color: var(--brand-accent); background: rgba(99,102,241,0.04); }
.ct-compare-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.ct-overlap-table { margin-top: 8px; }
.ct-kw-cell { font-size: 11px; font-weight: 600; color: var(--text-primary); max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ct-us-col { }
.ct-us-label { font-size: 10px; font-weight: 800; color: var(--brand-accent); }
.ct-rank-delta { display: block; font-size: 8px; font-weight: 700; margin-top: 1px; text-transform: uppercase; letter-spacing: 0.03em; }
.ct-delta-win { color: #16a34a; }
.ct-delta-lose { color: #dc2626; }

/* ── Historical Rank Charts Card ──────────────────────────────────────── */
.hc-card { }
.hc-controls { margin-bottom: 14px; }
.hc-kw-row { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }
.hc-kw-chip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background: var(--bg-surface); color: var(--text-muted);
  font-size: 11px; font-weight: 600; cursor: pointer; transition: all 0.15s;
}
.hc-kw-chip:hover:not(.hc-chip-disabled) { border-color: currentColor; }
.hc-chip-active { font-weight: 700; }
.hc-chip-disabled { opacity: 0.35; cursor: not-allowed; }
.hc-chip-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.hc-chip-rank { font-size: 9px; opacity: 0.7; }
.hc-loading { display: flex; flex-direction: column; gap: 8px; align-items: center; padding: 20px; color: var(--text-muted); font-size: 12px; }
.hc-loading-bar { width: 80px; height: 3px; background: var(--border-color); border-radius: 2px; overflow: hidden; position: relative; }
.hc-loading-bar::after { content: ''; position: absolute; left: -40px; width: 40px; height: 100%; background: var(--brand-accent); border-radius: 2px; animation: hc-slide 1s ease-in-out infinite; }
@keyframes hc-slide { to { left: 100%; } }
.hc-chart-area { display: flex; flex-direction: column; gap: 10px; }
.hc-note { font-size: 10px; color: var(--text-muted); }
.rank-chart { width: 100%; height: 220px; display: block; overflow: visible; cursor: crosshair; }
.chart-dot-group { cursor: pointer; }
.hc-legend { display: flex; flex-wrap: wrap; gap: 12px; padding-top: 4px; border-top: 1px solid var(--border-color); }
.hc-legend-item { display: flex; align-items: center; gap: 6px; }
.hc-legend-line { width: 18px; height: 2px; border-radius: 1px; flex-shrink: 0; }
.hc-legend-kw { font-size: 11px; font-weight: 600; color: var(--text-primary); }
.hc-legend-rank { font-size: 10px; font-weight: 700; }

/* Responsive */
@media (max-width: 900px) {
  .cards-grid { grid-template-columns: 1fr; }
  .split-screen { grid-template-columns: 1fr; }
  .ai-engine-grid { grid-template-columns: 1fr; }
  .alt-grid { grid-template-columns: 1fr; }
  .comp-grid { grid-template-columns: 1fr; }
  [style*="grid-column: span 2"] { grid-column: span 1 !important; }
}
@media (max-width: 600px) { .page-header { flex-direction: column; align-items: flex-start; gap: 10px; } .fc-stat-row { flex-direction: column; } }
</style>
