<template>
  <div class="llm-ranking-page fade-in">
    <!-- Top filter bar (dashboard-style) -->
    <div class="lr-topbar">
      <div class="lr-topbar-left">
        <h1 class="page-title" style="margin:0">LLM Ranking</h1>
        <span v-if="latestAudit" class="lr-pill">
          <span class="lr-pill-dot" :class="auditStatusBadge(latestAudit.status)"></span>
          {{ latestAudit.business_name || 'audit' }}
        </span>
        <span v-if="latestAudit?.location" class="lr-pill lr-pill-ghost">{{ latestAudit.location }}</span>
        <span v-if="(latestAudit?.providers_queried || []).length"
              class="lr-pill lr-pill-ghost">
          {{ (latestAudit.providers_queried || []).length }} model{{ (latestAudit.providers_queried || []).length === 1 ? '' : 's' }}
        </span>
      </div>
      <div class="lr-topbar-right">
        <button class="btn btn-primary btn-sm" @click="openRunAudit" :disabled="running">
          {{ running ? 'Running...' : 'Run New Audit' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">Loading LLM ranking data...</div>

    <template v-else>
      <!-- Empty state: onboarding wizard when no audits exist -->
      <div v-if="!audits.length" class="card lr-onboarding">
        <div class="lr-onb-eyebrow">FIRST AUDIT</div>
        <h2 class="lr-onb-title">Track how AI mentions your business</h2>
        <p class="lr-onb-sub">
          Tell us about your business and we'll generate buyer-style prompts that match how
          real people ask AI assistants for tools like yours. We'll send those prompts to
          Claude, GPT-4, Gemini, and Perplexity, and report where you show up — and where
          competitors get listed instead.
        </p>
        <button class="btn btn-primary btn-lg" @click="openRunAudit">
          Set up your first audit
        </button>
      </div>

      <!-- ═══ Brand Overview (Bear-style dashboard) ═══════════════════════ -->
      <div v-if="audits.length && isAuditComplete" class="brand-overview" style="margin-bottom:24px">

        <!-- Filter bar -->
        <div class="bo-filters">
          <button class="bo-filter" @click="toggleFilter('platform')" :class="{ open: openFilter === 'platform' }">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>
              <path d="M12 2a15 15 0 010 20 15 15 0 010-20"/>
            </svg>
            <span>{{ filters.platform === 'all' ? 'All Platforms' : providerLabel(filters.platform) }}</span>
            <svg class="bo-caret" width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 4l3 3 3-3"/></svg>
            <div v-if="openFilter === 'platform'" class="bo-filter-menu" @click.stop>
              <button class="bo-filter-item" :class="{ active: filters.platform === 'all' }" @click="setFilter('platform', 'all')">All Platforms</button>
              <button v-for="p in providerHealth.providers.filter(p => p.configured)" :key="p.key"
                      class="bo-filter-item" :class="{ active: filters.platform === p.key }"
                      @click="setFilter('platform', p.key)">{{ p.name }}</button>
            </div>
          </button>

          <button class="bo-filter" @click="toggleFilter('time')" :class="{ open: openFilter === 'time' }">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            <span>{{ timeRangeLabel }}</span>
            <svg class="bo-caret" width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 4l3 3 3-3"/></svg>
            <div v-if="openFilter === 'time'" class="bo-filter-menu" @click.stop>
              <button v-for="r in timeRanges" :key="r.value" class="bo-filter-item"
                      :class="{ active: filters.timeRange === r.value }"
                      @click="setFilter('timeRange', r.value)">{{ r.label }}</button>
            </div>
          </button>

          <button class="bo-filter" @click="toggleFilter('topic')" :class="{ open: openFilter === 'topic' }">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2zM22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/>
            </svg>
            <span>{{ filters.topic === 'all' ? 'All Topics' : formatIntent(filters.topic) }}</span>
            <svg class="bo-caret" width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 4l3 3 3-3"/></svg>
            <div v-if="openFilter === 'topic'" class="bo-filter-menu" @click.stop>
              <button class="bo-filter-item" :class="{ active: filters.topic === 'all' }" @click="setFilter('topic', 'all')">All Topics</button>
              <button v-for="t in availableTopics" :key="t" class="bo-filter-item"
                      :class="{ active: filters.topic === t }"
                      @click="setFilter('topic', t)">{{ formatIntent(t) }}</button>
            </div>
          </button>
        </div>

        <!-- 4-KPI strip -->
        <div class="kpi-strip">
          <div class="kpi-card">
            <div class="kpi-label">
              Brand Visibility
              <span class="kpi-info" title="How often you appear when AI assistants are asked about your category">i</span>
            </div>
            <div class="kpi-value">{{ kpiBrandVisibility.value }}<span class="kpi-unit">%</span></div>
            <div class="kpi-sub">Based on {{ kpiBrandVisibility.basis }} prompts simulated</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">
              Citation Share
              <span class="kpi-info" title="Of all brand mentions across AI responses, the share that are you">i</span>
            </div>
            <div class="kpi-value">{{ kpiCitationShare.value }}<span class="kpi-unit">%</span></div>
            <div class="kpi-sub">{{ kpiCitationShare.self }} of {{ kpiCitationShare.total }} citations</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">
              Brand Ranking
              <span class="kpi-info" title="Your position vs other brands by visibility in this audit">i</span>
            </div>
            <div class="kpi-value kpi-value-rank">#{{ kpiBrandRanking.rank }}</div>
            <div class="kpi-sub">{{ kpiBrandRanking.label }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">
              Closest Competitor
              <span class="kpi-info" title="The brand right above or below you in the rankings">i</span>
            </div>
            <div class="kpi-closest">
              <span class="kpi-closest-avatar" :style="{ background: brandColor(kpiClosestCompetitor.name) }">
                {{ (kpiClosestCompetitor.name || '—')[0] }}
              </span>
              <div class="kpi-closest-meta">
                <div class="kpi-closest-name">{{ kpiClosestCompetitor.name || '—' }}</div>
                <div class="kpi-sub">{{ kpiClosestCompetitor.mention_count || 0 }} mentions</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Row 2: Competitor Visibility chart + Competitor Rankings -->
        <div class="lr-grid-2 bo-row">
          <div class="card lr-grid-main bo-chart-card">
            <div class="card-header">
              <h3 class="card-title">Competitor Visibility</h3>
              <span class="text-xs text-muted">multi-line · hover for details</span>
            </div>
            <div class="bo-chart-wrap">
              <Line :data="competitorVisibilityData" :options="competitorVisibilityOptions" />
            </div>
          </div>

          <div class="card lr-grid-side bo-ranking-card">
            <div class="card-header">
              <h3 class="card-title">Competitor Rankings</h3>
            </div>
            <div class="bo-ranking-head">
              <span class="bo-rh-rank">#</span>
              <span class="bo-rh-name">Competitor</span>
              <span class="bo-rh-vis">Visibility</span>
            </div>
            <div class="bo-ranking-list">
              <div v-for="r in brandRankingRows" :key="r.name"
                   class="bo-ranking-row"
                   :class="{ 'is-you': r.is_you, 'is-highlighted': highlightedBrand === r.name }"
                   @mouseenter="highlightedBrand = r.name"
                   @mouseleave="highlightedBrand = null">
                <span class="bo-rh-rank">{{ r.rank }}</span>
                <span class="bo-rh-name">
                  <span class="bo-brand-avatar" :style="{ background: brandColor(r.name) }">{{ r.name[0] }}</span>
                  <span>{{ r.name }} <span v-if="r.is_you" class="bo-you-tag">(You)</span></span>
                </span>
                <span class="bo-rh-vis">{{ r.visibility }}%</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Row 3: Citation Share trend + Top Sources -->
        <div class="lr-grid-2 bo-row">
          <div class="card lr-grid-main bo-chart-card">
            <div class="card-header">
              <h3 class="card-title">Citation Share</h3>
              <span class="text-xs text-muted">your share of all brand citations over time</span>
            </div>
            <div class="bo-chart-wrap bo-chart-small">
              <Line :data="citationShareData" :options="citationShareOptions" />
            </div>
          </div>

          <div class="card lr-grid-side bo-sources-card">
            <div class="card-header">
              <h3 class="card-title">Top Sources</h3>
              <button class="btn-ghost btn-sm" v-if="topSources.length" @click="sortTopSources">
                Sort: {{ topSourcesSort === 'count' ? '↓ Citations' : '↓ Domain' }}
              </button>
            </div>
            <div class="bo-sources-head">
              <span class="bo-sh-rank">#</span>
              <span class="bo-sh-domain">Web Page</span>
              <span class="bo-sh-type">Type</span>
              <span class="bo-sh-count">Citations</span>
            </div>
            <div class="bo-sources-list">
              <div v-for="(s, i) in topSources" :key="s.domain" class="bo-source-row">
                <span class="bo-sh-rank">{{ i + 1 }}</span>
                <span class="bo-sh-domain">
                  <span class="bo-source-favicon" :style="{ background: brandColor(s.domain) }">
                    {{ s.domain[0].toUpperCase() }}
                  </span>
                  <span>
                    <span class="bo-source-name">{{ s.label }}</span>
                    <span class="bo-source-host">{{ s.domain }}</span>
                  </span>
                </span>
                <span class="bo-sh-type"><span class="bo-type-pill" :class="'bo-type-' + s.type">{{ s.type }}</span></span>
                <span class="bo-sh-count">{{ s.count }}</span>
              </div>
              <div v-if="!topSources.length" class="text-xs text-muted" style="padding:16px">
                No citations detected yet. Sources are extracted as audits run.
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- System Status: which LLMs are configured + (when running/recent) the audit log -->
      <div v-if="audits.length || providerHealth.providers.length" class="lr-grid-2 lr-status-grid" style="margin-bottom:24px">
        <!-- LLM provider health card -->
        <div class="card lr-status-card">
          <div class="card-header">
            <h3 class="card-title">
              LLM Systems
              <span class="text-xs text-muted">
                · {{ providerHealth.configured_count }}/{{ providerHealth.total }} configured
              </span>
            </h3>
          </div>
          <div class="provider-status-list">
            <div
              v-for="p in providerHealth.providers"
              :key="p.key"
              class="provider-status-row"
              :class="{ 'is-on': p.configured, 'is-off': !p.configured }"
            >
              <span class="provider-status-dot"></span>
              <span class="provider-status-name">{{ p.name }}</span>
              <span class="provider-status-model">{{ p.model }}</span>
              <span class="provider-status-state">
                {{ p.configured ? 'Enabled' : 'API key missing' }}
              </span>
            </div>
            <div v-if="!providerHealth.providers.length" class="text-xs text-muted" style="padding:8px 16px">
              Loading provider status...
            </div>
          </div>
          <p v-if="providerHealth.configured_count < providerHealth.total" class="text-xs text-muted" style="padding:0 16px 14px;line-height:1.5">
            Disabled providers won't be queried; configure their API keys in settings to include them.
          </p>
        </div>

        <!-- Component-level pipeline diagram -->
        <div class="card lr-pipeline-card">
          <div class="card-header">
            <h3 class="card-title">Pipeline</h3>
            <span class="text-xs text-muted">How a prompt flows through the system</span>
          </div>
          <div class="pipeline-diagram">
            <div class="pl-node pl-node-prompts" :class="{ active: pipelineState.prompts }">
              <div class="pl-node-label">Prompts</div>
              <div class="pl-node-value">{{ pipelinePromptCount }}</div>
              <div class="pl-node-sub">from {{ pipelinePackName }}</div>
            </div>
            <span class="pl-arrow"></span>
            <div class="pl-fanout">
              <div
                v-for="p in providerHealth.providers"
                :key="p.key"
                class="pl-node pl-node-llm"
                :class="{ active: pipelineLlmState(p.key), disabled: !p.configured }"
              >
                <span class="pl-node-dot" :class="pipelineLlmDotClass(p.key)"></span>
                <span class="pl-node-llm-name">{{ p.name.split(' ')[0] }}</span>
              </div>
            </div>
            <span class="pl-arrow"></span>
            <div class="pl-node pl-node-extract" :class="{ active: pipelineState.extract }">
              <div class="pl-node-label">Haiku Extract</div>
              <div class="pl-node-sub">JSON · brand + competitors</div>
            </div>
            <span class="pl-arrow"></span>
            <div class="pl-node pl-node-score" :class="{ active: pipelineState.score }">
              <div class="pl-node-label">Score</div>
              <div class="pl-node-value">{{ isAuditComplete ? latestAudit.overall_score : '—' }}</div>
              <div class="pl-node-sub">/100</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Audit Log timeline (running OR latest completed) -->
      <div v-if="auditLogEvents.length" class="card" style="margin-bottom:24px">
        <div class="card-header" style="cursor:pointer" @click="showAuditLog = !showAuditLog">
          <h3 class="card-title">
            Audit Log
            <span v-if="isAuditRunning" class="live-pulse"></span>
            <span class="text-xs text-muted" style="font-weight:500">
              · {{ auditLogEvents.length }} event{{ auditLogEvents.length === 1 ? '' : 's' }}
            </span>
          </h3>
          <span class="text-xs text-muted">{{ showAuditLog ? 'Hide' : 'Show' }}</span>
        </div>
        <div v-if="showAuditLog" class="audit-log-list">
          <div
            v-for="(ev, i) in auditLogEvents"
            :key="i"
            class="audit-log-row"
            :class="'log-' + ev.kind"
          >
            <span class="audit-log-time">{{ ev.time }}</span>
            <span class="audit-log-tag">{{ ev.tag }}</span>
            <span class="audit-log-msg">{{ ev.message }}</span>
            <span v-if="ev.detail" class="audit-log-detail">{{ ev.detail }}</span>
          </div>
        </div>
      </div>

      <!-- How Scoring Works -->
      <div v-if="audits.length && (!latestAudit || latestAudit.status !== 'completed')" class="card methodology-card" style="margin-bottom:24px">
        <div class="card-header">
          <h3 class="card-title">How LLM Ranking Works</h3>
        </div>
        <div class="methodology-content">
          <p class="text-sm text-muted" style="margin-bottom:16px;line-height:1.6">
            We ask leading AI assistants natural questions about your industry and analyze their responses
            to measure how visible your business is in AI-generated answers. The audit scores three factors:
          </p>
          <div class="method-grid">
            <div class="method-item">
              <div class="method-weight">40 pts</div>
              <div class="method-title">Mention Rate</div>
              <div class="method-desc">How often your business appears in AI responses across all prompts</div>
            </div>
            <div class="method-item">
              <div class="method-weight">35 pts</div>
              <div class="method-title">Rank Position</div>
              <div class="method-desc">Where you appear in ranked lists — #1 scores highest, lower positions score less</div>
            </div>
            <div class="method-item">
              <div class="method-weight">25 pts</div>
              <div class="method-title">Sentiment + Coverage</div>
              <div class="method-desc">Whether mentions are positive/neutral and how many providers include you</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Score Summary (latest completed audit) -->
      <div v-if="latestAudit" class="card" style="margin-bottom:24px">
        <div class="score-main">
          <div class="score-ring-wrap">
            <svg viewBox="0 0 100 100" class="score-ring-svg">
              <circle cx="50" cy="50" r="42" class="ring-track" />
              <circle cx="50" cy="50" r="42" class="ring-fill" :style="ringFillStyle(latestAudit.overall_score)" />
            </svg>
            <div class="score-center">
              <span class="score-num">{{ isAuditComplete ? latestAudit.overall_score : '—' }}</span>
              <span class="score-denom">/100</span>
            </div>
          </div>
          <div class="score-meta">
            <div class="card-title">AI Visibility Score</div>
            <p class="text-sm text-muted" style="margin-top:4px;margin-bottom:12px">
              {{ isAuditComplete
                ? 'How prominently LLMs mention your business'
                : 'Score will appear once the audit finishes running.' }}
            </p>
            <div class="flex gap-8" style="margin-bottom:8px">
              <span v-if="isAuditComplete" class="badge" :class="mentionBadge(latestAudit.mention_rate)">
                {{ Math.round(latestAudit.mention_rate || 0) }}% mention rate
              </span>
              <span v-else class="badge badge-neutral">Running across {{ (latestAudit.providers_queried || []).length }} provider{{ (latestAudit.providers_queried || []).length !== 1 ? 's' : '' }}</span>
              <span v-if="isAuditComplete" class="badge badge-neutral">{{ (latestAudit.providers_queried || []).length }} provider{{ (latestAudit.providers_queried || []).length !== 1 ? 's' : '' }}</span>
              <span v-if="latestAudit.location" class="badge badge-neutral">{{ latestAudit.location }}</span>
            </div>
            <!-- Progress bar for running audits -->
            <div v-if="latestAudit.status === 'running' || latestAudit.status === 'pending'" class="audit-progress-card">
              <div class="progress-header">
                <span class="pulse-dot"></span>
                <span class="progress-label">{{ latestAudit.status === 'pending' ? 'Queued — waiting to start...' : 'Audit in progress' }}</span>
                <span class="progress-pct">{{ auditProgressPct }}%</span>
              </div>
              <div class="progress-bar-track">
                <div class="progress-bar-fill" :style="{ width: auditProgressPct + '%' }"></div>
              </div>
              <div class="progress-details">
                <span>{{ latestAudit.queries_completed || 0 }} / {{ latestAudit.total_queries || '?' }} queries</span>
                <span v-if="auditETA">ETA: {{ auditETA }}</span>
                <span v-else-if="latestAudit.status === 'running'">Calculating ETA...</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Visual Score Breakdown -->
        <div v-if="latestAudit.status === 'completed'" class="score-factors" style="margin-top:20px">
          <h4 class="text-sm font-semibold" style="margin-bottom:12px;color:var(--text-primary)">Score Breakdown</h4>
          <div class="factor-row">
            <span class="factor-label">Mention Rate (40pts)</span>
            <div class="factor-bar-wrap">
              <div class="factor-bar" :style="{ width: mentionPts + '%', background: mentionPts > 25 ? 'var(--color-success)' : mentionPts > 10 ? 'var(--color-warning)' : 'var(--color-danger)' }"></div>
            </div>
            <span class="factor-value">{{ mentionPts }}/40</span>
          </div>
          <div class="factor-row">
            <span class="factor-label">Rank Position (35pts)</span>
            <div class="factor-bar-wrap">
              <div class="factor-bar" :style="{ width: rankPts / 35 * 100 + '%', background: rankPts > 20 ? 'var(--color-success)' : rankPts > 10 ? 'var(--color-warning)' : 'var(--color-danger)' }"></div>
            </div>
            <span class="factor-value">{{ rankPts }}/35</span>
          </div>
          <div class="factor-row">
            <span class="factor-label">Sentiment + Coverage (25pts)</span>
            <div class="factor-bar-wrap">
              <div class="factor-bar" :style="{ width: sentimentPts / 25 * 100 + '%', background: sentimentPts > 15 ? 'var(--color-success)' : sentimentPts > 8 ? 'var(--color-warning)' : 'var(--color-danger)' }"></div>
            </div>
            <span class="factor-value">{{ sentimentPts }}/25</span>
          </div>
          <div class="factor-total">
            <span>Total Score</span>
            <span class="font-semibold">{{ latestAudit.overall_score }}/100</span>
          </div>
        </div>

        <!-- Provider Breakdown -->
        <div v-if="latestBreakdown.length" class="provider-grid" style="margin-top:20px">
          <div
            v-for="p in latestBreakdown"
            :key="p.provider"
            class="provider-card"
            :class="{ 'provider-mentioned': p.mentioned > 0, 'provider-failed': p.succeeded === 0 }"
          >
            <div class="provider-icon">{{ providerInitial(p.provider) }}</div>
            <div class="provider-name">{{ p.provider_display || providerLabel(p.provider) }}</div>
            <template v-if="p.succeeded === 0">
              <span class="badge badge-danger">Not configured</span>
              <div class="text-xs text-muted" style="margin-top:4px">API key missing</div>
            </template>
            <template v-else>
              <span class="badge" :class="p.mentioned > 0 ? 'badge-success' : 'badge-neutral'">
                {{ p.mention_rate }}% mentioned
              </span>
              <div v-if="p.avg_rank" class="text-xs text-muted" style="margin-top:4px">Avg rank #{{ p.avg_rank }}</div>
              <div class="text-xs" style="margin-top:2px;color:var(--text-muted)">{{ p.succeeded }}/{{ p.total_prompts }} queries OK</div>
            </template>
          </div>
        </div>
      </div>

      <!-- Prompts list — visible whenever an audit has prompts, regardless of state -->
      <div v-if="latestAudit && (latestAudit.prompts || []).length" class="card" style="margin-bottom:24px">
        <div class="card-header" style="cursor:pointer" @click="showPrompts = !showPrompts">
          <h3 class="card-title">
            Questions we're asking
            <span class="text-xs text-muted" style="font-weight:500">
              ({{ latestAudit.prompts.length }} prompt{{ latestAudit.prompts.length === 1 ? '' : 's' }} × {{ (latestAudit.providers_queried || []).length }} LLM{{ (latestAudit.providers_queried || []).length === 1 ? '' : 's' }})
            </span>
          </h3>
          <span class="text-xs text-muted">{{ showPrompts ? 'Hide' : 'Show' }}</span>
        </div>
        <div v-if="showPrompts" class="prompt-list">
          <p class="text-sm text-muted" style="margin:0 0 12px;line-height:1.5">
            Each of these buyer-style questions will be sent to every selected LLM. We then scan the response for your business name and extract the rank, sentiment, and any competitors that got mentioned alongside you.
          </p>
          <div
            v-for="(p, i) in latestAudit.prompts"
            :key="i"
            class="prompt-row"
          >
            <span class="prompt-num">{{ i + 1 }}</span>
            <span class="prompt-text">{{ p }}</span>
            <span class="prompt-intent">{{ promptIntents[i] || 'custom' }}</span>
          </div>
        </div>
      </div>

      <!-- Prompts Table (rich view — matching reference design) -->
      <div v-if="isAuditComplete && intentGroups.length" class="card" style="margin-bottom:24px">
        <div class="card-header" style="border-bottom:1px solid var(--border-color, #E5E7EB)">
          <h3 class="card-title" style="font-size:1.1rem;font-weight:700">Prompts</h3>
          <div class="pt-header-right">
            <div class="pi-filter">
              <select v-model="providerFilter" class="pi-select">
                <option value="">All Providers</option>
                <option v-for="p in availableProviderFilters" :key="p" :value="p">{{ providerLabel(p) }}</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Table header -->
        <div class="pt-table">
          <div class="pt-thead">
            <span class="pt-th pt-th-topic">Topic</span>
            <span class="pt-th pt-th-count">Prompts</span>
            <span class="pt-th pt-th-vis">Avg Visibility</span>
            <span class="pt-th pt-th-perf">Top Performers</span>
            <span class="pt-th pt-th-status">Status</span>
          </div>

          <!-- Topic group rows -->
          <template v-for="group in intentGroups" :key="group.intent">
            <!-- Topic header row (clickable) -->
            <div class="pt-topic-row" @click="toggleIntent(group.intent)">
              <span class="pt-td pt-td-topic">
                <svg class="pi-chevron" :class="{ open: !collapsedIntents.has(group.intent) }"
                     width="10" height="10" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M5 4l5 4-5 4"/>
                </svg>
                <span class="pt-topic-name">{{ formatIntent(group.intent) }}</span>
              </span>
              <span class="pt-td pt-td-count">{{ group.prompts.length }}</span>
              <span class="pt-td pt-td-vis">
                <span :style="{ color: visibilityColor(group.avgVisibility) }">{{ group.avgVisibility }}%</span>
                <svg v-if="group.avgVisibility > 0" width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-left:3px">
                  <path d="M2 7L5 3L8 7" :stroke="group.avgVisibility >= 50 ? '#10b981' : '#f59e0b'"/>
                </svg>
              </span>
              <span class="pt-td pt-td-perf">
                <span
                  v-for="d in group.providerSummary"
                  :key="d.provider"
                  class="pt-perf-icon"
                  :class="{ 'is-hit': d.hitRate > 50, 'is-partial': d.hitRate > 0 && d.hitRate <= 50, 'is-miss': d.hitRate === 0 }"
                  :title="providerLabel(d.provider) + ': ' + d.hitRate + '% hit rate'"
                >{{ providerInitial(d.provider) }}</span>
              </span>
              <span class="pt-td pt-td-status">
                <span class="pt-see-link">See →</span>
              </span>
            </div>

            <!-- Expanded prompt rows -->
            <template v-if="!collapsedIntents.has(group.intent)">
              <div v-for="p in group.prompts" :key="p.text" class="pt-prompt-row">
                <span class="pt-td pt-td-topic pt-td-prompt-text">{{ p.text }}</span>
                <span class="pt-td pt-td-count"></span>
                <span class="pt-td pt-td-vis">
                  <strong :style="{ color: visibilityColor(p.visibility) }">{{ p.visibility }}%</strong>
                  <svg v-if="p.visibility > 0" width="10" height="10" viewBox="0 0 10 10" fill="none" stroke-width="1.5" style="margin-left:3px">
                    <path d="M2 7L5 3L8 7" :stroke="p.visibility >= 50 ? '#10b981' : '#f59e0b'"/>
                  </svg>
                </span>
                <span class="pt-td pt-td-perf">
                  <span
                    v-for="d in p.providerDots"
                    :key="d.provider"
                    class="pt-perf-icon"
                    :class="{ 'is-hit': d.mentioned, 'is-miss': !d.mentioned && d.succeeded, 'is-fail': !d.succeeded }"
                    :title="providerLabel(d.provider) + ': ' + providerDotTitle(d)"
                  >{{ providerInitial(d.provider) }}</span>
                </span>
                <span class="pt-td pt-td-status">
                  <span class="pt-status-pill" :class="p.visibility > 0 ? 'is-ran' : 'is-miss'">
                    {{ p.visibility > 0 ? 'Prompt Ran' : 'No Mention' }}
                  </span>
                </span>
              </div>
            </template>
          </template>
        </div>
      </div>

      <!-- Live query ticker (running audits only) -->
      <div v-if="isAuditRunning && liveResults.length" class="card" style="margin-bottom:24px">
        <div class="card-header">
          <h3 class="card-title">
            Live results
            <span class="live-pulse"></span>
          </h3>
          <span class="text-xs text-muted">{{ liveResults.length }} response{{ liveResults.length === 1 ? '' : 's' }} so far</span>
        </div>
        <div class="live-list">
          <div
            v-for="r in liveResults.slice(0, 10)"
            :key="r.id"
            class="live-row"
            :class="{ 'live-hit': r.is_mentioned, 'live-fail': !r.query_succeeded }"
          >
            <span class="live-provider">{{ providerLabel(r.provider) }}</span>
            <span class="live-prompt">{{ r.prompt }}</span>
            <span v-if="!r.query_succeeded" class="badge badge-danger">API error</span>
            <span v-else-if="r.is_mentioned" class="badge badge-success">
              Ranked #{{ r.mention_rank || '—' }}
            </span>
            <span v-else class="badge badge-neutral">Not mentioned</span>
          </div>
        </div>
      </div>

      <!-- Overview row: trends (left) + competitors leaderboard (right) -->
      <div v-if="history.length || (isAuditComplete && competitorLeaderboard.length)"
           class="lr-grid-2" style="margin-bottom:24px">
        <!-- AI Visibility Trends -->
        <div v-if="history.length >= 1" class="card lr-grid-main">
          <div class="card-header">
            <h3 class="card-title">AI Visibility Trends</h3>
            <span class="text-xs text-muted">{{ history.length }} completed audit{{ history.length !== 1 ? 's' : '' }}</span>
          </div>
          <div v-if="history.length === 1" class="empty-state" style="padding:24px">
            <p class="empty-state-desc">
              Run at least one more audit to see how your AI visibility changes over time.
            </p>
          </div>
          <div v-else class="trends-grid trends-grid-stacked">
            <div class="trend-block">
              <div class="trend-label">Overall Score & Mention Rate</div>
              <div class="trend-chart-wrap"><Line :data="overallTrendData" :options="overallTrendOptions" /></div>
            </div>
            <div class="trend-block">
              <div class="trend-label">Per-LLM Mention Rate</div>
              <div class="trend-chart-wrap"><Line :data="providerTrendData" :options="providerTrendOptions" /></div>
            </div>
          </div>
        </div>

        <!-- Competitors mentioned alongside you (right column) -->
        <div v-if="isAuditComplete && competitorLeaderboard.length" class="card lr-grid-side">
          <div class="card-header">
            <h3 class="card-title">Competitors</h3>
            <span class="text-xs text-muted">{{ competitorLeaderboard.length }} detected</span>
          </div>
          <div class="comp-leaderboard">
            <div v-for="(c, i) in competitorLeaderboard" :key="c.name" class="comp-row">
              <span class="comp-rank">{{ i + 1 }}</span>
              <span class="comp-name">{{ c.name }}</span>
              <span class="comp-bar-wrap">
                <span class="comp-bar" :style="{ width: (c.promptCount / uniquePromptCount * 100) + '%' }"></span>
              </span>
              <span class="comp-coverage">{{ c.promptCount }}/{{ uniquePromptCount }}</span>
              <span v-if="c.avgRank" class="comp-avg-rank">#{{ c.avgRank }}</span>
            </div>
          </div>
          <p class="text-xs text-muted" style="padding:0 16px 16px">
            Brands LLMs list alongside you. Your real competitive set in AI search.
          </p>
        </div>
      </div>

      <!-- Detailed Findings -->
      <div v-if="auditDetail && auditDetail.results && auditDetail.results.length" class="card" style="margin-bottom:24px">
        <div class="card-header" style="cursor:pointer" @click="showFindings = !showFindings">
          <h3 class="card-title">Detailed Findings ({{ successfulResults.length }} queries analyzed)</h3>
          <span class="text-xs text-muted">{{ showFindings ? 'Collapse' : 'Expand' }}</span>
        </div>
        <div v-if="showFindings" class="findings-list">
          <!-- Summary stats at top -->
          <div class="findings-summary">
            <div class="summary-stat">
              <span class="summary-num">{{ successfulResults.length }}</span>
              <span class="summary-label">Queries Sent</span>
            </div>
            <div class="summary-stat">
              <span class="summary-num">{{ mentionedResults.length }}</span>
              <span class="summary-label">Mentions Found</span>
            </div>
            <div class="summary-stat">
              <span class="summary-num">{{ mentionedResults.length ? avgRankDisplay : 'N/A' }}</span>
              <span class="summary-label">Avg Rank</span>
            </div>
            <div class="summary-stat">
              <span class="summary-num">{{ promptsUsed }}</span>
              <span class="summary-label">Unique Prompts</span>
            </div>
          </div>

          <!-- Per-query results -->
          <template v-for="(r, i) in auditDetail.results" :key="i">
            <div v-if="r.query_succeeded" class="finding-card" :class="{ 'finding-mentioned': r.is_mentioned }">
              <div class="finding-number">#{{ i + 1 }}</div>
              <div class="finding-body">
                <div class="finding-header">
                  <span class="finding-provider">{{ providerLabel(r.provider) }}</span>
                  <span v-if="r.is_mentioned" class="badge badge-success">Ranked #{{ r.mention_rank || '?' }}</span>
                  <span v-else class="badge badge-neutral">Not found in response</span>
                  <span v-if="r.sentiment && r.sentiment !== 'not_mentioned'" class="badge" :class="r.sentiment === 'positive' ? 'badge-success' : r.sentiment === 'negative' ? 'badge-danger' : 'badge-neutral'" style="margin-left:4px">
                    {{ r.sentiment }}
                  </span>
                  <span class="finding-confidence" v-if="r.confidence_score">{{ Math.round(r.confidence_score) }}% confidence</span>
                </div>
                <div class="finding-prompt">
                  <strong>Q:</strong> {{ r.prompt }}
                </div>
                <div v-if="r.mention_context" class="finding-context">
                  <strong>Match:</strong> "...{{ r.mention_context }}..."
                </div>
                <details v-if="r.response_text" class="finding-response">
                  <summary class="response-toggle">View full AI response ({{ r.response_text.length }} chars)</summary>
                  <pre class="response-pre">{{ r.response_text }}</pre>
                </details>
              </div>
            </div>
            <!-- Failed queries shown compactly -->
            <div v-else class="finding-card finding-failed">
              <div class="finding-number">#{{ i + 1 }}</div>
              <div class="finding-body">
                <div class="finding-header">
                  <span class="finding-provider">{{ providerLabel(r.provider) }}</span>
                  <span class="badge badge-danger">API Failed</span>
                </div>
                <div class="finding-error">{{ r.error_message }}</div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Recommendations -->
      <div v-if="recommendations.length" class="card" style="margin-bottom:24px">
        <div class="card-header">
          <h3 class="card-title">Recommendations</h3>
        </div>
        <div class="recs-list">
          <div v-for="(rec, i) in recommendations" :key="i" class="rec-row">
            <span class="rec-num">{{ i + 1 }}</span>
            <span class="text-sm" style="color:var(--text-secondary);line-height:1.5">{{ rec }}</span>
          </div>
        </div>
      </div>

      <!-- How Scoring Works (when audit is completed, shown below) -->
      <div v-if="latestAudit && latestAudit.status === 'completed'" class="card" style="margin-bottom:24px">
        <div class="card-header" style="cursor:pointer" @click="showMethodology = !showMethodology">
          <h3 class="card-title">How This Score Was Calculated</h3>
          <span class="text-xs text-muted">{{ showMethodology ? 'Hide' : 'Show' }}</span>
        </div>
        <div v-if="showMethodology" class="methodology-content">
          <div class="method-steps">
            <div class="method-step">
              <div class="step-num">1</div>
              <div>
                <div class="step-title">Generate Prompts</div>
                <div class="step-desc">{{ auditDetail?.prompts?.length || latestAudit.prompts?.length || '?' }} natural-language questions were generated based on your business name, industry{{ latestAudit.location ? ', and location (' + latestAudit.location + ')' : '' }}.</div>
              </div>
            </div>
            <div class="method-step">
              <div class="step-num">2</div>
              <div>
                <div class="step-title">Query AI Providers</div>
                <div class="step-desc">Each prompt was sent to {{ (latestAudit.providers_queried || []).join(', ') || 'selected providers' }}. We ask the AI to list top options in your industry to simulate real user queries.</div>
              </div>
            </div>
            <div class="method-step">
              <div class="step-num">3</div>
              <div>
                <div class="step-title">Analyze Responses</div>
                <div class="step-desc">Each response is scanned for your business name. If found, we extract the rank position (e.g., listed 3rd out of 10) and the sentiment of the mention (positive, neutral, or negative).</div>
              </div>
            </div>
            <div class="method-step">
              <div class="step-num">4</div>
              <div>
                <div class="step-title">Compute Score</div>
                <div class="step-desc">
                  <strong>Mention Rate</strong> (40pts): % of queries where you appear.
                  <strong>Rank Position</strong> (35pts): Higher rank = more points (rank #1 → 35pts, #5 → 20pts).
                  <strong>Sentiment + Coverage</strong> (25pts): Positive mentions and multi-provider presence boost this.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Audit History -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Audit History</h3>
        </div>

        <div v-if="audits.length === 0" class="empty-state">
          <div class="empty-state-title">No audits yet</div>
          <p class="empty-state-desc">Run your first audit to see how LLMs rank your business.</p>
        </div>

        <table v-else class="data-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Business</th>
              <th>Score</th>
              <th>Mention Rate</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="audit in audits"
              :key="audit.id"
              class="audit-row"
              :class="{ 'row-selected': selectedAuditId === audit.id }"
              @click="selectAudit(audit)"
            >
              <td class="text-sm">{{ formatDate(audit.created_at) }}</td>
              <td class="font-semibold">{{ audit.business_name }}</td>
              <td>
                <span class="score-pill" :class="scorePillClass(audit.overall_score)">
                  {{ audit.overall_score ?? '—' }}
                </span>
              </td>
              <td class="text-sm">{{ Math.round(audit.mention_rate || 0) }}%</td>
              <td><span class="badge" :class="auditStatusBadge(audit.status)">{{ audit.status }}</span></td>
              <td>
                <!-- Inline delete confirmation -->
                <div v-if="confirmDeleteId === audit.id" class="flex gap-8 items-center">
                  <span class="text-xs" style="color:var(--color-danger)">Delete?</span>
                  <button class="btn btn-danger btn-sm" @click.stop="confirmDelete(audit)">Yes</button>
                  <button class="btn btn-secondary btn-sm" @click.stop="confirmDeleteId = null">No</button>
                </div>
                <button
                  v-else
                  class="btn btn-ghost btn-sm delete-btn"
                  @click.stop="confirmDeleteId = audit.id"
                >Delete</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Run Audit Modal -->
    <BaseModal v-model="showRunForm" title="" :wide="true">
      <div class="wizard-layout">
        <!-- Step sidebar -->
        <div class="wizard-sidebar">
          <div
            v-for="(step, idx) in wizardSteps"
            :key="step.id"
            class="wizard-step-item"
            :class="{ active: wizardStep === idx, done: wizardStep > idx }"
          >
            <span class="wizard-step-dot">
              <svg v-if="wizardStep > idx" width="14" height="14" viewBox="0 0 16 16" fill="#10b981">
                <circle cx="8" cy="8" r="8"/>
                <path d="M5 8l2 2 4-4" stroke="#fff" stroke-width="1.5" fill="none"/>
              </svg>
            </span>
            <span class="wizard-step-label">{{ step.label }}</span>
          </div>
        </div>

        <!-- Step content -->
        <div class="wizard-content">

          <!-- Step 0: Website — domain scan -->
          <div v-if="wizardStep === 0" class="wizard-pane">
            <h2 class="wizard-pane-title">Enter your website</h2>
            <p class="wizard-pane-sub">We'll scan your site to auto-fill your business details.</p>

            <div class="form-group">
              <label class="form-label">Domain or URL</label>
              <div class="wizard-scan-row">
                <input
                  v-model="auditForm.scan_url"
                  class="form-input"
                  placeholder="e.g. acme.com or https://acme.com"
                  @keydown.enter.prevent="scanDomain"
                  :disabled="scanning"
                />
                <button
                  class="btn btn-primary btn-sm"
                  @click="scanDomain"
                  :disabled="scanning || !auditForm.scan_url"
                >
                  {{ scanning ? 'Scanning...' : 'Scan' }}
                </button>
              </div>
            </div>

            <!-- Scanning animation -->
            <div v-if="scanning" class="wizard-scan-progress">
              <div class="wizard-scan-spinner"></div>
              <div class="wizard-scan-status">
                <span class="wizard-scan-status-text">Analyzing {{ auditForm.scan_url }}...</span>
                <span class="text-xs text-muted">Extracting business info, competitors, and ranking topics via AI</span>
              </div>
            </div>

            <!-- Scan result preview -->
            <div v-if="scanResult && !scanning" class="wizard-scan-result" :class="{ 'is-error': !scanResult.success }">
              <div v-if="scanResult.success" class="wizard-scan-success">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="#10b981">
                  <circle cx="8" cy="8" r="8"/>
                  <path d="M5 8l2 2 4-4" stroke="#fff" stroke-width="1.5" fill="none"/>
                </svg>
                <div>
                  <div class="wizard-scan-name">{{ scanResult.business_name || scanResult.domain }}</div>
                  <div class="text-xs text-muted">{{ scanResult.description ? scanResult.description.slice(0, 100) + '...' : 'Description extracted' }}</div>
                </div>
              </div>
              <div v-else class="wizard-scan-error">
                <span class="text-sm" style="color:var(--color-danger, #EF4444)">{{ scanResult.error || 'Could not scan this domain.' }}</span>
                <p class="text-xs text-muted" style="margin-top:4px">You can fill in the details manually on the next step.</p>
              </div>
            </div>
          </div>

          <!-- Step 1: Description (auto-filled from scan) -->
          <div v-if="wizardStep === 1" class="wizard-pane">
            <h2 class="wizard-pane-title">Tell us about your business</h2>
            <p class="wizard-pane-sub">Verify and edit the details we extracted from your website.</p>

            <div class="form-group">
              <label class="form-label">Business Name</label>
              <input v-model="auditForm.business_name" class="form-input" placeholder="e.g. Acme Corp" />
            </div>
            <div class="form-row-2" style="margin-top:12px">
              <div class="form-group">
                <label class="form-label">Industry / Category</label>
                <input v-model="auditForm.industry" class="form-input" placeholder="e.g. SaaS analytics" />
              </div>
              <div class="form-group">
                <label class="form-label">Location <span class="text-muted">(optional)</span></label>
                <input v-model="auditForm.location" class="form-input" placeholder="e.g. New York, US" />
              </div>
            </div>
            <div class="form-group" style="margin-top:12px">
              <label class="form-label">
                Description
                <span class="text-muted text-xs">Who you serve and what makes you different</span>
              </label>
              <textarea
                v-model="auditForm.description"
                class="form-input wizard-textarea"
                rows="5"
                maxlength="500"
                placeholder="Describe your product, who it's for, and what makes it unique."
              ></textarea>
              <div class="wizard-textarea-meta">
                <span class="text-xs text-muted">{{ (auditForm.description || '').length }}/500 characters</span>
                <button class="wizard-regen-btn" @click="regenerateTopics" :disabled="generatingTopics">
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M2 8a6 6 0 0110.9-3.5M14 8A6 6 0 013.1 11.5"/>
                    <path d="M14 2v4h-4M2 14v-4h4"/>
                  </svg>
                  Regenerate Description
                </button>
              </div>
            </div>
          </div>

          <!-- Step 2: Topics — "What do you want to show up on ChatGPT for?" -->
          <div v-if="wizardStep === 2" class="wizard-pane">
            <h2 class="wizard-pane-title">What do you want to show up on ChatGPT for?</h2>
            <p class="wizard-pane-sub">Choose the topics where you want your business to be recommended by AI assistants like ChatGPT, Perplexity, and Claude.</p>

            <!-- Loading state -->
            <div v-if="generatingTopics" class="wizard-topics-loading">
              <div class="wizard-scan-spinner" style="width:28px;height:28px;border-width:3px"></div>
              <span class="text-sm text-muted">Generating relevant topics for {{ auditForm.business_name }}...</span>
            </div>

            <!-- Topics grid -->
            <template v-else>
              <div class="wizard-topics-actions">
                <button class="btn-ghost btn-sm" @click="auditForm.selectedTopics = [...wizardTopics]">Select All</button>
                <button class="btn-ghost btn-sm" @click="auditForm.selectedTopics = []">Deselect All</button>
                <button class="btn-ghost btn-sm" @click="regenerateTopics" style="margin-left:auto">
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px">
                    <path d="M1 4v5h5"/><path d="M3.51 10a6 6 0 1 0 .59-6.2L1 4"/>
                  </svg>
                  Regenerate
                </button>
              </div>

              <div class="wizard-topics-grid">
                <button
                  v-for="topic in wizardTopics"
                  :key="topic"
                  class="wizard-topic-chip"
                  :class="{ active: auditForm.selectedTopics.includes(topic) }"
                  @click="toggleWizardTopic(topic)"
                >
                  <svg v-if="auditForm.selectedTopics.includes(topic)" class="wizard-topic-check" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.5">
                    <path d="M3 8l3 3 7-7"/>
                  </svg>
                  {{ topic }}
                </button>
              </div>

              <div v-if="!wizardTopics.length" class="wizard-topics-empty">
                <p class="text-sm text-muted">No topics generated yet. Click <strong>Regenerate</strong> to create topics from your business description.</p>
              </div>

              <p class="text-xs text-muted" style="text-align:center;margin-top:16px">
                {{ auditForm.selectedTopics.length }} of {{ wizardTopics.length }} topics selected
              </p>
            </template>
          </div>

          <!-- Step 3: Competitors -->
          <div v-if="wizardStep === 3" class="wizard-pane">
            <h2 class="wizard-pane-title">Add Your Competitors</h2>
            <p class="wizard-pane-sub">Track up to 20 competitors to monitor your relative AI visibility</p>

            <div class="wc-header">
              <label class="form-label" style="margin:0;font-weight:700">Add New Competitor</label>
              <span class="wc-counter">{{ auditForm.competitors.length }}/20</span>
            </div>

            <div class="wc-input-row">
              <div class="wc-input-wrap">
                <svg class="wc-input-icon" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="2" y="3" width="12" height="10" rx="2"/>
                  <path d="M2 6h12"/>
                </svg>
                <input
                  v-model="competitorInput"
                  class="form-input wc-input"
                  placeholder="Competitor name"
                  @keydown.enter.prevent="addCompetitor"
                />
              </div>
              <div class="wc-input-wrap">
                <svg class="wc-input-icon" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="8" cy="8" r="6"/>
                  <path d="M2 8h12M8 2c-1.5 2-1.5 10 0 12M8 2c1.5 2 1.5 10 0 12"/>
                </svg>
                <input
                  v-model="competitorDomainInput"
                  class="form-input wc-input"
                  placeholder="www.example.com (optional)"
                  @keydown.enter.prevent="addCompetitor"
                />
              </div>
              <button
                class="btn btn-primary wc-add-btn"
                @click="addCompetitor"
                :disabled="!competitorInput.trim() || auditForm.competitors.length >= 20"
              >+</button>
            </div>

            <div v-if="auditForm.competitors.length" class="wc-grid">
              <div
                v-for="c in auditForm.competitors"
                :key="c.name"
                class="wc-card"
              >
                <img
                  :src="'https://www.google.com/s2/favicons?domain=' + (c.domain || c.name) + '&sz=32'"
                  class="wc-favicon"
                  :alt="c.name"
                  @error="$event.target.src = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2232%22 height=%2232%22 viewBox=%220 0 32 32%22%3E%3Crect width=%2232%22 height=%2232%22 rx=%226%22 fill=%22%23E5E7EB%22/%3E%3Ctext x=%2216%22 y=%2220%22 text-anchor=%22middle%22 font-size=%2214%22 fill=%22%236B7280%22%3E' + c.name.charAt(0).toUpperCase() + '%3C/text%3E%3C/svg%3E'"
                />
                <div class="wc-card-info">
                  <span class="wc-card-name">{{ c.name }}</span>
                  <span class="wc-card-domain">{{ c.domain || '—' }}</span>
                </div>
                <button class="wc-card-x" @click="removeCompetitor(c.name)">&times;</button>
              </div>
            </div>
            <p v-else class="text-xs text-muted" style="margin-top:16px;text-align:center">
              No competitors added yet. You can skip this step.
            </p>
          </div>

          <!-- Step 4: Providers -->
          <div v-if="wizardStep === 4" class="wizard-pane">
            <h2 class="wizard-pane-title">Choose AI models to audit</h2>
            <p class="wizard-pane-sub">Select which LLMs to include in your audit. Unconfigured models will be skipped.</p>

            <div class="wizard-provider-grid">
              <label
                v-for="p in availableProviders"
                :key="p.value"
                class="wizard-provider-card"
                :class="{ active: auditForm.providers.includes(p.value), disabled: !p.configured }"
              >
                <input type="checkbox" :value="p.value" v-model="auditForm.providers" />
                <span class="wizard-provider-name">{{ p.label }}</span>
                <span class="wizard-provider-model">{{ p.model }}</span>
                <span class="wizard-provider-status" :class="p.configured ? 'is-on' : 'is-off'">
                  {{ p.configured ? 'Ready' : 'API key missing' }}
                </span>
              </label>
            </div>
          </div>

          <!-- Step 5: Review -->
          <div v-if="wizardStep === 5" class="wizard-pane">
            <h2 class="wizard-pane-title">Review &amp; run your audit</h2>
            <p class="wizard-pane-sub">Everything looks good? Hit start to kick off the audit.</p>

            <div class="wizard-review-grid">
              <div class="wizard-review-item">
                <span class="wizard-review-label">Website</span>
                <span class="wizard-review-value">{{ auditForm.scan_url || '—' }}</span>
              </div>
              <div class="wizard-review-item">
                <span class="wizard-review-label">Business</span>
                <span class="wizard-review-value">{{ auditForm.business_name || '—' }}</span>
              </div>
              <div class="wizard-review-item">
                <span class="wizard-review-label">Industry</span>
                <span class="wizard-review-value">{{ auditForm.industry || '—' }}</span>
              </div>
              <div class="wizard-review-item">
                <span class="wizard-review-label">Topics</span>
                <span class="wizard-review-value">{{ auditForm.selectedTopics.length }} selected</span>
              </div>
              <div class="wizard-review-item">
                <span class="wizard-review-label">Competitors</span>
                <span class="wizard-review-value">{{ auditForm.competitors.length ? auditForm.competitors.map(c => c.name).join(', ') : 'None' }}</span>
              </div>
              <div class="wizard-review-item">
                <span class="wizard-review-label">Models</span>
                <span class="wizard-review-value">{{ auditForm.providers.length }} LLMs</span>
              </div>
            </div>

            <details class="run-modal-advanced" style="margin-top:16px">
              <summary class="text-xs text-muted" style="cursor:pointer;padding:4px 0">Advanced — custom prompts</summary>
              <div class="form-group" style="margin-top:8px">
                <label class="form-label">Custom prompts (one per line, replaces auto-generated)</label>
                <textarea v-model="customPromptsText" class="form-input" rows="3" placeholder="Best SaaS tools for startups"></textarea>
                <p class="text-xs text-muted" style="margin-top:4px">Leave blank to use auto-generated prompts.</p>
              </div>
            </details>
          </div>

          <!-- Error -->
          <p v-if="auditError" class="form-error" style="margin-top:8px">{{ auditError }}</p>

          <!-- Nav buttons -->
          <div class="wizard-nav">
            <button v-if="wizardStep > 0" class="btn btn-secondary" @click="wizardStep--">Back</button>
            <span v-else></span>
            <button
              v-if="wizardStep < wizardSteps.length - 1"
              class="btn btn-primary"
              @click="wizardNext"
            >Continue</button>
            <button
              v-else
              class="btn btn-primary"
              @click="submitAudit"
              :disabled="running"
            >{{ running ? 'Queuing...' : 'Start Audit' }}</button>
          </div>
        </div>
      </div>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, shallowRef, computed, onMounted, onBeforeUnmount, markRaw } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from '@/composables/useToast'
import llmRankingApi from '@/api/llm_ranking'
import BaseModal from '@/components/ui/BaseModal.vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement,
  Filler, Tooltip, Legend,
} from 'chart.js'

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  Filler, Tooltip, Legend,
)

const route = useRoute()
const websiteId = route.params.websiteId
const toast = useToast()

const audits = shallowRef([])
const history = shallowRef([])
const providerHealth = shallowRef({ providers: [], configured_count: 0, total: 0 })
const loading = ref(true)
const running = ref(false)
const showRunForm = ref(false)
const auditError = ref('')
const selectedAuditId = ref(null)
const latestBreakdown = shallowRef([])
const recommendations = shallowRef([])
const auditDetail = shallowRef(null)
const showFindings = ref(true)
const showMethodology = ref(false)
const showPrompts = ref(true)
const showAuditLog = ref(true)
const confirmDeleteId = ref(null)

// Intent tags for each prompt — derived from the prompt text via the backend
// library keywords. Purely cosmetic; falls back to "custom" on miss.
const INTENT_PATTERNS = [
  { intent: 'recommendation', keywords: ['best', 'recommend', 'most companies', 'leading', 'top options'] },
  { intent: 'comparison',     keywords: ['compare', 'side-by-side', 'pros and cons'] },
  { intent: 'alternatives',   keywords: ['alternative', 'up-and-coming', 'newer', 'indie'] },
  { intent: 'use_case',       keywords: ['i need to', 'helps with', 'platform for'] },
  { intent: 'category',       keywords: ['new to', 'categories of'] },
  { intent: 'local',          keywords: ['in dallas', 'in new york', 'businesses in', ' in '] },
  { intent: 'persona',        keywords: ['startup', 'mid-market', 'enterprise teams'] },
  { intent: 'review',         keywords: ['users say', 'reputation', 'reviewers'] },
]
function classifyIntent(text) {
  const lower = text.toLowerCase()
  for (const { intent, keywords } of INTENT_PATTERNS) {
    if (keywords.some(k => lower.includes(k))) return intent
  }
  return 'custom'
}
const promptIntents = computed(() =>
  (latestAudit.value?.prompts || []).map(classifyIntent)
)
let pollTimer = null

const PROVIDER_META = {
  claude:     { label: 'Claude',       color: '#A78BFA' },
  gpt4:       { label: 'GPT-4',        color: '#34D399' },
  gemini:     { label: 'Gemini',       color: '#5B8DEF' },
  perplexity: { label: 'Perplexity',   color: '#F59E0B' },
  meta_llama: { label: 'Meta Llama',   color: '#3B82F6' },
  mistral:    { label: 'Mistral AI',   color: '#F97316' },
  cohere:     { label: 'Cohere',       color: '#14B8A6' },
  deepseek:   { label: 'DeepSeek',     color: '#6366F1' },
  grok:       { label: 'Grok',         color: '#EF4444' },
  amazon_nova:{ label: 'Amazon Nova',  color: '#EC4899' },
}

const customPromptsText = ref('')
const auditForm = ref({
  business_name: '',
  industry: '',
  location: '',
  description: '',
  themes: ['recommendation', 'comparison', 'use_case', 'persona'],
  providers: ['claude', 'gpt4', 'gemini', 'perplexity'],
  selectedTopics: [],
  competitors: [],
  scan_url: '',
})

// ── Wizard state ──
const wizardStep = ref(0)
const wizardTopics = ref([])
const generatingTopics = ref(false)
const competitorInput = ref('')
const competitorDomainInput = ref('')
const scanning = ref(false)
const scanResult = ref(null)

const wizardSteps = Object.freeze([
  { id: 'website', label: 'Website' },
  { id: 'description', label: 'Description' },
  { id: 'topics', label: 'Topics' },
  { id: 'competitors', label: 'Competitors' },
  { id: 'providers', label: 'Models' },
  { id: 'review', label: 'Review' },
])

async function scanDomain() {
  const url = (auditForm.value.scan_url || '').trim()
  if (!url) return
  scanning.value = true
  scanResult.value = null
  auditError.value = ''
  try {
    const { data } = await llmRankingApi.scanDomain(url)
    scanResult.value = data
    if (data.success) {
      // Auto-fill the form from scan results
      auditForm.value.business_name = data.business_name || auditForm.value.business_name
      auditForm.value.description = data.description || auditForm.value.description
      auditForm.value.industry = data.industry || auditForm.value.industry

      // Auto-populate real topics from LLM
      if (data.topics && data.topics.length) {
        wizardTopics.value = data.topics
        auditForm.value.selectedTopics = [...data.topics] // pre-select all
      } else {
        // Fallback: generate topics locally
        wizardTopics.value = generateLocalTopics(
          auditForm.value.business_name,
          auditForm.value.description,
          auditForm.value.industry
        )
        auditForm.value.selectedTopics = [...wizardTopics.value]
      }

      // Auto-populate real competitors from LLM
      if (data.competitors && data.competitors.length) {
        auditForm.value.competitors = data.competitors.map(c => ({
          name: c.name || '',
          domain: c.domain || '',
        }))
      }

      // Auto-advance to Description step
      wizardStep.value = 1
    }
  } catch (err) {
    scanResult.value = { success: false, error: err.displayMessage || 'Scan failed. Please try again.' }
  } finally {
    scanning.value = false
  }
}

async function regenerateTopics() {
  generatingTopics.value = true
  let gotTopics = false
  try {
    const { data } = await llmRankingApi.suggestContext({
      business_name: auditForm.value.business_name,
      description: auditForm.value.description,
      industry: auditForm.value.industry,
      domain: auditForm.value.scan_url || '',
    })
    if (data.topics && data.topics.length) {
      wizardTopics.value = data.topics
      auditForm.value.selectedTopics = [...data.topics] // pre-select all
      gotTopics = true
    }
    if (data.competitors && data.competitors.length) {
      auditForm.value.competitors = data.competitors.map(c => ({
        name: c.name || '',
        domain: c.domain || '',
      }))
    }
  } catch (err) {
    console.warn('LLM topic generation failed, using smart fallback:', err)
  }

  // Fallback: generate topics locally from business description + industry
  if (!gotTopics) {
    wizardTopics.value = generateLocalTopics(
      auditForm.value.business_name,
      auditForm.value.description,
      auditForm.value.industry
    )
    auditForm.value.selectedTopics = [...wizardTopics.value]
  }

  generatingTopics.value = false
}

/**
 * Smart client-side fallback: generates buyer-intent search queries
 * derived directly from the business description. Extracts real
 * product terms, use cases, and features from the text.
 */
function generateLocalTopics(name, desc, industry) {
  const ind = industry || 'software'
  const topics = []
  const seen = new Set()

  function add(t) {
    const key = t.toLowerCase().trim()
    if (key && !seen.has(key) && key.length > 12) {
      seen.add(key)
      topics.push(t)
    }
  }

  if (desc && desc.length > 10) {
    const descLower = desc.toLowerCase()

    // 1. Extract "X for Y" patterns from the description
    const forPatterns = descLower.matchAll(/(\b[\w\s]{6,40})\s+for\s+([\w\s]{4,30})/gi)
    for (const m of forPatterns) {
      const what = m[1].trim()
      const who = m[2].trim().replace(/[.,!]+$/, '')
      add(`best ${what} for ${who}`)
      add(`top ${what} tools for ${who}`)
    }

    // 2. Extract meaningful noun phrases (3+ char words not in stop list)
    const stopWords = new Set([
      'the','and','for','with','that','this','from','your','their','have',
      'been','will','are','our','you','can','all','more','most','also',
      'about','just','into','very','every','not','but','than','then',
      'only','such','like','over','each','both','its','was','were','has',
      'does','get','use','any','help','make','need','want','take'
    ])
    const words = desc.split(/[\s,.;:!?()\[\]{}]+/).filter(w => w.length > 3)
    const meaningfulWords = words.filter(w => !stopWords.has(w.toLowerCase()))

    // Build 2-3 word phrases from consecutive meaningful words
    const phrases = []
    for (let i = 0; i < meaningfulWords.length - 1; i++) {
      const w1 = meaningfulWords[i]
      const w2 = meaningfulWords[i + 1]
      if (w1.length > 3 && w2.length > 3) {
        phrases.push(`${w1} ${w2}`.toLowerCase())
      }
    }

    // Use the best phrases to create topics
    const uniquePhrases = [...new Set(phrases)].slice(0, 5)
    for (const phrase of uniquePhrases) {
      add(`best ${phrase} tools`)
      add(`top ${phrase} solutions compared`)
    }

    // 3. Look for key product/feature terms in the description
    const productTerms = [
      'analytics', 'tracking', 'automation', 'monitoring', 'reporting',
      'management', 'platform', 'dashboard', 'integration', 'optimization',
      'detection', 'scoring', 'generation', 'intelligence', 'engagement',
      'conversion', 'retention', 'acquisition', 'verification', 'scheduling',
      'collaboration', 'communication', 'marketplace', 'payment', 'billing'
    ]
    const foundTerms = productTerms.filter(t => descLower.includes(t))
    for (const term of foundTerms.slice(0, 3)) {
      add(`best ${term} software for businesses`)
      add(`top ${term} tools compared`)
    }

    // 4. Create a "what is X" and comparison query from the full description
    const firstSentence = desc.split(/[.!?]/)[0]?.trim()
    if (firstSentence && firstSentence.length > 15 && firstSentence.length < 80) {
      add(`tools for ${firstSentence.toLowerCase()}`)
    }
  }

  // Industry-level queries (only if we don't have enough from description)
  if (topics.length < 6) {
    add(`best ${ind} tools for small businesses`)
    add(`top ${ind} platforms compared`)
    add(`most recommended ${ind} solutions`)
    add(`${ind} tools for startups and growing companies`)
  }

  // Name-specific
  if (name && name.length > 2) {
    add(`${name} alternatives and competitors`)
    add(`is ${name} the best ${ind} tool`)
  }

  return topics.slice(0, 12)
}

function toggleWizardTopic(topic) {
  const idx = auditForm.value.selectedTopics.indexOf(topic)
  if (idx >= 0) {
    auditForm.value.selectedTopics.splice(idx, 1)
  } else {
    auditForm.value.selectedTopics.push(topic)
  }
}

function addCompetitor() {
  const name = competitorInput.value.trim()
  if (!name || auditForm.value.competitors.length >= 20) return
  const domain = competitorDomainInput.value.trim()
  // Support comma-separated names
  const names = name.split(',').map(s => s.trim()).filter(Boolean)
  for (const n of names) {
    if (!auditForm.value.competitors.some(c => c.name === n)) {
      auditForm.value.competitors.push({ name: n, domain: domain || '' })
    }
  }
  competitorInput.value = ''
  competitorDomainInput.value = ''
}

function removeCompetitor(name) {
  auditForm.value.competitors = auditForm.value.competitors.filter(c => c.name !== name)
}

async function wizardNext() {
  auditError.value = ''
  // Step 0: Website — just need a URL or allow skip
  if (wizardStep.value === 0) {
    if (!auditForm.value.scan_url) {
      auditError.value = 'Enter a domain to scan, or type any URL to continue.'
      return
    }
    // If not yet scanned, scan now
    if (!scanResult.value) {
      scanDomain()
      return
    }
  }
  // Step 1: Description
  if (wizardStep.value === 1) {
    if (!auditForm.value.business_name) { auditError.value = 'Business name is required.'; return }
    if (!auditForm.value.industry) { auditError.value = 'Industry is required.'; return }
    // If no topics were loaded from scan, fetch them now and wait
    if (!wizardTopics.value.length) {
      await regenerateTopics()
    }
  }
  // Step 2: Topics
  if (wizardStep.value === 2) {
    if (!auditForm.value.selectedTopics.length) {
      auditError.value = 'Select at least one topic.'
      return
    }
  }
  wizardStep.value++
}

const availableProviders = computed(() =>
  providerHealth.value.providers.map(p => ({
    value: p.key,
    label: p.name,
    model: p.model,
    configured: p.configured,
  }))
)

// Theme chips shown in the Run Audit modal — drive prompt generation.
const promptThemes = Object.freeze([
  { id: 'recommendation', label: 'Recommendation',
    example: '"What are the best ___ tools right now?"' },
  { id: 'comparison',     label: 'Comparison',
    example: '"Compare the top 5 ___ platforms"' },
  { id: 'alternatives',   label: 'Alternatives',
    example: '"Good alternatives to the market leader in ___?"' },
  { id: 'use_case',       label: 'Use cases',
    example: '"I need to do X. What ___ tool should I use?"' },
  { id: 'persona',        label: 'Persona / fit',
    example: '"Best ___ for a 20-person engineering team"' },
  { id: 'review',         label: 'Reviews & reputation',
    example: '"What do users say about the top ___?"' },
  { id: 'local',          label: 'Local',
    example: '"Best ___ in {your location}"' },
  { id: 'category',       label: 'Category overview',
    example: '"What main ___ tools should I know about?"' },
])

const latestAudit = computed(() => {
  // Prefer the selected audit, fallback to first completed, then first overall
  if (selectedAuditId.value) {
    const selected = audits.value.find(a => a.id === selectedAuditId.value)
    if (selected) return selected
  }
  return audits.value.find(a => a.status === 'completed') || audits.value[0] || null
})

const isAuditComplete = computed(() => latestAudit.value?.status === 'completed')
const isAuditRunning = computed(() => {
  const s = latestAudit.value?.status
  return s === 'running' || s === 'pending'
})

// Live per-query results: sorted newest-first for the running ticker
const liveResults = computed(() => {
  const list = auditDetail.value?.results || []
  return [...list].reverse()
})

// ── Prompt Intelligence aggregation ─────────────────────────────────────────
const providerFilter = ref('')
const collapsedIntents = ref(new Set())

function toggleIntent(intent) {
  const s = new Set(collapsedIntents.value)
  if (s.has(intent)) s.delete(intent)
  else s.add(intent)
  collapsedIntents.value = s
}

const filteredResults = computed(() => {
  const results = auditDetail.value?.results || []
  if (!providerFilter.value) return results
  return results.filter(r => r.provider === providerFilter.value)
})

const availableProviderFilters = computed(() => {
  const set = new Set((auditDetail.value?.results || []).map(r => r.provider))
  return [...set]
})

const uniquePromptCount = computed(() => {
  return new Set((auditDetail.value?.results || []).map(r => r.prompt)).size
})

// Map prompt text -> intent, derived once from the audit's prompts list
const promptIntentByText = computed(() => {
  const map = {}
  const prompts = latestAudit.value?.prompts || []
  prompts.forEach((p, i) => { map[p] = promptIntents.value[i] || 'custom' })
  return map
})

// Build per-prompt aggregate rows from the filtered result set
const promptRows = computed(() => {
  const byPrompt = new Map()
  for (const r of filteredResults.value) {
    if (!byPrompt.has(r.prompt)) byPrompt.set(r.prompt, [])
    byPrompt.get(r.prompt).push(r)
  }

  const rows = []
  for (const [text, results] of byPrompt.entries()) {
    const succeeded = results.filter(r => r.query_succeeded)
    const mentioned = succeeded.filter(r => r.is_mentioned)
    const visibility = succeeded.length
      ? Math.round(mentioned.length / succeeded.length * 100)
      : 0
    const ranks = mentioned.map(r => r.mention_rank).filter(x => x != null)
    const avgRank = ranks.length
      ? (ranks.reduce((a, b) => a + b, 0) / ranks.length).toFixed(1).replace(/\.0$/, '')
      : null

    const providerDots = results.map(r => ({
      provider: r.provider,
      mentioned: r.is_mentioned,
      succeeded: r.query_succeeded,
      rank: r.mention_rank,
    }))

    // Aggregate competitors co-mentioned in this prompt's responses
    const compCounts = new Map()
    for (const r of results) {
      for (const c of (r.competitors_mentioned || [])) {
        if (!c?.name) continue
        compCounts.set(c.name, (compCounts.get(c.name) || 0) + 1)
      }
    }
    const topCompetitors = [...compCounts.entries()]
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)

    rows.push({
      text,
      intent: promptIntentByText.value[text] || 'custom',
      visibility,
      avgRank,
      providerDots,
      topCompetitors,
      responses: results.filter(r => r.query_succeeded && r.response_text),
    })
  }
  return rows
})

const intentGroups = computed(() => {
  const groups = {}
  for (const row of promptRows.value) {
    if (!groups[row.intent]) groups[row.intent] = []
    groups[row.intent].push(row)
  }
  return Object.entries(groups)
    .map(([intent, prompts]) => {
      const avgVisibility = prompts.length
        ? Math.round(prompts.reduce((a, p) => a + p.visibility, 0) / prompts.length)
        : 0
      // Aggregate provider hit rates across all prompts in this group
      const providerStats = {}
      for (const p of prompts) {
        for (const d of (p.providerDots || [])) {
          if (!providerStats[d.provider]) providerStats[d.provider] = { total: 0, hits: 0 }
          providerStats[d.provider].total++
          if (d.mentioned) providerStats[d.provider].hits++
        }
      }
      const providerSummary = Object.entries(providerStats).map(([provider, s]) => ({
        provider,
        hitRate: s.total ? Math.round(s.hits / s.total * 100) : 0,
      }))
      return { intent, prompts, avgVisibility, providerSummary }
    })
    .sort((a, b) => b.avgVisibility - a.avgVisibility)
})

// Competitors leaderboard: aggregated across all prompts, not filtered
const competitorLeaderboard = computed(() => {
  const results = auditDetail.value?.results || []
  const stats = new Map()
  for (const r of results) {
    if (!r.query_succeeded) continue
    for (const c of (r.competitors_mentioned || [])) {
      if (!c?.name) continue
      if (!stats.has(c.name)) stats.set(c.name, { name: c.name, prompts: new Set(), ranks: [] })
      const s = stats.get(c.name)
      s.prompts.add(r.prompt)
      if (typeof c.position === 'number') s.ranks.push(c.position)
    }
  }
  return [...stats.values()]
    .map(s => ({
      name: s.name,
      promptCount: s.prompts.size,
      avgRank: s.ranks.length
        ? (s.ranks.reduce((a, b) => a + b, 0) / s.ranks.length).toFixed(1).replace(/\.0$/, '')
        : null,
    }))
    .sort((a, b) => b.promptCount - a.promptCount)
    .slice(0, 10)
})

function formatIntent(intent) {
  if (!intent) return 'Other'
  return intent.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function visibilityColor(pct) {
  if (pct >= 60) return 'var(--color-success, #10B981)'
  if (pct >= 30) return 'var(--color-warning, #F59E0B)'
  return 'var(--color-danger, #DC2626)'
}

function providerDotTitle(d) {
  if (!d.succeeded) return 'failed'
  if (d.mentioned) return `mentioned #${d.rank || '—'}`
  return 'not mentioned'
}

function sentimentBadge(s) {
  return s === 'positive' ? 'badge-success' : s === 'negative' ? 'badge-danger' : 'badge-neutral'
}

// ── Brand Overview (Bear-style) ─────────────────────────────────────────────

const filters = ref({ platform: 'all', timeRange: '7d', topic: 'all' })
const openFilter = ref(null)
const highlightedBrand = ref(null)
const topSourcesSort = ref('count')

const timeRanges = Object.freeze([
  { label: 'Last 24 hours', value: '24h' },
  { label: 'Last 7 days', value: '7d' },
  { label: 'Last 30 days', value: '30d' },
  { label: 'Last 90 days', value: '90d' },
  { label: 'All time', value: 'all' },
])

const timeRangeLabel = computed(() => {
  const r = timeRanges.find(t => t.value === filters.value.timeRange)
  return r ? r.label : 'Last 7 days'
})

function toggleFilter(name) {
  openFilter.value = openFilter.value === name ? null : name
}
function setFilter(name, value) {
  filters.value = { ...filters.value, [name]: value }
  openFilter.value = null
}

const availableTopics = computed(() => {
  const set = new Set(promptIntents.value)
  return [...set]
})

// Deterministic brand-name -> hue mapping so each brand keeps its colour.
function brandColor(name) {
  if (!name) return '#9CA3AF'
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) | 0
  const hue = Math.abs(h) % 360
  return `hsl(${hue}, 55%, 55%)`
}

// ── KPIs ───────────────────────────────────────────────────────────────────

const kpiBrandVisibility = computed(() => {
  const a = latestAudit.value
  if (!a) return { value: 0, basis: 0 }
  // When a platform filter is set, recompute against just that provider's
  // responses; otherwise fall back to the audit-level mention_rate.
  if (filters.value.platform && filters.value.platform !== 'all') {
    const results = platformFilteredResults.value.filter(r => r.query_succeeded)
    if (!results.length) return { value: 0, basis: 0 }
    const mentioned = results.filter(r => r.is_mentioned).length
    return {
      value: Math.round(mentioned / results.length * 100),
      basis: results.length,
    }
  }
  return {
    value: Math.round(a.mention_rate || 0),
    basis: a.queries_completed || a.total_queries || 0,
  }
})

const kpiCitationShare = computed(() => {
  // When a platform filter is active, derive from the filtered results so
  // the KPI matches the filter. Otherwise prefer the precomputed history.
  if (filters.value.platform && filters.value.platform !== 'all') {
    const results = platformFilteredResults.value
    let self = 0
    let total = 0
    for (const r of results) {
      if (!r.query_succeeded) continue
      if (r.is_mentioned) { self++; total++ }
      total += (r.competitors_mentioned || []).length
    }
    return {
      value: total ? Math.round(self / total * 1000) / 10 : 0,
      self, total,
    }
  }

  const aid = latestAudit.value?.id
  const fromHistory = (history.value || []).find(h => h.id === aid)
  if (fromHistory && fromHistory.citation_total > 0) {
    return {
      value: fromHistory.citation_share,
      self: fromHistory.citation_self,
      total: fromHistory.citation_total,
    }
  }
  // Fallback: derive from the loaded audit detail.
  const results = auditDetail.value?.results || []
  let self = 0
  let total = 0
  for (const r of results) {
    if (!r.query_succeeded) continue
    if (r.is_mentioned) { self++; total++ }
    total += (r.competitors_mentioned || []).length
  }
  return {
    value: total ? Math.round(self / total * 1000) / 10 : 0,
    self,
    total,
  }
})

const brandRankingRows = computed(() => {
  // Combine you + competitors from the leaderboard, ranked by visibility.
  const a = latestAudit.value
  const yourName = a?.business_name || 'You'
  const yourVis = Math.round(a?.mention_rate || 0)
  const rows = [{ name: yourName, visibility: yourVis, mention_count: 0, is_you: true }]
  for (const c of competitorLeaderboard.value || []) {
    rows.push({
      name: c.name,
      visibility: uniquePromptCount.value
        ? Math.round(c.promptCount / uniquePromptCount.value * 100)
        : 0,
      mention_count: c.promptCount,
      avg_rank: c.avgRank,
      is_you: false,
    })
  }
  rows.sort((a, b) => b.visibility - a.visibility)
  return rows.map((r, i) => ({ ...r, rank: i + 1 }))
})

const kpiBrandRanking = computed(() => {
  const rows = brandRankingRows.value
  const me = rows.find(r => r.is_you)
  if (!me) return { rank: '—', label: '' }
  let label
  if (me.rank === 1) label = 'Market leader'
  else if (me.rank <= 3) label = `Top ${me.rank}`
  else label = `${me.rank} of ${rows.length}`
  return { rank: me.rank, label }
})

const kpiClosestCompetitor = computed(() => {
  const rows = brandRankingRows.value
  const meIdx = rows.findIndex(r => r.is_you)
  if (meIdx < 0) return { name: null, mention_count: 0 }
  // Pick the brand that's directly above us; if we're #1, pick the one below.
  const target = meIdx === 0 ? rows[1] : rows[meIdx - 1]
  return target || { name: null, mention_count: 0 }
})

// ── Competitor Visibility chart (multi-line) ───────────────────────────────

// History scoped to the active filter range. Time-range is applied as a
// last-N-audits cutoff since we don't have hourly audits yet (Phase 2).
const filteredHistory = computed(() => {
  const all = history.value || []
  const range = filters.value.timeRange
  if (range === 'all') return all
  // Treat each historical audit as roughly one daily run for the purpose of
  // the time-range filter. Take the trailing N audits.
  const days = ({ '24h': 1, '7d': 7, '30d': 30, '90d': 90 })[range] || 7
  return all.slice(-days)
})

// "Brand mentions" considered for the active platform filter. When the
// filter is 'all', all results count. When a specific provider is chosen,
// only results from that provider are aggregated. Used by Citation Share
// and Top Sources to make the platform filter actually do work.
const platformFilteredResults = computed(() => {
  const results = auditDetail.value?.results || []
  const p = filters.value.platform
  if (!p || p === 'all') return results
  return results.filter(r => r.provider === p)
})

const competitorVisibilityData = computed(() => {
  const audits = filteredHistory.value
  const labels = audits.map(h => shortDate(h.completed_at))
  if (!audits.length) return { labels: [], datasets: [] }

  // Top brands by latest audit's visibility (so the most relevant lines)
  const latest = audits[audits.length - 1] || {}
  const topCompetitorNames = (latest.competitors || []).slice(0, 5).map(c => c.name)
  const yourName = latestAudit.value?.business_name || 'You'

  const datasets = []
  // Your line
  datasets.push({
    label: yourName + ' (You)',
    data: audits.map(h => Math.round(h.mention_rate || 0)),
    borderColor: '#5B8DEF',
    backgroundColor: 'rgba(91,141,239,0.10)',
    borderWidth: 2.5,
    fill: 'origin',
    tension: 0.4,
    pointRadius: 3,
    pointHoverRadius: 5,
  })
  for (const name of topCompetitorNames) {
    datasets.push({
      label: name,
      data: audits.map(h => {
        const found = (h.competitors || []).find(c => c.name === name)
        return found ? found.visibility : null
      }),
      borderColor: brandColor(name),
      backgroundColor: brandColor(name) + '14',
      borderWidth: 2,
      fill: false,
      tension: 0.4,
      pointRadius: 3,
      pointHoverRadius: 5,
      spanGaps: true,
    })
  }
  return { labels, datasets }
})

const competitorVisibilityOptions = markRaw({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(15, 23, 42, 0.98)',
      titleColor: '#fff',
      bodyColor: '#cbd5e1',
      borderColor: 'rgba(255,255,255,0.08)',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 10,
      displayColors: true,
      boxWidth: 8,
      boxHeight: 8,
      usePointStyle: true,
      titleFont: { size: 11, weight: '600' },
      bodyFont: { size: 12 },
      callbacks: {
        title: (ctx) => 'Visibility · ' + (ctx[0]?.label || ''),
        label: (ctx) => {
          const v = ctx.parsed.y
          return `  ${ctx.dataset.label}: ${v == null ? 'n/a' : v + '%'}`
        },
      },
    },
  },
  scales: {
    x: { grid: { display: false }, border: { display: false }, ticks: { maxTicksLimit: 8, padding: 8, font: { size: 11 } } },
    y: {
      grid: { color: 'rgba(15,23,42,0.05)', drawTicks: false },
      border: { display: false },
      ticks: { padding: 10, font: { size: 11 }, callback: (v) => v + '%' },
      beginAtZero: true,
      max: 100,
    },
  },
})

// ── Citation Share trend ───────────────────────────────────────────────────

const citationShareData = computed(() => {
  const audits = filteredHistory.value
  return {
    labels: audits.map(h => shortDate(h.completed_at)),
    datasets: [{
      label: 'Citation Share',
      data: audits.map(h => h.citation_share || 0),
      borderColor: '#10B981',
      backgroundColor: 'rgba(16,185,129,0.12)',
      borderWidth: 2.5,
      fill: 'origin',
      tension: 0.4,
      pointRadius: 3,
      pointHoverRadius: 5,
    }],
  }
})

const citationShareOptions = markRaw({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(15, 23, 42, 0.98)',
      titleColor: '#fff', bodyColor: '#cbd5e1',
      padding: 10, cornerRadius: 10,
      callbacks: { label: (ctx) => `Citation share: ${ctx.parsed.y}%` },
    },
  },
  scales: {
    x: { grid: { display: false }, border: { display: false }, ticks: { font: { size: 11 } } },
    y: {
      grid: { color: 'rgba(15,23,42,0.05)' },
      border: { display: false },
      ticks: { font: { size: 11 }, callback: (v) => v + '%' },
      beginAtZero: true,
    },
  },
})

// ── Top Sources ────────────────────────────────────────────────────────────

function classifyDomainType(host) {
  const h = host.toLowerCase()
  if (/reddit|quora|stackexchange|stackoverflow|discord|forum|community/.test(h)) return 'UGC'
  if (/wikipedia/.test(h)) return 'Editorial'
  if (/medium|substack|techradar|theverge|wired|tnw|forbes|bloomberg|nytimes|wsj|bbc|cnn|tc|techcrunch/.test(h)) return 'Editorial'
  if (/g2|capterra|trustpilot|getapp|softwareadvice/.test(h)) return 'Reviews'
  if (/youtube|tiktok|instagram|x\.com|twitter\.com|linkedin/.test(h)) return 'Social'
  return 'Corporate'
}

function hostFromUrl(url) {
  try {
    const u = new URL(url)
    return u.hostname.replace(/^www\./, '')
  } catch { return null }
}

const topSources = computed(() => {
  // Honour both the platform filter (which provider's responses to look at)
  // and the topic filter (limit to results whose prompt has the given intent).
  const results = platformFilteredResults.value
  const topic = filters.value.topic
  const counts = new Map()
  for (const r of results) {
    if (!r.query_succeeded) continue
    if (topic && topic !== 'all') {
      const intent = promptIntentByText.value[r.prompt] || 'custom'
      if (intent !== topic) continue
    }
    for (const url of (r.citations || [])) {
      const host = hostFromUrl(url)
      if (!host) continue
      const cur = counts.get(host) || { domain: host, count: 0 }
      cur.count++
      counts.set(host, cur)
    }
  }
  let arr = [...counts.values()].map(s => ({
    domain: s.domain,
    label: s.domain.split('.')[0].replace(/^./, c => c.toUpperCase()),
    type: classifyDomainType(s.domain),
    count: s.count,
  }))
  if (topSourcesSort.value === 'count') arr.sort((a, b) => b.count - a.count)
  else arr.sort((a, b) => a.domain.localeCompare(b.domain))
  return arr.slice(0, 10)
})

function sortTopSources() {
  topSourcesSort.value = topSourcesSort.value === 'count' ? 'domain' : 'count'
}

// ── Pipeline state — drives the component-level flow diagram ─────────────────

const pipelineState = computed(() => {
  const a = latestAudit.value
  if (!a) return { prompts: false, extract: false, score: false }
  return {
    prompts: (a.prompts || []).length > 0,
    extract: a.status === 'running' || a.status === 'completed',
    score: a.status === 'completed',
  }
})

const pipelinePromptCount = computed(() => (latestAudit.value?.prompts || []).length || '—')

// Best-effort pack guess from the audit's industry
const pipelinePackName = computed(() => {
  const ind = (latestAudit.value?.industry || '').toLowerCase()
  if (!ind) return 'Default pack'
  if (/saas|software|cloud/.test(ind))                       return 'Default + SaaS'
  if (/ecommerce|e-commerce|shopify|dtc|retail/.test(ind))   return 'Default + E-commerce'
  if (/law|legal|attorney|lawyer/.test(ind))                 return 'Default + Legal'
  if (/agency|marketing|seo/.test(ind))                      return 'Default + Agency'
  if (/health|clinic|medical|telehealth|dental/.test(ind))   return 'Default + Healthcare'
  return 'Default pack'
})

function pipelineLlmState(providerKey) {
  const a = latestAudit.value
  if (!a) return false
  if (a.status === 'completed') return (a.providers_queried || []).includes(providerKey)
  // While running: green only if at least one result has come back from this provider
  return (auditDetail.value?.results || []).some(r => r.provider === providerKey)
}

function pipelineLlmDotClass(providerKey) {
  const provider = providerHealth.value.providers.find(p => p.key === providerKey)
  if (!provider) return 'dot-off'
  if (!provider.configured) return 'dot-off'
  if (pipelineLlmState(providerKey)) return 'dot-on'
  return 'dot-idle'
}

// ── Audit log — synthesised from existing audit + result timestamps ─────────

function fmtTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const auditLogEvents = computed(() => {
  const a = latestAudit.value
  if (!a) return []

  const events = []

  if (a.created_at) {
    events.push({
      kind: 'info',
      tag: 'QUEUED',
      time: fmtTime(a.created_at),
      message: `Audit created — ${a.prompts?.length || 0} prompt${a.prompts?.length === 1 ? '' : 's'} queued for ${(a.providers_queried || []).length} provider${(a.providers_queried || []).length === 1 ? '' : 's'}`,
    })
  }
  if (a.started_at) {
    events.push({
      kind: 'info',
      tag: 'STARTED',
      time: fmtTime(a.started_at),
      message: `Worker picked up audit — ${a.total_queries || '?'} queries planned`,
    })
  }

  // Per-result events
  const results = auditDetail.value?.results || []
  for (const r of [...results].sort((x, y) => (x.created_at || '').localeCompare(y.created_at || ''))) {
    const provider = providerLabel(r.provider)
    const promptShort = (r.prompt || '').length > 70 ? r.prompt.slice(0, 70) + '...' : (r.prompt || '')
    if (!r.query_succeeded) {
      events.push({
        kind: 'fail',
        tag: provider.toUpperCase(),
        time: fmtTime(r.created_at),
        message: `Query failed — "${promptShort}"`,
        detail: r.error_message,
      })
      continue
    }
    if (r.is_mentioned) {
      events.push({
        kind: 'hit',
        tag: provider.toUpperCase(),
        time: fmtTime(r.created_at),
        message: `Ranked #${r.mention_rank ?? '—'} — "${promptShort}"`,
        detail: r.sentiment && r.sentiment !== 'not_mentioned' ? r.sentiment : '',
      })
    } else {
      events.push({
        kind: 'miss',
        tag: provider.toUpperCase(),
        time: fmtTime(r.created_at),
        message: `Not mentioned — "${promptShort}"`,
      })
    }
  }

  if (a.completed_at) {
    events.push({
      kind: a.status === 'completed' ? 'done' : 'fail',
      tag: 'COMPLETED',
      time: fmtTime(a.completed_at),
      message: a.status === 'completed'
        ? `Audit complete — Score ${a.overall_score}/100, mention rate ${Math.round(a.mention_rate || 0)}%`
        : `Audit ${a.status}`,
    })
  }

  return events
})

// Score factor breakdown (must sum to ~overall_score)
const mentionPts = computed(() => {
  const a = latestAudit.value
  if (!a) return 0
  return Math.round((a.mention_rate || 0) * 0.4)
})
const rankPts = computed(() => {
  const a = latestAudit.value
  if (!a || !a.avg_mention_rank || a.mention_rate === 0) return 0
  // rank #1 → 35pts, rank #10 → 0pts
  return Math.max(0, Math.round(35 * (1 - (a.avg_mention_rank - 1) / 9)))
})
const sentimentPts = computed(() => {
  const a = latestAudit.value
  if (!a) return 0
  return Math.max(0, (a.overall_score || 0) - mentionPts.value - rankPts.value)
})

// Findings stats
const successfulResults = computed(() => {
  if (!auditDetail.value?.results) return []
  return auditDetail.value.results.filter(r => r.query_succeeded)
})
const mentionedResults = computed(() => {
  return successfulResults.value.filter(r => r.is_mentioned)
})
const avgRankDisplay = computed(() => {
  const ranks = mentionedResults.value.map(r => r.mention_rank).filter(Boolean)
  if (!ranks.length) return 'N/A'
  return '#' + Math.round(ranks.reduce((a, b) => a + b, 0) / ranks.length)
})
const promptsUsed = computed(() => {
  if (!auditDetail.value?.results) return 0
  return new Set(auditDetail.value.results.filter(r => r.query_succeeded).map(r => r.prompt)).size
})

// ── Historic trend charts ──
function shortDate(dt) {
  return new Date(dt).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

const trendLabels = computed(() => history.value.map(h => shortDate(h.completed_at)))

const overallTrendData = computed(() => ({
  labels: trendLabels.value,
  datasets: [
    {
      label: 'Overall Score',
      data: history.value.map(h => h.overall_score ?? 0),
      borderColor: '#F5A623',
      backgroundColor: 'rgba(245, 166, 35, 0.12)',
      fill: true,
      tension: 0.35,
      borderWidth: 2.5,
      pointRadius: 3,
      pointHoverRadius: 5,
      yAxisID: 'y',
    },
    {
      label: 'Mention Rate (%)',
      data: history.value.map(h => Math.round(h.mention_rate || 0)),
      borderColor: '#5B8DEF',
      backgroundColor: 'rgba(91, 141, 239, 0.08)',
      fill: false,
      tension: 0.35,
      borderWidth: 2,
      pointRadius: 3,
      pointHoverRadius: 5,
      yAxisID: 'y',
    },
  ],
}))

const overallTrendOptions = markRaw({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { display: true, position: 'top', align: 'end', labels: { usePointStyle: true, pointStyle: 'circle', padding: 16, boxWidth: 6 } },
    tooltip: {
      backgroundColor: 'rgba(26, 26, 46, 0.95)', titleColor: '#fff', bodyColor: '#ccc',
      borderColor: 'rgba(91, 141, 239, 0.15)', borderWidth: 1, padding: 12, cornerRadius: 8,
      displayColors: true, usePointStyle: true,
    },
  },
  scales: {
    x: { grid: { display: false }, border: { display: false }, ticks: { maxTicksLimit: 10, padding: 8 } },
    y: { grid: { color: 'rgba(138, 138, 154, 0.08)', drawTicks: false }, border: { display: false }, ticks: { padding: 10 }, beginAtZero: true, max: 100 },
  },
})

// Build per-provider datasets: one line per provider across all audits
const providerTrendDatasets = computed(() => {
  const providers = new Set()
  for (const h of history.value) {
    for (const p of (h.providers || [])) providers.add(p.provider)
  }
  return [...providers].map(key => {
    const meta = PROVIDER_META[key] || { label: key, color: '#6B7280' }
    return {
      label: meta.label,
      data: history.value.map(h => {
        const entry = (h.providers || []).find(x => x.provider === key)
        return entry ? entry.mention_rate : null
      }),
      borderColor: meta.color,
      backgroundColor: meta.color + '22',
      fill: false,
      tension: 0.35,
      borderWidth: 2,
      pointRadius: 3,
      pointHoverRadius: 5,
      spanGaps: true,
    }
  })
})

const providerTrendData = computed(() => ({
  labels: trendLabels.value,
  datasets: providerTrendDatasets.value,
}))

const providerTrendOptions = markRaw({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { display: true, position: 'top', align: 'end', labels: { usePointStyle: true, pointStyle: 'circle', padding: 16, boxWidth: 6 } },
    tooltip: {
      backgroundColor: 'rgba(26, 26, 46, 0.95)', titleColor: '#fff', bodyColor: '#ccc',
      borderColor: 'rgba(91, 141, 239, 0.15)', borderWidth: 1, padding: 12, cornerRadius: 8,
      displayColors: true, usePointStyle: true,
      callbacks: {
        label: (ctx) => ctx.parsed.y == null ? `${ctx.dataset.label}: n/a` : `${ctx.dataset.label}: ${ctx.parsed.y}%`,
      },
    },
  },
  scales: {
    x: { grid: { display: false }, border: { display: false }, ticks: { maxTicksLimit: 10, padding: 8 } },
    y: {
      grid: { color: 'rgba(138, 138, 154, 0.08)', drawTicks: false },
      border: { display: false },
      ticks: { padding: 10, callback: (v) => v + '%' },
      beginAtZero: true,
      max: 100,
      title: { display: true, text: 'Mention rate', color: '#8a8a9a', font: { size: 11 } },
    },
  },
})

const auditProgressPct = computed(() => {
  const a = latestAudit.value
  if (!a || !a.total_queries) return 0
  return Math.min(100, Math.round((a.queries_completed / a.total_queries) * 100))
})

const auditETA = computed(() => {
  const a = latestAudit.value
  if (!a || !a.started_at || !a.queries_completed || !a.total_queries) return ''
  const started = new Date(a.started_at).getTime()
  const now = Date.now()
  const elapsed = (now - started) / 1000 // seconds
  const perQuery = elapsed / a.queries_completed
  const remaining = (a.total_queries - a.queries_completed) * perQuery
  if (remaining < 5) return 'Almost done...'
  if (remaining < 60) return `~${Math.ceil(remaining)}s remaining`
  const mins = Math.ceil(remaining / 60)
  return `~${mins} min remaining`
})

function ringFillStyle(score) {
  if (score == null) return {}
  const pct = Math.min(100, Math.max(0, score))
  const circ = 2 * Math.PI * 42
  const stroke = pct >= 70
    ? 'var(--color-success)'
    : pct >= 40
      ? 'var(--color-warning)'
      : 'var(--color-danger)'
  return {
    strokeDasharray: `${(pct / 100) * circ} ${circ}`,
    stroke,
  }
}

function mentionBadge(rate) {
  // mention_rate is already 0-100 from backend
  const pct = rate || 0
  return pct >= 60 ? 'badge-success' : pct >= 30 ? 'badge-warning' : 'badge-neutral'
}

function providerLabel(p) {
  return {
    claude: 'Claude', gpt4: 'GPT-4', gemini: 'Gemini', perplexity: 'Perplexity',
    meta_llama: 'Meta Llama', mistral: 'Mistral AI', cohere: 'Cohere',
    deepseek: 'DeepSeek', grok: 'Grok', amazon_nova: 'Amazon Nova',
  }[p] || p
}

function providerInitial(p) {
  return {
    claude: 'A', gpt4: 'G', gemini: 'G', perplexity: 'P',
    meta_llama: 'M', mistral: 'M', cohere: 'C',
    deepseek: 'D', grok: 'X', amazon_nova: 'N',
  }[p] || p[0].toUpperCase()
}

function formatDate(dt) {
  return new Date(dt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function scorePillClass(score) {
  if (score == null) return 'pill-neutral'
  return score >= 70 ? 'pill-green' : score >= 40 ? 'pill-yellow' : 'pill-red'
}

function auditStatusBadge(status) {
  return {
    pending: 'badge-neutral',
    running: 'badge-warning',
    completed: 'badge-success',
    failed: 'badge-danger',
  }[status] || 'badge-neutral'
}

function openRunAudit() {
  auditError.value = ''
  customPromptsText.value = ''
  auditForm.value = {
    business_name: '',
    industry: '',
    location: '',
    description: '',
    themes: ['recommendation', 'comparison', 'use_case', 'persona'],
    providers: providerHealth.value.providers.filter(p => p.configured).map(p => p.key),
    selectedTopics: [],
    competitors: [],
    scan_url: '',
  }
  wizardStep.value = 0
  wizardTopics.value = []
  competitorInput.value = ''
  competitorDomainInput.value = ''
  scanning.value = false
  scanResult.value = null
  showRunForm.value = true
}

async function submitAudit() {
  if (!auditForm.value.business_name) { auditError.value = 'Business name is required.'; return }
  if (!auditForm.value.industry) { auditError.value = 'Industry is required.'; return }
  if (!auditForm.value.providers.length) { auditError.value = 'Select at least one provider.'; return }
  if (!customPromptsText.value.trim() && !(auditForm.value.themes || []).length) {
    auditError.value = 'Pick at least one theme or paste custom prompts.'
    return
  }
  running.value = true
  auditError.value = ''
  try {
    const payload = {
      business_name: auditForm.value.business_name,
      business_description: auditForm.value.description || '',
      industry: auditForm.value.industry,
      location: auditForm.value.location,
      providers: auditForm.value.providers,
      themes: auditForm.value.themes || [],
      keywords: auditForm.value.selectedTopics || [],
      competitors: (auditForm.value.competitors || []).map(c => typeof c === 'string' ? c : c.name),
    }
    if (customPromptsText.value.trim()) {
      payload.custom_prompts = customPromptsText.value.split('\n').map(s => s.trim()).filter(Boolean)
    }
    const { data } = await llmRankingApi.runAudit(websiteId, payload)
    const audit = data?.data || data
    audits.value = [audit, ...audits.value]
    selectedAuditId.value = audit.id
    // Show the prompts panel immediately so the user sees what's being asked
    auditDetail.value = audit
    showRunForm.value = false
    toast.success('Audit queued. Results will appear once complete.')
    // Start polling for results
    startPolling()
  } catch (err) {
    auditError.value = err.displayMessage || 'Failed to start audit.'
  } finally {
    running.value = false
  }
}

async function selectAudit(audit) {
  selectedAuditId.value = audit.id
  latestBreakdown.value = []
  recommendations.value = []
  auditDetail.value = null

  if (audit.status !== 'completed') return

  try {
    const [bRes, rRes, dRes] = await Promise.all([
      llmRankingApi.breakdown(websiteId, audit.id),
      llmRankingApi.recommendations(websiteId, audit.id),
      llmRankingApi.getAudit(websiteId, audit.id),
    ])
    latestBreakdown.value = bRes.data?.data || bRes.data?.results || bRes.data || []
    recommendations.value = rRes.data?.data?.recommendations || rRes.data?.recommendations || []
    auditDetail.value = dRes.data?.data || dRes.data || null
  } catch (e) {
    console.error('Audit breakdown fetch error', e)
  }
}

async function confirmDelete(audit) {
  confirmDeleteId.value = null
  try {
    await llmRankingApi.deleteAudit(websiteId, audit.id)
    audits.value = audits.value.filter(a => a.id !== audit.id)
    if (selectedAuditId.value === audit.id) {
      selectedAuditId.value = null
      latestBreakdown.value = []
      recommendations.value = []
    }
    toast.success('Audit deleted.')
  } catch (err) {
    toast.error(err.displayMessage || 'Failed to delete audit.')
  }
}

// Auto-polling for running audits
function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    const hasRunning = audits.value.some(a => a.status === 'pending' || a.status === 'running')
    if (!hasRunning) {
      stopPolling()
      return
    }
    try {
      const { data } = await llmRankingApi.listAudits(websiteId)
      const newAudits = data?.data?.results || data?.results || data || []
      let anyCompleted = false
      for (const newA of newAudits) {
        const oldA = audits.value.find(a => a.id === newA.id)
        if (oldA && (oldA.status === 'pending' || oldA.status === 'running') && newA.status === 'completed') {
          toast.success(`Audit for "${newA.business_name}" completed! Score: ${newA.overall_score}/100`)
          anyCompleted = true
        }
      }
      audits.value = newAudits
      if (audits.value.length && audits.value[0].status === 'completed' && !latestBreakdown.value.length) {
        await selectAudit(audits.value[0])
      }
      // During a running audit, fetch partial results so the live ticker
      // updates as each LLM finishes — without blocking on /breakdown/ or
      // /recommendations/ which require a completed audit.
      const selected = audits.value.find(a => a.id === selectedAuditId.value)
      if (selected && (selected.status === 'running' || selected.status === 'pending')) {
        try {
          const dRes = await llmRankingApi.getAudit(websiteId, selected.id)
          auditDetail.value = dRes.data?.data || dRes.data || null
        } catch (_) { /* ignore partial fetch errors */ }
      }
      if (anyCompleted) {
        await fetchHistory()
      }
    } catch (e) {
      console.error('Poll error', e)
    }
  }, 5000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function fetchHistory() {
  try {
    const { data } = await llmRankingApi.history(websiteId)
    history.value = data?.data || data || []
  } catch (e) {
    console.error('LLM ranking history fetch error', e)
    history.value = []
  }
}

async function fetchProviderHealth() {
  try {
    const { data } = await llmRankingApi.providerHealth()
    providerHealth.value = data?.data || data || { providers: [], configured_count: 0, total: 0 }
  } catch (e) {
    console.error('Provider health fetch error', e)
  }
}

async function fetchData() {
  loading.value = true
  try {
    const [listRes] = await Promise.all([
      llmRankingApi.listAudits(websiteId),
      fetchHistory(),
      fetchProviderHealth(),
    ])
    const { data } = listRes
    audits.value = data?.data?.results || data?.results || data || []
    if (audits.value.length) {
      // Auto-select the first completed audit so its findings load
      const firstCompleted = audits.value.find(a => a.status === 'completed')
      if (firstCompleted) {
        selectedAuditId.value = firstCompleted.id
        await selectAudit(firstCompleted)
      } else {
        selectedAuditId.value = audits.value[0].id
      }
      // Start polling if any audits are running
      if (audits.value.some(a => a.status === 'pending' || a.status === 'running')) {
        startPolling()
      }
    }
  } catch (e) {
    console.error('LLM ranking fetch error', e)
    audits.value = []
  } finally {
    loading.value = false
  }
}

// Close any open filter dropdown when clicking outside the filter bar.
function onDocClick(ev) {
  if (!openFilter.value) return
  const t = ev.target
  if (t && t.closest && t.closest('.bo-filter')) return
  openFilter.value = null
}

onMounted(() => {
  fetchData()
  document.addEventListener('click', onDocClick)
})
onBeforeUnmount(() => {
  stopPolling()
  document.removeEventListener('click', onDocClick)
})
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }

/* Top filter bar */
.lr-topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 0 18px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--border-color);
}
.lr-topbar-left { display: flex; align-items: center; gap: 10px; flex: 1; flex-wrap: wrap; }
.lr-topbar-right { display: flex; align-items: center; gap: 8px; }
.lr-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: var(--bg-base);
  font-size: var(--font-xs);
  font-weight: 600;
  color: var(--text-primary);
}
.lr-pill-ghost { background: transparent; color: var(--text-muted); font-weight: 500; }
.lr-pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
}
.lr-pill-dot.badge-success { background: var(--color-success, #10B981); }
.lr-pill-dot.badge-warning { background: var(--color-warning, #F59E0B); }
.lr-pill-dot.badge-danger  { background: var(--color-danger,  #DC2626); }
.lr-pill-dot.badge-neutral { background: var(--text-muted); }

/* Onboarding empty state */
.lr-onboarding {
  text-align: center;
  padding: 56px 32px;
}
.lr-onb-eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.15em;
  color: var(--text-muted);
  margin-bottom: 12px;
}
.lr-onb-title {
  font-size: clamp(1.6rem, 3vw, 2.2rem);
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  margin: 0 0 12px;
  line-height: 1.15;
}
.lr-onb-sub {
  max-width: 620px;
  margin: 0 auto 28px;
  font-size: var(--font-sm);
  color: var(--text-secondary);
  line-height: 1.55;
}

/* 2-col grid (overview row) */
.lr-grid-2 {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
}
.lr-grid-2 > .card { margin-bottom: 0 !important; }
@media (max-width: 1100px) {
  .lr-grid-2 { grid-template-columns: 1fr; }
}
.trends-grid-stacked {
  grid-template-columns: 1fr !important;
}

/* Run-audit modal extras */
.form-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
@media (max-width: 600px) { .form-row-2 { grid-template-columns: 1fr; } }
.theme-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}
@media (max-width: 600px) { .theme-grid { grid-template-columns: 1fr; } }
.theme-chip {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--border-color);
  cursor: pointer;
  transition: all 0.15s;
  background: var(--bg-base);
  user-select: none;
}
.theme-chip:hover { border-color: var(--text-muted); }
.theme-chip.active {
  border-color: var(--brand-accent, #4F46E5);
  background: rgba(79, 70, 229, 0.04);
}
.theme-chip input { display: none; }
.theme-chip-title {
  font-size: var(--font-sm);
  font-weight: 700;
  color: var(--text-primary);
}
.theme-chip-desc {
  font-size: 11px;
  color: var(--text-muted);
  font-style: italic;
}

/* ── Wizard layout ── */
.wizard-layout {
  display: flex;
  gap: 0;
  min-height: 480px;
}
.wizard-sidebar {
  width: 180px;
  flex-shrink: 0;
  border-right: 1px solid var(--border-color);
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 0;
}
.wizard-step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  position: relative;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  transition: color 0.2s;
}
.wizard-step-item.active {
  color: var(--text-primary);
  font-weight: 700;
}
.wizard-step-item.done {
  color: var(--text-secondary);
}
/* Vertical connector line */
.wizard-step-item:not(:last-child)::after {
  content: '';
  position: absolute;
  left: 6px;
  top: 34px;
  width: 2px;
  height: 20px;
  background: var(--border-color);
}
.wizard-step-item.done:not(:last-child)::after {
  background: #10b981;
}
.wizard-step-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.wizard-step-item.active .wizard-step-dot {
  border-color: var(--text-primary);
}
.wizard-step-item.done .wizard-step-dot {
  border-color: transparent;
}
.wizard-content {
  flex: 1;
  padding: 32px 40px;
  display: flex;
  flex-direction: column;
}
.wizard-pane {
  flex: 1;
}
.wizard-pane-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
  letter-spacing: -0.02em;
}

/* Scan step */
.wizard-scan-row {
  display: flex;
  gap: 8px;
}
.wizard-scan-row .form-input {
  flex: 1;
}
.wizard-scan-progress {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
  padding: 20px;
  background: var(--bg-offset, #F9FAFB);
  border-radius: var(--radius-md, 10px);
}
.wizard-scan-spinner {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 3px solid var(--border-color, #E5E7EB);
  border-top-color: var(--text-primary, #0F172A);
  animation: wizardSpin 0.7s linear infinite;
  flex-shrink: 0;
}
@keyframes wizardSpin {
  to { transform: rotate(360deg); }
}
.wizard-scan-status {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.wizard-scan-status-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.wizard-scan-result {
  margin-top: 20px;
  padding: 16px 20px;
  border-radius: var(--radius-md, 10px);
  border: 1.5px solid #10b981;
  background: rgba(16, 185, 129, 0.04);
}
.wizard-scan-result.is-error {
  border-color: var(--color-danger, #EF4444);
  background: rgba(239, 68, 68, 0.04);
}
.wizard-scan-success {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.wizard-scan-success svg {
  flex-shrink: 0;
  margin-top: 2px;
}
.wizard-scan-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}
.wizard-scan-error {
  display: flex;
  flex-direction: column;
}
.wizard-pane-sub {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 24px;
  line-height: 1.5;
}
.wizard-textarea {
  font-size: 14px;
  line-height: 1.6;
  min-height: 120px;
  resize: vertical;
}
.wizard-textarea-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
}
.wizard-regen-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  color: #A78BFA;
  transition: color 0.2s;
}
.wizard-regen-btn:hover { color: #7C3AED; }
.wizard-regen-btn:disabled { opacity: 0.5; cursor: default; }

/* Topics grid */
.wizard-topics-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 40px 20px;
}
.wizard-topics-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  max-width: 620px;
  margin-left: auto;
  margin-right: auto;
}
.wizard-topics-actions .btn-ghost {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 5px 12px;
  cursor: pointer;
  transition: all 0.12s;
}
.wizard-topics-actions .btn-ghost:hover {
  color: var(--text-primary);
  border-color: var(--text-muted);
}
.wizard-topics-empty {
  text-align: center;
  padding: 32px 20px;
}
.wizard-topics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  max-width: 620px;
  margin: 0 auto;
}
.wizard-topic-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border-radius: 999px;
  border: 1.5px solid var(--border-color);
  background: var(--bg-base);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
  line-height: 1.3;
}
.wizard-topic-chip:hover {
  border-color: var(--text-muted);
  background: var(--bg-offset, #F9FAFB);
}
.wizard-topic-chip.active {
  background: #0F172A;
  color: #fff;
  border-color: #0F172A;
}
.wizard-topic-check {
  flex-shrink: 0;
}

/* Competitor cards */
.wc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.wc-counter {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}
.wc-input-row {
  display: flex;
  gap: 8px;
  align-items: stretch;
}
.wc-input-wrap {
  flex: 1;
  position: relative;
}
.wc-input-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted, #9CA3AF);
  pointer-events: none;
}
.wc-input {
  padding-left: 34px !important;
}
.wc-add-btn {
  width: 42px;
  min-width: 42px;
  height: 42px;
  padding: 0;
  font-size: 20px;
  font-weight: 700;
  border-radius: var(--radius-md, 10px);
  display: flex;
  align-items: center;
  justify-content: center;
}
.wc-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 16px;
}
.wc-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: var(--radius-md, 10px);
  border: 1.5px solid var(--border-color, #E5E7EB);
  background: #fff;
  transition: border-color 0.15s;
}
.wc-card:hover {
  border-color: var(--text-muted, #9CA3AF);
}
.wc-favicon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  flex-shrink: 0;
  object-fit: contain;
  background: var(--bg-offset, #F5F5F5);
}
.wc-card-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  flex: 1;
  min-width: 0;
}
.wc-card-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wc-card-domain {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wc-card-x {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  color: var(--text-muted);
  padding: 0;
  line-height: 1;
  flex-shrink: 0;
  opacity: 0.5;
  transition: opacity 0.15s, color 0.15s;
}
.wc-card-x:hover {
  opacity: 1;
  color: var(--color-danger, #EF4444);
}

/* Provider grid */
.wizard-provider-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}
.wizard-provider-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 14px 16px;
  border-radius: var(--radius-md, 10px);
  border: 1.5px solid var(--border-color);
  cursor: pointer;
  transition: all 0.15s;
  background: var(--bg-base);
}
.wizard-provider-card:hover { border-color: var(--text-muted); }
.wizard-provider-card.active {
  border-color: #0F172A;
  background: rgba(15, 23, 42, 0.03);
}
.wizard-provider-card.disabled {
  opacity: 0.5;
}
.wizard-provider-card input { display: none; }
.wizard-provider-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}
.wizard-provider-model {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'SF Mono', 'Monaco', monospace;
}
.wizard-provider-status {
  font-size: 10px;
  font-weight: 600;
  margin-top: 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.wizard-provider-status.is-on { color: #10B981; }
.wizard-provider-status.is-off { color: #EF4444; }

/* Review grid */
.wizard-review-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--bg-offset, #F9FAFB);
  padding: 20px 24px;
  border-radius: var(--radius-md, 10px);
}
.wizard-review-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.wizard-review-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.wizard-review-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

/* Wizard nav */
.wizard-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

@media (max-width: 600px) {
  .wizard-layout { flex-direction: column; }
  .wizard-sidebar {
    width: 100%;
    flex-direction: row;
    overflow-x: auto;
    padding: 16px 20px;
    border-right: none;
    border-bottom: 1px solid var(--border-color);
    gap: 16px;
  }
  .wizard-step-item:not(:last-child)::after { display: none; }
  .wizard-content { padding: 20px; }
  .wizard-topics-grid { max-width: 100%; }
  .wizard-provider-grid { grid-template-columns: 1fr; }
}

/* ─────────────────────────────────────────────────────────────────
   Brand Overview (Bear-style dashboard)
   ───────────────────────────────────────────────────────────────── */

.brand-overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.bo-row { gap: 16px; margin: 0; }
.bo-row > .card { margin-bottom: 0 !important; }

/* Filter bar */
.bo-filters { display: flex; gap: 8px; flex-wrap: wrap; }
.bo-filter {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: var(--bg-base);
  color: var(--text-primary);
  font-size: var(--font-sm);
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.bo-filter:hover { border-color: var(--text-muted); }
.bo-filter.open { border-color: var(--brand-accent, #4F46E5); box-shadow: 0 0 0 3px rgba(79,70,229,0.08); }
.bo-caret { color: var(--text-muted); }
.bo-filter-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 200px;
  padding: 6px;
  border-radius: 12px;
  background: var(--bg-base);
  border: 1px solid var(--border-color);
  box-shadow: 0 12px 32px rgba(15,23,42,0.10), 0 2px 8px rgba(15,23,42,0.04);
  z-index: 20;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.bo-filter-item {
  text-align: left;
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: var(--font-sm);
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.12s;
}
.bo-filter-item:hover { background: var(--bg-surface); }
.bo-filter-item.active {
  background: rgba(79,70,229,0.06);
  color: var(--brand-accent, #4F46E5);
}

/* 4-KPI strip */
.kpi-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
@media (max-width: 1100px) {
  .kpi-strip { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .kpi-strip { grid-template-columns: 1fr; }
}
.kpi-card {
  background: var(--bg-base);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  padding: 18px 18px 16px;
  position: relative;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s;
}
.kpi-card:hover {
  border-color: var(--text-muted);
  box-shadow: 0 8px 24px rgba(15,23,42,0.05);
  transform: translateY(-1px);
}
.kpi-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-xs);
  color: var(--text-muted);
  font-weight: 600;
  margin-bottom: 12px;
}
.kpi-info {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--bg-surface);
  color: var(--text-muted);
  font-size: 9px;
  font-weight: 800;
  cursor: help;
  font-style: italic;
}
.kpi-value {
  font-size: 36px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
  letter-spacing: -0.025em;
  font-variant-numeric: tabular-nums;
}
.kpi-value-rank { color: #131718; }
.kpi-unit {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-muted);
  margin-left: 2px;
}
.kpi-sub {
  margin-top: 8px;
  font-size: var(--font-xs);
  color: var(--text-muted);
  font-weight: 500;
}
.kpi-closest {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
}
.kpi-closest-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 16px;
  flex-shrink: 0;
}
.kpi-closest-meta { display: flex; flex-direction: column; gap: 2px; }
.kpi-closest-name {
  font-size: var(--font-md);
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.1;
}

/* Chart cards */
.bo-chart-card { padding-bottom: 8px; }
.bo-chart-wrap {
  position: relative;
  height: 320px;
  padding: 6px 16px 16px;
}
.bo-chart-small { height: 220px; }

/* Competitor Rankings */
.bo-ranking-card { padding-bottom: 8px; }
.bo-ranking-head, .bo-sources-head {
  display: grid;
  grid-template-columns: 32px 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-color);
}
.bo-sources-head {
  grid-template-columns: 32px 1fr 80px 80px;
}
.bo-ranking-list, .bo-sources-list {
  display: flex;
  flex-direction: column;
  padding: 6px 0;
}
.bo-ranking-row, .bo-source-row {
  display: grid;
  grid-template-columns: 32px 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  font-size: var(--font-sm);
  cursor: default;
  transition: background 0.15s;
}
.bo-source-row { grid-template-columns: 32px 1fr 80px 80px; cursor: default; }
.bo-ranking-row:hover, .bo-source-row:hover { background: var(--bg-surface); }
.bo-ranking-row.is-you {
  background: rgba(91,141,239,0.06);
  border-left: 3px solid #5B8DEF;
  padding-left: 13px;
}
.bo-ranking-row.is-highlighted { background: rgba(79,70,229,0.06); }
.bo-rh-rank, .bo-sh-rank { color: var(--text-muted); font-weight: 700; }
.bo-rh-name, .bo-sh-domain {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  color: var(--text-primary);
  min-width: 0;
}
.bo-rh-vis, .bo-sh-count {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}
.bo-brand-avatar, .bo-source-favicon {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  flex-shrink: 0;
}
.bo-source-favicon { border-radius: 4px; }
.bo-source-name {
  display: block;
  font-weight: 700;
  color: var(--text-primary);
  font-size: var(--font-sm);
  line-height: 1.2;
}
.bo-source-host {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}
.bo-you-tag {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
  margin-left: 4px;
}

/* Type pill */
.bo-type-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
}
.bo-type-UGC       { background: rgba(91,141,239,0.12); color: #3B5EAF; }
.bo-type-Editorial { background: rgba(245,166,35,0.14); color: #B45309; }
.bo-type-Reviews   { background: rgba(167,139,250,0.16); color: #6B21A8; }
.bo-type-Social    { background: rgba(236,72,153,0.14); color: #BE185D; }
.bo-type-Corporate { background: rgba(107,114,128,0.14); color: #374151; }

/* System status grid */
.lr-status-grid { grid-template-columns: 1fr 2fr; }
@media (max-width: 1100px) { .lr-status-grid { grid-template-columns: 1fr; } }

/* Provider status list */
.provider-status-list { display: flex; flex-direction: column; gap: 4px; padding: 8px 0; }
.provider-status-row {
  display: grid;
  grid-template-columns: 14px 1fr auto auto;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  font-size: var(--font-sm);
}
.provider-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success, #10B981);
  box-shadow: 0 0 0 0 rgba(16,185,129,0.5);
}
.provider-status-row.is-on .provider-status-dot {
  animation: dot-breathe 2s ease-in-out infinite;
}
.provider-status-row.is-off .provider-status-dot {
  background: var(--text-muted);
  box-shadow: none;
}
@keyframes dot-breathe {
  0%, 100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.5); }
  50%      { box-shadow: 0 0 0 5px rgba(16,185,129,0); }
}
.provider-status-name { font-weight: 600; color: var(--text-primary); }
.provider-status-model {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
  color: var(--text-muted);
}
.provider-status-state {
  font-size: var(--font-xs);
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
}
.provider-status-row.is-on  .provider-status-state {
  background: rgba(16,185,129,0.12);
  color: #047857;
}
.provider-status-row.is-off .provider-status-state {
  background: var(--bg-surface);
  color: var(--text-muted);
}

/* Pipeline diagram */
.pipeline-diagram {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 16px 22px;
  flex-wrap: wrap;
}
.pl-node {
  position: relative;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--bg-base);
  min-width: 96px;
  text-align: center;
  transition: all 0.25s ease;
}
.pl-node.active {
  border-color: var(--brand-accent, #4F46E5);
  background: rgba(79, 70, 229, 0.04);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.08);
}
.pl-node.disabled { opacity: 0.4; }
.pl-node-label {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 4px;
}
.pl-node-value {
  font-family: 'DM Serif Display', Georgia, serif;
  font-weight: 400;
  font-size: 24px;
  color: var(--text-primary);
  line-height: 1;
  letter-spacing: -0.02em;
}
.pl-node-sub {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 4px;
}

.pl-arrow {
  width: 22px;
  height: 1px;
  background: var(--border-color);
  position: relative;
  flex-shrink: 0;
}
.pl-arrow::after {
  content: '';
  position: absolute;
  right: -1px;
  top: -3px;
  width: 0;
  height: 0;
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
  border-left: 6px solid var(--border-color);
}

.pl-fanout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}
.pl-node-llm {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-base);
  min-width: 0;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-primary);
  transition: all 0.25s ease;
}
.pl-node-llm.active {
  border-color: var(--color-success, #10B981);
  background: rgba(16,185,129,0.06);
}
.pl-node-llm.disabled { opacity: 0.4; }
.pl-node-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
}
.pl-node-dot.dot-on   { background: var(--color-success, #10B981); }
.pl-node-dot.dot-idle { background: var(--text-muted); }
.pl-node-dot.dot-off  { background: var(--color-danger, #DC2626); }

/* Audit Log */
.audit-log-list {
  display: flex;
  flex-direction: column;
  padding: 4px 0 8px;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
}
.audit-log-row {
  display: grid;
  grid-template-columns: 80px 80px 1fr auto;
  align-items: baseline;
  gap: 12px;
  padding: 6px 16px;
  border-left: 2px solid transparent;
  transition: background 0.15s;
}
.audit-log-row:hover { background: var(--bg-surface); }
.audit-log-row.log-info { border-left-color: var(--text-muted); }
.audit-log-row.log-hit  { border-left-color: var(--color-success, #10B981); }
.audit-log-row.log-miss { border-left-color: var(--text-muted); opacity: 0.7; }
.audit-log-row.log-fail { border-left-color: var(--color-danger,  #DC2626); }
.audit-log-row.log-done { border-left-color: var(--brand-accent, #4F46E5); background: rgba(79,70,229,0.04); }

.audit-log-time {
  color: var(--text-muted);
  font-weight: 500;
}
.audit-log-tag {
  font-weight: 800;
  letter-spacing: 0.04em;
}
.log-info .audit-log-tag { color: var(--text-muted); }
.log-hit  .audit-log-tag { color: #047857; }
.log-miss .audit-log-tag { color: var(--text-muted); }
.log-fail .audit-log-tag { color: #B91C1C; }
.log-done .audit-log-tag { color: #4F46E5; }

.audit-log-msg {
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.audit-log-detail {
  color: var(--text-muted);
  font-size: 11px;
  font-style: italic;
}

/* Score summary */
.score-main { display: flex; align-items: center; gap: 32px; }
.score-ring-wrap { position: relative; width: 110px; height: 110px; flex-shrink: 0; }
.score-ring-svg { width: 110px; height: 110px; transform: rotate(-90deg); }
.ring-track { fill: none; stroke: var(--border-color); stroke-width: 8; }
.ring-fill { fill: none; stroke-width: 8; stroke-linecap: round; transition: stroke-dasharray 0.6s ease; }
.score-center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.score-num { font-size: 26px; font-weight: 800; color: var(--text-primary); line-height: 1; }
.score-denom { font-size: var(--font-xs); color: var(--text-muted); }
.score-meta { flex: 1; }

/* Running audit progress */
.audit-progress-card {
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  border: none;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.progress-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.progress-label {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}
.progress-pct {
  font-size: var(--font-sm);
  font-weight: 700;
  color: var(--color-warning);
}
.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-warning);
  animation: pulse 1.5s ease-in-out infinite;
  flex-shrink: 0;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}
.progress-bar-track {
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-warning), var(--color-success));
  border-radius: 3px;
  transition: width 0.5s ease;
  min-width: 2px;
}
.progress-details {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: var(--font-xs);
  color: var(--text-muted);
}

/* Provider grid */
.provider-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.provider-card {
  border: none;
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  text-align: center;
  transition: border-color var(--transition-fast);
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
}
.provider-card.provider-mentioned { border-color: var(--color-success); background: var(--color-success-bg); }
.provider-card.provider-failed { opacity: 0.5; border-style: dashed; }
.score-breakdown { padding: 12px 16px; border-radius: var(--radius-md); background: var(--bg-surface); border: 1px solid var(--border-color); }
.provider-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--bg-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: var(--font-base);
  color: var(--text-secondary);
}
.provider-name { font-size: var(--font-sm); font-weight: 600; color: var(--text-primary); }

/* Methodology */
.methodology-content { padding: 16px; }
.method-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.method-item {
  padding: 16px;
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  text-align: center;
}
.method-weight {
  font-size: var(--font-lg);
  font-weight: 800;
  color: var(--color-primary);
  margin-bottom: 4px;
}
.method-title {
  font-size: var(--font-sm);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}
.method-desc {
  font-size: var(--font-xs);
  color: var(--text-muted);
  line-height: 1.5;
}
.method-steps { display: flex; flex-direction: column; gap: 16px; padding: 16px; }
.method-step { display: flex; gap: 12px; align-items: flex-start; }
.step-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-weight: 800;
  font-size: var(--font-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.step-title { font-weight: 700; font-size: var(--font-sm); color: var(--text-primary); margin-bottom: 2px; }
.step-desc { font-size: var(--font-xs); color: var(--text-muted); line-height: 1.6; }

/* Score factor bars */
.score-factors {
  padding: 16px;
  border-top: 1px solid var(--border-color);
}
.factor-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.factor-label {
  width: 180px;
  font-size: var(--font-xs);
  color: var(--text-muted);
  flex-shrink: 0;
}
.factor-bar-wrap {
  flex: 1;
  height: 8px;
  background: var(--border-color);
  border-radius: 4px;
  overflow: hidden;
}
.factor-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
  min-width: 2px;
}
.factor-value {
  width: 50px;
  text-align: right;
  font-size: var(--font-xs);
  font-weight: 700;
  color: var(--text-primary);
}
.factor-total {
  display: flex;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
  font-size: var(--font-sm);
  color: var(--text-primary);
}

/* Visibility trend charts */
.trends-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 16px;
}
@media (max-width: 900px) {
  .trends-grid { grid-template-columns: 1fr; }
}
.trend-block {
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.trend-label {
  font-size: var(--font-xs);
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}
.trend-chart-wrap {
  position: relative;
  height: 240px;
}

/* Findings summary */
.findings-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.summary-stat {
  text-align: center;
  padding: 12px;
  border-radius: var(--radius-md);
  background: var(--bg-base);
  border: none;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.summary-num {
  display: block;
  font-size: var(--font-lg);
  font-weight: 800;
  color: var(--text-primary);
}
.summary-label {
  font-size: var(--font-xs);
  color: var(--text-muted);
}

/* Detailed Findings */
.findings-list { display: flex; flex-direction: column; gap: 12px; padding: 16px; }
.finding-card {
  display: flex;
  gap: 12px;
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--text-muted);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  background: var(--bg-base);
}
.finding-card.finding-mentioned { border-left-color: var(--color-success); }
.finding-card.finding-failed { border-left-color: var(--color-danger); opacity: 0.5; }
.finding-number {
  font-size: var(--font-xs);
  font-weight: 800;
  color: var(--text-muted);
  padding-top: 2px;
  flex-shrink: 0;
  width: 24px;
}
.finding-body { flex: 1; min-width: 0; }
.finding-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.finding-provider { font-weight: 700; font-size: var(--font-sm); color: var(--text-primary); }
.finding-confidence { font-size: var(--font-xs); color: var(--text-muted); margin-left: auto; }
.finding-label { font-weight: 600; color: var(--text-muted); font-size: var(--font-xs); text-transform: uppercase; letter-spacing: 0.5px; }
.finding-prompt { font-size: var(--font-sm); color: var(--text-secondary); margin-bottom: 6px; line-height: 1.5; }
.finding-context { font-size: var(--font-sm); color: var(--color-success); font-style: italic; margin-bottom: 6px; }
.finding-error { font-size: var(--font-xs); color: var(--color-danger); margin-bottom: 6px; }
.finding-response { margin-top: 8px; }
.response-toggle {
  font-size: var(--font-xs);
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 0;
}
.response-toggle:hover { color: var(--text-primary); }
.response-pre {
  margin-top: 8px;
  padding: 12px;
  background: var(--bg-surface);
  border-radius: var(--radius-sm);
  font-size: var(--font-xs);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

/* Prompt list (shown before / during an audit) */
.prompt-list { display: flex; flex-direction: column; gap: 6px; padding: 16px; }
.prompt-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--bg-base);
  border: 1px solid var(--border-color);
  font-size: var(--font-sm);
}
.prompt-num {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--bg-surface);
  color: var(--text-muted);
  font-weight: 700;
  font-size: var(--font-xs);
  display: flex;
  align-items: center;
  justify-content: center;
}
.prompt-text {
  flex: 1;
  color: var(--text-primary);
  line-height: 1.45;
}
.prompt-intent {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(91, 141, 239, 0.12);
  color: #3B5EAF;
}

/* Prompt Intelligence (post-audit rich view) */
.pi-filter { display: flex; align-items: center; }
.pi-select {
  padding: 4px 8px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-base);
  color: var(--text-primary);
  font-size: var(--font-xs);
  font-weight: 600;
}
.pi-groups { display: flex; flex-direction: column; gap: 12px; padding: 16px; }
.pi-group {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-base);
  overflow: hidden;
}
.pi-group-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  cursor: pointer;
  background: var(--bg-surface);
  user-select: none;
}
.pi-group-header:hover { background: rgba(0,0,0,0.02); }
.pi-chevron { color: var(--text-muted); transition: transform 0.2s; flex-shrink: 0; }
.pi-chevron.open { transform: rotate(90deg); }
.pi-intent-name {
  font-size: var(--font-xs);
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-primary);
}
.pi-group-stats {
  font-size: var(--font-xs);
  color: var(--text-muted);
  flex: 0 0 auto;
  margin-left: auto;
}
.pi-vis-bar-wrap {
  flex: 0 0 80px;
  height: 4px;
  background: var(--border-color);
  border-radius: 2px;
  overflow: hidden;
  margin-left: 8px;
}
.pi-vis-bar {
  display: block;
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}

.pi-group-body { display: flex; flex-direction: column; padding: 4px 0; }
.pi-prompt {
  padding: 12px 14px;
  border-top: 1px solid var(--border-color);
}
.pi-prompt:first-child { border-top: none; }
.pi-prompt-text {
  font-size: var(--font-sm);
  color: var(--text-primary);
  font-weight: 500;
  line-height: 1.45;
  margin-bottom: 8px;
}
.pi-prompt-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: var(--font-xs);
  color: var(--text-muted);
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.pi-stat { display: inline-flex; align-items: center; gap: 4px; }
.pi-stat strong { font-weight: 700; color: var(--text-primary); }
.pi-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--border-color);
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 800;
  margin-left: 2px;
  cursor: help;
}
.pi-dot.hit  { background: var(--color-success, #10B981); color: #fff; }
.pi-dot.fail { background: var(--color-danger, #DC2626); color: #fff; opacity: 0.7; }

.pi-competitors {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: var(--font-xs);
}
.pi-comp-label { color: var(--text-muted); font-weight: 600; margin-right: 2px; }
.pi-comp-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  font-weight: 500;
}
.pi-comp-count {
  color: var(--text-muted);
  margin-left: 4px;
  font-weight: 600;
}

.pi-responses { margin-top: 10px; }
.pi-responses-toggle {
  font-size: var(--font-xs);
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 0;
}
.pi-responses-toggle:hover { color: var(--text-primary); }
.pi-response {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
}
.pi-response-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.pi-response-provider { font-weight: 700; font-size: var(--font-sm); color: var(--text-primary); }
.pi-response-text {
  margin: 0;
  font-size: var(--font-xs);
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 260px;
  overflow-y: auto;
  color: var(--text-secondary);
  font-family: inherit;
}

/* ═══ Prompts Table ═══════════════════════════════════════════════════════ */
.pt-header-right { display: flex; align-items: center; gap: 12px; }
.pt-table { }
.pt-thead {
  display: grid;
  grid-template-columns: 1fr 80px 120px 140px 100px;
  padding: 10px 20px;
  border-bottom: 1px solid var(--border-color, #E5E7EB);
  background: var(--bg-offset, #FAFAFA);
}
.pt-th {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted, #9CA3AF);
}
.pt-topic-row {
  display: grid;
  grid-template-columns: 1fr 80px 120px 140px 100px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-color, #E5E7EB);
  cursor: pointer;
  transition: background 0.12s;
  align-items: center;
  background: var(--bg-surface, #fff);
}
.pt-topic-row:hover { background: var(--bg-offset, #F9FAFB); }
.pt-prompt-row {
  display: grid;
  grid-template-columns: 1fr 80px 120px 140px 100px;
  padding: 10px 20px 10px 44px;
  border-bottom: 1px solid var(--border-color, #E5E7EB);
  align-items: center;
  background: var(--bg-offset, #FAFAFA);
  font-size: 13px;
}
.pt-prompt-row:last-child { border-bottom: none; }
.pt-td { display: flex; align-items: center; gap: 4px; }
.pt-td-topic {
  font-weight: 600;
  color: var(--text-primary);
  gap: 8px;
}
.pt-topic-name { font-size: 13px; }
.pt-td-prompt-text {
  font-weight: 400;
  color: var(--text-secondary, #6B7280);
  font-size: 12.5px;
  line-height: 1.4;
}
.pt-td-count {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  justify-content: center;
}
.pt-td-vis {
  font-size: 13px;
  font-weight: 600;
}
.pt-td-perf { gap: 3px; }
.pt-perf-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 800;
  background: var(--border-color, #E5E7EB);
  color: var(--text-muted, #9CA3AF);
  cursor: help;
}
.pt-perf-icon.is-hit { background: #10b981; color: #fff; }
.pt-perf-icon.is-partial { background: #f59e0b; color: #fff; }
.pt-perf-icon.is-miss { background: var(--border-color, #E5E7EB); color: var(--text-muted); }
.pt-perf-icon.is-fail { background: var(--color-danger, #EF4444); color: #fff; opacity: 0.6; }
.pt-td-status { justify-content: flex-end; }
.pt-see-link {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  cursor: pointer;
}
.pt-status-pill {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid;
}
.pt-status-pill.is-ran {
  color: #D97706;
  border-color: #FDE68A;
  background: #FFFBEB;
}
.pt-status-pill.is-miss {
  color: var(--text-muted);
  border-color: var(--border-color);
  background: var(--bg-offset);
}


.comp-leaderboard { display: flex; flex-direction: column; padding: 16px 16px 0; gap: 6px; }
.comp-row {
  display: grid;
  grid-template-columns: 24px 1fr 1fr auto auto;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: var(--bg-base);
  border: 1px solid var(--border-color);
  font-size: var(--font-sm);
}
.comp-rank {
  font-family: 'DM Serif Display', Georgia, serif;
  font-size: var(--font-md);
  color: var(--text-muted);
  text-align: center;
}
.comp-name { font-weight: 700; color: var(--text-primary); }
.comp-bar-wrap {
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  overflow: hidden;
}
.comp-bar {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #5B8DEF, #A78BFA);
  border-radius: 3px;
  transition: width 0.5s ease;
}
.comp-coverage { font-size: var(--font-xs); color: var(--text-muted); white-space: nowrap; }
.comp-avg-rank {
  font-size: var(--font-xs);
  font-weight: 700;
  color: var(--text-primary);
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--bg-surface);
}

/* Live ticker (during a running audit) */
.live-pulse {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success, #34D399);
  margin-left: 8px;
  animation: live-pulse-kf 1.3s ease-in-out infinite;
  vertical-align: middle;
}
@keyframes live-pulse-kf {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(52,211,153,0.6); }
  50%      { opacity: 0.6; box-shadow: 0 0 0 6px rgba(52,211,153,0); }
}
.live-list { display: flex; flex-direction: column; gap: 6px; padding: 16px; }
.live-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--bg-base);
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--text-muted);
  font-size: var(--font-sm);
  animation: live-row-in 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}
.live-row.live-hit  { border-left-color: var(--color-success, #34D399); }
.live-row.live-fail { border-left-color: var(--color-danger, #DC2626); opacity: 0.7; }
.live-provider {
  flex-shrink: 0;
  font-weight: 700;
  color: var(--text-primary);
  width: 76px;
}
.live-prompt {
  flex: 1;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
@keyframes live-row-in {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Recommendations */
.recs-list { display: flex; flex-direction: column; gap: 0; }
.rec-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}
.rec-row:last-child { border-bottom: none; }
.rec-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--text-primary);
  color: var(--text-inverse);
  font-size: var(--font-xs);
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* Audit table */
.audit-row { cursor: pointer; }
.audit-row.row-selected td { background: var(--bg-surface); }

.score-pill { padding: 2px 10px; border-radius: var(--radius-full); font-size: var(--font-xs); font-weight: 700; }
.pill-green { background: var(--color-success-bg); color: var(--color-success); }
.pill-yellow { background: var(--color-warning-bg); color: var(--color-warning); }
.pill-red { background: var(--color-danger-bg); color: var(--color-danger); }
.pill-neutral { background: var(--bg-surface); color: var(--text-muted); }

.delete-btn { color: var(--color-danger); }

/* Modal extras */
.provider-checks { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 4px; }
.check-label { display: flex; align-items: center; gap: 6px; font-size: var(--font-sm); color: var(--text-secondary); cursor: pointer; }
</style>
