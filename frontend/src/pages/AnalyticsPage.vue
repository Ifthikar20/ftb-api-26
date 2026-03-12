<template>
  <div class="analytics-page fade-in">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Analytics</h1>
        <p class="page-subtitle">Product analytics, funnels, retention, and AI insights.</p>
      </div>
      <div class="flex gap-8 items-center">
        <button class="refresh-btn" :class="{ spinning: isRefreshing }" title="Refresh data" @click="handleRefresh">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M1 1v5h5"/><path d="M15 15v-5h-5"/>
            <path d="M2.4 10a6 6 0 0010.3 1.5L15 10M1 6l2.3-1.5A6 6 0 0113.6 6"/>
          </svg>
        </button>
        <div class="period-tabs">
          <button v-for="p in periods" :key="p.value" class="period-tab" :class="{ active: period === p.value }" @click="changePeriod(p.value)">{{ p.label }}</button>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="analytics-tabs">
      <button v-for="tab in tabs" :key="tab.id" class="atab" :class="{ active: activeTab === tab.id }" @click="switchTab(tab.id)">
        <svg class="atab-icon" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" v-html="tab.svg"></svg>
        <span class="atab-label">{{ tab.label }}</span>
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <span style="margin-top:12px">Loading analytics...</span>
    </div>
    <div v-if="refreshing && !loading" class="refresh-indicator">
      <div class="refresh-dot"></div> Updating...
    </div>

    <template v-else>
      <!-- Empty State -->
      <div v-if="noData && activeTab === 'overview'" class="empty-state-card">
        <div class="empty-icon">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="var(--brand-accent)" stroke-width="1.5">
            <rect x="6" y="6" width="36" height="36" rx="4"/>
            <path d="M6 18h36M18 18v24"/>
            <circle cx="30" cy="30" r="6" fill="none" stroke-dasharray="4"/>
          </svg>
        </div>
        <h3 class="empty-title">Install the tracking pixel</h3>
        <p class="empty-desc">Add the FetchBot tracking snippet to your website to start collecting real visitor data.</p>
        <div class="empty-snippet">
          <code>&lt;script src="/fetchbot-pixel.js" data-site="YOUR_PIXEL_KEY" async&gt;&lt;/script&gt;</code>
        </div>
        <p class="empty-hint">Go to <strong>Projects → Settings</strong> to copy your personalized snippet.</p>
      </div>

      <!-- ═══════════ TAB 1: Overview ═══════════ -->
      <div v-show="activeTab === 'overview' && !noData">

        <!-- KPI Cards with tooltips -->
        <div class="kpi-grid">
          <div class="kpi-card" v-for="stat in stats" :key="stat.label" :class="stat.highlight ? 'kpi-highlight' : ''">
            <div class="kpi-header">
              <span class="kpi-label">
                {{ stat.label }}
                <span class="kpi-info" v-if="kpiTooltips[stat.label]" @mouseenter="showTooltip = stat.label" @mouseleave="showTooltip = null">
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="7"/><path d="M8 7v4M8 5.5v0"/></svg>
                  <div class="kpi-tooltip" v-show="showTooltip === stat.label">{{ kpiTooltips[stat.label] }}</div>
                </span>
              </span>
              <span class="kpi-trend" :class="stat.trend >= 0 ? 'trend-up' : 'trend-down'">
                {{ stat.trend >= 0 ? '↑' : '↓' }} {{ Math.abs(stat.trend) }}%
              </span>
            </div>
            <div class="kpi-value">{{ stat.value }}</div>
          </div>
        </div>

        <!-- Traffic Charts Row -->
        <div class="analytics-row chart-animate">
          <div class="card chart-card" style="flex:1.5">
            <div class="card-header">
              <div>
                <h3 class="card-title">Traffic Overview</h3>
                <p class="card-subtitle">Visitor sessions over time</p>
              </div>
            </div>
            <div class="chart-container" style="height:280px;position:relative">
              <Line v-if="chartData.length" :data="trafficChartData" :options="trafficChartOptions" />
              <div v-else class="empty-inline">No chart data yet</div>
            </div>
          </div>
          <div class="card chart-card chart-animate-delay">
            <div class="card-header">
              <div>
                <h3 class="card-title">Live Activity</h3>
                <p class="card-subtitle">Recent visitor events in real-time</p>
              </div>
              <span class="live-badge"><span class="live-pulse"></span>LIVE</span>
            </div>
            <div class="live-feed" v-if="liveEvents.length">
              <div v-for="ev in liveEvents.slice(0, 10)" :key="ev.id" class="live-feed-item">
                <span class="badge badge-sm" :class="eventBadge(ev.event_type)">{{ ev.event_type }}</span>
                <span class="live-feed-url truncate">{{ cleanPath(ev.url) }}</span>
                <span class="text-xs text-muted">{{ formatTime(ev.timestamp) }}</span>
              </div>
            </div>
            <div v-else class="empty-inline" style="padding:40px 20px">
              <p style="margin:0;font-size:var(--font-sm)">No live events in the last 2 minutes.</p>
              <p class="text-xs text-muted" style="margin-top:6px">Events appear here as visitors interact with your site.</p>
            </div>
          </div>
        </div>

        <!-- Sources + Pages Row -->
        <div class="analytics-row">
          <div class="card">
            <div class="card-header"><h3 class="card-title">Top Sources</h3></div>
            <div class="chart-container" style="height:220px;position:relative" v-if="sources.length">
              <Bar :data="sourcesChartData" :options="sourcesChartOptions" />
            </div>
            <div v-else class="empty-inline">No source data yet</div>
          </div>
          <div class="card">
            <div class="card-header"><h3 class="card-title">Top Pages</h3></div>
            <table class="data-table">
              <thead><tr><th>Page</th><th style="text-align:right">Views</th></tr></thead>
              <tbody>
                <tr v-for="(page, i) in topPages" :key="i">
                  <td><span class="page-rank">{{ i + 1 }}</span> {{ page.url }}</td>
                  <td style="text-align:right" class="font-semibold">{{ page.views }}</td>
                </tr>
              </tbody>
            </table>
            <div v-if="!topPages.length" class="empty-inline">No page data yet</div>
          </div>
        </div>

        <!-- Engagement Radar + Source Polar Row -->
        <div class="analytics-row">
          <div class="card">
            <div class="card-header"><h3 class="card-title">Engagement Score</h3></div>
            <div class="chart-container" style="height:250px;position:relative">
              <Radar :data="radarChartData" :options="radarChartOptions" />
            </div>
          </div>
          <div class="card">
            <div class="card-header"><h3 class="card-title">Source Distribution</h3></div>
            <div class="chart-container" style="height:250px;position:relative" v-if="sources.length">
              <PolarArea :data="polarChartData" :options="polarChartOptions" />
            </div>
            <div v-else class="empty-inline">No source data yet</div>
          </div>
        </div>

        <!-- Devices + Countries Row -->
        <div class="analytics-row">
          <div class="card">
            <div class="card-header"><h3 class="card-title">Devices</h3></div>
            <div class="chart-container" style="height:200px;position:relative" v-if="devices.length">
              <Doughnut :data="devicesChartData" :options="devicesChartOptions" />
            </div>
            <div v-else class="empty-inline">No device data yet</div>
          </div>
          <div class="card">
            <div class="card-header"><h3 class="card-title">Top Countries</h3></div>
            <div class="country-list" v-if="countries.length">
              <div v-for="(c, i) in countries" :key="i" class="country-item">
                <div class="country-rank">{{ i + 1 }}</div>
                <div class="country-info">
                  <span class="country-name">{{ c.name }}</span>
                  <div class="country-bar-wrap"><div class="country-bar" :style="{ width: c.pct + '%' }"></div></div>
                </div>
                <span class="font-semibold">{{ c.visitors }}</span>
              </div>
            </div>
            <div v-else class="empty-inline">No geo data yet</div>
          </div>
        </div>

        <!-- Browsers + Live Events Row -->
        <div class="analytics-row">
          <div class="card">
            <div class="card-header"><h3 class="card-title">Browsers</h3></div>
            <div v-if="browserData.length" class="browser-list">
              <div v-for="(b, i) in browserData" :key="i" class="browser-item">
                <div class="browser-info">
                  <svg class="browser-icon" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M2 8h12M8 2c-2 2-2 10 0 12M8 2c2 2 2 10 0 12"/></svg>
                  <span class="browser-name">{{ b.name }}</span>
                </div>
                <div class="browser-bar-wrap"><div class="browser-bar" :style="{ width: b.pct + '%', background: browserColors[i % browserColors.length] }"></div></div>
                <span class="browser-pct">{{ b.pct }}%</span>
              </div>
            </div>
            <div v-else class="empty-inline">No browser data yet</div>
          </div>
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">Live Events</h3>
              <div v-if="realtimeVisitors > 0" class="realtime-badge">
                <span class="realtime-dot"></span>
                <span>{{ realtimeVisitors }} active</span>
              </div>
            </div>
            <div v-if="liveEvents.length" class="live-feed">
              <div v-for="(ev, i) in liveEvents.slice(0, 8)" :key="i" class="live-event">
                <span class="live-event-type" :class="eventBadge(ev.event_type)">{{ ev.event_type }}</span>
                <span class="live-event-url">{{ ev.page || ev.url || '--' }}</span>
                <span class="live-event-time">{{ formatTime(ev.timestamp) }}</span>
              </div>
            </div>
            <div v-else class="empty-inline">No live events yet — data will appear as visitors browse your site</div>
          </div>
        </div>
      </div>

      <!-- ═══════════ TAB 2: Funnels ═══════════ -->
      <div v-show="activeTab === 'funnels'">
        <div class="card" style="margin-bottom:20px">
          <div class="card-header">
            <h3 class="card-title">Conversion Funnels</h3>
            <button class="btn btn-primary btn-sm" @click="showCreateFunnel = true">+ New Funnel</button>
          </div>
          <!-- Saved funnels -->
          <div v-if="funnelList.length" class="funnel-list">
            <div v-for="f in funnelList" :key="f.id" class="funnel-item" @click="runFunnel(f.id)">
              <span class="font-semibold">{{ f.name }}</span>
              <span class="text-xs text-muted">{{ f.steps?.length || 0 }} steps</span>
            </div>
          </div>
          <div v-else class="empty-inline">No funnels yet. Create one to track conversions.</div>
        </div>

        <!-- Funnel result -->
        <div v-if="funnelResult" class="card">
          <div class="card-header">
            <h3 class="card-title">{{ funnelResult.name }}</h3>
            <span class="badge badge-success">{{ funnelResult.overall_conversion_pct }}% conversion</span>
          </div>
          <div class="funnel-viz">
            <div v-for="(step, i) in funnelResult.steps" :key="i" class="funnel-step">
              <div class="funnel-bar" :style="{ height: step.conversion_pct + '%' }">
                <div class="funnel-bar-fill"></div>
              </div>
              <div class="funnel-step-info">
                <div class="font-semibold text-sm">{{ step.name }}</div>
                <div class="text-xs text-muted">{{ step.visitors }} visitors</div>
                <div v-if="step.drop_off_pct > 0" class="text-xs text-danger">-{{ step.drop_off_pct }}% drop</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Create Funnel Modal -->
        <div v-if="showCreateFunnel" class="modal-overlay" @click.self="showCreateFunnel = false">
          <div class="modal-card" style="max-width:500px">
            <h3 class="card-title" style="margin-bottom:16px">Create Funnel</h3>
            <div class="form-group"><label class="form-label">Name</label><input v-model="newFunnel.name" class="form-input" placeholder="e.g. Signup Flow" /></div>
            <div v-for="(step, i) in newFunnel.steps" :key="i" class="form-group" style="display:flex;gap:8px">
              <input v-model="step.name" class="form-input" :placeholder="'Step ' + (i+1) + ' name'" style="flex:1" />
              <input v-model="step.value" class="form-input" :placeholder="'URL contains...'" style="flex:1" />
            </div>
            <button class="btn btn-secondary btn-sm" @click="newFunnel.steps.push({name:'',type:'url',value:''})" style="margin-bottom:16px">+ Add Step</button>
            <div class="flex gap-8">
              <button class="btn btn-primary" @click="createFunnel">Create</button>
              <button class="btn btn-secondary" @click="showCreateFunnel = false">Cancel</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════ TAB 3: Retention ═══════════ -->
      <div v-show="activeTab === 'retention'" @click.self="showCardPicker = false">

        <!-- Empty State -->
        <div v-if="!retentionCards.length" class="ret-empty-state">
          <div class="ret-empty-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="var(--text-muted)" stroke-width="1.5">
              <rect x="6" y="6" width="36" height="36" rx="4"/><path d="M24 16v16M16 24h16"/>
            </svg>
          </div>
          <h3 class="ret-empty-title">Build Your Retention Dashboard</h3>
          <p class="ret-empty-desc">Add widgets to track visitor engagement, retention, and behavior patterns.</p>
          <div class="ret-add-wrap">
            <button class="btn btn-primary" @click.stop="showCardPicker = !showCardPicker">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:6px"><path d="M7 1v12M1 7h12"/></svg>
              Add Widget
            </button>
            <div v-if="showCardPicker" class="card-picker-dropdown card-picker-center" @click.stop>
              <div class="card-picker-header">Choose a widget</div>
              <div v-for="c in retAvailableCards" :key="c.id" class="card-picker-item" :class="{ disabled: retentionCards.includes(c.id) }" @click="addRetCard(c.id)">
                <div class="card-picker-icon" v-html="c.icon"></div>
                <div class="card-picker-info">
                  <div class="card-picker-name">{{ c.title }}</div>
                  <div class="card-picker-desc">{{ c.desc }}</div>
                </div>
                <span v-if="retentionCards.includes(c.id)" class="card-picker-check">✓</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Dynamic Card Grid -->
        <div v-else class="ret-card-grid">
          <template v-for="cid in retentionCards" :key="cid">

            <!-- Engagement Score -->
            <div v-if="cid === 'engagement_score'" class="ret-dyn-card ret-half">
              <button class="ret-card-close" @click="removeRetCard(cid)" title="Remove">&times;</button>
              <div class="card engagement-score-card">
                <div class="card-header"><h3 class="card-title">Engagement Score</h3><span class="text-xs text-muted">Composite health metric</span></div>
                <div class="engagement-ring-wrap">
                  <svg class="engagement-ring" viewBox="0 0 120 120">
                    <circle cx="60" cy="60" r="50" fill="none" stroke="var(--bg-surface)" stroke-width="8"/>
                    <circle cx="60" cy="60" r="50" fill="none" :stroke="engScoreColor" stroke-width="8" stroke-linecap="round" :stroke-dasharray="engDash" stroke-dashoffset="0" transform="rotate(-90 60 60)" class="ring-progress"/>
                  </svg>
                  <div class="engagement-ring-label"><span class="eng-score-num">{{ engagementData.engagement_score || 0 }}</span><span class="eng-score-unit">/100</span></div>
                </div>
                <div class="eng-breakdown">
                  <div class="eng-factor"><span class="eng-factor-label">Low Bounce</span><div class="eng-factor-bar"><div class="eng-factor-fill" :style="{ width: (100 - (engagementData.bounce_rate || 0)) + '%', background: 'var(--color-success)' }"></div></div></div>
                  <div class="eng-factor"><span class="eng-factor-label">Depth</span><div class="eng-factor-bar"><div class="eng-factor-fill" :style="{ width: Math.min((engagementData.avg_pages_per_session || 0) / 5 * 100, 100) + '%', background: 'var(--color-info)' }"></div></div></div>
                  <div class="eng-factor"><span class="eng-factor-label">Return Rate</span><div class="eng-factor-bar"><div class="eng-factor-fill" :style="{ width: (engagementData.returning_pct || 0) + '%', background: 'var(--brand-accent)' }"></div></div></div>
                </div>
              </div>
            </div>

            <!-- New vs Returning -->
            <div v-if="cid === 'new_vs_returning'" class="ret-dyn-card ret-half">
              <button class="ret-card-close" @click="removeRetCard(cid)" title="Remove">&times;</button>
              <div class="card">
                <div class="card-header"><h3 class="card-title">New vs Returning</h3><span class="text-xs text-muted">{{ engagementData.total_visitors || 0 }} total</span></div>
                <div class="donut-wrap">
                  <svg class="donut-chart" viewBox="0 0 120 120">
                    <circle cx="60" cy="60" r="44" fill="none" stroke="var(--color-info)" stroke-width="14" :stroke-dasharray="newDonutDash" stroke-dashoffset="0" transform="rotate(-90 60 60)" class="donut-arc"/>
                    <circle cx="60" cy="60" r="44" fill="none" stroke="var(--color-success)" stroke-width="14" :stroke-dasharray="retDonutDash" :stroke-dashoffset="retDonutOffset" transform="rotate(-90 60 60)" class="donut-arc"/>
                  </svg>
                  <div class="donut-center-label"><span class="donut-big">{{ engagementData.returning_pct || 0 }}%</span><span class="donut-sub">returning</span></div>
                </div>
                <div class="donut-legend">
                  <div class="legend-item"><span class="legend-dot" style="background:var(--color-info)"></span>New <b>{{ engagementData.new_visitors || 0 }}</b></div>
                  <div class="legend-item"><span class="legend-dot" style="background:var(--color-success)"></span>Returning <b>{{ engagementData.returning_visitors || 0 }}</b></div>
                </div>
              </div>
            </div>

            <!-- Bounce Rate -->
            <div v-if="cid === 'bounce_rate'" class="ret-dyn-card ret-quarter">
              <button class="ret-card-close" @click="removeRetCard(cid)" title="Remove">&times;</button>
              <div class="ret-stat-card" :class="{ 'stat-danger': (engagementData.bounce_rate || 0) > 60 }">
                <div class="ret-stat-icon"><svg width="20" height="20" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 12l4-8 4 8"/><line x1="5.5" y1="9" x2="10.5" y2="9"/></svg></div>
                <div class="ret-stat-value">{{ engagementData.bounce_rate || 0 }}%</div>
                <div class="ret-stat-label">Bounce Rate</div>
                <div class="ret-stat-hint">{{ (engagementData.bounce_rate || 0) > 50 ? 'Higher than ideal' : 'Healthy range' }}</div>
              </div>
            </div>

            <!-- Pages / Session -->
            <div v-if="cid === 'pages_session'" class="ret-dyn-card ret-quarter">
              <button class="ret-card-close" @click="removeRetCard(cid)" title="Remove">&times;</button>
              <div class="ret-stat-card">
                <div class="ret-stat-icon"><svg width="20" height="20" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="2"/><path d="M5 6h6M5 8h4M5 10h5"/></svg></div>
                <div class="ret-stat-value">{{ engagementData.avg_pages_per_session || 0 }}</div>
                <div class="ret-stat-label">Pages / Session</div>
                <div class="ret-stat-hint">Average page depth</div>
              </div>
            </div>

            <!-- Avg Duration -->
            <div v-if="cid === 'avg_duration'" class="ret-dyn-card ret-quarter">
              <button class="ret-card-close" @click="removeRetCard(cid)" title="Remove">&times;</button>
              <div class="ret-stat-card">
                <div class="ret-stat-icon"><svg width="20" height="20" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M8 4v4l3 2"/></svg></div>
                <div class="ret-stat-value">{{ formatDuration(engagementData.avg_session_duration_secs || 0) }}</div>
                <div class="ret-stat-label">Avg Duration</div>
                <div class="ret-stat-hint">Time per session</div>
              </div>
            </div>

            <!-- Total Sessions -->
            <div v-if="cid === 'total_sessions'" class="ret-dyn-card ret-quarter">
              <button class="ret-card-close" @click="removeRetCard(cid)" title="Remove">&times;</button>
              <div class="ret-stat-card">
                <div class="ret-stat-icon"><svg width="20" height="20" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 12V4a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2z"/><path d="M5 8h6M8 5v6"/></svg></div>
                <div class="ret-stat-value">{{ engagementData.total_sessions || 0 }}</div>
                <div class="ret-stat-label">Total Sessions</div>
                <div class="ret-stat-hint">In selected period</div>
              </div>
            </div>

            <!-- Top Returning Visitors -->
            <div v-if="cid === 'top_returners'" class="ret-dyn-card ret-full">
              <button class="ret-card-close" @click="removeRetCard(cid)" title="Remove">&times;</button>
              <div class="card">
                <div class="card-header"><h3 class="card-title">Top Returning Visitors</h3><span class="text-xs text-muted">Most loyal by visit count</span></div>
                <table v-if="engagementData.top_returners && engagementData.top_returners.length" class="data-table">
                  <thead><tr><th>Visitor</th><th>Visits</th><th>Avg Pages</th><th>Device</th><th>Country</th><th>Last Seen</th></tr></thead>
                  <tbody>
                    <tr v-for="r in engagementData.top_returners" :key="r.hash" class="returner-row">
                      <td><span class="visitor-hash">{{ r.hash }}...</span><span v-if="r.browser" class="badge badge-sm badge-outline" style="margin-left:6px">{{ r.browser }}</span></td>
                      <td><span class="visit-count-badge">{{ r.visits }}</span></td>
                      <td>{{ r.avg_pages }}</td><td>{{ r.device || '—' }}</td><td>{{ r.country || '—' }}</td>
                      <td class="text-muted">{{ r.last_seen ? relativeTime(r.last_seen) : '—' }}</td>
                    </tr>
                  </tbody>
                </table>
                <div v-else class="empty-inline">No returning visitors yet.</div>
              </div>
            </div>

            <!-- Cohort Matrix -->
            <div v-if="cid === 'cohort_matrix'" class="ret-dyn-card ret-full">
              <button class="ret-card-close" @click="removeRetCard(cid)" title="Remove">&times;</button>
              <div class="card">
                <div class="card-header"><h3 class="card-title">Cohort Retention</h3><p class="card-subtitle">How many visitors return over time</p></div>
                <div v-if="retentionData.rows && retentionData.rows.length" class="retention-matrix">
                  <table class="data-table retention-table">
                    <thead><tr><th>Cohort</th><th>Size</th><th v-for="w in maxRetentionWeeks" :key="w">Wk {{ w - 1 }}</th></tr></thead>
                    <tbody>
                      <tr v-for="row in retentionData.rows" :key="row.cohort">
                        <td class="font-semibold">{{ row.cohort }}</td><td>{{ row.cohort_size }}</td>
                        <td v-for="(w, i) in row.weeks" :key="i" :style="{ background: retentionColor(w.pct) }" class="retention-cell">{{ w.pct }}%</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="empty-inline">No retention data yet.</div>
              </div>
            </div>

          </template>

          <!-- Inline + Add Widget -->
          <div class="ret-dyn-card ret-add-inline">
            <button class="ret-add-btn" @click.stop="showCardPicker = !showCardPicker">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3v14M3 10h14"/></svg>
            </button>
            <div v-if="showCardPicker" class="card-picker-dropdown" @click.stop>
              <div class="card-picker-header">Add Widget</div>
              <div v-for="c in retAvailableCards" :key="c.id" class="card-picker-item" :class="{ disabled: retentionCards.includes(c.id) }" @click="addRetCard(c.id)">
                <div class="card-picker-icon" v-html="c.icon"></div>
                <div class="card-picker-info">
                  <div class="card-picker-name">{{ c.title }}</div>
                  <div class="card-picker-desc">{{ c.desc }}</div>
                </div>
                <span v-if="retentionCards.includes(c.id)" class="card-picker-check">✓</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- ═══════════ TAB 4: Flows ═══════════ -->
      <div v-show="activeTab === 'flows'" @click.self="showFlowPicker = false">

        <!-- Empty State -->
        <div v-if="!flowCards.length" class="ret-empty-state">
          <div class="ret-empty-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="var(--text-muted)" stroke-width="1.5">
              <path d="M6 20h12l6 8-6 8H6M42 20H30l-6 8 6 8h12"/><path d="M24 16v16M16 24h16"/>
            </svg>
          </div>
          <h3 class="ret-empty-title">Build Your Flow Analytics</h3>
          <p class="ret-empty-desc">Add widgets to analyze visitor journeys, page flows, and navigation patterns.</p>
          <div class="ret-add-wrap">
            <button class="btn btn-primary" @click.stop="showFlowPicker = !showFlowPicker">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:6px"><path d="M7 1v12M1 7h12"/></svg>
              Add Widget
            </button>
            <div v-if="showFlowPicker" class="card-picker-dropdown card-picker-center" @click.stop>
              <div class="card-picker-header">Choose a widget</div>
              <div v-for="c in flowAvailableCards" :key="c.id" class="card-picker-item" :class="{ disabled: flowCards.includes(c.id) }" @click="addFlowCard(c.id)">
                <div class="card-picker-icon" v-html="c.icon"></div>
                <div class="card-picker-info">
                  <div class="card-picker-name">{{ c.title }}</div>
                  <div class="card-picker-desc">{{ c.desc }}</div>
                </div>
                <span v-if="flowCards.includes(c.id)" class="card-picker-check">✓</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Dynamic Card Grid -->
        <div v-else>

          <!-- Flow Filters (always visible when cards exist) -->
          <div class="flow-filters" style="margin-bottom:16px">
            <input v-model="flowSearch" type="text" class="flow-filter-input" placeholder="Filter by visitor, page, or source..." />
            <select v-model="flowFilterSource" class="flow-filter-select">
              <option value="">All Sources</option>
              <option v-for="s in flowSources" :key="s" :value="s">{{ s }}</option>
            </select>
            <select v-model="flowFilterPage" class="flow-filter-select">
              <option value="">All Pages</option>
              <option v-for="p in flowPages" :key="p" :value="p">{{ p }}</option>
            </select>
            <select v-model="flowFilterDevice" class="flow-filter-select">
              <option value="">All Devices</option>
              <option v-for="d in flowDevices" :key="d" :value="d">{{ d }}</option>
            </select>
            <select v-model="flowFilterCountry" class="flow-filter-select">
              <option value="">All Countries</option>
              <option v-for="c in flowCountries" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>

          <div class="ret-card-grid">
            <template v-for="cid in flowCards" :key="cid">

              <!-- Common Flow Patterns -->
              <div v-if="cid === 'flow_patterns'" class="ret-dyn-card ret-half">
                <button class="ret-card-close" @click="removeFlowCard(cid)" title="Remove">&times;</button>
                <div class="card">
                  <div class="card-header"><h3 class="card-title">Common Flow Patterns</h3><span class="text-xs text-muted">Page-to-page transitions</span></div>
                  <div v-if="flowData.links && flowData.links.length" class="flow-list">
                    <div v-for="(link, i) in flowData.links.slice(0, 12)" :key="i" class="flow-item-enhanced">
                      <div class="flow-item-route">
                        <span class="flow-page">{{ cleanPath(link.source) }}</span>
                        <span class="flow-arrow">&rarr;</span>
                        <span class="flow-page">{{ cleanPath(link.target) }}</span>
                      </div>
                      <div class="flow-item-bar-wrap"><div class="flow-item-bar" :style="{ width: flowBarWidth(link.value) + '%', background: flowBarColor(i) }"></div></div>
                      <span class="flow-count">{{ link.value }}&times;</span>
                    </div>
                  </div>
                  <div v-else class="empty-inline">No flow data yet</div>
                </div>
              </div>

              <!-- Entry & Exit Pages -->
              <div v-if="cid === 'entry_exit'" class="ret-dyn-card ret-half">
                <button class="ret-card-close" @click="removeFlowCard(cid)" title="Remove">&times;</button>
                <div class="card">
                  <div class="card-header"><h3 class="card-title">Entry & Exit Pages</h3><span class="text-xs text-muted">Where sessions start and end</span></div>
                  <div v-if="entryExitData.entry_pages && entryExitData.entry_pages.length">
                    <h4 class="text-sm font-semibold" style="margin-bottom:8px;color:var(--color-success)">Entry Pages</h4>
                    <div v-for="p in entryExitData.entry_pages" :key="'e'+p.page" class="flow-bar-row">
                      <div class="flow-bar-label-group">
                        <span class="flow-bar-label truncate">{{ cleanPath(p.page) }}</span>
                        <span v-if="p.source" class="flow-source-tag">via {{ p.source }}</span>
                      </div>
                      <div class="flow-bar-track"><div class="flow-bar-fill entry" :style="{ width: entryPct(p.count) + '%' }"></div></div>
                      <span class="flow-bar-count">{{ p.count }}</span>
                    </div>
                    <h4 class="text-sm font-semibold" style="margin:20px 0 8px;color:var(--color-danger)">Exit Pages</h4>
                    <div v-for="p in entryExitData.exit_pages || []" :key="'x'+p.page" class="flow-bar-row">
                      <span class="flow-bar-label truncate">{{ cleanPath(p.page) }}</span>
                      <div class="flow-bar-track"><div class="flow-bar-fill exit" :style="{ width: exitPct(p.count) + '%' }"></div></div>
                      <span class="flow-bar-count">{{ p.count }}</span>
                    </div>
                  </div>
                  <div v-else class="empty-inline">No entry/exit data yet</div>
                </div>
              </div>

              <!-- Visitor Journeys -->
              <div v-if="cid === 'visitor_journeys'" class="ret-dyn-card ret-full">
                <button class="ret-card-close" @click="removeFlowCard(cid)" title="Remove">&times;</button>
                <div class="card" v-if="filteredJourneys.length">
                  <div class="card-header">
                    <h3 class="card-title">Visitor Journeys</h3>
                    <span class="text-xs text-muted">{{ filteredJourneys.length }} of {{ journeys.length }} sessions{{ activeFlowFilterCount ? ` (${activeFlowFilterCount} filter${activeFlowFilterCount > 1 ? 's' : ''})` : '' }}</span>
                  </div>
                  <div class="journey-list">
                    <div v-for="(j, i) in filteredJourneys" :key="i" class="journey-card" :class="{ 'journey-expanded': expandedJourneys.has(i) }">
                      <div class="journey-meta">
                        <span class="journey-visitor">
                          <span class="intent-dot" :class="j.intent_cls || 'dot-neutral'"></span>
                          <span class="visitor-hash">{{ j.visitor_hash }}...</span>
                          <span v-if="j.intent_score != null" class="intent-score-badge" :class="intentScoreClass(j.intent_score)">{{ j.intent_score }}%</span>
                          <span v-if="j.company" class="journey-company">{{ j.company }}</span>
                        </span>
                        <div class="journey-tags">
                          <span class="badge badge-sm badge-outline" v-if="j.device">{{ j.device }}</span>
                          <span class="badge badge-sm badge-outline" v-if="j.country">{{ j.country }}</span>
                          <span class="badge badge-sm badge-outline" v-if="j.source && j.source !== 'direct'">{{ j.source }}</span>
                          <span class="journey-duration" v-if="j.duration_secs">{{ formatDuration(j.duration_secs) }}</span>
                        </div>
                      </div>
                      <div class="journey-summary-row">
                        <span class="journey-intent-label">{{ j.intent_label || 'Analyzing...' }}</span>
                        <span class="journey-pages-count">{{ j.page_count }} pages</span>
                      </div>
                      <div class="journey-path">
                        <!-- Short path (≤5 pages): show all -->
                        <template v-if="j.pages.length <= 5 || expandedJourneys.has(i)">
                          <template v-for="(page, pi) in j.pages" :key="pi">
                            <span class="journey-step" :class="{ 'step-entry': pi === 0, 'step-exit': pi === j.pages.length - 1 }">{{ page }}</span>
                            <span v-if="pi < j.pages.length - 1" class="journey-arrow">&rarr;</span>
                          </template>
                          <button v-if="j.pages.length > 5" class="journey-collapse-btn" @click.stop="expandedJourneys.delete(i)">collapse</button>
                        </template>
                        <!-- Long path (>5 pages): show first 2 + ...N more... + last 2 -->
                        <template v-else>
                          <span class="journey-step step-entry">{{ j.pages[0] }}</span>
                          <span class="journey-arrow">&rarr;</span>
                          <span class="journey-step">{{ j.pages[1] }}</span>
                          <span class="journey-arrow">&rarr;</span>
                          <button class="journey-more-btn" @click.stop="expandedJourneys.add(i); expandedJourneys = new Set(expandedJourneys)">+{{ j.pages.length - 4 }} more</button>
                          <span class="journey-arrow">&rarr;</span>
                          <span class="journey-step">{{ j.pages[j.pages.length - 2] }}</span>
                          <span class="journey-arrow">&rarr;</span>
                          <span class="journey-step step-exit">{{ j.pages[j.pages.length - 1] }}</span>
                        </template>
                      </div>
                      <div v-if="j.recommendations && j.recommendations.length" class="journey-recs">
                        <span class="rec-label">Recommended:</span>
                        <span v-for="(r, ri) in j.recommendations.slice(0, 3)" :key="ri" class="rec-item" :title="r.reason">{{ r.page }}</span>
                      </div>
                      <div v-if="j.predicted_next && j.predicted_next.length" class="journey-predicted">
                        <span class="predicted-label">Likely next:</span>
                        <span v-for="(p, pi) in j.predicted_next.slice(0, 3)" :key="pi" class="predicted-page">{{ p }}</span>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="card" v-else-if="journeys.length && !filteredJourneys.length">
                  <div class="empty-inline">No journeys match your filters</div>
                </div>
                <div class="card" v-else>
                  <div class="empty-inline">No journey data yet</div>
                </div>
              </div>

            </template>

            <!-- Inline + Add Widget -->
            <div class="ret-dyn-card ret-add-inline">
              <button class="ret-add-btn" @click.stop="showFlowPicker = !showFlowPicker">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3v14M3 10h14"/></svg>
              </button>
              <div v-if="showFlowPicker" class="card-picker-dropdown" @click.stop>
                <div class="card-picker-header">Add Widget</div>
                <div v-for="c in flowAvailableCards" :key="c.id" class="card-picker-item" :class="{ disabled: flowCards.includes(c.id) }" @click="addFlowCard(c.id)">
                  <div class="card-picker-icon" v-html="c.icon"></div>
                  <div class="card-picker-info">
                    <div class="card-picker-name">{{ c.title }}</div>
                    <div class="card-picker-desc">{{ c.desc }}</div>
                  </div>
                  <span v-if="flowCards.includes(c.id)" class="card-picker-check">✓</span>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- ═══════════ TAB 5: AI Insights ═══════════ -->
      <div v-show="activeTab === 'insights'" @click.self="showInsightPicker = false">

        <!-- Empty State -->
        <div v-if="!insightCards.length" class="ret-empty-state">
          <div class="ret-empty-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="var(--text-muted)" stroke-width="1.5">
              <circle cx="24" cy="20" r="12"/><path d="M18 32v2a6 6 0 0012 0v-2"/><line x1="24" y1="38" x2="24" y2="42"/>
            </svg>
          </div>
          <h3 class="ret-empty-title">Actionable Growth Insights</h3>
          <p class="ret-empty-desc">Add widgets to see AI-generated recommendations for improving traffic, engagement, and conversions.</p>
          <div class="ret-add-wrap">
            <button class="btn btn-primary" @click.stop="showInsightPicker = !showInsightPicker">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:6px"><path d="M7 1v12M1 7h12"/></svg>
              Add Widget
            </button>
            <div v-if="showInsightPicker" class="card-picker-dropdown card-picker-center" @click.stop>
              <div class="card-picker-header">Choose a widget</div>
              <div v-for="c in insightAvailableCards" :key="c.id" class="card-picker-item" :class="{ disabled: insightCards.includes(c.id) }" @click="addInsightCard(c.id)">
                <div class="card-picker-icon" v-html="c.icon"></div>
                <div class="card-picker-info">
                  <div class="card-picker-name">{{ c.title }}</div>
                  <div class="card-picker-desc">{{ c.desc }}</div>
                </div>
                <span v-if="insightCards.includes(c.id)" class="card-picker-check">✓</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Dynamic Card Grid -->
        <div v-else>
          <div class="ret-card-grid">
            <template v-for="cid in insightCards" :key="cid">

              <!-- Growth Actions -->
              <div v-if="cid === 'growth_actions'" class="ret-dyn-card ret-full">
                <button class="ret-card-close" @click="removeInsightCard(cid)">&times;</button>
                <div class="card">
                  <div class="card-header"><h3 class="card-title">🚀 Growth Actions</h3><span class="text-xs text-muted">Prioritized by impact</span></div>
                  <div v-if="insightsData.actions && insightsData.actions.length">
                    <div v-for="(a, i) in insightsData.actions" :key="i" class="growth-action-item">
                      <div class="growth-action-priority" :class="'gap-' + a.priority">{{ a.priority }}</div>
                      <div class="growth-action-content">
                        <div class="growth-action-title">{{ a.action }}</div>
                        <div class="growth-action-reason">{{ a.reason }}</div>
                      </div>
                      <div v-if="a.impact" class="growth-action-impact">{{ a.impact }}</div>
                    </div>
                  </div>
                  <div v-else class="empty-inline">Collecting data to generate actions...</div>
                </div>
              </div>

              <!-- Anomalies -->
              <div v-if="cid === 'anomalies'" class="ret-dyn-card ret-half">
                <button class="ret-card-close" @click="removeInsightCard(cid)">&times;</button>
                <div class="card">
                  <div class="card-header"><h3 class="card-title">⚡ Anomaly Detection</h3><span class="text-xs text-muted">Unusual patterns</span></div>
                  <div v-if="anomalyInsights.length">
                    <div v-for="(ins, i) in anomalyInsights" :key="i" class="insight-compact-item" :class="'ic-' + ins.type">
                      <span class="insight-compact-badge" :class="'icb-' + ins.type">{{ ins.type }}</span>
                      <div class="insight-compact-body">
                        <div class="insight-compact-title">{{ ins.title }}</div>
                        <div class="insight-compact-desc">{{ ins.description }}</div>
                      </div>
                      <span v-if="ins.metric" class="insight-compact-metric">{{ ins.metric }}</span>
                    </div>
                  </div>
                  <div v-else class="empty-inline">No anomalies detected</div>
                </div>
              </div>

              <!-- Content Performance -->
              <div v-if="cid === 'content_perf'" class="ret-dyn-card ret-half">
                <button class="ret-card-close" @click="removeInsightCard(cid)">&times;</button>
                <div class="card">
                  <div class="card-header"><h3 class="card-title">📄 Content Performance</h3><span class="text-xs text-muted">Top & underperforming pages</span></div>
                  <div v-if="contentInsights.length">
                    <div v-for="(ins, i) in contentInsights" :key="i" class="insight-compact-item" :class="'ic-' + ins.type">
                      <span class="insight-compact-badge" :class="'icb-' + ins.type">{{ ins.type }}</span>
                      <div class="insight-compact-body">
                        <div class="insight-compact-title">{{ ins.title }}</div>
                        <div class="insight-compact-desc">{{ ins.description }}</div>
                        <div v-if="ins.action" class="insight-compact-action">→ {{ ins.action }}</div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="empty-inline">Need more page data</div>
                </div>
              </div>

              <!-- Engagement Health -->
              <div v-if="cid === 'engagement_health'" class="ret-dyn-card ret-full">
                <button class="ret-card-close" @click="removeInsightCard(cid)">&times;</button>
                <div class="card">
                  <div class="card-header"><h3 class="card-title">💡 Engagement Health</h3><span class="text-xs text-muted">Behavioral patterns & improvement areas</span></div>
                  <div v-if="engagementInsights.length">
                    <div v-for="(ins, i) in engagementInsights" :key="i" class="insight-compact-item" :class="'ic-' + ins.type">
                      <span class="insight-compact-badge" :class="'icb-' + ins.type">{{ ins.type }}</span>
                      <div class="insight-compact-body">
                        <div class="insight-compact-title">{{ ins.title }}</div>
                        <div class="insight-compact-desc">{{ ins.description }}</div>
                        <div v-if="ins.action" class="insight-compact-action">→ {{ ins.action }}</div>
                      </div>
                      <span v-if="ins.metric" class="insight-compact-metric">{{ ins.metric }}</span>
                    </div>
                  </div>
                  <div v-else class="empty-inline">Need more engagement data</div>
                </div>
              </div>

            </template>

            <!-- Inline + Add Widget -->
            <div class="ret-dyn-card ret-add-inline">
              <button class="ret-add-btn" @click.stop="showInsightPicker = !showInsightPicker">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3v14M3 10h14"/></svg>
              </button>
              <div v-if="showInsightPicker" class="card-picker-dropdown" @click.stop>
                <div class="card-picker-header">Add Widget</div>
                <div v-for="c in insightAvailableCards" :key="c.id" class="card-picker-item" :class="{ disabled: insightCards.includes(c.id) }" @click="addInsightCard(c.id)">
                  <div class="card-picker-icon" v-html="c.icon"></div>
                  <div class="card-picker-info">
                    <div class="card-picker-name">{{ c.title }}</div>
                    <div class="card-picker-desc">{{ c.desc }}</div>
                  </div>
                  <span v-if="insightCards.includes(c.id)" class="card-picker-check">✓</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════ TAB 6: Keywords ═══════════ -->
      <div v-show="activeTab === 'keywords'" @click.self="showKeywordPicker = false">

        <!-- Empty State -->
        <div v-if="!keywordCards.length" class="ret-empty-state">
          <div class="ret-empty-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="var(--text-muted)" stroke-width="1.5">
              <path d="M12 36l8-8M16 32l-4 4"/><circle cx="28" cy="20" r="12"/><path d="M24 16l4 8h-8z"/>
            </svg>
          </div>
          <h3 class="ret-empty-title">AI-Guided Keywords</h3>
          <p class="ret-empty-desc">Discover trending keywords, track rankings, and get AI-powered SEO recommendations for your site.</p>
          <div class="ret-add-wrap">
            <button class="btn btn-primary" @click.stop="showKeywordPicker = !showKeywordPicker">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:6px"><path d="M7 1v12M1 7h12"/></svg>
              Add Widget
            </button>
            <div v-if="showKeywordPicker" class="card-picker-dropdown card-picker-center" @click.stop>
              <div class="card-picker-header">Choose a widget</div>
              <div v-for="c in keywordAvailableCards" :key="c.id" class="card-picker-item" :class="{ disabled: keywordCards.includes(c.id) }" @click="addKeywordCard(c.id)">
                <div class="card-picker-icon" v-html="c.icon"></div>
                <div class="card-picker-info">
                  <div class="card-picker-name">{{ c.title }}</div>
                  <div class="card-picker-desc">{{ c.desc }}</div>
                </div>
                <span v-if="keywordCards.includes(c.id)" class="card-picker-check">✓</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Dynamic Card Grid -->
        <div v-else>
          <div class="ret-card-grid">
            <template v-for="cid in keywordCards" :key="cid">

              <!-- Trending Now -->
              <div v-if="cid === 'trending_keywords'" class="ret-dyn-card ret-half">
                <button class="ret-card-close" @click="removeKeywordCard(cid)">&times;</button>
                <div class="card">
                  <div class="card-header"><h3 class="card-title">🔥 Trending Now</h3><span class="text-xs text-muted">Real-time trending searches</span></div>
                  <div v-if="trendingKeywords.length" class="kw-trending-list">
                    <div v-for="(kw, i) in trendingKeywords.slice(0, 10)" :key="i" class="kw-trending-item">
                      <span class="kw-trending-rank">#{{ i + 1 }}</span>
                      <span class="kw-trending-name">{{ kw.keyword || kw.title || kw }}</span>
                      <span v-if="kw.traffic" class="kw-trending-traffic">{{ kw.traffic }}</span>
                    </div>
                  </div>
                  <div v-else class="empty-inline">Loading trending keywords...</div>
                </div>
              </div>

              <!-- Keyword Opportunities -->
              <div v-if="cid === 'keyword_scores'" class="ret-dyn-card ret-half">
                <button class="ret-card-close" @click="removeKeywordCard(cid)">&times;</button>
                <div class="card">
                  <div class="card-header"><h3 class="card-title">🎯 Keyword Opportunities</h3><span class="text-xs text-muted">AI-scored by potential</span></div>
                  <div v-if="keywordScoresList.length" class="kw-scores-list">
                    <div v-for="(kw, i) in keywordScoresList" :key="i" class="kw-score-item">
                      <div class="kw-score-gauge" :class="'kw-grade-' + (kw.grade || 'C').charAt(0).toLowerCase()">{{ kw.score || 0 }}</div>
                      <div class="kw-score-info">
                        <div class="kw-score-keyword">{{ kw.keyword }}</div>
                        <div class="kw-score-rec">{{ kw.recommendation || kw.grade_label || '' }}</div>
                      </div>
                      <span v-if="kw.grade" class="kw-score-grade" :class="'kw-grade-' + kw.grade.charAt(0).toLowerCase()">{{ kw.grade }}</span>
                    </div>
                  </div>
                  <div v-else class="empty-inline">Add tracked keywords to see scores</div>
                </div>
              </div>

              <!-- AI Suggestions -->
              <div v-if="cid === 'keyword_suggestions'" class="ret-dyn-card ret-full">
                <button class="ret-card-close" @click="removeKeywordCard(cid)">&times;</button>
                <div class="card">
                  <div class="card-header"><h3 class="card-title">🤖 AI Keyword Suggestions</h3><span class="text-xs text-muted">Based on your site content & industry</span></div>
                  <div v-if="keywordSuggestionsList.length" class="kw-suggestions-grid">
                    <div v-for="(kw, i) in keywordSuggestionsList" :key="i" class="kw-suggestion-chip">
                      <span class="kw-suggestion-text">{{ kw.keyword || kw }}</span>
                      <span v-if="kw.relevance" class="kw-suggestion-rel">{{ kw.relevance }}%</span>
                      <span v-if="kw.source" class="kw-suggestion-src">{{ kw.source }}</span>
                    </div>
                  </div>
                  <div v-else class="empty-inline">Analyzing your site for keyword opportunities...</div>
                </div>
              </div>

              <!-- Tracked Keywords -->
              <div v-if="cid === 'keyword_tracker'" class="ret-dyn-card ret-full">
                <button class="ret-card-close" @click="removeKeywordCard(cid)">&times;</button>
                <div class="card">
                  <div class="card-header"><h3 class="card-title">📊 Tracked Keywords</h3><span class="text-xs text-muted">Monitor your rankings over time</span></div>
                  <div class="kw-tracker-note">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5" style="flex-shrink:0"><circle cx="7" cy="7" r="6"/><path d="M7 4v3M7 9v1"/></svg>
                    <span>Add keywords via the API to start tracking rank history. Scores refresh automatically.</span>
                  </div>
                </div>
              </div>

              <!-- Keyword Comparison (Google Trends) -->
              <div v-if="cid === 'keyword_compare'" class="ret-dyn-card ret-full">
                <button class="ret-card-close" @click="removeKeywordCard(cid)">&times;</button>
                <div class="card">
                  <div class="card-header"><h3 class="card-title">📈 Keyword Comparison</h3><span class="text-xs text-muted">Google Trends side-by-side</span></div>
                  <div class="kw-compare-input">
                    <input v-model="compareInput" class="flow-filter-input" placeholder="e.g. react, vue, angular (comma separated)" @keydown.enter="fetchCompareKeywords" />
                    <button class="btn btn-primary btn-sm" @click="fetchCompareKeywords" :disabled="compareLoading">{{ compareLoading ? 'Loading...' : 'Compare' }}</button>
                  </div>
                  <div v-if="compareData.data && compareData.data.length" class="kw-compare-results">
                    <div class="kw-compare-legend">
                      <span v-for="(kw, ki) in compareData.keywords" :key="ki" class="kw-compare-legend-item">
                        <span class="kw-legend-dot" :style="{ background: compareColors[ki] }"></span>
                        {{ kw }}
                      </span>
                    </div>
                    <div class="kw-compare-chart">
                      <div v-for="(point, pi) in compareData.data" :key="pi" class="kw-compare-bar-group">
                        <div class="kw-compare-bars">
                          <div v-for="(kw, ki) in compareData.keywords" :key="ki" class="kw-compare-bar" :style="{ height: (point[kw] || 0) + '%', background: compareColors[ki] }" :title="kw + ': ' + (point[kw] || 0)"></div>
                        </div>
                        <span class="kw-compare-date">{{ point.date ? point.date.slice(5) : '' }}</span>
                      </div>
                    </div>
                  </div>
                  <div v-else-if="compareData.note || compareData.error" class="empty-inline">{{ compareData.note || compareData.error }}</div>
                  <div v-else class="empty-inline">Enter keywords above and click Compare</div>
                </div>
              </div>

              <!-- Related Keywords -->
              <div v-if="cid === 'related_keywords'" class="ret-dyn-card ret-full">
                <button class="ret-card-close" @click="removeKeywordCard(cid)">&times;</button>
                <div class="card">
                  <div class="card-header"><h3 class="card-title">🔗 Related Keywords</h3><span class="text-xs text-muted">Rising & top queries from Google Trends</span></div>
                  <div class="kw-compare-input">
                    <input v-model="relatedInput" class="flow-filter-input" placeholder="Enter a keyword to explore..." @keydown.enter="fetchRelatedKeywords" />
                    <button class="btn btn-primary btn-sm" @click="fetchRelatedKeywords" :disabled="relatedLoading">{{ relatedLoading ? 'Loading...' : 'Explore' }}</button>
                  </div>
                  <div v-if="relatedData.rising && relatedData.rising.length || relatedData.top && relatedData.top.length" class="kw-related-results">
                    <div class="kw-related-cols">
                      <div class="kw-related-col" v-if="relatedData.rising && relatedData.rising.length">
                        <h4 class="kw-related-heading">🚀 Rising</h4>
                        <div v-for="(r, i) in relatedData.rising" :key="'r'+i" class="kw-related-item">
                          <span class="kw-related-name">{{ r.keyword }}</span>
                          <span class="kw-related-value rising">+{{ r.value }}%</span>
                        </div>
                      </div>
                      <div class="kw-related-col" v-if="relatedData.top && relatedData.top.length">
                        <h4 class="kw-related-heading">⭐ Top</h4>
                        <div v-for="(t, i) in relatedData.top" :key="'t'+i" class="kw-related-item">
                          <span class="kw-related-name">{{ t.keyword }}</span>
                          <span class="kw-related-value">{{ t.value }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div v-else-if="relatedData.note || relatedData.error" class="empty-inline">{{ relatedData.note || relatedData.error }}</div>
                  <div v-else class="empty-inline">Enter a keyword above and click Explore</div>
                </div>
              </div>

              <!-- SEO Keyword Scanner -->
              <div v-if="cid === 'seo_scanner'" class="ret-dyn-card ret-full">
                <button class="ret-card-close" @click="removeKeywordCard(cid)">&times;</button>
                <div class="card">
                  <div class="card-header">
                    <h3 class="card-title">🔍 SEO Keyword Scanner</h3>
                    <button class="btn btn-primary btn-sm" @click="runKeywordScan" :disabled="scanLoading">
                      {{ scanLoading ? 'Scanning...' : (scanData.score != null ? 'Re-scan' : 'Scan Site') }}
                    </button>
                  </div>

                  <div v-if="scanData.score != null" class="seo-scanner-results">
                    <!-- Score Gauge -->
                    <div class="seo-score-row">
                      <div class="seo-score-gauge" :class="scanData.score >= 70 ? 'sg-good' : scanData.score >= 40 ? 'sg-mid' : 'sg-bad'">
                        <span class="seo-score-num">{{ scanData.score }}</span>
                        <span class="seo-score-label">/ 100</span>
                      </div>
                      <div class="seo-score-meta">
                        <div class="seo-score-verdict" :class="scanData.score >= 70 ? 'sv-good' : scanData.score >= 40 ? 'sv-mid' : 'sv-bad'">
                          {{ scanData.score >= 70 ? 'Good' : scanData.score >= 40 ? 'Needs Work' : 'Poor' }}
                        </div>
                        <div class="text-xs text-muted">{{ scanData.page_meta?.word_count || 0 }} words • {{ scanData.keywords?.length || 0 }} keywords found</div>
                        <div v-if="scanData.scanned_at" class="text-xs text-muted" style="margin-top:2px">Scanned {{ new Date(scanData.scanned_at).toLocaleString() }}</div>
                      </div>
                    </div>

                    <!-- Score Breakdown -->
                    <div class="seo-breakdown">
                      <h4 class="seo-section-title">Score Breakdown</h4>
                      <div v-for="(comp, key) in scanData.score_breakdown" :key="key" v-if="comp && comp.label" class="seo-br-item">
                        <div class="seo-br-label">{{ comp.label }} <span class="text-xs text-muted">({{ comp.weight }}%)</span></div>
                        <div class="seo-br-bar-wrap">
                          <div class="seo-br-bar" :style="{ width: comp.score + '%' }" :class="comp.score >= 70 ? 'sb-good' : comp.score >= 40 ? 'sb-mid' : 'sb-bad'"></div>
                        </div>
                        <span class="seo-br-val">{{ comp.score }}</span>
                      </div>
                    </div>

                    <!-- Extracted Keywords -->
                    <div v-if="scanData.keywords?.length" class="seo-keywords-section">
                      <h4 class="seo-section-title">Extracted Keywords</h4>
                      <div class="seo-kw-table">
                        <div class="seo-kw-hdr">
                          <span>Keyword</span><span>Trend</span><span>Density</span><span>Found In</span>
                        </div>
                        <div v-for="(k, i) in scanData.keywords.slice(0, 10)" :key="i" class="seo-kw-row">
                          <span class="seo-kw-word">{{ k.keyword }}</span>
                          <span class="seo-kw-trend">
                            <span class="seo-trend-dot" :class="(scanData.trends?.[k.keyword]?.trend || 'unknown') === 'rising' ? 'st-up' : (scanData.trends?.[k.keyword]?.trend || 'unknown') === 'declining' ? 'st-down' : 'st-flat'"></span>
                            {{ scanData.trends?.[k.keyword]?.interest || 0 }}
                          </span>
                          <span :class="'seo-density ' + ('sd-' + k.density_status)">{{ k.density }}%</span>
                          <span class="seo-kw-locs">
                            <span v-for="l in k.locations" :key="l" class="seo-loc-pill">{{ l }}</span>
                          </span>
                        </div>
                      </div>
                    </div>

                    <!-- Synonym Suggestions -->
                    <div v-if="scanData.suggestions?.length" class="seo-synonyms-section">
                      <h4 class="seo-section-title">💡 Better Alternatives</h4>
                      <div class="seo-syn-table">
                        <div class="seo-syn-hdr">
                          <span>Your Keyword</span><span>→</span><span>Suggested</span><span>Improvement</span>
                        </div>
                        <div v-for="(s, i) in scanData.suggestions.slice(0, 8)" :key="i" class="seo-syn-row">
                          <span class="seo-syn-orig">{{ s.original }}</span>
                          <span class="seo-syn-arrow">→</span>
                          <span class="seo-syn-alt">{{ s.suggested }}</span>
                          <span class="seo-syn-delta">+{{ s.improvement }}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div v-else-if="scanData.error" class="empty-inline">{{ scanData.error }}</div>
                  <div v-else class="empty-inline">Click scan to analyze your site's keywords and get optimization suggestions</div>
                </div>
              </div>

            </template>

            <!-- Inline + Add Widget -->
            <div class="ret-dyn-card ret-add-inline">
              <button class="ret-add-btn" @click.stop="showKeywordPicker = !showKeywordPicker">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 3v14M3 10h14"/></svg>
              </button>
              <div v-if="showKeywordPicker" class="card-picker-dropdown" @click.stop>
                <div class="card-picker-header">Add Widget</div>
                <div v-for="c in keywordAvailableCards" :key="c.id" class="card-picker-item" :class="{ disabled: keywordCards.includes(c.id) }" @click="addKeywordCard(c.id)">
                  <div class="card-picker-icon" v-html="c.icon"></div>
                  <div class="card-picker-info">
                    <div class="card-picker-name">{{ c.title }}</div>
                    <div class="card-picker-desc">{{ c.desc }}</div>
                  </div>
                  <span v-if="keywordCards.includes(c.id)" class="card-picker-check">✓</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════ TAB 6: Events ═══════════ -->
      <div v-show="activeTab === 'events'">

        <!-- Search & Filter Bar -->
        <div class="filter-bar">
          <div class="filter-input-wrap">
            <svg class="filter-search-icon" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="7" cy="7" r="5"/><path d="M11 11l3 3"/></svg>
            <input class="filter-input" v-model="searchQuery" placeholder="Search pages, events, sources..." @keydown.enter="addFilter" />
          </div>
          <div class="filter-selects">
            <select class="filter-select" v-model="filterEvent" @change="addFilterFromSelect('event')">
              <option value="">Event Type</option>
              <option value="pageview">Pageview</option>
              <option value="click">Click</option>
              <option value="scroll">Scroll</option>
              <option value="form_submit">Form Submit</option>
            </select>
            <select class="filter-select" v-model="filterDevice" @change="addFilterFromSelect('device')">
              <option value="">Device</option>
              <option value="desktop">Desktop</option>
              <option value="mobile">Mobile</option>
              <option value="tablet">Tablet</option>
            </select>
            <select class="filter-select" v-model="filterCountry" @change="addFilterFromSelect('country')">
              <option value="">Country</option>
              <option v-for="c in countries" :key="c.name" :value="c.name">{{ c.name }}</option>
            </select>
          </div>
        </div>
        <!-- Active Filters -->
        <TransitionGroup name="chip" tag="div" class="filter-chips" v-if="activeFilters.length">
          <span v-for="(f, i) in activeFilters" :key="f.label" class="filter-chip">
            {{ f.label }}
            <button class="chip-remove" @click="removeFilter(i)">&times;</button>
          </span>
        </TransitionGroup>
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Visitor Profiles</h3>
            <span class="text-xs text-muted">{{ filteredVisitors.length }} of {{ visitorList.length }} visitors</span>
          </div>
          <table class="data-table" v-if="filteredVisitors.length">
            <thead>
              <tr><th>Visitor</th><th>Device</th><th>Country</th><th>Visits</th><th>Events</th><th>Last Seen</th></tr>
            </thead>
            <tbody>
              <tr v-for="v in filteredVisitors" :key="v.id" class="clickable-row" @click="loadTimeline(v.id)">
                <td>
                  <div class="visitor-id">{{ v.fingerprint_hash?.substring(0, 8) }}...</div>
                  <div class="text-xs text-muted" v-if="v.company_name">{{ v.company_name }}</div>
                </td>
                <td>{{ v.device_type || '--' }}<br><span class="text-xs text-muted">{{ v.browser }}</span></td>
                <td>{{ v.geo_country || '--' }} {{ v.geo_city || '' }}</td>
                <td class="font-semibold">{{ v.visit_count }}</td>
                <td>{{ v.event_count }}</td>
                <td class="text-xs text-muted">{{ formatDate(v.last_seen) }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-inline">{{ visitorList.length ? 'No visitors match your filters' : 'No visitor data yet' }}</div>
        </div>

        <!-- Visitor Timeline -->
        <div v-if="timelineEvents.length" class="card" style="margin-top:20px">
          <div class="card-header">
            <h3 class="card-title">Event Timeline</h3>
            <button class="btn btn-secondary btn-sm" @click="timelineEvents = []">Close</button>
          </div>
          <div class="timeline">
            <div v-for="e in timelineEvents" :key="e.id" class="timeline-item">
              <div class="timeline-dot" :class="'dot-' + e.event_type"></div>
              <div class="timeline-content">
                <span class="badge badge-sm" :class="eventBadge(e.event_type)">{{ e.event_type }}</span>
                <span class="text-sm truncate" style="max-width:300px">{{ e.url }}</span>
                <span class="text-xs text-muted">{{ formatTime(e.timestamp) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAnalyticsStore } from '@/stores/analytics'
import analyticsApi from '@/api/analytics'
import { Line, Bar, Doughnut, Radar, PolarArea } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, ArcElement, RadialLinearScale,
  Filler, Tooltip, Legend,
} from 'chart.js'

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, ArcElement, RadialLinearScale,
  Filler, Tooltip, Legend,
)

// Global Chart.js defaults for dark/professional look
ChartJS.defaults.color = '#8a8a9a'
ChartJS.defaults.font.family = "'Inter', 'SF Pro Display', system-ui, sans-serif"
ChartJS.defaults.font.size = 11

const route = useRoute()
const store = useAnalyticsStore()
const websiteId = route.params.websiteId

const tabs = [
  { id: 'overview', svg: '<path d="M2 14V6l4-4 4 4 4-4v12" stroke-linejoin="round"/>', label: 'Overview' },
  { id: 'funnels', svg: '<path d="M2 2h12l-3 5v5l-2 2V7z"/>', label: 'Funnels' },
  { id: 'retention', svg: '<path d="M1 8a7 7 0 0114 0M12 5l3 3-3 3"/><circle cx="8" cy="8" r="2"/>', label: 'Retention' },
  { id: 'flows', svg: '<path d="M1 4h4l3 4-3 4H1M15 4h-4l-3 4 3 4h4"/>', label: 'Flows' },
  { id: 'insights', svg: '<circle cx="8" cy="6" r="4"/><path d="M5 10v1a3 3 0 006 0v-1"/><line x1="8" y1="14" x2="8" y2="15"/>', label: 'AI Insights' },
  { id: 'keywords', svg: '<circle cx="7" cy="7" r="5"/><path d="M11 11l3 3"/>', label: 'Keywords' },
  { id: 'events', svg: '<path d="M3 2h10v12H3zM6 5h4M6 8h4M6 11h2"/>', label: 'Events' },
]

const periods = [
  { label: '5m', value: '5m' },
  { label: '15m', value: '15m' },
  { label: '30m', value: '30m' },
  { label: '1h', value: '1h' },
  { label: '6h', value: '6h' },
  { label: '24h', value: '24h' },
  { label: '7d', value: '7d' },
  { label: '30d', value: '30d' },
  { label: '90d', value: '90d' },
]

// ── Bind to store ──
const activeTab = computed(() => store.activeTab)
const period = computed(() => store.activePeriod)
const loading = computed(() => store.initialLoading)
const refreshing = computed(() => store.refreshing)

const cached = computed(() => store.data)
const stats = computed(() => cached.value.stats || [])
const chartData = computed(() => cached.value.chartData || [])
const topPages = computed(() => cached.value.topPages || [])
const sources = computed(() => cached.value.sources || [])
const devices = computed(() => cached.value.devices || [])
const countries = computed(() => cached.value.countries || [])
const realtimeVisitors = computed(() => cached.value.realtimeVisitors || 0)
const noData = computed(() => cached.value.noData)
const funnelList = computed(() => cached.value.funnelList || [])
const funnelResult = computed(() => cached.value.funnelResult)
const retentionData = computed(() => cached.value.retentionData || {})
const engagementData = computed(() => cached.value.engagementData || {})

// ── Customizable Retention Cards ──
const retAvailableCards = [
  { id: 'engagement_score', title: 'Engagement Score', desc: 'Composite health score (0-100) from bounce, depth, and return rate', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M8 4v4l3 2"/></svg>', size: 'half' },
  { id: 'new_vs_returning', title: 'New vs Returning', desc: 'Donut chart showing first-time vs repeat visitor split', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M8 2a6 6 0 010 12"/></svg>', size: 'half' },
  { id: 'bounce_rate', title: 'Bounce Rate', desc: 'Percentage of single-page sessions', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 12l4-8 4 8"/><line x1="5.5" y1="9" x2="10.5" y2="9"/></svg>', size: 'quarter' },
  { id: 'pages_session', title: 'Pages / Session', desc: 'Average number of pages viewed per visit', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="2"/><path d="M5 6h6M5 8h4M5 10h5"/></svg>', size: 'quarter' },
  { id: 'avg_duration', title: 'Avg Duration', desc: 'Average time visitors spend per session', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M8 4v4l3 2"/></svg>', size: 'quarter' },
  { id: 'total_sessions', title: 'Total Sessions', desc: 'Number of sessions in the selected period', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 12V4a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2z"/><path d="M5 8h6M8 5v6"/></svg>', size: 'quarter' },
  { id: 'top_returners', title: 'Top Returning Visitors', desc: 'Table of your most loyal repeat visitors', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="5" r="3"/><path d="M3 14c0-3 2-5 5-5s5 2 5 5"/></svg>', size: 'full' },
  { id: 'cohort_matrix', title: 'Cohort Retention', desc: 'Weekly retention heatmap by visitor cohort', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="1"/><path d="M2 6h12M2 10h12M6 2v12M10 2v12"/></svg>', size: 'full' },
]

const _retStorageKey = computed(() => `ftb_ret_cards_${store.activeWebsiteId}`)
const retentionCards = ref([])
const showCardPicker = ref(false)

// Load from localStorage on mount
onMounted(() => {
  try {
    const saved = localStorage.getItem(_retStorageKey.value)
    if (saved) retentionCards.value = JSON.parse(saved)
  } catch { /* ignore */ }
})

function _saveRetCards() {
  try { localStorage.setItem(_retStorageKey.value, JSON.stringify(retentionCards.value)) } catch {}
}

function addRetCard(id) {
  if (retentionCards.value.includes(id)) return
  retentionCards.value.push(id)
  _saveRetCards()
  showCardPicker.value = false
}

function removeRetCard(id) {
  retentionCards.value = retentionCards.value.filter(c => c !== id)
  _saveRetCards()
}

// ── Customizable Flow Cards ──
const flowAvailableCards = [
  { id: 'flow_patterns', title: 'Common Flow Patterns', desc: 'Page-to-page transitions ranked by frequency', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 8h4l2-4 2 4h4"/></svg>', size: 'half' },
  { id: 'entry_exit', title: 'Entry & Exit Pages', desc: 'Where visitors land and where they leave', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3v10M13 3v10M3 8h10"/><path d="M10 5l3 3-3 3"/></svg>', size: 'half' },
  { id: 'visitor_journeys', title: 'Visitor Journeys', desc: 'Per-session page paths with ML intent scoring and recommendations', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="3" cy="8" r="2"/><circle cx="13" cy="4" r="2"/><circle cx="13" cy="12" r="2"/><path d="M5 8h3l3-4M8 8l3 4"/></svg>', size: 'full' },
]

const _flowStorageKey = computed(() => `ftb_flow_cards_${store.activeWebsiteId}`)
const flowCards = ref([])
const showFlowPicker = ref(false)
const expandedJourneys = ref(new Set())

onMounted(() => {
  try {
    const saved = localStorage.getItem(_flowStorageKey.value)
    if (saved) flowCards.value = JSON.parse(saved)
  } catch {}
})

function _saveFlowCards() {
  try { localStorage.setItem(_flowStorageKey.value, JSON.stringify(flowCards.value)) } catch {}
}

function addFlowCard(id) {
  if (flowCards.value.includes(id)) return
  flowCards.value.push(id)
  _saveFlowCards()
  showFlowPicker.value = false
}

function removeFlowCard(id) {
  flowCards.value = flowCards.value.filter(c => c !== id)
  _saveFlowCards()
}

// ── Customizable Insight Cards ──
const insightAvailableCards = [
  { id: 'growth_actions', title: 'Growth Actions', desc: 'Prioritized action items ranked by expected impact', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2l2 4h4l-3 3 1 5-4-2-4 2 1-5-3-3h4z"/></svg>', size: 'full' },
  { id: 'anomalies', title: 'Anomaly Detection', desc: 'Traffic spikes, drops, and unusual behavioral patterns', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 12l3-2 3 4 3-8 3 6"/></svg>', size: 'half' },
  { id: 'content_perf', title: 'Content Performance', desc: 'Top and underperforming pages with improvement tips', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="2"/><path d="M5 6h6M5 9h4"/></svg>', size: 'half' },
  { id: 'engagement_health', title: 'Engagement Health', desc: 'Bounce, depth, and return rate with improvement suggestions', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2C4 2 1 8 1 8s3 6 7 6 7-6 7-6-3-6-7-6z"/><circle cx="8" cy="8" r="2"/></svg>', size: 'full' },
]

const _insightStorageKey = computed(() => `ftb_insight_cards_${store.activeWebsiteId}`)
const insightCards = ref([])
const showInsightPicker = ref(false)

onMounted(() => {
  try {
    const saved = localStorage.getItem(_insightStorageKey.value)
    if (saved) insightCards.value = JSON.parse(saved)
  } catch {}
})

function _saveInsightCards() {
  try { localStorage.setItem(_insightStorageKey.value, JSON.stringify(insightCards.value)) } catch {}
}

function addInsightCard(id) {
  if (insightCards.value.includes(id)) return
  insightCards.value.push(id)
  _saveInsightCards()
  showInsightPicker.value = false
}

function removeInsightCard(id) {
  insightCards.value = insightCards.value.filter(c => c !== id)
  _saveInsightCards()
}

// Computed: filter insights by category
const allInsights = computed(() => insightsData.value?.insights || [])
const anomalyInsights = computed(() => allInsights.value.filter(i => ['anomaly', 'warning', 'spike', 'drop'].includes(i.type)))
const contentInsights = computed(() => allInsights.value.filter(i => ['content', 'opportunity', 'success'].includes(i.type)))
const engagementInsights = computed(() => allInsights.value.filter(i => ['engagement', 'trend', 'info'].includes(i.type)))

// ── Customizable Keyword Cards ──
const keywordAvailableCards = [
  { id: 'trending_keywords', title: 'Trending Now', desc: 'Real-time trending searches from Google Trends', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 14l4-6 3 3 5-9"/></svg>', size: 'half' },
  { id: 'keyword_scores', title: 'Keyword Opportunities', desc: 'AI-scored keywords with quick-win detection and grades', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M8 4v4l3 2"/></svg>', size: 'half' },
  { id: 'keyword_suggestions', title: 'AI Suggestions', desc: 'Auto-generated keywords from your site content and industry', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 12l2-4h4l2 4M6 8V4l2-2 2 2v4"/></svg>', size: 'full' },
  { id: 'keyword_tracker', title: 'Tracked Keywords', desc: 'Monitor keyword rankings and position changes over time', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="1"/><path d="M2 6h12M2 10h12M6 2v12M10 2v12"/></svg>', size: 'full' },
  { id: 'keyword_compare', title: 'Keyword Comparison', desc: 'Compare up to 5 keywords side-by-side using Google Trends', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 14V4M6 14V2M10 14V6M14 14V8"/></svg>', size: 'full' },
  { id: 'related_keywords', title: 'Related Keywords', desc: 'Discover rising and top related queries for any keyword', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="3"/><path d="M8 1v4M8 11v4M1 8h4M11 8h4"/></svg>', size: 'full' },
  { id: 'seo_scanner', title: 'Keyword Agents', desc: 'Scan your site, check AI engine rankings (Claude, ChatGPT, Perplexity), get keyword optimization suggestions', icon: '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="7" cy="7" r="5"/><path d="M11 11l3 3"/><path d="M5 7h4M7 5v4"/></svg>', size: 'full' },
]

const _kwStorageKey = computed(() => `ftb_kw_cards_${store.activeWebsiteId}`)
const keywordCards = ref([])
const showKeywordPicker = ref(false)

onMounted(() => {
  try {
    const saved = localStorage.getItem(_kwStorageKey.value)
    if (saved) keywordCards.value = JSON.parse(saved)
  } catch {}
})

function _saveKwCards() {
  try { localStorage.setItem(_kwStorageKey.value, JSON.stringify(keywordCards.value)) } catch {}
}

function addKeywordCard(id) {
  if (keywordCards.value.includes(id)) return
  keywordCards.value.push(id)
  _saveKwCards()
  showKeywordPicker.value = false
}

function removeKeywordCard(id) {
  keywordCards.value = keywordCards.value.filter(c => c !== id)
  _saveKwCards()
}

// ── Google Trends Comparison ──
const compareInput = ref('')
const compareData = ref({})
const compareLoading = ref(false)
const compareColors = ['#6366f1', '#f59e0b', '#22c55e', '#ef4444', '#3b82f6']

const relatedInput = ref('')
const relatedData = ref({})
const relatedLoading = ref(false)

async function fetchCompareKeywords() {
  const kws = compareInput.value.split(',').map(k => k.trim()).filter(Boolean)
  if (!kws.length) return
  compareLoading.value = true
  try {
    const res = await analyticsApi.keywordInterest(store.activeWebsiteId, { keywords: kws.slice(0, 5) })
    compareData.value = res.data?.data || res.data || {}
  } catch (e) {
    compareData.value = { error: 'Failed to fetch comparison data' }
  } finally {
    compareLoading.value = false
  }
}

async function fetchRelatedKeywords() {
  const kw = relatedInput.value.trim()
  if (!kw) return
  relatedLoading.value = true
  try {
    const res = await analyticsApi.keywordInterest(store.activeWebsiteId, { keywords: [kw], related: true })
    relatedData.value = res.data?.data || res.data || {}
  } catch (e) {
    relatedData.value = { error: 'Failed to fetch related keywords' }
  } finally {
    relatedLoading.value = false
  }
}

// Computed: keyword data accessors
// ── SEO Keyword Scanner ──
const scanData = ref({})
const scanLoading = ref(false)

async function runKeywordScan() {
  scanLoading.value = true
  try {
    const res = await analyticsApi.keywordScanTrigger(store.activeWebsiteId)
    scanData.value = res.data?.data || res.data || {}
  } catch (e) {
    scanData.value = { error: 'Scan failed — check your site URL is accessible' }
  } finally {
    scanLoading.value = false
  }
}

// Computed: keyword data accessors
const keywordsData = computed(() => cached.value.keywordsData || {})
const trendingKeywords = computed(() => {
  const t = keywordsData.value.trending
  return Array.isArray(t) ? t : (t?.keywords || [])
})
const keywordScoresList = computed(() => {
  const s = keywordsData.value.scores
  return Array.isArray(s) ? s : (s?.scores || s?.keywords || [])
})
const keywordSuggestionsList = computed(() => {
  const s = keywordsData.value.suggestions
  return Array.isArray(s) ? s : (s?.suggestions || s?.keywords || [])
})

const flowData = computed(() => cached.value.flowData || {})
const entryExitData = computed(() => cached.value.entryExitData || {})
const insightsData = computed(() => cached.value.insightsData || {})
const visitorList = computed(() => cached.value.visitorList || [])
const timelineEvents = computed(() => cached.value.timelineEvents || [])

// ── Extended analytics data ──
const browserData = computed(() => cached.value.browserData || cached.value.browsers || [])
const liveEvents = computed(() => cached.value.liveEvents || [])
const journeys = computed(() => cached.value.journeys || [])
const browserColors = ['#5B8DEF', '#34D399', '#A78BFA', '#F59E0B', '#6B7280', '#EC4899']

// Engagement metrics (derived from stats)
const newVisitorPct = computed(() => {
  const s = stats.value.find(s => s.label?.toLowerCase()?.includes('new'))
  return s ? parseInt(s.value) || 65 : 65
})
const pagesPerSession = computed(() => {
  const s = stats.value.find(s => s.label?.toLowerCase()?.includes('page'))
  const visitors = stats.value.find(s => s.label?.toLowerCase()?.includes('visitor'))
  if (s && visitors && parseInt(visitors.value) > 0) {
    return (parseInt(s.value) / parseInt(visitors.value)).toFixed(1)
  }
  return '1.0'
})
const avgTimeOnPage = computed(() => {
  const s = stats.value.find(s => s.label?.toLowerCase()?.includes('session') || s.label?.toLowerCase()?.includes('time'))
  return s ? s.value : '0:00'
})
const bounceRate = computed(() => {
  const s = stats.value.find(s => s.label?.toLowerCase()?.includes('bounce'))
  return s ? parseInt(s.value) || 0 : 0
})
const conversionRate = computed(() => cached.value.conversionRate || 0)
const avgLoadTime = computed(() => cached.value.avgLoadTime || 0)

// Local UI state
const showCreateFunnel = ref(false)
const newFunnel = ref({ name: '', steps: [{ name: '', type: 'url', value: '' }, { name: '', type: 'url', value: '' }] })
const showTooltip = ref(null)

// ── Filter state ──
const searchQuery = ref('')
const filterEvent = ref('')
const filterDevice = ref('')
const filterCountry = ref('')
const activeFilters = ref([])

// ── Flow-specific filter state ──
const flowSearch = ref('')
const flowFilterSource = ref('')
const flowFilterPage = ref('')
const flowFilterDevice = ref('')
const flowFilterCountry = ref('')

const flowSources = computed(() => {
  const s = new Set()
  journeys.value.forEach(j => { if (j.source) s.add(j.source) })
  return [...s].sort()
})

const flowPages = computed(() => {
  const p = new Set()
  journeys.value.forEach(j => (j.pages || []).forEach(pg => p.add(pg)))
  return [...p].sort()
})

const flowDevices = computed(() => {
  const d = new Set()
  journeys.value.forEach(j => { if (j.device) d.add(j.device) })
  return [...d].sort()
})

const flowCountries = computed(() => {
  const c = new Set()
  journeys.value.forEach(j => { if (j.country) c.add(j.country) })
  return [...c].sort()
})

const activeFlowFilterCount = computed(() => {
  let n = 0
  if (flowSearch.value.trim()) n++
  if (flowFilterSource.value) n++
  if (flowFilterPage.value) n++
  if (flowFilterDevice.value) n++
  if (flowFilterCountry.value) n++
  return n
})

const filteredJourneys = computed(() => {
  let list = journeys.value
  const q = flowSearch.value.toLowerCase().trim()
  if (q) {
    list = list.filter(j =>
      (j.visitor_hash || '').toLowerCase().includes(q) ||
      (j.company || '').toLowerCase().includes(q) ||
      (j.source || '').toLowerCase().includes(q) ||
      (j.device || '').toLowerCase().includes(q) ||
      (j.country || '').toLowerCase().includes(q) ||
      (j.pages || []).some(p => p.toLowerCase().includes(q))
    )
  }
  if (flowFilterSource.value) {
    list = list.filter(j => j.source === flowFilterSource.value)
  }
  if (flowFilterPage.value) {
    list = list.filter(j => (j.pages || []).includes(flowFilterPage.value))
  }
  if (flowFilterDevice.value) {
    list = list.filter(j => j.device === flowFilterDevice.value)
  }
  if (flowFilterCountry.value) {
    list = list.filter(j => j.country === flowFilterCountry.value)
  }
  return list
})

function intentScoreClass(score) {
  if (score >= 60) return 'score-high'
  if (score >= 40) return 'score-med'
  if (score >= 20) return 'score-low'
  return 'score-bounce'
}

function addFilter() {
  if (searchQuery.value.trim()) {
    activeFilters.value.push({ type: 'search', label: `"${searchQuery.value.trim()}"` })
    searchQuery.value = ''
  }
}
function addFilterFromSelect(type) {
  const map = { event: filterEvent, device: filterDevice, country: filterCountry }
  const val = map[type].value
  if (val) {
    activeFilters.value.push({ type, label: `${type}: ${val}` })
    map[type].value = ''
  }
}
function removeFilter(i) { activeFilters.value.splice(i, 1) }

// ── Filtered visitors based on active filter chips ──
const filteredVisitors = computed(() => {
  let list = visitorList.value
  if (!activeFilters.value.length && !searchQuery.value.trim()) return list

  // Apply active filter chips
  for (const f of activeFilters.value) {
    if (f.type === 'search') {
      const q = f.label.replace(/^"|"$/g, '').toLowerCase()
      list = list.filter(v =>
        (v.fingerprint_hash || '').toLowerCase().includes(q) ||
        (v.company_name || '').toLowerCase().includes(q) ||
        (v.geo_city || '').toLowerCase().includes(q) ||
        (v.browser || '').toLowerCase().includes(q)
      )
    } else if (f.type === 'device') {
      const val = f.label.replace(/^device:\s*/i, '').toLowerCase()
      list = list.filter(v => (v.device_type || '').toLowerCase() === val)
    } else if (f.type === 'country') {
      const val = f.label.replace(/^country:\s*/i, '').toLowerCase()
      list = list.filter(v => (v.geo_country || '').toLowerCase() === val)
    } else if (f.type === 'event') {
      // Event type filter — keep visitors that have matching event types
      // Since we don't have per-visitor event types in the list, filter by general match
      const val = f.label.replace(/^event:\s*/i, '').toLowerCase()
      list = list.filter(v => v.event_count > 0 || val === 'pageview')
    }
  }

  // Live search (before pressing Enter)
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(v =>
      (v.fingerprint_hash || '').toLowerCase().includes(q) ||
      (v.company_name || '').toLowerCase().includes(q) ||
      (v.geo_city || '').toLowerCase().includes(q) ||
      (v.geo_country || '').toLowerCase().includes(q) ||
      (v.browser || '').toLowerCase().includes(q) ||
      (v.device_type || '').toLowerCase().includes(q)
    )
  }

  return list
})

// ── Flow insights: user-level analysis ──
const flowInsights = computed(() => {
  const insights = []
  const entries = entryExitData.value?.entry_pages || []
  const exits = entryExitData.value?.exit_pages || []
  const links = flowData.value?.links || []
  const jList = journeys.value || []
  const keyPages = ['/pricing', '/features', '/about', '/signup', '/demo', '/contact', '/blog']
  const allVisitedPages = new Set()
  jList.forEach(j => (j.pages || []).forEach(p => allVisitedPages.add(p)))
  links.forEach(l => { allVisitedPages.add(cleanPath(l.source)); allVisitedPages.add(cleanPath(l.target)) })

  if (jList.length) {
    jList.forEach((j, idx) => {
      const pages = j.pages || []
      if (!pages.length) return
      const visited = new Set(pages)
      const viewedProduct = pages.some(p => p.startsWith('/product'))
      const reachedLogin = pages.some(p => p.includes('login') || p.includes('signup'))
      const sawPricing = visited.has('/pricing')
      const name = j.company || j.visitor_hash || `Visitor ${idx + 1}`
      let intent = 'Browsing', sev = 'dot-neutral'
      if (reachedLogin) { intent = 'High intent - tried to log in'; sev = 'dot-success' }
      else if (viewedProduct && sawPricing) { intent = 'Evaluating - viewed product + pricing'; sev = 'dot-info' }
      else if (viewedProduct) { intent = 'Interested - viewed a product'; sev = 'dot-warning' }
      else if (pages.length <= 1) { intent = 'Quick visit - single page'; sev = 'dot-muted' }
      insights.push({ severity: sev, title: name, value: pages.join(' > '), desc: `${intent}. ${pages.length} pages visited${j.duration_secs ? ', ' + formatDuration(j.duration_secs) + ' session' : ''}.` })
      if (pages.length > 1) {
        const critical = []
        if (viewedProduct && !sawPricing) critical.push('/pricing')
        if (viewedProduct && !visited.has('/signup') && !reachedLogin) critical.push('/signup')
        if (!visited.has('/features')) critical.push('/features')
        if (critical.length) {
          insights.push({ severity: 'dot-danger', title: `${name} - missed pages`, value: critical.join(', '), desc: viewedProduct && !sawPricing ? 'Viewed a product but never saw pricing. Add pricing CTAs on product pages.' : 'Consider adding navigation prompts to guide visitors to these key pages.' })
        }
      }
    })
  }

  const missedOverall = keyPages.filter(p => !allVisitedPages.has(p))
  if (missedOverall.length && allVisitedPages.size > 0) {
    insights.push({ severity: 'dot-danger', title: 'Pages with zero visits', value: missedOverall.join(', '), desc: 'No visitors have reached these pages. Check navigation links and internal linking.' })
  }
  if (entries.length) {
    insights.push({ severity: 'dot-info', title: 'Top landing page', value: cleanPath(entries[0].page), desc: `${entries[0].count} visit${entries[0].count > 1 ? 's' : ''} start here.` })
  }
  if (exits.length) {
    const top = exits[0]
    const isConversion = cleanPath(top.page).match(/signup|login|checkout|thank/)
    insights.push({ severity: isConversion ? 'dot-success' : 'dot-danger', title: isConversion ? 'Conversion exit' : 'Top drop-off', value: cleanPath(top.page), desc: isConversion ? `${top.count} visitors leave after ${cleanPath(top.page)}.` : `${top.count} visitors leave from here. Add CTAs or improve content.` })
  }
  return insights
})



function cleanPath(url) {
  if (!url) return '--'
  try { return new URL(url).pathname } catch { return url.startsWith('/') ? url : '/' + url }
}

function flowBarWidth(value) {
  const links = flowData.value?.links || []
  const max = links.length ? links[0].value : 1
  return Math.max(8, (value / max) * 100)
}

function flowBarColor(i) {
  const colors = ['var(--brand-accent)', '#34d399', '#fbbf24', '#f97316', '#a78bfa', '#f472b6']
  return colors[i % colors.length]
}

function entryPct(count) {
  const entries = entryExitData.value?.entry_pages || []
  const max = entries.length ? entries[0].count : 1
  return Math.max(8, (count / max) * 100)
}

function exitPct(count) {
  const exits = entryExitData.value?.exit_pages || []
  const max = exits.length ? exits[0].count : 1
  return Math.max(8, (count / max) * 100)
}

// ── KPI tooltip definitions ──
const kpiTooltips = {
  'UNIQUE VISITORS': 'Count of distinct visitor IDs in the selected time period.',
  'PAGE VIEWS': 'Total number of pages loaded by all visitors.',
  'AVG. SESSION': 'Average time between first and last event in a session.',
  'BOUNCE RATE': 'Percentage of single-page sessions. Formula: (Single-page sessions \u00f7 Total sessions) \u00d7 100',
}

// ── Helpers ──
function eventBadge(type) {
  const m = { pageview: 'badge-info', click: 'badge-warning', scroll: 'badge-neutral', form_submit: 'badge-success', exit: 'badge-danger' }
  return m[type] || 'badge-neutral'
}
function formatTime(ts) {
  if (!ts) return '--'
  const d = new Date(ts)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
function formatDate(ts) {
  if (!ts) return '--'
  return new Date(ts).toLocaleDateString()
}
function formatDuration(secs) {
  if (!secs || secs <= 0) return '--'
  const m = Math.floor(secs / 60)
  const s = secs % 60
  if (m > 60) return `${Math.floor(m / 60)}h ${m % 60}m`
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

// ════════════ CHART.JS CONFIGURATIONS ════════════

// Traffic Overview — Line chart with gradient fill
const trafficChartData = computed(() => ({
  labels: chartData.value.map(d => d.label),
  datasets: [
    {
      label: 'Visitors',
      data: chartData.value.map(d => d.visitors || 0),
      borderColor: '#5B8DEF',
      backgroundColor: 'rgba(91, 141, 239, 0.08)',
      fill: true,
      tension: 0.4,
      borderWidth: 2.5,
      pointRadius: 0,
      pointHoverRadius: 5,
      pointHoverBackgroundColor: '#5B8DEF',
      pointHoverBorderColor: '#fff',
      pointHoverBorderWidth: 2,
    },
    {
      label: 'Page Views',
      data: chartData.value.map(d => d.pageviews || 0),
      borderColor: '#3498db',
      backgroundColor: 'rgba(52, 152, 219, 0.05)',
      fill: true,
      tension: 0.4,
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 4,
      pointHoverBackgroundColor: '#3498db',
      pointHoverBorderColor: '#fff',
      pointHoverBorderWidth: 2,
    },
  ],
}))

const trafficChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { display: true, position: 'top', align: 'end', labels: { usePointStyle: true, pointStyle: 'circle', padding: 20, boxWidth: 6 } },
    tooltip: {
      backgroundColor: 'rgba(26, 26, 46, 0.95)',
      titleColor: '#fff',
      bodyColor: '#ccc',
      borderColor: 'rgba(91, 141, 239, 0.15)',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
      displayColors: true,
      boxWidth: 8,
      boxHeight: 8,
      usePointStyle: true,
    },
  },
  scales: {
    x: {
      grid: { display: false },
      border: { display: false },
      ticks: { maxTicksLimit: 8, padding: 8 },
    },
    y: {
      grid: { color: 'rgba(138, 138, 154, 0.08)', drawTicks: false },
      border: { display: false },
      ticks: { padding: 12 },
      beginAtZero: true,
    },
  },
}

// Sources — Horizontal Bar chart
const sourcesChartData = computed(() => ({
  labels: sources.value.map(s => s.name),
  datasets: [{
    label: 'Sessions',
    data: sources.value.map(s => s.sessions || 0),
    backgroundColor: ['#5B8DEF', '#34D399', '#A78BFA', '#F59E0B', '#6B7280', '#EC4899'],
    borderRadius: 4,
    barThickness: 22,
  }],
}))

const sourcesChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: 'y',
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(26, 26, 46, 0.95)',
      titleColor: '#fff',
      bodyColor: '#ccc',
      borderColor: 'rgba(91, 141, 239, 0.15)',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
    },
  },
  scales: {
    x: {
      grid: { color: 'rgba(138, 138, 154, 0.08)', drawTicks: false },
      border: { display: false },
      ticks: { padding: 8 },
      beginAtZero: true,
    },
    y: {
      grid: { display: false },
      border: { display: false },
      ticks: { padding: 8 },
    },
  },
}

// Devices — Doughnut chart
const deviceColors = ['#5B8DEF', '#34D399', '#A78BFA', '#F59E0B', '#6B7280']
const devicesChartData = computed(() => ({
  labels: devices.value.map(d => d.name),
  datasets: [{
    data: devices.value.map(d => d.pct || 0),
    backgroundColor: deviceColors.slice(0, devices.value.length),
    borderWidth: 0,
    hoverOffset: 6,
  }],
}))

const devicesChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '65%',
  plugins: {
    legend: { display: true, position: 'right', labels: { usePointStyle: true, pointStyle: 'circle', padding: 14, boxWidth: 8, font: { size: 12 } } },
    tooltip: {
      backgroundColor: 'rgba(26, 26, 46, 0.95)',
      titleColor: '#fff',
      bodyColor: '#ccc',
      borderColor: 'rgba(91, 141, 239, 0.15)',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
      callbacks: { label: (ctx) => `${ctx.label}: ${ctx.parsed}%` },
    },
  },
}

// Engagement Radar chart
const radarChartData = computed(() => ({
  labels: ['Bounce Rate', 'Session Duration', 'Pages/Visit', 'Return Rate', 'Scroll Depth'],
  datasets: [{
    label: 'Engagement',
    data: [
      100 - bounceRate.value,
      Math.min(parseFloat(avgTimeOnPage.value) * 20 || 30, 100),
      Math.min(parseFloat(pagesPerSession.value) * 25 || 25, 100),
      100 - newVisitorPct.value,
      65,
    ],
    backgroundColor: 'rgba(91, 141, 239, 0.15)',
    borderColor: '#5B8DEF',
    borderWidth: 2,
    pointBackgroundColor: '#5B8DEF',
    pointBorderColor: '#fff',
    pointRadius: 4,
    pointHoverRadius: 6,
  }],
}))

const radarChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(26, 26, 46, 0.95)',
      titleColor: '#fff', bodyColor: '#ccc',
      borderColor: 'rgba(91, 141, 239, 0.15)', borderWidth: 1,
      padding: 12, cornerRadius: 8,
      callbacks: { label: (ctx) => `${ctx.label}: ${ctx.parsed.r}/100` },
    },
  },
  scales: {
    r: {
      beginAtZero: true, max: 100,
      grid: { color: 'rgba(138, 138, 154, 0.08)' },
      pointLabels: { font: { size: 11 }, color: '#8a8a9a' },
      ticks: { display: false },
    },
  },
}

// Traffic Sources — PolarArea (alternative view)
const polarChartData = computed(() => ({
  labels: sources.value.map(s => s.name),
  datasets: [{
    data: sources.value.map(s => s.sessions || 0),
    backgroundColor: [
      'rgba(91, 141, 239, 0.7)',
      'rgba(52, 211, 153, 0.7)',
      'rgba(167, 139, 250, 0.7)',
      'rgba(245, 158, 11, 0.7)',
      'rgba(107, 114, 128, 0.7)',
      'rgba(236, 72, 153, 0.7)',
    ],
    borderWidth: 0,
  }],
}))

const polarChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: true, position: 'right', labels: { usePointStyle: true, pointStyle: 'circle', padding: 14, boxWidth: 8, font: { size: 12 } } },
    tooltip: {
      backgroundColor: 'rgba(26, 26, 46, 0.95)',
      titleColor: '#fff', bodyColor: '#ccc',
      borderColor: 'rgba(91, 141, 239, 0.15)', borderWidth: 1,
      padding: 12, cornerRadius: 8,
    },
  },
  scales: {
    r: {
      grid: { color: 'rgba(138, 138, 154, 0.08)' },
      ticks: { display: false },
    },
  },
}

// ════════════ UTILITY FUNCTIONS ════════════

const maxRetentionWeeks = computed(() => {
  if (!retentionData.value.rows?.length) return 0
  return Math.max(...retentionData.value.rows.map(r => r.weeks?.length || 0))
})

function retentionColor(pct) {
  if (pct >= 80) return 'rgba(39, 174, 96, 0.3)'
  if (pct >= 60) return 'rgba(39, 174, 96, 0.2)'
  if (pct >= 40) return 'rgba(201, 160, 80, 0.2)'
  if (pct >= 20) return 'rgba(231, 76, 60, 0.15)'
  if (pct > 0) return 'rgba(231, 76, 60, 0.1)'
  return 'transparent'
}

// ── Engagement Score Ring ──
const engScoreColor = computed(() => {
  const s = engagementData.value.engagement_score || 0
  if (s >= 60) return 'var(--color-success)'
  if (s >= 40) return 'var(--color-info)'
  if (s >= 20) return 'var(--color-warning)'
  return 'var(--color-danger)'
})

const engDash = computed(() => {
  const circ = 2 * Math.PI * 50 // r=50
  const score = engagementData.value.engagement_score || 0
  const filled = circ * score / 100
  return `${filled} ${circ - filled}`
})

// ── New vs Returning Donut ──
const donutCirc = 2 * Math.PI * 44 // r=44

const newDonutDash = computed(() => {
  const pct = engagementData.value.new_pct || 0
  const filled = donutCirc * pct / 100
  return `${filled} ${donutCirc - filled}`
})

const retDonutDash = computed(() => {
  const pct = engagementData.value.returning_pct || 0
  const filled = donutCirc * pct / 100
  return `${filled} ${donutCirc - filled}`
})

const retDonutOffset = computed(() => {
  const newPct = engagementData.value.new_pct || 0
  return `-${donutCirc * newPct / 100}`
})

// ── Relative time helper ──
function relativeTime(iso) {
  if (!iso) return '—'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days}d ago`
  return `${Math.floor(days / 7)}w ago`
}

// ── Store-backed actions ──
function switchTab(tabId) {
  store.switchTab(tabId)
}

function changePeriod(p) {
  store.changePeriod(p)
}

async function runFunnel(fid) {
  await store.runFunnel(websiteId, fid, period.value)
}

async function createFunnel() {
  await store.createFunnel(websiteId, { name: newFunnel.value.name, steps: newFunnel.value.steps })
  showCreateFunnel.value = false
  newFunnel.value = { name: '', steps: [{ name: '', type: 'url', value: '' }, { name: '', type: 'url', value: '' }] }
}

async function loadTimeline(vid) {
  await store.loadTimeline(websiteId, vid)
}

// ── Save to sessionStorage when data changes ──
let saveTimer = null
watch(() => store.cache, () => {
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => store.saveToSession(), 500)
}, { deep: true })

// ── Init ──
const isRefreshing = ref(false)

function handleRefresh() {
  isRefreshing.value = true
  store.forceRefresh()
  setTimeout(() => { isRefreshing.value = false }, 1000)
}

onMounted(async () => {
  store.init(websiteId, period.value)
  await store.fetchOverview(websiteId, period.value)
  store.fetchLiveEvents(websiteId)
  store.startPolling()
})

onBeforeUnmount(() => {
  store.stopPolling()
  store.saveToSession()
})
</script>

<style scoped>
.loading-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 20px; color: var(--text-muted); }
.refresh-indicator { display: flex; align-items: center; gap: 8px; padding: 6px 14px; font-size: var(--font-xs); color: var(--text-muted); }
.refresh-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--brand-accent); animation: pulse 1s infinite; }

/* Refresh Button */
.refresh-btn {
  display: flex; align-items: center; justify-content: center;
  width: 34px; height: 34px; border-radius: var(--radius-md);
  border: 1px solid var(--border-color); background: var(--bg-card);
  color: var(--text-secondary); cursor: pointer;
  transition: all 0.2s;
}
.refresh-btn:hover { border-color: var(--brand-accent); color: var(--brand-accent); }
.refresh-btn.spinning svg { animation: spin-refresh 0.8s ease; }
@keyframes spin-refresh { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* ── Tabs ── */
.analytics-tabs { display: flex; gap: 4px; margin-bottom: 24px; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 4px; overflow-x: auto; }
.atab { display: flex; align-items: center; gap: 6px; padding: 10px 16px; border: none; background: transparent; border-radius: var(--radius-md); font-size: var(--font-sm); font-weight: 600; color: var(--text-muted); cursor: pointer; transition: all 0.15s; white-space: nowrap; font-family: var(--font-family); }
.atab:hover { color: var(--text-primary); background: var(--bg-surface); }
.atab.active { background: var(--text-primary); color: var(--text-inverse); }
.atab-icon { width: 16px; height: 16px; flex-shrink: 0; }
.chart-container canvas { width: 100% !important; }

/* ── Chart Entrance Animations ── */
@keyframes chart-fade-up {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
.chart-animate > .card {
  animation: chart-fade-up 0.6s cubic-bezier(0.22, 1, 0.36, 1) both;
}
.chart-animate > .card:nth-child(2) {
  animation-delay: 0.15s;
}
.chart-animate-delay {
  animation: chart-fade-up 0.6s cubic-bezier(0.22, 1, 0.36, 1) 0.2s both;
}

/* ── KPI Grid ── */
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 24px; }
.kpi-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 20px; transition: all var(--transition-base); }
.kpi-card:hover { border-color: var(--border-hover); box-shadow: var(--shadow-sm); }
.kpi-highlight { border-color: var(--brand-accent); background: linear-gradient(135deg, var(--bg-card) 0%, rgba(91, 141, 239, 0.04) 100%); }
.kpi-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.kpi-label { font-size: var(--font-xs); font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.06em; }
.kpi-trend { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: var(--radius-full); }
.trend-up { color: var(--color-success); background: var(--color-success-bg); }
.trend-down { color: var(--color-danger); background: var(--color-danger-bg); }
.kpi-value { font-family: var(--font-display); font-size: var(--font-3xl); color: var(--text-primary); line-height: 1.1; }

/* ── Chart ── */
.chart-card { margin-bottom: 24px; }
.chart-legend { display: flex; gap: 16px; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: var(--font-xs); color: var(--text-secondary); }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.area-chart-wrap { position: relative; margin-top: 12px; }
.area-chart-svg { width: 100%; height: 220px; display: block; }
.chart-tooltip { position: absolute; top: 10px; transform: translateX(-50%); background: var(--text-primary); color: var(--text-inverse); padding: 8px 14px; border-radius: var(--radius-md); font-size: var(--font-xs); white-space: nowrap; z-index: 10; box-shadow: var(--shadow-md); pointer-events: none; }
.area-chart-labels { display: flex; justify-content: space-between; padding: 8px 0 0; font-size: 10px; color: var(--text-muted); }
.area-chart-labels .highlighted { color: var(--text-secondary); font-weight: 600; }

/* ── Layout ── */
.analytics-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }

/* ── Channels ── */
.channel-list { display: flex; flex-direction: column; gap: 14px; }
.channel-item { display: flex; align-items: center; gap: 14px; }
.channel-info { min-width: 130px; }
.channel-name { font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); display: block; }
.channel-bar-wrap { flex: 1; height: 6px; background: var(--bg-surface); border-radius: var(--radius-full); overflow: hidden; }
.channel-bar { height: 100%; border-radius: var(--radius-full); transition: width var(--transition-slow); }
.channel-pct { font-size: var(--font-sm); font-weight: 700; color: var(--text-primary); min-width: 36px; text-align: right; }

/* ── Pages ── */
.page-rank { width: 22px; height: 22px; background: var(--bg-surface); border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: var(--text-muted); margin-right: 8px; }

/* ── Devices ── */
.device-breakdown { display: flex; align-items: center; gap: 28px; }
.donut-chart { position: relative; width: 120px; height: 120px; flex-shrink: 0; }
.donut-chart svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.device-legend { display: flex; flex-direction: column; gap: 10px; flex: 1; }
.device-legend-item { display: flex; align-items: center; gap: 10px; font-size: var(--font-sm); }
.device-name { flex: 1; color: var(--text-secondary); }
.device-value { color: var(--text-primary); }

/* ── Countries ── */
.country-list { display: flex; flex-direction: column; gap: 10px; }
.country-item { display: flex; align-items: center; gap: 12px; }
.country-rank { width: 22px; height: 22px; background: var(--bg-surface); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: var(--text-muted); }
.country-info { flex: 1; }
.country-name { font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
.country-bar-wrap { height: 4px; background: var(--bg-surface); border-radius: var(--radius-full); overflow: hidden; }
.country-bar { height: 100%; background: var(--brand-accent); border-radius: var(--radius-full); }

/* ── Realtime ── */
.realtime-card { display: flex; align-items: center; gap: 12px; padding: 16px 24px; }
.realtime-dot { width: 10px; height: 10px; background: var(--color-success); border-radius: 50%; animation: pulse 2s infinite; }

/* ── Period Tabs ── */
.period-tabs { display: flex; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-full); overflow: hidden; }
.period-tab { padding: 6px 14px; font-size: var(--font-xs); font-weight: 600; color: var(--text-muted); background: transparent; border: none; cursor: pointer; transition: all var(--transition-fast); font-family: var(--font-family); }
.period-tab:hover { color: var(--text-primary); }
.period-tab.active { background: var(--brand-accent); color: #1a1a2e; }

/* ── Funnels ── */
.funnel-list { display: flex; flex-direction: column; gap: 8px; }
.funnel-item { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; background: var(--bg-surface); border-radius: var(--radius-md); cursor: pointer; transition: all 0.15s; }
.funnel-item:hover { background: var(--bg-card); border: 1px solid var(--border-hover); }
.funnel-viz { display: flex; gap: 4px; align-items: flex-end; padding: 20px 0; height: 200px; }
.funnel-step { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8px; height: 100%; }
.funnel-bar { width: 100%; background: rgba(91,141,239,0.08); border-radius: var(--radius-md) var(--radius-md) 0 0; position: relative; min-height: 20px; transition: height 0.5s; display: flex; align-items: flex-end; }
.funnel-bar-fill { width: 100%; height: 100%; background: linear-gradient(180deg, var(--brand-accent), rgba(91,141,239,0.3)); border-radius: var(--radius-md) var(--radius-md) 0 0; }
.funnel-step-info { text-align: center; }
.text-danger { color: var(--color-danger); }

/* ── Retention ── */
.retention-table { font-size: var(--font-xs); }
/* ── Retention: Empty State ── */
.ret-empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 300px; text-align: center; padding: 40px 20px; }
.ret-empty-icon { margin-bottom: 16px; opacity: 0.5; }
.ret-empty-title { font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0 0 8px; }
.ret-empty-desc { font-size: 13px; color: var(--text-muted); margin: 0 0 24px; max-width: 360px; }
.ret-add-wrap { position: relative; display: inline-block; }

/* ── Card Picker Dropdown ── */
.card-picker-dropdown { position: absolute; top: 100%; right: 0; z-index: 100; width: 320px; max-height: 400px; overflow-y: auto; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); box-shadow: 0 12px 40px rgba(0,0,0,0.2); margin-top: 8px; animation: pickerFadeIn 0.15s ease; }
.card-picker-center { left: 50%; transform: translateX(-50%); }
@keyframes pickerFadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
.card-picker-header { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); padding: 12px 16px 8px; }
.card-picker-item { display: flex; align-items: center; gap: 12px; padding: 10px 16px; cursor: pointer; transition: background 0.15s; }
.card-picker-item:hover:not(.disabled) { background: var(--bg-surface); }
.card-picker-item.disabled { opacity: 0.4; cursor: default; }
.card-picker-icon { flex-shrink: 0; color: var(--brand-accent); }
.card-picker-info { flex: 1; min-width: 0; }
.card-picker-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.card-picker-desc { font-size: 11px; color: var(--text-muted); line-height: 1.3; }
.card-picker-check { color: var(--color-success); font-size: 14px; font-weight: 700; }

/* ── Dynamic Card Grid ── */
.ret-card-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
@media (max-width: 768px) { .ret-card-grid { grid-template-columns: repeat(2, 1fr); } }
.ret-dyn-card { position: relative; animation: cardSlideIn 0.25s ease; }
@keyframes cardSlideIn { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
.ret-half { grid-column: span 2; }
.ret-quarter { grid-column: span 1; }
.ret-full { grid-column: 1 / -1; }
.ret-card-close { position: absolute; top: 8px; right: 8px; z-index: 5; width: 22px; height: 22px; border: none; border-radius: 50%; background: var(--bg-surface); color: var(--text-muted); font-size: 16px; line-height: 1; cursor: pointer; opacity: 0; transition: opacity 0.15s, background 0.15s, color 0.15s; display: flex; align-items: center; justify-content: center; }
.ret-dyn-card:hover .ret-card-close { opacity: 1; }
.ret-card-close:hover { background: var(--color-danger); color: white; }

/* ── Add Widget Inline ── */
.ret-add-inline { display: flex; align-items: center; justify-content: flex-end; position: relative; min-height: auto; border: none; border-radius: 0; grid-column: 1 / -1; padding: 0; margin: -8px 0 8px; order: -1; }
.ret-add-btn { width: 36px; height: 36px; border-radius: 50%; border: 2px solid var(--border-color); background: var(--bg-card); color: var(--text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s; box-shadow: var(--shadow-sm); }
.ret-add-btn:hover { border-color: var(--brand-accent); color: var(--brand-accent); background: rgba(99,102,241,0.08); }

/* ── Engagement Score Ring ── */
.engagement-score-card { display: flex; flex-direction: column; }
.engagement-ring-wrap { position: relative; display: flex; align-items: center; justify-content: center; padding: 16px 0; }
.engagement-ring { width: 130px; height: 130px; }
.ring-progress { transition: stroke-dasharray 1s ease; }
.engagement-ring-label { position: absolute; text-align: center; }
.eng-score-num { font-size: 32px; font-weight: 700; color: var(--text-primary); }
.eng-score-unit { font-size: 13px; color: var(--text-muted); margin-left: 2px; }
.eng-breakdown { padding: 0 8px; display: flex; flex-direction: column; gap: 8px; }
.eng-factor { display: flex; align-items: center; gap: 8px; }
.eng-factor-label { font-size: 11px; color: var(--text-muted); min-width: 72px; }
.eng-factor-bar { flex: 1; height: 6px; background: var(--bg-surface); border-radius: var(--radius-full); overflow: hidden; }
.eng-factor-fill { height: 100%; border-radius: var(--radius-full); transition: width 0.8s ease; }

/* ── Donut Chart ── */
.donut-wrap { position: relative; display: flex; align-items: center; justify-content: center; padding: 16px 0; }
.donut-chart { width: 140px; height: 140px; }
.donut-arc { transition: stroke-dasharray 0.8s ease, stroke-dashoffset 0.8s ease; }
.donut-center-label { position: absolute; text-align: center; }
.donut-big { font-size: 26px; font-weight: 700; color: var(--text-primary); display: block; }
.donut-sub { font-size: 11px; color: var(--text-muted); }
.donut-legend { display: flex; gap: 20px; justify-content: center; padding-top: 8px; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

/* ── Retention Stat Grid ── */
.ret-stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
@media (max-width: 768px) { .ret-stat-grid { grid-template-columns: repeat(2, 1fr); } }
.ret-stat-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 20px; text-align: center; transition: transform 0.2s, box-shadow 0.2s; cursor: default; }
.ret-stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 20px rgba(0,0,0,0.12); }
.ret-stat-card.stat-danger { border-color: rgba(231,76,60,0.3); }
.ret-stat-icon { margin-bottom: 8px; color: var(--text-muted); }
.ret-stat-value { font-size: 28px; font-weight: 700; color: var(--text-primary); line-height: 1.1; }
.ret-stat-label { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
.ret-stat-hint { font-size: 10px; color: var(--text-muted); margin-top: 4px; }
.visit-count-badge { display: inline-block; background: var(--brand-accent); color: white; font-weight: 700; font-size: 12px; padding: 2px 8px; border-radius: var(--radius-full); min-width: 28px; text-align: center; }
.returner-row:hover { background: var(--bg-surface); }
.retention-cell { text-align: center; font-weight: 600; font-size: 11px; min-width: 50px; }

/* ── Flows: Insights Grid ── */
.flow-insights-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px; margin-bottom: 20px;
}
.flow-insight-card { display: flex; flex-direction: column; gap: 6px; padding: 16px !important; position: relative; }
.flow-insight-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot-danger { background: var(--color-danger, #ef4444); }
.dot-warning { background: #f59e0b; }
.dot-info { background: #5B8DEF; }
.dot-success { background: var(--color-success, #22c55e); }
.dot-muted { background: var(--text-muted); }
.dot-neutral { background: var(--text-secondary); }
.flow-insight-title { font-size: var(--font-xs); text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); font-weight: 700; }
.flow-insight-value { font-size: var(--font-base); font-weight: 700; color: var(--text-primary); word-break: break-word; }
.flow-insight-desc { font-size: var(--font-xs); color: var(--text-secondary); line-height: 1.5; }

/* ── Flow Filters ── */
.flow-filters { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
.flow-filter-input { flex: 1; min-width: 200px; padding: 8px 14px; border-radius: var(--radius-md); border: 1px solid var(--border-color); background: var(--bg-surface); color: var(--text-primary); font-size: var(--font-sm); outline: none; }
.flow-filter-input:focus { border-color: var(--brand-accent); }
.flow-filter-select { padding: 8px 12px; border-radius: var(--radius-md); border: 1px solid var(--border-color); background: var(--bg-surface); color: var(--text-primary); font-size: var(--font-sm); cursor: pointer; }

/* ── Journey Intent ── */
.intent-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; display: inline-block; margin-right: 6px; }
.journey-intent-label { font-size: var(--font-xs); color: var(--text-secondary); margin-bottom: 6px; }
.intent-score-badge { display: inline-block; font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: var(--radius-full); margin-left: 6px; }
.score-high { background: rgba(52,199,89,0.15); color: var(--color-success); }
.score-med { background: rgba(0,122,255,0.12); color: var(--color-info); }
.score-low { background: rgba(255,159,10,0.12); color: var(--color-warning); }
.score-bounce { background: var(--bg-surface); color: var(--text-muted); }
.journey-recs { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 4px; padding-top: 6px; border-top: 1px dashed var(--border-color); }
.rec-label { font-size: 10px; color: var(--text-muted); font-weight: 500; }
.rec-item { font-size: 10px; padding: 2px 8px; border-radius: var(--radius-full); background: rgba(99,102,241,0.1); color: var(--brand-accent); cursor: help; font-family: 'SF Mono', monospace; }
.journey-predicted { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 3px; }
.predicted-label { font-size: 10px; color: var(--text-muted); font-style: italic; }
.predicted-page { font-size: 10px; padding: 2px 8px; border-radius: var(--radius-full); background: var(--bg-surface); color: var(--text-secondary); font-family: 'SF Mono', monospace; }
.journey-duration { font-size: var(--font-xs); color: var(--text-muted); font-weight: 600; font-variant-numeric: tabular-nums; }

/* ── Flows: Enhanced Items ── */
.flow-list { display: flex; flex-direction: column; gap: 6px; }
.flow-item-enhanced { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--border-color); }
.flow-item-enhanced:last-child { border-bottom: none; }
.flow-item-route { display: flex; align-items: center; gap: 6px; min-width: 200px; flex-shrink: 0; }
.flow-page { background: var(--bg-surface); padding: 4px 10px; border-radius: var(--radius-sm); font-family: 'SF Mono', monospace; font-size: var(--font-xs); }
.flow-arrow { color: var(--text-muted); font-size: 14px; }
.flow-count { margin-left: 8px; font-weight: 700; color: var(--text-primary); font-size: var(--font-sm); min-width: 30px; text-align: right; flex-shrink: 0; }
.flow-item-bar-wrap { flex: 1; height: 6px; background: var(--bg-surface); border-radius: var(--radius-full); overflow: hidden; }
.flow-item-bar { height: 100%; border-radius: var(--radius-full); transition: width 0.5s ease; }

/* ── Flows: Bar Rows ── */
.flow-bar-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; border-bottom: 1px solid var(--border-color); font-size: var(--font-sm); }
.flow-bar-row:last-child { border-bottom: none; }
.flow-bar-label { min-width: 100px; max-width: 160px; font-family: 'SF Mono', monospace; font-size: var(--font-xs); color: var(--text-secondary); }
.flow-bar-label-group { display: flex; flex-direction: column; gap: 2px; min-width: 100px; max-width: 180px; }
.flow-bar-label-group .flow-bar-label { min-width: auto; max-width: none; }
.flow-source-tag { font-size: 10px; color: var(--brand-accent); opacity: 0.8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.flow-bar-track { flex: 1; height: 8px; background: var(--bg-surface); border-radius: var(--radius-full); overflow: hidden; }
.flow-bar-fill { height: 100%; border-radius: var(--radius-full); transition: width 0.5s ease; }
.flow-bar-fill.entry { background: var(--color-success); }
.flow-bar-fill.exit { background: var(--color-danger); }
.flow-bar-count { font-weight: 700; color: var(--text-primary); min-width: 24px; text-align: right; }
.flow-stat-item { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border-color); font-size: var(--font-sm); }
.flow-stat-item:last-child { border-bottom: none; }

/* ── AI Insights ── */
.insights-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.insight-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 20px; transition: all 0.15s; }
.insight-card:hover { box-shadow: var(--shadow-sm); }
.insight-warning { border-left: 3px solid var(--color-warning); }
.insight-critical { border-left: 3px solid var(--color-danger); }
.insight-opportunity { border-left: 3px solid var(--color-success); }
.insight-info { border-left: 3px solid var(--color-info); }
.insight-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.insight-icon { font-size: 20px; }
.insight-badge { font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 2px 8px; border-radius: var(--radius-full); }
.ibadge-warning { background: rgba(243,156,18,0.12); color: var(--color-warning); }
.ibadge-critical { background: rgba(231,76,60,0.12); color: var(--color-danger); }
.ibadge-opportunity { background: rgba(39,174,96,0.12); color: var(--color-success); }
.ibadge-info { background: rgba(52,152,219,0.12); color: var(--color-info); }
.insight-metric { margin-left: auto; font-size: var(--font-md); font-weight: 700; color: var(--text-primary); }
.insight-title { font-size: var(--font-md); color: var(--text-primary); margin: 0 0 6px; }
.insight-desc { font-size: var(--font-sm); color: var(--text-secondary); line-height: 1.5; margin: 0 0 12px; }
.insight-action { display: flex; align-items: center; gap: 6px; font-size: var(--font-xs); color: var(--brand-accent); font-weight: 600; }

/* ── Actions ── */
.action-item { display: flex; align-items: center; gap: 14px; padding: 14px 0; border-bottom: 1px solid var(--border-color); }
.action-item:last-child { border-bottom: none; }
.action-priority { font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 3px 10px; border-radius: var(--radius-full); }
.ap-critical { background: rgba(231,76,60,0.12); color: var(--color-danger); }
.ap-warning { background: rgba(243,156,18,0.12); color: var(--color-warning); }
.ap-opportunity { background: rgba(39,174,96,0.12); color: var(--color-success); }
.ap-info { background: rgba(52,152,219,0.12); color: var(--color-info); }

/* ── Visitors ── */
.clickable-row { cursor: pointer; transition: background 0.1s; }
.clickable-row:hover { background: var(--bg-surface); }
.visitor-id { font-family: 'SF Mono', monospace; font-size: var(--font-sm); color: var(--text-primary); }

/* ── Timeline ── */
.timeline { display: flex; flex-direction: column; gap: 0; }
.timeline-item { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border-color); }
.timeline-item:last-child { border-bottom: none; }
.timeline-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.dot-pageview { background: var(--color-info); }
.dot-click { background: var(--color-warning); }
.dot-scroll { background: var(--text-muted); }
.dot-form_submit { background: var(--color-success); }
.dot-exit { background: var(--color-danger); }
.dot-custom { background: var(--brand-accent); }
.timeline-content { display: flex; align-items: center; gap: 10px; flex: 1; }
.badge-sm { font-size: 10px; padding: 1px 6px; }

/* ── Empty ── */
.empty-state-card { text-align: center; padding: 60px 40px; background: var(--bg-card); border: 2px dashed var(--border-color); border-radius: var(--radius-lg); margin-bottom: 24px; }
.empty-icon { margin-bottom: 20px; opacity: 0.7; }
.empty-title { font-size: var(--font-lg); color: var(--text-primary); margin: 0 0 10px; }
.empty-desc { font-size: var(--font-sm); color: var(--text-secondary); max-width: 480px; margin: 0 auto 20px; line-height: 1.6; }
.empty-snippet { background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px 20px; display: inline-block; margin-bottom: 16px; }
.empty-snippet code { font-size: var(--font-xs); color: var(--brand-accent); font-family: 'SF Mono', 'Fira Code', monospace; }
.empty-hint { font-size: var(--font-xs); color: var(--text-muted); }
.empty-inline { text-align: center; padding: 40px 20px; color: var(--text-muted); font-size: var(--font-sm); }

/* ── Modal ── */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal-card { background: var(--bg-card); padding: 28px; border-radius: var(--radius-lg); width: 100%; box-shadow: var(--shadow-lg); }

/* ── Browser List ── */
.browser-list { display: flex; flex-direction: column; gap: 12px; }
.browser-item { display: flex; align-items: center; gap: 12px; }
.browser-info { display: flex; align-items: center; gap: 8px; min-width: 100px; }
.browser-icon { color: var(--text-muted); flex-shrink: 0; }
.browser-name { font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); }
.browser-bar-wrap { flex: 1; height: 6px; background: var(--bg-surface); border-radius: var(--radius-full); overflow: hidden; }
.browser-bar { height: 100%; border-radius: var(--radius-full); transition: width var(--transition-slow); }
.browser-pct { font-size: var(--font-sm); font-weight: 700; color: var(--text-primary); min-width: 36px; text-align: right; }

/* ── Live Events ── */
.realtime-badge { display: flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: var(--radius-full); background: rgba(34, 197, 94, 0.1); color: var(--color-success); font-size: var(--font-xs); font-weight: 600; }
.live-badge { display: flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: var(--radius-full); background: rgba(239, 68, 68, 0.1); color: #ef4444; font-size: 10px; font-weight: 700; letter-spacing: 0.05em; }
.live-pulse { width: 6px; height: 6px; border-radius: 50%; background: #ef4444; animation: pulse 1.5s infinite; }
.live-feed { display: flex; flex-direction: column; gap: 0; max-height: 300px; overflow-y: auto; }
.live-feed-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--border-color); font-size: var(--font-sm); }
.live-feed-item:last-child { border-bottom: none; }
.live-feed-url { flex: 1; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: 'SF Mono', monospace; font-size: var(--font-xs); }

/* ── Visitor Journeys ── */
.journey-list { display: flex; flex-direction: column; gap: 0; }
.journey-card { padding: 14px 0; border-bottom: 1px solid var(--border-color); }
.journey-card:last-child { border-bottom: none; }
.journey-meta { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; gap: 8px; flex-wrap: wrap; }
.journey-visitor { display: flex; align-items: center; gap: 8px; }
.visitor-hash { font-family: 'SF Mono', monospace; font-size: var(--font-xs); color: var(--text-secondary); }
.journey-company { font-size: var(--font-xs); font-weight: 600; color: var(--brand-accent); }
.journey-tags { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.badge-outline { border: 1px solid var(--border-color); background: transparent; color: var(--text-muted); }
.journey-path { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.journey-step { padding: 3px 10px; background: var(--bg-surface); border-radius: var(--radius-sm); font-family: 'SF Mono', monospace; font-size: 11px; color: var(--text-primary); }
.step-entry { border-left: 3px solid var(--color-success); }
.step-exit { border-right: 3px solid var(--color-danger); }
.journey-arrow { color: var(--text-muted); font-size: 12px; }
.journey-pages-count { margin-left: auto; font-size: var(--font-xs); color: var(--text-muted); font-weight: 600; }
.journey-summary-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.journey-more-btn { display: inline-flex; align-items: center; padding: 2px 10px; border: 1px solid var(--brand-accent); border-radius: var(--radius-full); background: rgba(99,102,241,0.08); color: var(--brand-accent); font-size: 11px; font-weight: 600; cursor: pointer; transition: all 0.15s; white-space: nowrap; }
.journey-more-btn:hover { background: var(--brand-accent); color: white; }
.journey-collapse-btn { display: inline-flex; align-items: center; padding: 1px 8px; border: none; border-radius: var(--radius-full); background: var(--bg-surface); color: var(--text-muted); font-size: 10px; cursor: pointer; margin-left: 6px; transition: all 0.15s; }
.journey-collapse-btn:hover { color: var(--text-primary); }

/* ── Growth Actions ── */
.growth-action-item { display: flex; align-items: flex-start; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--border-color); }
.growth-action-item:last-child { border-bottom: none; }
.growth-action-priority { flex-shrink: 0; padding: 3px 10px; border-radius: var(--radius-full); font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
.gap-high { background: rgba(239,68,68,0.12); color: #ef4444; }
.gap-medium { background: rgba(245,158,11,0.12); color: #f59e0b; }
.gap-low { background: rgba(34,197,94,0.12); color: #22c55e; }
.growth-action-content { flex: 1; min-width: 0; }
.growth-action-title { font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px; }
.growth-action-reason { font-size: 11px; color: var(--text-muted); line-height: 1.4; }
.growth-action-impact { flex-shrink: 0; font-size: 12px; font-weight: 700; color: var(--brand-accent); white-space: nowrap; }

/* ── Insight Compact Items ── */
.insight-compact-item { display: flex; align-items: flex-start; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--border-color); }
.insight-compact-item:last-child { border-bottom: none; }
.insight-compact-badge { flex-shrink: 0; padding: 2px 8px; border-radius: var(--radius-full); font-size: 9px; font-weight: 700; text-transform: uppercase; }
.icb-anomaly, .icb-warning, .icb-spike { background: rgba(239,68,68,0.12); color: #ef4444; }
.icb-drop { background: rgba(245,158,11,0.12); color: #f59e0b; }
.icb-content, .icb-opportunity, .icb-success { background: rgba(34,197,94,0.12); color: #22c55e; }
.icb-engagement, .icb-trend, .icb-info { background: rgba(99,102,241,0.12); color: var(--brand-accent); }
.insight-compact-body { flex: 1; min-width: 0; }
.insight-compact-title { font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px; }
.insight-compact-desc { font-size: 11px; color: var(--text-muted); line-height: 1.4; }
.insight-compact-action { font-size: 11px; color: var(--brand-accent); font-weight: 600; margin-top: 4px; }
.insight-compact-metric { flex-shrink: 0; font-size: 14px; font-weight: 700; color: var(--text-primary); }

/* ── Keyword Cards ── */
.kw-trending-list { padding: 4px 0; }
.kw-trending-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--border-color); }
.kw-trending-item:last-child { border-bottom: none; }
.kw-trending-rank { flex-shrink: 0; width: 28px; height: 28px; border-radius: 50%; background: var(--bg-surface); display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: var(--text-muted); }
.kw-trending-item:nth-child(-n+3) .kw-trending-rank { background: rgba(245,158,11,0.15); color: #f59e0b; }
.kw-trending-name { flex: 1; font-size: 13px; font-weight: 500; color: var(--text-primary); }
.kw-trending-traffic { font-size: 11px; color: var(--text-muted); white-space: nowrap; }

.kw-scores-list { padding: 4px 0; }
.kw-score-item { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border-color); }
.kw-score-item:last-child { border-bottom: none; }
.kw-score-gauge { flex-shrink: 0; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: white; }
.kw-grade-a { background: #22c55e; }
.kw-grade-b { background: #3b82f6; }
.kw-grade-c { background: #f59e0b; }
.kw-grade-d, .kw-grade-f { background: #ef4444; }
.kw-score-info { flex: 1; min-width: 0; }
.kw-score-keyword { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.kw-score-rec { font-size: 11px; color: var(--text-muted); line-height: 1.3; }
.kw-score-grade { font-size: 14px; font-weight: 800; }

.kw-suggestions-grid { display: flex; flex-wrap: wrap; gap: 8px; padding: 8px 0; }
.kw-suggestion-chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: var(--radius-full); background: var(--bg-surface); border: 1px solid var(--border-color); transition: all 0.15s; cursor: default; }
.kw-suggestion-chip:hover { border-color: var(--brand-accent); background: rgba(99,102,241,0.06); }
.kw-suggestion-text { font-size: 12px; font-weight: 500; color: var(--text-primary); }
.kw-suggestion-rel { font-size: 10px; font-weight: 700; color: var(--brand-accent); }
.kw-suggestion-src { font-size: 9px; color: var(--text-muted); text-transform: uppercase; }

.kw-tracker-note { display: flex; align-items: flex-start; gap: 10px; padding: 16px; background: var(--bg-surface); border-radius: var(--radius-md); font-size: 12px; color: var(--text-muted); line-height: 1.5; }

/* ── Keyword Comparison Chart ── */
.kw-compare-input { display: flex; gap: 8px; margin-bottom: 16px; }
.kw-compare-input .flow-filter-input { flex: 1; }
.btn-sm { padding: 6px 14px; font-size: 12px; }
.kw-compare-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; }
.kw-compare-legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 500; color: var(--text-primary); }
.kw-legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.kw-compare-chart { display: flex; align-items: flex-end; gap: 2px; height: 120px; padding: 8px 0; overflow-x: auto; }
.kw-compare-bar-group { display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 24px; }
.kw-compare-bars { display: flex; align-items: flex-end; gap: 1px; height: 100px; }
.kw-compare-bar { width: 8px; min-height: 2px; border-radius: 2px 2px 0 0; transition: height 0.3s ease; }
.kw-compare-date { font-size: 8px; color: var(--text-muted); margin-top: 4px; white-space: nowrap; }

/* ── Related Keywords ── */
.kw-related-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 640px) { .kw-related-cols { grid-template-columns: 1fr; } }
.kw-related-heading { font-size: 13px; font-weight: 700; margin: 0 0 8px; color: var(--text-primary); }
.kw-related-item { display: flex; align-items: center; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border-color); }
.kw-related-item:last-child { border-bottom: none; }
.kw-related-name { font-size: 12px; color: var(--text-primary); }
.kw-related-value { font-size: 12px; font-weight: 700; color: var(--text-muted); }
.kw-related-value.rising { color: #22c55e; }

/* ── SEO Keyword Scanner ── */
.seo-scanner-results { display: flex; flex-direction: column; gap: 20px; }
.seo-section-title { font-size: 13px; font-weight: 700; color: var(--text-primary); margin: 0 0 10px; padding-bottom: 6px; border-bottom: 1px solid var(--border-color); }

.seo-score-row { display: flex; align-items: center; gap: 20px; }
.seo-score-gauge { width: 80px; height: 80px; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 4px solid; flex-shrink: 0; }
.sg-good { border-color: #22c55e; background: rgba(34,197,94,0.06); }
.sg-mid { border-color: #f59e0b; background: rgba(245,158,11,0.06); }
.sg-bad { border-color: #ef4444; background: rgba(239,68,68,0.06); }
.seo-score-num { font-size: 24px; font-weight: 800; color: var(--text-primary); line-height: 1; }
.seo-score-label { font-size: 10px; color: var(--text-muted); font-weight: 600; }
.seo-score-meta { flex: 1; }
.seo-score-verdict { font-size: 16px; font-weight: 700; margin-bottom: 4px; }
.sv-good { color: #22c55e; }
.sv-mid { color: #f59e0b; }
.sv-bad { color: #ef4444; }

.seo-breakdown { display: flex; flex-direction: column; gap: 6px; }
.seo-br-item { display: flex; align-items: center; gap: 10px; }
.seo-br-label { width: 160px; font-size: 12px; color: var(--text-primary); flex-shrink: 0; }
.seo-br-bar-wrap { flex: 1; height: 8px; background: var(--bg-surface); border-radius: 4px; overflow: hidden; }
.seo-br-bar { height: 100%; border-radius: 4px; transition: width 0.4s ease; }
.sb-good { background: #22c55e; }
.sb-mid { background: #f59e0b; }
.sb-bad { background: #ef4444; }
.seo-br-val { width: 28px; text-align: right; font-size: 12px; font-weight: 700; color: var(--text-primary); }

.seo-kw-table, .seo-syn-table { width: 100%; }
.seo-kw-hdr, .seo-syn-hdr { display: grid; gap: 8px; padding: 6px 0; border-bottom: 2px solid var(--border-color); font-size: 10px; font-weight: 700; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.5px; }
.seo-kw-hdr { grid-template-columns: 2fr 1fr 1fr 2fr; }
.seo-syn-hdr { grid-template-columns: 2fr 30px 2fr 1fr; }
.seo-kw-row, .seo-syn-row { display: grid; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border-color); align-items: center; font-size: 12px; }
.seo-kw-row { grid-template-columns: 2fr 1fr 1fr 2fr; }
.seo-syn-row { grid-template-columns: 2fr 30px 2fr 1fr; }
.seo-kw-row:last-child, .seo-syn-row:last-child { border-bottom: none; }
.seo-kw-word { font-weight: 600; color: var(--text-primary); }
.seo-kw-trend { display: flex; align-items: center; gap: 4px; font-weight: 600; }
.seo-trend-dot { width: 8px; height: 8px; border-radius: 50%; }
.st-up { background: #22c55e; }
.st-down { background: #ef4444; }
.st-flat { background: #f59e0b; }
.seo-density { font-weight: 600; }
.sd-optimal { color: #22c55e; }
.sd-low { color: #f59e0b; }
.sd-high { color: #ef4444; }
.seo-kw-locs { display: flex; flex-wrap: wrap; gap: 4px; }
.seo-loc-pill { padding: 1px 6px; border-radius: var(--radius-full); font-size: 9px; font-weight: 700; text-transform: uppercase; background: rgba(99,102,241,0.1); color: var(--brand-accent); }

.seo-syn-orig { color: var(--text-muted); font-weight: 500; }
.seo-syn-arrow { color: var(--text-muted); text-align: center; }
.seo-syn-alt { font-weight: 600; color: var(--brand-accent); }
.seo-syn-delta { font-weight: 700; color: #22c55e; }

/* ── Engagement ── */
.engagement-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.engagement-item { display: flex; align-items: center; gap: 12px; padding: 12px; background: var(--bg-surface); border-radius: var(--radius-md); }
.engagement-label { font-size: var(--font-xs); color: var(--text-secondary); font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.engagement-value { font-size: var(--font-xl); font-weight: 700; color: var(--text-primary); margin-top: 2px; }

/* ── Performance ── */
.perf-grid { display: flex; flex-direction: column; gap: 18px; }
.perf-item { display: flex; align-items: center; gap: 14px; }
.perf-label { font-size: var(--font-sm); font-weight: 600; color: var(--text-secondary); min-width: 120px; }
.perf-bar-wrap { flex: 1; height: 8px; background: var(--bg-surface); border-radius: var(--radius-full); overflow: hidden; }
.perf-bar { height: 100%; border-radius: var(--radius-full); transition: width var(--transition-slow); }
.perf-good { background: var(--color-success); }
.perf-ok { background: var(--color-warning); }
.perf-bad { background: var(--color-danger); }
.perf-value { font-size: var(--font-sm); font-weight: 700; color: var(--text-primary); min-width: 40px; text-align: right; }
/* ── Filter Bar ── */
.filter-bar { display: flex; gap: 12px; margin-bottom: 12px; align-items: center; flex-wrap: wrap; }
.filter-input-wrap { position: relative; flex: 1; min-width: 200px; }
.filter-search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text-muted); pointer-events: none; }
.filter-input { width: 100%; padding: 10px 14px 10px 36px; font-family: var(--font-family); font-size: var(--font-sm); color: var(--text-primary); background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); outline: none; transition: all var(--transition-fast); }
.filter-input:focus { border-color: var(--brand-accent); box-shadow: var(--shadow-glow); }
.filter-input::placeholder { color: var(--text-muted); }
.filter-selects { display: flex; gap: 8px; }
.filter-select { padding: 8px 12px; font-family: var(--font-family); font-size: var(--font-xs); font-weight: 600; color: var(--text-secondary); background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); cursor: pointer; outline: none; transition: all var(--transition-fast); appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' fill='%236b7280' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10z'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 10px center; padding-right: 26px; }
.filter-select:focus { border-color: var(--brand-accent); }

/* ── Filter Chips ── */
.filter-chips { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
.filter-chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; background: var(--brand-accent-glow); color: var(--brand-accent); border-radius: var(--radius-full); font-size: var(--font-xs); font-weight: 600; }
.chip-remove { background: none; border: none; color: var(--brand-accent); cursor: pointer; font-size: 14px; line-height: 1; padding: 0 2px; opacity: 0.7; transition: opacity 0.15s; }
.chip-remove:hover { opacity: 1; }
.chip-enter-active { transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }
.chip-leave-active { transition: all 0.2s ease; }
.chip-enter-from { opacity: 0; transform: scale(0.8) translateY(-4px); }
.chip-leave-to { opacity: 0; transform: scale(0.8); }

/* ── KPI Tooltip ── */
.kpi-info { position: relative; display: inline-flex; align-items: center; margin-left: 4px; cursor: help; vertical-align: middle; color: var(--text-muted); }
.kpi-tooltip { position: absolute; bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%); background: var(--text-primary); color: var(--text-inverse); padding: 10px 14px; border-radius: var(--radius-md); font-size: var(--font-xs); font-weight: 400; text-transform: none; letter-spacing: 0; line-height: 1.5; white-space: nowrap; max-width: 300px; white-space: normal; z-index: 50; box-shadow: var(--shadow-md); pointer-events: none; }

/* ── Responsive ── */
@media (max-width: 900px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } .analytics-row { grid-template-columns: 1fr; } .analytics-tabs { flex-wrap: wrap; } .engagement-grid { grid-template-columns: 1fr; } .filter-bar { flex-direction: column; } .filter-selects { flex-wrap: wrap; } }
@media (max-width: 600px) { .kpi-grid { grid-template-columns: 1fr; } .insights-grid { grid-template-columns: 1fr; } }
</style>
