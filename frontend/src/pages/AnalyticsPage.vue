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
      <div v-show="activeTab === 'retention'">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Cohort Retention</h3>
            <p class="card-subtitle">How many visitors return over time</p>
          </div>
          <div v-if="retentionData.rows && retentionData.rows.length" class="retention-matrix">
            <table class="data-table retention-table">
              <thead>
                <tr>
                  <th>Cohort</th>
                  <th>Size</th>
                  <th v-for="w in maxRetentionWeeks" :key="w">Wk {{ w - 1 }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in retentionData.rows" :key="row.cohort">
                  <td class="font-semibold">{{ row.cohort }}</td>
                  <td>{{ row.cohort_size }}</td>
                  <td v-for="(w, i) in row.weeks" :key="i" :style="{ background: retentionColor(w.pct) }" class="retention-cell">
                    {{ w.pct }}%
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="empty-inline">No retention data yet. Data appears after visitors return to your site.</div>
        </div>
      </div>

      <!-- ═══════════ TAB 4: Flows ═══════════ -->
      <div v-show="activeTab === 'flows'">

        <!-- Flow-specific Filters -->
        <div class="flow-filters">
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

        <!-- Actionable Insights -->
        <div v-if="flowInsights.length" class="flow-insights-grid">
          <div v-for="(insight, i) in flowInsights" :key="i" class="flow-insight-card card">
            <div class="flow-insight-dot" :class="insight.severity"></div>
            <div class="flow-insight-title">{{ insight.title }}</div>
            <div class="flow-insight-value">{{ insight.value }}</div>
            <div class="flow-insight-desc">{{ insight.desc }}</div>
          </div>
        </div>

        <div class="analytics-row">
          <!-- Common Flow Patterns -->
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">Common Flow Patterns</h3>
              <span class="text-xs text-muted">Page-to-page transitions by frequency</span>
            </div>
            <div v-if="flowData.links && flowData.links.length" class="flow-list">
              <div v-for="(link, i) in flowData.links.slice(0, 12)" :key="i" class="flow-item-enhanced">
                <div class="flow-item-route">
                  <span class="flow-page">{{ cleanPath(link.source) }}</span>
                  <span class="flow-arrow">&rarr;</span>
                  <span class="flow-page">{{ cleanPath(link.target) }}</span>
                </div>
                <div class="flow-item-bar-wrap">
                  <div class="flow-item-bar" :style="{ width: flowBarWidth(link.value) + '%', background: flowBarColor(i) }"></div>
                </div>
                <span class="flow-count">{{ link.value }}&times;</span>
              </div>
            </div>
            <div v-else class="empty-inline">No flow data yet</div>
          </div>

          <!-- Entry & Exit Pages -->
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">Entry & Exit Pages</h3>
              <span class="text-xs text-muted">Where sessions start and end</span>
            </div>
            <div v-if="entryExitData.entry_pages && entryExitData.entry_pages.length">
              <h4 class="text-sm font-semibold" style="margin-bottom:8px;color:var(--color-success)">Entry Pages</h4>
              <div v-for="p in entryExitData.entry_pages" :key="'e'+p.page" class="flow-bar-row">
                <div class="flow-bar-label-group">
                  <span class="flow-bar-label truncate">{{ cleanPath(p.page) }}</span>
                  <span v-if="p.source" class="flow-source-tag">via {{ p.source }}</span>
                </div>
                <div class="flow-bar-track">
                  <div class="flow-bar-fill entry" :style="{ width: entryPct(p.count) + '%' }"></div>
                </div>
                <span class="flow-bar-count">{{ p.count }}</span>
              </div>
              <h4 class="text-sm font-semibold" style="margin:20px 0 8px;color:var(--color-danger)">Exit Pages</h4>
              <div v-for="p in entryExitData.exit_pages || []" :key="'x'+p.page" class="flow-bar-row">
                <span class="flow-bar-label truncate">{{ cleanPath(p.page) }}</span>
                <div class="flow-bar-track">
                  <div class="flow-bar-fill exit" :style="{ width: exitPct(p.count) + '%' }"></div>
                </div>
                <span class="flow-bar-count">{{ p.count }}</span>
              </div>
            </div>
            <div v-else class="empty-inline">No entry/exit data yet</div>
          </div>
        </div>

        <!-- Per-Visitor Journeys -->
        <div class="card" style="margin-top:20px" v-if="filteredJourneys.length">
          <div class="card-header">
            <h3 class="card-title">Visitor Journeys</h3>
            <span class="text-xs text-muted">{{ filteredJourneys.length }} of {{ journeys.length }} sessions{{ activeFlowFilterCount ? ` (${activeFlowFilterCount} filter${activeFlowFilterCount > 1 ? 's' : ''})` : '' }}</span>
          </div>
          <div class="journey-list">
            <div v-for="(j, i) in filteredJourneys" :key="i" class="journey-card">
              <div class="journey-meta">
                <span class="journey-visitor">
                  <span class="intent-dot" :class="journeyIntent(j).cls"></span>
                  <span class="visitor-hash">{{ j.visitor_hash }}...</span>
                  <span v-if="j.company" class="journey-company">{{ j.company }}</span>
                </span>
                <div class="journey-tags">
                  <span class="badge badge-sm badge-outline" v-if="j.device">{{ j.device }}</span>
                  <span class="badge badge-sm badge-outline" v-if="j.country">{{ j.country }}</span>
                  <span class="badge badge-sm badge-outline" v-if="j.source && j.source !== 'direct'">{{ j.source }}</span>
                  <span class="journey-duration" v-if="j.duration_secs">{{ formatDuration(j.duration_secs) }}</span>
                </div>
              </div>
              <div class="journey-intent-label">{{ journeyIntent(j).label }}</div>
              <div class="journey-path">
                <template v-for="(page, pi) in j.pages" :key="pi">
                  <span class="journey-step" :class="{ 'step-entry': pi === 0, 'step-exit': pi === j.pages.length - 1 }">{{ page }}</span>
                  <span v-if="pi < j.pages.length - 1" class="journey-arrow">&rarr;</span>
                </template>
                <span class="journey-pages-count">{{ j.page_count }} pages</span>
              </div>
            </div>
          </div>
        </div>
        <div class="card" style="margin-top:20px" v-else-if="journeys.length && !filteredJourneys.length">
          <div class="empty-inline">No journeys match your filters</div>
        </div>
      </div>

      <!-- ═══════════ TAB 5: AI Insights ═══════════ -->
      <div v-show="activeTab === 'insights'">
        <div class="insights-grid">
          <div v-for="(insight, i) in insightsData.insights || []" :key="i" class="insight-card" :class="'insight-' + insight.type">
            <div class="insight-header">
              <svg class="insight-type-icon" width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><path d="M8 5v3M8 10v1"/></svg>
              <span class="insight-badge" :class="'ibadge-' + insight.type">{{ insight.type }}</span>
              <span v-if="insight.metric" class="insight-metric">{{ insight.metric }}</span>
            </div>
            <h4 class="insight-title">{{ insight.title }}</h4>
            <p class="insight-desc">{{ insight.description }}</p>
            <div class="insight-action" v-if="insight.action">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M1 7h12M8 2l5 5-5 5"/></svg>
              {{ insight.action }}
            </div>
          </div>
        </div>
        <div v-if="!insightsData.insights || !insightsData.insights.length" class="empty-state-card">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="var(--text-muted)" stroke-width="1.5" style="margin-bottom:16px"><circle cx="24" cy="24" r="16"/><path d="M18 28c2-4 4-8 6-8s4 4 6 8"/><circle cx="24" cy="18" r="3"/></svg>
          <h3 class="empty-title">AI Insights need more data</h3>
          <p class="empty-desc">Once you have enough traffic data, FetchBot AI will detect anomalies, spot trends, and suggest actionable improvements.</p>
        </div>

        <!-- Suggested Actions -->
        <div v-if="insightsData.actions && insightsData.actions.length" class="card" style="margin-top:20px">
          <div class="card-header"><h3 class="card-title">Suggested Actions</h3></div>
          <div v-for="(a, i) in insightsData.actions" :key="i" class="action-item">
            <span class="action-priority" :class="'ap-' + a.priority">{{ a.priority }}</span>
            <div>
              <div class="font-semibold text-sm">{{ a.action }}</div>
              <div class="text-xs text-muted">{{ a.reason }}</div>
            </div>
            <span v-if="a.impact" class="text-sm font-semibold">{{ a.impact }}</span>
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

function journeyIntent(j) {
  const pages = j.pages || []
  const hasProduct = pages.some(p => p.startsWith('/product'))
  const hasLogin = pages.some(p => p.includes('login') || p.includes('signup'))
  const hasPricing = pages.some(p => p.includes('pricing'))
  if (hasLogin) return { cls: 'dot-success', label: 'High intent - attempted login/signup' }
  if (hasProduct && hasPricing) return { cls: 'dot-info', label: 'Evaluating - viewed product and pricing' }
  if (hasProduct) return { cls: 'dot-warning', label: 'Interested - viewed product but skipped pricing' }
  if (pages.length <= 1) return { cls: 'dot-muted', label: 'Quick visit - single page view' }
  return { cls: 'dot-neutral', label: 'Browsing - exploring the site' }
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
