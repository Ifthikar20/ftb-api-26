<template>
  <div class="llm-ranking-page fade-in">
    <!-- First-run gate: split into two states. If the user has no saved
         prompts, push them to the Prompt Library. If they have prompts
         but no audits, surface a clear "kick off the first audit" CTA
         so the dashboard isn't a dead end after they finish step one. -->
    <div v-if="showFirstRun" class="empty-dashboard">
      <div class="empty-dashboard-card">
        <div class="empty-dashboard-icon" aria-hidden="true">
          <svg v-if="!savedPromptsCount" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7"/>
            <path d="M21 21l-4.3-4.3"/>
          </svg>
          <svg v-else width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
        </div>

        <template v-if="!savedPromptsCount">
          <h1 class="empty-dashboard-title">Your LLM Dashboard is empty</h1>
          <p class="empty-dashboard-sub">
            Nothing has been measured yet for <strong>{{ websiteName || 'this website' }}</strong>.
            Add a prompt of your own or pull one from the prompt repository to start tracking how
            AI assistants talk about your brand.
          </p>
          <div class="empty-dashboard-actions">
            <router-link :to="promptLibraryRoute" class="btn btn-primary">Create a prompt</router-link>
            <router-link :to="promptLibraryRepoRoute" class="btn btn-secondary">Browse the prompt repository</router-link>
          </div>
        </template>

        <template v-else>
          <h1 class="empty-dashboard-title">Ready to run your first audit</h1>
          <p class="empty-dashboard-sub">
            <strong>{{ savedPromptsCount }} prompt{{ savedPromptsCount === 1 ? '' : 's' }}</strong> saved for
            <strong>{{ websiteName || 'this website' }}</strong>. Kick off an audit and we'll send them to
            Claude, GPT-4, Gemini, and Perplexity, then chart how often you surface.
          </p>
          <div class="empty-dashboard-actions">
            <button class="btn btn-primary" :disabled="running" @click="openRunAudit">
              {{ running ? 'Running audit…' : 'Run my first audit' }}
            </button>
            <router-link :to="promptLibraryRoute" class="btn btn-secondary">Edit my prompts</router-link>
          </div>
        </template>
      </div>
    </div>
    <template v-else>
    <div class="page-header">
      <div>
        <div class="page-eyebrow">
          <Activity :size="12" :stroke-width="2"/>
          <span>AI Visibility</span>
        </div>
        <h1 class="page-title">LLM Dashboard</h1>
        <p class="page-subtitle">
          See how AI tools like Claude, GPT-4, Gemini, and Perplexity rank your business
          when users ask them to find a service like yours.
        </p>
        <p v-if="currentWebsite" class="page-context">
          <Globe :size="12" :stroke-width="1.8"/>
          Auditing <strong>{{ websiteName }}</strong>
          <span v-if="homepageUrl" class="text-muted">· {{ homepageUrl }}</span>
          <a href="/websites/" class="page-context-link">change website</a>
        </p>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary btn-sm" @click="showScheduleModal = true">
          <CalendarClock :size="14" :stroke-width="1.8"/>
          {{ schedule ? 'Edit Schedule' : 'Schedule' }}
        </button>
        <button class="btn btn-primary btn-sm" @click="openRunAudit" :disabled="running">
          <Play v-if="!running" :size="13" :stroke-width="2.2" fill="currentColor"/>
          {{ running ? 'Running audit...' : 'Run New Audit' }}
        </button>
      </div>
    </div>

    <!-- Tab nav: Overview is the dense brand-visibility dashboard; Performance
         is a chart-first view of how each model is doing on the latest run. -->
    <div class="lr-tabs" role="tablist">
      <button
        type="button"
        class="lr-tab"
        :class="{ active: activeTab === 'overview' }"
        role="tab"
        :aria-selected="activeTab === 'overview'"
        @click="activeTab = 'overview'"
      >Overview</button>
      <button
        type="button"
        class="lr-tab"
        :class="{ active: activeTab === 'performance' }"
        role="tab"
        :aria-selected="activeTab === 'performance'"
        @click="activeTab = 'performance'"
      >Performance</button>
      <button
        type="button"
        class="lr-tab"
        :class="{ active: activeTab === 'pages' }"
        role="tab"
        :aria-selected="activeTab === 'pages'"
        @click="activeTab = 'pages'"
      >Pages
        <span v-if="importedCount" class="lr-tab-badge">{{ importedCount }}</span>
      </button>
    </div>

    <div v-show="activeTab === 'overview'" class="lr-overview">

      <!-- Schedule banner: shown only when the website has a schedule on file.
           Keeps the action affordance prominent without dominating the dashboard. -->
      <div v-if="schedule" class="ov-banner" :class="{ paused: !schedule.is_enabled }">
        <div class="ov-banner-icon" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="8" cy="8" r="6"/><path d="M8 4v4l3 2"/>
          </svg>
        </div>
        <div class="ov-banner-text">
          <strong>{{ schedule.is_enabled ? 'Scheduled audit active' : 'Schedule paused' }}</strong>
          <span v-if="schedule.cadence" class="text-muted">· {{ schedule.cadence }}</span>
          <span v-if="scheduleETA?.next_run_human" class="text-muted">· next run {{ scheduleETA.next_run_human }}</span>
        </div>
        <button class="btn btn-ghost btn-sm" @click="showScheduleModal = true">Manage</button>
      </div>

      <div v-if="loading" class="ov-loading">
        <div class="ov-spinner" aria-hidden="true"></div>
        <span>Loading dashboard...</span>
      </div>

      <template v-else>
      <!-- KPI strip -->
      <div class="ov-kpis">
        <div class="ov-kpi">
          <div class="ov-kpi-head">
            <span class="ov-kpi-label">AI Visibility Score</span>
            <span v-if="isAuditComplete" class="ov-kpi-badge" :class="scorePillClass(latestAudit.overall_score)">
              {{ latestAudit.overall_score >= 70 ? 'Strong' : latestAudit.overall_score >= 40 ? 'Fair' : 'Weak' }}
            </span>
          </div>
          <div class="ov-kpi-value">
            <template v-if="isAuditComplete">{{ Math.round(latestAudit.overall_score || 0) }}<span class="ov-kpi-unit">/100</span></template>
            <template v-else>—</template>
          </div>
          <div class="ov-kpi-sub" :class="perfKpis.scoreTrendClass">
            {{ isAuditComplete ? perfKpis.scoreTrendLabel : (latestAudit?.status ? capitalize(latestAudit.status) : 'No audit yet') }}
          </div>
        </div>

        <div class="ov-kpi">
          <div class="ov-kpi-head"><span class="ov-kpi-label">Mention Rate</span></div>
          <div class="ov-kpi-value">
            <template v-if="isAuditComplete">{{ Math.round(latestAudit.mention_rate || 0) }}<span class="ov-kpi-unit">%</span></template>
            <template v-else>—</template>
          </div>
          <div class="ov-kpi-sub">
            {{ isAuditComplete ? `${latestAudit.total_queries || 0} queries · ${(latestAudit.providers_queried || []).length} models` : 'Waiting on first completed audit' }}
          </div>
        </div>

        <div class="ov-kpi">
          <div class="ov-kpi-head"><span class="ov-kpi-label">Top Model</span></div>
          <div class="ov-kpi-value ov-kpi-value-sm">{{ perfKpis.topProvider || '—' }}</div>
          <div class="ov-kpi-sub">
            {{ perfKpis.topProvider ? `${perfKpis.topProviderRate}% mention rate` : 'No model data yet' }}
          </div>
        </div>

        <div class="ov-kpi">
          <div class="ov-kpi-head"><span class="ov-kpi-label">Audits Run</span></div>
          <div class="ov-kpi-value">{{ audits.length }}</div>
          <div class="ov-kpi-sub">
            {{ usageData?.audit_stats?.total_audits ? `${usageData.audit_stats.total_audits} total all-time` : 'Across this workspace' }}
          </div>
        </div>
      </div>

      <!-- Trend + model coverage -->
      <div class="ov-grid ov-grid-2">
        <div class="card ov-card">
          <div class="ov-card-head">
            <div>
              <h3 class="ov-card-title"><TrendingUp :size="14" :stroke-width="2"/>Visibility Over Time</h3>
              <p class="ov-card-sub">{{ historyData.length || 0 }} completed audits</p>
            </div>
          </div>
          <div class="ov-chart">
            <Line v-if="historyData.length" :data="trendChartData" :options="trendChartOptions" />
            <div v-else class="ov-empty-inline">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 3v18h18"/><path d="M7 14l4-4 3 3 5-6"/>
              </svg>
              <p>A trend line appears after your first completed audit.</p>
            </div>
          </div>
        </div>

        <div class="card ov-card">
          <div class="ov-card-head">
            <div>
              <h3 class="ov-card-title"><Bot :size="14" :stroke-width="2"/>Model Coverage</h3>
              <p class="ov-card-sub">{{ providerHealth.configured_count }}/{{ providerHealth.total }} configured</p>
            </div>
          </div>
          <div class="ov-models">
            <div
              v-for="p in providerHealth.providers"
              :key="p.key"
              class="ov-model-row"
              :class="{ off: !p.configured }"
            >
              <span class="ov-model-dot" :style="{ background: p.configured ? providerColor(p.key) : 'var(--border-color, #e5e7eb)' }"></span>
              <span class="ov-model-name">{{ p.name.split('(')[0].trim() }}</span>
              <span class="ov-model-meta">
                <span v-if="!p.configured" class="ov-tag ov-tag-warn">Not configured</span>
                <span v-else-if="modelMentionRate(p.key) !== null" class="ov-model-rate">{{ modelMentionRate(p.key) }}%</span>
                <span v-else class="ov-tag ov-tag-muted">Ready</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Recent audits -->
      <div class="card ov-card">
        <div class="ov-card-head">
          <div>
            <h3 class="ov-card-title"><History :size="14" :stroke-width="2"/>Recent Audits</h3>
            <p class="ov-card-sub">{{ audits.length }} {{ audits.length === 1 ? 'run' : 'runs' }}</p>
          </div>
          <button v-if="audits.length > 5" class="btn btn-ghost btn-sm" @click="showAllAudits = !showAllAudits">
            {{ showAllAudits ? 'Show recent' : 'Show all' }}
          </button>
        </div>

        <div v-if="!audits.length" class="ov-empty-inline">
          <p>No audits yet. Kick off your first run from the Prompt Library.</p>
        </div>
        <div v-else class="ov-audit-table">
          <div class="ov-audit-head">
            <span>Date</span>
            <span>Score</span>
            <span>Mention Rate</span>
            <span>Queries</span>
            <span>Status</span>
            <span></span>
          </div>
          <div
            v-for="audit in visibleAudits"
            :key="audit.id"
            class="ov-audit-row"
            :class="{ selected: selectedAuditId === audit.id }"
            @click="selectedAuditId = audit.id"
          >
            <span class="ov-audit-date">{{ formatDate(audit.created_at) }}</span>
            <span class="ov-audit-score">
              <strong>{{ audit.overall_score != null ? Math.round(audit.overall_score) : '—' }}</strong>
              <span v-if="audit.overall_score != null" class="text-muted">/100</span>
            </span>
            <span>{{ audit.mention_rate != null ? Math.round(audit.mention_rate) + '%' : '—' }}</span>
            <span class="text-muted">{{ audit.total_queries || 0 }} queries</span>
            <span>
              <span class="ov-status" :class="auditStatusClass(audit.status)">{{ capitalize(audit.status || 'pending') }}</span>
            </span>
            <span class="ov-audit-actions">
              <button
                v-if="audit.status === 'pending' || audit.status === 'failed'"
                class="btn btn-ghost btn-sm"
                @click.stop="runAuditNow(audit)"
                :disabled="runningAuditId === audit.id"
              >
                {{ runningAuditId === audit.id ? 'Running…' : 'Run' }}
              </button>
              <button
                class="btn btn-ghost btn-sm ov-audit-delete"
                aria-label="Delete audit"
                @click.stop="confirmDeleteId = audit.id"
              >×</button>
            </span>
          </div>
        </div>
      </div>

      <!-- Usage -->
      <div v-if="usageData" class="card ov-card">
        <div class="ov-card-head">
          <div>
            <h3 class="ov-card-title"><Coins :size="14" :stroke-width="2"/>Usage</h3>
            <p class="ov-card-sub">Last {{ usageDays }} days</p>
          </div>
          <select v-model.number="usageDays" class="ov-select" @change="loadUsage">
            <option :value="7">Last 7 days</option>
            <option :value="30">Last 30 days</option>
            <option :value="90">Last 90 days</option>
          </select>
        </div>

        <div class="ov-usage-totals">
          <div class="ov-usage-cell">
            <div class="ov-usage-val">{{ usageData.totals.calls }}</div>
            <div class="ov-usage-label">API Calls</div>
          </div>
          <div class="ov-usage-cell">
            <div class="ov-usage-val">{{ formatTokens(usageData.totals.total_tokens) }}</div>
            <div class="ov-usage-label">Tokens</div>
          </div>
          <div class="ov-usage-cell">
            <div class="ov-usage-val">${{ usageData.totals.estimated_cost_usd.toFixed(2) }}</div>
            <div class="ov-usage-label">Estimated Cost</div>
          </div>
          <div class="ov-usage-cell">
            <div class="ov-usage-val">{{ usageData.audit_stats.total_audits }}</div>
            <div class="ov-usage-label">Audits</div>
          </div>
        </div>

        <div v-if="usageData.by_model && usageData.by_model.length" class="ov-usage-models">
          <div class="ov-usage-models-head">
            <span>Model</span><span>Calls</span><span>Tokens</span><span>Cost</span>
          </div>
          <div v-for="m in usageData.by_model" :key="m.model_name" class="ov-usage-models-row">
            <span class="ov-usage-model-name">{{ m.model_name }}</span>
            <span>{{ m.calls }}</span>
            <span>{{ formatTokens(m.tokens) }}</span>
            <span>${{ Number(m.cost || 0).toFixed(4) }}</span>
          </div>
        </div>
      </div>

      </template>
    </div><!-- /overview tab -->

    <div v-show="activeTab === 'performance'" class="lr-performance">
      <!-- Empty state when there's nothing to chart yet. The Overview tab
           handles the truly-empty website (no audits at all); this branch
           covers the case where audits exist but haven't completed. -->
      <div v-if="!perfHasData" class="perf-empty">
        <div class="perf-empty-icon" aria-hidden="true">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 3v18h18"/>
            <path d="M7 14l4-4 3 3 5-6"/>
          </svg>
        </div>
        <h3>No model performance data yet</h3>
        <p>Charts appear once at least one audit finishes. Kick off a run from the Prompt Library to start collecting data.</p>
      </div>

      <template v-else>
        <!-- KPI strip: one-glance summary of the latest model run. -->
        <div class="perf-kpis">
          <div class="perf-kpi">
            <div class="perf-kpi-label">Overall visibility</div>
            <div class="perf-kpi-value">{{ perfKpis.overallScore }}<span class="perf-kpi-unit">/100</span></div>
            <div class="perf-kpi-sub" :class="perfKpis.scoreTrendClass">{{ perfKpis.scoreTrendLabel }}</div>
          </div>
          <div class="perf-kpi">
            <div class="perf-kpi-label">Mention rate</div>
            <div class="perf-kpi-value">{{ perfKpis.mentionRate }}<span class="perf-kpi-unit">%</span></div>
            <div class="perf-kpi-sub">across {{ perfKpis.totalQueries }} queries</div>
          </div>
          <div class="perf-kpi">
            <div class="perf-kpi-label">Top model</div>
            <div class="perf-kpi-value perf-kpi-value-sm">{{ perfKpis.topProvider || '—' }}</div>
            <div class="perf-kpi-sub">{{ perfKpis.topProviderRate }}% mention rate</div>
          </div>
          <div class="perf-kpi">
            <div class="perf-kpi-label">Models tested</div>
            <div class="perf-kpi-value">{{ perfKpis.providerCount }}</div>
            <div class="perf-kpi-sub">{{ perfKpis.successfulProviders }} returning mentions</div>
          </div>
        </div>

        <!-- Row 1: provider comparison (bar) + visibility trend (line) -->
        <div class="perf-grid">
          <div class="card perf-card">
            <div class="perf-card-head">
              <h3>Mention rate by model</h3>
              <span class="perf-card-sub">Latest audit</span>
            </div>
            <div class="perf-chart">
              <Bar :data="providerChartData" :options="providerChartOptions" />
            </div>
          </div>
          <div class="card perf-card">
            <div class="perf-card-head">
              <h3>Visibility over time</h3>
              <span class="perf-card-sub">{{ historyData.length }} audits</span>
            </div>
            <div class="perf-chart">
              <Line v-if="historyData.length" :data="trendChartData" :options="trendChartOptions" />
              <div v-else class="perf-chart-empty">A trend line will appear after your second audit.</div>
            </div>
          </div>
        </div>

        <!-- Row 2: per-prompt hit rate by provider (heatmap) + provider agreement -->
        <div class="perf-grid">
          <div class="card perf-card">
            <div class="perf-card-head">
              <h3>Prompt × model heatmap</h3>
              <span class="perf-card-sub">Where each model recommends you</span>
            </div>
            <div class="perf-heatmap">
              <PromptHeatmap
                v-if="latestAudit?.prompts?.length"
                :prompts="latestAudit.prompts"
                :target-name="latestAudit?.business_name || 'You'"
                :provider-label="providerLabel"
                :provider-color="providerColor"
              />
              <div v-else class="perf-chart-empty">No prompt-level results yet.</div>
            </div>
          </div>
          <div class="card perf-card">
            <div class="perf-card-head">
              <h3>Model agreement</h3>
              <span class="perf-card-sub">Do the models tell the same story?</span>
            </div>
            <div class="perf-chart">
              <ProviderAgreement
                v-if="latestBreakdown.length"
                :breakdown="latestBreakdown"
                :provider-label="providerLabel"
              />
              <div v-else class="perf-chart-empty">Need at least two providers with results.</div>
            </div>
          </div>
        </div>

        <!-- Row 3: per-model scorecards -->
        <div class="card perf-card">
          <div class="perf-card-head">
            <h3>Per-model scorecard</h3>
            <span class="perf-card-sub">Latest audit breakdown</span>
          </div>
          <div class="perf-scorecards">
            <div
              v-for="p in latestBreakdown"
              :key="p.provider"
              class="perf-scorecard"
            >
              <div class="perf-scorecard-head">
                <span class="perf-scorecard-dot" :style="{ background: providerColor(p.provider) }"></span>
                <span class="perf-scorecard-name">{{ p.provider_display || providerLabel(p.provider) }}</span>
              </div>
              <div class="perf-scorecard-metric">
                <span class="perf-scorecard-value">{{ Math.round(p.mention_rate || 0) }}%</span>
                <span class="perf-scorecard-label">mention rate</span>
              </div>
              <div class="perf-scorecard-bar">
                <div
                  class="perf-scorecard-bar-fill"
                  :style="{ width: Math.min(100, Math.max(0, p.mention_rate || 0)) + '%', background: providerColor(p.provider) }"
                ></div>
              </div>
              <div class="perf-scorecard-foot">
                <span>{{ p.succeeded || 0 }}/{{ (p.succeeded || 0) + (p.failed || 0) }} queries</span>
                <span v-if="p.failed">· {{ p.failed }} failed</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div><!-- /performance tab -->

    <!-- ═════════════════════════════════════════════════════════════════════
         Pages tab — manage which pages of the project's site get scanned and
         imported into the next model-test run. Reuses the same reactive
         refs (extraPaths, contextUrls) and helpers (addExtraPath,
         addContextUrl) the audit-wizard reads from, so anything selected
         here flows into the next "Run New Audit" without further wiring.
         ═══════════════════════════════════════════════════════════════════ -->
    <div v-show="activeTab === 'pages'" class="lr-pages">
      <!-- Project URL card: shows the existing project-level URL so the user
           always sees what site we're working on. The change-website link
           on the page header still owns the swap action. -->
      <div class="card pages-project">
        <div class="pages-project-head">
          <div class="pages-project-icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <path d="M2 12h20"/>
              <path d="M12 2a15 15 0 0 1 0 20"/>
              <path d="M12 2a15 15 0 0 0 0 20"/>
            </svg>
          </div>
          <div class="pages-project-body">
            <div class="pages-project-label">Project site</div>
            <div class="pages-project-url">
              <a v-if="homepageUrl" :href="homepageUrl" target="_blank" rel="noopener">{{ homepageUrl }}</a>
              <span v-else class="text-muted">No URL on file</span>
            </div>
            <div class="pages-project-meta">
              <strong>{{ websiteName || '—' }}</strong>
              <span class="text-muted" v-if="currentWebsite?.industry">· {{ currentWebsite.industry }}</span>
            </div>
          </div>
          <router-link class="btn btn-ghost btn-sm" to="/websites/">Change site</router-link>
        </div>
      </div>

      <!-- Summary strip: how many pages are queued for the next run. -->
      <div class="pages-summary">
        <div class="pages-summary-cell">
          <div class="pages-summary-val">{{ extraPaths.length }}</div>
          <div class="pages-summary-label">Same-site pages</div>
        </div>
        <div class="pages-summary-cell">
          <div class="pages-summary-val">{{ scannedContextCount }}</div>
          <div class="pages-summary-label">External sources</div>
        </div>
        <div class="pages-summary-cell">
          <div class="pages-summary-val">{{ uploadedDocsReady.length }}</div>
          <div class="pages-summary-label">Uploaded docs</div>
        </div>
        <div class="pages-summary-cell pages-summary-cell-strong">
          <div class="pages-summary-val">{{ importedCount }}</div>
          <div class="pages-summary-label">Will import into next audit</div>
        </div>
        <button class="btn btn-primary btn-sm pages-summary-cta" @click="openRunAudit" :disabled="running">
          {{ running ? 'Running…' : 'Run audit with these pages' }}
        </button>
      </div>

      <div class="ov-grid ov-grid-2">
        <!-- Same-domain sub-paths. Add a path like /pricing or a full URL on
             the same origin; the audit's enrichment will scan each at run
             time. -->
        <div class="card ov-card">
          <div class="ov-card-head">
            <div>
              <h3 class="ov-card-title"><FileText :size="14" :stroke-width="2"/>Pages on your site</h3>
              <p class="ov-card-sub">
                Pull in any path on <strong v-if="homepageOrigin">{{ homepageOrigin }}</strong><span v-else>this domain</span> so models see them when answering buyer-style questions.
              </p>
            </div>
            <span class="pages-count">{{ extraPaths.length }}/20</span>
          </div>
          <form class="pages-input-row" @submit.prevent="addExtraPath">
            <span class="pages-input-prefix" v-if="homepageOrigin">{{ homepageOrigin }}</span>
            <input
              v-model="extraPathInput"
              class="form-input pages-input"
              :placeholder="homepageOrigin ? '/pricing or full URL on same domain' : 'Add a URL'"
              :disabled="!homepageOrigin || extraPaths.length >= 20"
            />
            <button
              type="submit"
              class="btn btn-secondary btn-sm"
              :disabled="!extraPathInput.trim() || !homepageOrigin || extraPaths.length >= 20"
            >Add</button>
          </form>
          <div v-if="!extraPaths.length" class="ov-empty-inline" style="min-height:80px">
            <p>No additional pages yet — root URL is always included.</p>
          </div>
          <div v-else class="pages-list">
            <div v-for="p in extraPaths" :key="p.url" class="pages-list-row">
              <span class="pages-list-icon" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M3 3h7l3 3v7H3z"/><path d="M10 3v3h3"/>
                </svg>
              </span>
              <span class="pages-list-text">
                <span class="pages-list-label">{{ p.label || p.url }}</span>
                <a :href="p.url" target="_blank" rel="noopener" class="pages-list-url">{{ p.url }}</a>
              </span>
              <button
                class="pages-list-remove"
                aria-label="Remove page"
                @click="removeExtraPath(p.url)"
              >×</button>
            </div>
          </div>
        </div>

        <!-- External context URLs — scanned via llmRankingApi.scanUrl so the
             user can see what we'll send into the audit. -->
        <div class="card ov-card">
          <div class="ov-card-head">
            <div>
              <h3 class="ov-card-title"><Link2 :size="14" :stroke-width="2"/>External sources</h3>
              <p class="ov-card-sub">Press, docs, comparison sites — anything off your domain. We'll scan and summarize each.</p>
            </div>
            <span class="pages-count">{{ contextUrls.length }}/5</span>
          </div>
          <form class="pages-input-row" @submit.prevent="addContextUrl">
            <input
              v-model="contextUrlInput"
              class="form-input pages-input"
              placeholder="https://example.com/article"
              :disabled="contextUrls.length >= 5"
            />
            <button
              type="submit"
              class="btn btn-secondary btn-sm"
              :disabled="!contextUrlInput.trim() || contextUrls.length >= 5 || scanningContextUrl"
            >{{ scanningContextUrl ? 'Scanning…' : 'Scan' }}</button>
          </form>
          <div v-if="!contextUrls.length" class="ov-empty-inline" style="min-height:80px">
            <p>No external sources added.</p>
          </div>
          <div v-else class="pages-list">
            <div
              v-for="c in contextUrls"
              :key="c.url"
              class="pages-list-row pages-list-row-tall"
              :class="{ scanning: c.scanning, errored: !c.scanning && !c.success }"
            >
              <span class="pages-list-icon" aria-hidden="true">
                <span v-if="c.scanning" class="pages-list-spinner"></span>
                <svg v-else-if="c.success" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M3 8.5l3 3 7-7"/>
                </svg>
                <svg v-else width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
                  <path d="M4 4l8 8M12 4l-8 8"/>
                </svg>
              </span>
              <span class="pages-list-text">
                <span class="pages-list-label">{{ c.title || c.url }}</span>
                <a :href="c.url" target="_blank" rel="noopener" class="pages-list-url">{{ c.url }}</a>
                <span v-if="c.summary" class="pages-list-summary">{{ c.summary }}</span>
                <span v-if="c.error" class="pages-list-error">{{ c.error }}</span>
              </span>
              <button
                class="pages-list-remove"
                aria-label="Remove source"
                @click="removeContextUrl(c.url)"
              >×</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Uploaded documents card: same upload zone the wizard uses, so
           anything dropped here is immediately queued for the next run. -->
      <div class="card ov-card">
        <div class="ov-card-head">
          <div>
            <h3 class="ov-card-title"><UploadCloud :size="14" :stroke-width="2"/>Uploaded documents</h3>
            <p class="ov-card-sub">Briefs, sheets, or notes you want the models to read alongside your pages.</p>
          </div>
          <span class="pages-count">{{ uploadedDocuments.length }} files</span>
        </div>
        <div
          class="ctx-upload-zone"
          :class="{ dragging: uploadDragging }"
          @dragover.prevent="uploadDragging = true"
          @dragleave="uploadDragging = false"
          @drop.prevent="onContextFileDrop"
          @click="triggerContextUpload"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <path d="M17 8l-5-5-5 5"/>
            <path d="M12 3v12"/>
          </svg>
          <div class="ctx-upload-zone-text">
            <strong>Drag &amp; drop or click to upload</strong>
            <span class="text-muted">.txt, .md, .csv, .json, .html · up to 256 KB each</span>
          </div>
        </div>
        <div v-if="uploadedDocuments.length" class="ctx-uploaded-list" style="margin-top:12px">
          <div
            v-for="doc in uploadedDocuments"
            :key="doc.id"
            class="ctx-uploaded-row"
            :class="{ errored: doc.error }"
          >
            <span class="ctx-uploaded-icon" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M3 2h7l3 3v9H3z"/><path d="M10 2v3h3"/>
              </svg>
            </span>
            <div class="ctx-uploaded-body">
              <div class="ctx-uploaded-name">{{ doc.name }}</div>
              <div class="ctx-uploaded-meta">
                <span>{{ formatBytes(doc.size) }}</span>
                <span v-if="doc.error" class="wizard-scan-error">· {{ doc.error }}</span>
                <span v-else>· {{ doc.charCount }} chars extracted</span>
              </div>
            </div>
            <button class="ctx-uploaded-remove" aria-label="Remove" @click.stop="removeUploadedDoc(doc.id)">×</button>
          </div>
        </div>
      </div>

      <label class="wizard-permission pages-permission">
        <input type="checkbox" v-model="agentScanPermission" />
        <span>
          <strong>I authorize agents to scan these pages</strong> and use the extracted content as context for the next model test on this project. Without permission, only the project root URL is sent.
        </span>
      </label>

      <p class="pages-note">
        These pages are imported into the next model test on this project.
        Click <strong>Run New Audit</strong> in the header to send them to Claude, GPT-4, Gemini, and Perplexity — usage and cost
        are tracked per run on the Overview tab.
      </p>
    </div><!-- /pages tab -->

      <!-- ═══ Provider Detail Modal ═══════════════════════════════════════ -->
      <BaseModal v-model="showProviderDetail" :title="providerDetailData?.provider_display + ' — Detailed Report'" :wide="true">
        <div v-if="providerDetailLoading" class="loading-state" style="padding:24px">Loading...</div>
        <div v-else-if="providerDetailData" class="pd-content">
          <!-- Summary stats -->
          <div class="pd-stats">
            <div class="pd-stat">
              <div class="pd-stat-val" :class="visTier(providerDetailData.summary.mention_rate)">
                {{ providerDetailData.summary.mention_rate }}%
              </div>
              <div class="pd-stat-label">Visibility</div>
            </div>
            <div class="pd-stat">
              <div class="pd-stat-val">{{ providerDetailData.summary.avg_rank ?? '—' }}</div>
              <div class="pd-stat-label">Avg Rank</div>
            </div>
            <div class="pd-stat">
              <div class="pd-stat-val">{{ providerDetailData.summary.mentioned }}/{{ providerDetailData.summary.total_prompts }}</div>
              <div class="pd-stat-label">Mentioned</div>
            </div>
            <div class="pd-stat">
              <div class="pd-stat-val">{{ providerDetailData.summary.avg_confidence }}%</div>
              <div class="pd-stat-label">Confidence</div>
            </div>
          </div>

          <!-- Sentiment breakdown -->
          <div class="pd-section">
            <h4 class="pd-section-title">Sentiment</h4>
            <div class="pd-sentiment-bar">
              <div class="pd-sent-seg positive" :style="{ width: sentPct(providerDetailData, 'positive') + '%' }"
                   :title="'Positive: ' + providerDetailData.summary.sentiments.positive">
                {{ providerDetailData.summary.sentiments.positive }}
              </div>
              <div class="pd-sent-seg neutral" :style="{ width: sentPct(providerDetailData, 'neutral') + '%' }"
                   :title="'Neutral: ' + providerDetailData.summary.sentiments.neutral">
                {{ providerDetailData.summary.sentiments.neutral }}
              </div>
              <div class="pd-sent-seg negative" :style="{ width: sentPct(providerDetailData, 'negative') + '%' }"
                   :title="'Negative: ' + providerDetailData.summary.sentiments.negative">
                {{ providerDetailData.summary.sentiments.negative }}
              </div>
            </div>
          </div>

          <!-- Top Competitors -->
          <div v-if="providerDetailData.top_competitors.length" class="pd-section">
            <h4 class="pd-section-title">Top Competitors Mentioned</h4>
            <div class="pd-comp-list">
              <div v-for="c in providerDetailData.top_competitors.slice(0, 5)" :key="c.name" class="pd-comp">
                <span class="pd-comp-name">{{ c.name }}</span>
                <span class="pd-comp-count">{{ c.mentions }}×</span>
              </div>
            </div>
          </div>

          <!-- Per-prompt results -->
          <div class="pd-section">
            <h4 class="pd-section-title">Per-Prompt Results</h4>
            <table class="pr-table">
              <thead>
                <tr>
                  <th style="width:28px">#</th>
                  <th>Prompt</th>
                  <th style="width:72px">Mentioned</th>
                  <th style="width:48px">Rank</th>
                  <th style="width:72px">Sentiment</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="pr in providerDetailData.prompts" :key="pr.index" class="pr-row">
                  <td class="pr-num">{{ pr.index }}</td>
                  <td class="pr-prompt" style="font-size:12px">{{ pr.prompt }}</td>
                  <td>
                    <span v-if="!pr.succeeded" class="badge badge-danger" style="font-size:10px">Error</span>
                    <span v-else-if="pr.mentioned" class="badge badge-success" style="font-size:10px">Yes</span>
                    <span v-else class="badge badge-neutral" style="font-size:10px">No</span>
                  </td>
                  <td class="text-center">{{ pr.rank ?? '—' }}</td>
                  <td>
                    <span class="badge" :class="sentimentBadge(pr.sentiment)" style="font-size:10px;text-transform:capitalize">
                      {{ pr.sentiment_display }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </BaseModal>

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

          <!-- Step 0: Pages to scan (same domain only) -->
          <div v-if="wizardStep === 0" class="wizard-pane">
            <h2 class="wizard-pane-title">Pages to scan</h2>
            <p class="wizard-pane-sub">
              We'll scan <strong>{{ websiteName }}</strong> for this audit.
              Add specific pages you want grounded into the LLMs' context —
              blog posts, product pages, case studies, etc.
              <a href="/websites/" class="wizard-link-inline">Switch website →</a>
            </p>

            <div class="wizard-pages-list">
              <!-- Homepage row, always included, can't be removed -->
              <div class="wizard-page-row is-homepage">
                <span class="wizard-page-icon">⌂</span>
                <div class="wizard-page-meta">
                  <div class="wizard-page-url">{{ homepageUrl || '—' }}</div>
                  <div class="text-xs text-muted">Homepage · always included</div>
                </div>
              </div>
              <!-- User-added sub-paths -->
              <div
                v-for="p in extraPaths"
                :key="p.url"
                class="wizard-page-row"
              >
                <span class="wizard-page-icon">↳</span>
                <div class="wizard-page-meta">
                  <div class="wizard-page-url">{{ p.url }}</div>
                  <div class="text-xs text-muted">Sub-path · {{ p.label }}</div>
                </div>
                <button class="wizard-page-remove" @click="removeExtraPath(p.url)" title="Remove">
                  ×
                </button>
              </div>
            </div>

            <div class="form-group" style="margin-top:12px">
              <label class="form-label">Add a page</label>
              <div class="wizard-scan-row">
                <input
                  v-model="extraPathInput"
                  class="form-input"
                  :placeholder="`/blog or ${homepageOrigin}/products/...`"
                  @keydown.enter.prevent="addExtraPath"
                />
                <button
                  class="btn btn-primary btn-sm"
                  @click="addExtraPath"
                  :disabled="!extraPathInput.trim()"
                >
                  Add
                </button>
              </div>
              <p class="text-xs text-muted" style="margin-top:6px">
                Paths must be on <strong>{{ homepageOrigin || 'this domain' }}</strong>.
                External URLs go in the next step's Context Sources.
              </p>
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
                Region
                <span class="text-muted text-xs">Biases prompts and Perplexity web grounding to this country</span>
              </label>
              <select v-model="auditForm.region" class="form-input">
                <option v-for="opt in REGION_OPTIONS" :key="opt.code" :value="opt.code">
                  {{ opt.label }}
                </option>
              </select>
            </div>
            <div class="form-group" style="margin-top:12px">
              <label class="form-label">
                Description
                <span class="text-muted text-xs">Type or upload — who you serve and what makes you different</span>
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
                <div class="wizard-textarea-actions">
                  <!-- Upload a small text brief and stitch it into the
                       description. Reads .txt / .md / .csv client-side
                       only, capped at the same 500-char limit as the
                       textarea so the payload stays predictable. -->
                  <input
                    ref="descriptionUploadInput"
                    type="file"
                    accept=".txt,.md,.csv,text/plain,text/markdown"
                    class="visually-hidden"
                    @change="onDescriptionUpload"
                  />
                  <button class="wizard-regen-btn" type="button" @click="triggerDescriptionUpload">
                    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                      <path d="M8 1v10"/><path d="M4 5l4-4 4 4"/><path d="M2 13h12"/>
                    </svg>
                    Upload brief
                  </button>
                  <button class="wizard-regen-btn" type="button" @click="regenerateTopics" :disabled="generatingTopics">
                    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                      <path d="M2 8a6 6 0 0110.9-3.5M14 8A6 6 0 013.1 11.5"/>
                      <path d="M14 2v4h-4M2 14v-4h4"/>
                    </svg>
                    Regenerate Description
                  </button>
                </div>
              </div>
              <p v-if="descriptionUploadStatus" class="text-xs" :class="descriptionUploadStatus.error ? 'wizard-scan-error' : 'text-muted'" style="margin-top:6px">
                {{ descriptionUploadStatus.message }}
              </p>
            </div>

            <!-- Compare-against-prompts panel ──────────────────────────────
                 Lets the user add pages for our agents to read, grant
                 explicit scan permission, and see sample prompts the
                 models will be asked. Writes to the same extraPaths /
                 contextUrls refs the Pages tab and submitAudit use, so
                 nothing is forked. -->
            <div class="wizard-compare">
              <div class="wizard-compare-head">
                <h3 class="wizard-compare-title">Compare your application against the prompts</h3>
                <p class="wizard-compare-sub">
                  Point our agents at the pages they should learn from. We'll scan each one before sending the questions below to Claude, GPT-4, Gemini, and Perplexity, then show you where you surface.
                </p>
              </div>

              <div class="wizard-compare-grid">
                <!-- LEFT: pages we'll scan -->
                <div class="wizard-compare-col">
                  <div class="wizard-compare-col-head">
                    <span class="wizard-compare-col-label">Pages our agents will read</span>
                    <span class="text-xs text-muted">{{ wizardImportedCount }} queued</span>
                  </div>

                  <div class="wizard-scan-list">
                    <div class="wizard-scan-row wizard-scan-row-root">
                      <span class="wizard-scan-pill">Root</span>
                      <span class="wizard-scan-url">
                        <a v-if="homepageUrl" :href="homepageUrl" target="_blank" rel="noopener">{{ homepageUrl }}</a>
                        <span v-else class="text-muted">No project URL on file</span>
                      </span>
                    </div>
                    <div v-for="p in extraPaths" :key="p.url" class="wizard-scan-row">
                      <span class="wizard-scan-pill wizard-scan-pill-same">Same site</span>
                      <span class="wizard-scan-url">
                        <a :href="p.url" target="_blank" rel="noopener">{{ p.label || p.url }}</a>
                      </span>
                      <button class="wizard-scan-remove" aria-label="Remove" @click="removeExtraPath(p.url)">×</button>
                    </div>
                    <div
                      v-for="c in contextUrls"
                      :key="c.url"
                      class="wizard-scan-row"
                      :class="{ scanning: c.scanning, errored: !c.scanning && !c.success }"
                    >
                      <span class="wizard-scan-pill wizard-scan-pill-ext">External</span>
                      <span class="wizard-scan-url">
                        <a :href="c.url" target="_blank" rel="noopener">{{ c.title || c.url }}</a>
                        <span v-if="c.scanning" class="text-xs text-muted">· scanning…</span>
                        <span v-else-if="c.error" class="text-xs wizard-scan-error">· {{ c.error }}</span>
                      </span>
                      <button class="wizard-scan-remove" aria-label="Remove" @click="removeContextUrl(c.url)">×</button>
                    </div>
                  </div>

                  <form class="wizard-scan-add" @submit.prevent="addQuickPage">
                    <input
                      v-model="quickPageInput"
                      class="form-input"
                      :placeholder="quickPagePlaceholder"
                    />
                    <button
                      type="submit"
                      class="btn btn-secondary btn-sm"
                      :disabled="!quickPageInput.trim() || scanningContextUrl"
                    >{{ scanningContextUrl ? 'Scanning…' : 'Add page' }}</button>
                  </form>
                  <p v-if="quickPageError" class="wizard-scan-error" style="margin:6px 0 0">{{ quickPageError }}</p>

                  <label class="wizard-permission">
                    <input type="checkbox" v-model="agentScanPermission" />
                    <span>
                      <strong>I authorize agents to scan these pages</strong> and use the extracted content as context for this model test.
                    </span>
                  </label>
                </div>

                <!-- RIGHT: sample prompts we'll compare against -->
                <div class="wizard-compare-col">
                  <div class="wizard-compare-col-head">
                    <span class="wizard-compare-col-label">Sample prompts we'll compare against</span>
                    <span class="text-xs text-muted">{{ samplePrompts.length }} previews</span>
                  </div>

                  <ul class="wizard-prompt-preview-list">
                    <li v-for="(sp, i) in samplePrompts" :key="i" class="wizard-prompt-preview-row">
                      <span class="wizard-prompt-preview-num">{{ i + 1 }}</span>
                      <div class="wizard-prompt-preview-body">
                        <span class="wizard-prompt-preview-text">"{{ sp.text }}"</span>
                        <span class="wizard-prompt-preview-meta">{{ sp.intent }} · {{ sp.funnel }}</span>
                      </div>
                    </li>
                  </ul>
                  <p class="wizard-compare-foot">
                    The full prompt set is finalized in the <strong>Topics</strong> step. Each model's answer is then compared against your description and the pages above.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Step 2: Context Sources — add extra URLs for richer LLM evaluation -->
          <div v-if="wizardStep === 2" class="wizard-pane">
            <h2 class="wizard-pane-title">Add context sources</h2>
            <p class="wizard-pane-sub">
              Connect a cloud source or paste URLs so our agents can read more about
              what we're prompting against. The content feeds into every model
              that answers your prompts.
            </p>

            <!-- Drag-and-drop / click-to-pick upload zone. Reads each
                 file client-side (.txt / .md / .csv / .json / .html),
                 caps the per-file size, and adds the parsed text to
                 uploadedDocuments. The backend receives them on submit
                 via the inline_documents field. -->
            <div
              class="ctx-upload-zone"
              :class="{ dragging: uploadDragging }"
              @dragover.prevent="uploadDragging = true"
              @dragleave="uploadDragging = false"
              @drop.prevent="onContextFileDrop"
              @click="triggerContextUpload"
            >
              <input
                ref="contextUploadInput"
                type="file"
                multiple
                accept=".txt,.md,.csv,.json,.html,text/plain,text/markdown,text/csv,application/json,text/html"
                class="visually-hidden"
                @change="onContextFilePick"
              />
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <path d="M17 8l-5-5-5 5"/>
                <path d="M12 3v12"/>
              </svg>
              <div class="ctx-upload-zone-text">
                <strong>Drag &amp; drop files here</strong>
                <span class="text-muted">or click to pick · .txt, .md, .csv, .json, .html · up to 256 KB each</span>
              </div>
            </div>

            <div v-if="uploadedDocuments.length" class="ctx-uploaded-list">
              <div
                v-for="(doc, idx) in uploadedDocuments"
                :key="doc.id"
                class="ctx-uploaded-row"
                :class="{ errored: doc.error }"
              >
                <span class="ctx-uploaded-icon" aria-hidden="true">
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M3 2h7l3 3v9H3z"/><path d="M10 2v3h3"/>
                  </svg>
                </span>
                <div class="ctx-uploaded-body">
                  <div class="ctx-uploaded-name">{{ doc.name }}</div>
                  <div class="ctx-uploaded-meta">
                    <span>{{ formatBytes(doc.size) }}</span>
                    <span v-if="doc.error" class="wizard-scan-error">· {{ doc.error }}</span>
                    <span v-else>· {{ doc.charCount }} chars extracted</span>
                  </div>
                </div>
                <button
                  type="button"
                  class="ctx-uploaded-remove"
                  aria-label="Remove file"
                  @click.stop="removeUploadedDoc(doc.id)"
                >×</button>
              </div>
            </div>

            <!-- Connector strip is purely informational — direct OAuth sync
                 is on the roadmap. Clicking a card still opens the local
                 file picker so the workflow keeps moving. -->
            <div class="ctx-connectors">
              <button
                v-for="conn in cloudConnectors"
                :key="conn.key"
                type="button"
                class="ctx-connector"
                @click="onConnectorClick(conn)"
              >
                <span class="ctx-connector-logo" v-html="conn.logo"></span>
                <span class="ctx-connector-body">
                  <span class="ctx-connector-name">{{ conn.name }}</span>
                  <span class="ctx-connector-desc">{{ conn.desc }}</span>
                </span>
                <span class="ctx-connector-status">Upload</span>
              </button>
            </div>

            <div class="ctx-divider"><span>or paste a URL</span></div>

            <div class="ctx-url-input-row">
              <input
                v-model="contextUrlInput"
                class="form-input"
                placeholder="https://blog.example.com/our-latest-feature"
                @keydown.enter.prevent="addContextUrl"
                :disabled="scanningContextUrl"
              />
              <button
                class="btn btn-primary btn-sm"
                @click="addContextUrl"
                :disabled="scanningContextUrl || !contextUrlInput.trim() || contextUrls.length >= 5"
              >
                {{ scanningContextUrl ? 'Scanning...' : '+ Add' }}
              </button>
            </div>

            <div v-if="contextUrls.length" class="ctx-url-list">
              <div
                v-for="(cu, idx) in contextUrls"
                :key="cu.url"
                class="ctx-url-card"
                :class="{ 'is-error': !cu.success && !cu.scanning }"
              >
                <div v-if="cu.scanning" class="ctx-url-scanning">
                  <div class="wizard-scan-spinner" style="width:18px;height:18px;border-width:2px"></div>
                  <span class="text-xs text-muted">Scanning {{ cu.url.slice(0, 50) }}...</span>
                </div>
                <template v-else>
                  <div class="ctx-url-status">
                    <svg v-if="cu.success" width="14" height="14" viewBox="0 0 16 16" fill="#10b981">
                      <circle cx="8" cy="8" r="8"/>
                      <path d="M5 8l2 2 4-4" stroke="#fff" stroke-width="1.5" fill="none"/>
                    </svg>
                    <svg v-else width="14" height="14" viewBox="0 0 16 16" fill="#EF4444">
                      <circle cx="8" cy="8" r="8"/>
                      <path d="M5 5l6 6M11 5l-6 6" stroke="#fff" stroke-width="1.5"/>
                    </svg>
                  </div>
                  <div class="ctx-url-info">
                    <div class="ctx-url-title">{{ cu.title || cu.url.slice(0, 60) }}</div>
                    <div class="ctx-url-summary text-xs text-muted">{{ cu.summary || cu.error || 'No content extracted' }}</div>
                  </div>
                  <button class="ctx-url-remove" @click="contextUrls.splice(idx, 1)">&times;</button>
                </template>
              </div>
            </div>

            <p class="text-xs text-muted" style="margin-top:12px;text-align:center">
              {{ contextUrls.length }}/5 context sources added · <em>This step is optional</em>
            </p>
          </div>

          <!-- Step 3: Topics — "What do you want to show up on ChatGPT for?" -->
          <div v-if="wizardStep === 3" class="wizard-pane">
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

          <!-- Step 4: Competitors -->
          <div v-if="wizardStep === 4" class="wizard-pane">
            <h2 class="wizard-pane-title">Add Your Competitors</h2>
            <p class="wizard-pane-sub">Track up to 20 competitors to monitor your relative AI visibility. We've surfaced names co-mentioned with you in past audits — tap to add.</p>

            <!-- Auto-suggested competitors: pulled from competitors_mentioned
                 on prior audit responses. Clicking a chip adds it to the
                 form's competitor list and removes it from the suggestion
                 strip so the user sees forward progress. -->
            <div v-if="suggestedCompetitors.length" class="wc-suggestions">
              <span class="wc-suggestions-label">Suggested from past audits:</span>
              <div class="wc-suggestions-chips">
                <button
                  v-for="c in suggestedCompetitors"
                  :key="c.name"
                  type="button"
                  class="wc-suggestion-chip"
                  @click="addSuggestedCompetitor(c)"
                  :disabled="auditForm.competitors.length >= 20"
                >
                  <span>+ {{ c.name }}</span>
                  <span class="wc-suggestion-count">{{ c.count }}× mentioned</span>
                </button>
              </div>
            </div>

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

          <!-- Step 5: Providers -->
          <div v-if="wizardStep === 5" class="wizard-pane">
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

          <!-- Step 6: Review -->
          <div v-if="wizardStep === 6" class="wizard-pane">
            <h2 class="wizard-pane-title">Review &amp; run your audit</h2>
            <p class="wizard-pane-sub">Here's the estimated cost, how we'll run this, and how your sources connect to what we'll measure.</p>

            <!-- Run flow: sources → models → prompts → results. The arrows
                 visualise the pipeline so the user understands what
                 happens when they hit "Start audit" instead of seeing a
                 flat list of metadata. -->
            <div class="wizard-flow" aria-label="Audit run flow">
              <div class="wizard-flow-stage">
                <div class="wizard-flow-icon wizard-flow-icon-src" aria-hidden="true">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <path d="M14 2v6h6"/>
                  </svg>
                </div>
                <div class="wizard-flow-label">Sources</div>
                <div class="wizard-flow-count">{{ 1 + extraPaths.length + contextUrls.filter(c => c.success).length + uploadedDocsReady.length }}</div>
                <div class="wizard-flow-sub">root + {{ extraPaths.length }} pages + {{ contextUrls.filter(c => c.success).length }} external + {{ uploadedDocsReady.length }} uploads</div>
              </div>
              <div class="wizard-flow-arrow" aria-hidden="true">→</div>
              <div class="wizard-flow-stage">
                <div class="wizard-flow-icon wizard-flow-icon-prompt" aria-hidden="true">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                </div>
                <div class="wizard-flow-label">Prompts</div>
                <div class="wizard-flow-count">{{ flowPromptCount }}</div>
                <div class="wizard-flow-sub">{{ auditForm.selectedTopics.length }} topics × intents</div>
              </div>
              <div class="wizard-flow-arrow" aria-hidden="true">→</div>
              <div class="wizard-flow-stage">
                <div class="wizard-flow-icon wizard-flow-icon-models" aria-hidden="true">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="3" width="7" height="7" rx="1"/>
                    <rect x="14" y="3" width="7" height="7" rx="1"/>
                    <rect x="3" y="14" width="7" height="7" rx="1"/>
                    <rect x="14" y="14" width="7" height="7" rx="1"/>
                  </svg>
                </div>
                <div class="wizard-flow-label">Models</div>
                <div class="wizard-flow-count">{{ auditForm.providers.length }}</div>
                <div class="wizard-flow-sub">{{ auditForm.providers.map(providerLabel).join(', ') || 'None selected' }}</div>
              </div>
              <div class="wizard-flow-arrow" aria-hidden="true">→</div>
              <div class="wizard-flow-stage">
                <div class="wizard-flow-icon wizard-flow-icon-result" aria-hidden="true">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 3v18h18"/>
                    <path d="M7 14l4-4 3 3 5-6"/>
                  </svg>
                </div>
                <div class="wizard-flow-label">Results</div>
                <div class="wizard-flow-count">{{ flowQueryCount }}</div>
                <div class="wizard-flow-sub">queries · scored &amp; trended</div>
              </div>
            </div>

            <p class="wizard-flow-note text-xs text-muted">
              Each source is scanned before the prompts run, so models see your
              latest copy. Every query is logged and added to your usage on the
              Overview tab.
            </p>

            <div class="wizard-review-grid">
              <div class="wizard-review-item">
                <span class="wizard-review-label">Website</span>
                <span class="wizard-review-value">{{ websiteName }}</span>
              </div>
              <div class="wizard-review-item">
                <span class="wizard-review-label">Pages scanned</span>
                <span class="wizard-review-value">{{ 1 + extraPaths.length }} ({{ extraPaths.length }} extra)</span>
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
              <div class="wizard-review-item">
                <span class="wizard-review-label">Context Sources</span>
                <span class="wizard-review-value">
                  {{ contextUrls.filter(c => c.success).length }} URLs · {{ uploadedDocsReady.length }} uploads
                </span>
              </div>
              <div class="wizard-review-item wizard-review-cost" :class="{ 'over-cap': preflight && preflight.cap_status.would_exceed }">
                <span class="wizard-review-label">Estimated cost</span>
                <span v-if="preflightLoading" class="wizard-review-value">Estimating…</span>
                <span v-else-if="preflight" class="wizard-review-value">
                  ${{ preflight.estimate.cost_usd.toFixed(4) }}
                  <span class="wizard-review-cost-sub">
                    (${{ preflight.estimate.cost_usd_low.toFixed(4) }} – ${{ preflight.estimate.cost_usd_high.toFixed(4) }},
                    {{ preflight.queries }} queries,
                    {{ preflight.method === 'historical' ? 'from your history' : 'default rates' }})
                  </span>
                </span>
                <span v-else class="wizard-review-value">—</span>
              </div>
            </div>
            <p v-if="preflight && preflight.cap_status.would_exceed" class="form-error" style="margin-top:6px">
              This audit would push your month-to-date spend past your cap of
              ${{ Number(preflight.cap_status.cap_usd).toFixed(2) }} (currently
              ${{ Number(preflight.cap_status.spent_usd).toFixed(2) }}). Raise the cap in Settings to proceed.
            </p>

            <div class="form-group" style="margin-top:16px">
              <label class="form-label">Prompt source</label>
              <PromptSourceToggle v-model="promptSource" />
              <button
                v-if="promptSource !== 'vault'"
                type="button"
                class="btn btn-link"
                style="margin-top:6px;padding:0;font-size:12px"
                @click="previewOpen = true"
              >
                Preview prompts
              </button>
              <p v-if="previewedPrompts.length" class="text-xs text-muted" style="margin-top:4px">
                {{ previewedPrompts.length }} prompts selected from preview.
              </p>
            </div>

            <PromptPreviewDrawer
              v-model:open="previewOpen"
              :industry-id="auditForm.industry_id || null"
              :n="50"
              @confirm="onPreviewConfirm"
            />

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

    <!-- Schedule Modal -->
    <BaseModal v-model="showScheduleModal" title="Schedule Periodic Audits">
      <p class="text-sm text-muted" style="margin-bottom:16px;line-height:1.5">
        Automatically run LLM ranking audits on a schedule so you can track visibility trends without manual effort.
      </p>
      <div class="form-group">
        <label class="form-label">Business Name</label>
        <input v-model="scheduleForm.business_name" class="form-input" placeholder="e.g. Acme Corp" />
      </div>
      <div class="form-group" style="margin-top:12px">
        <label class="form-label">Industry</label>
        <input v-model="scheduleForm.industry" class="form-input" placeholder="e.g. SaaS, marketing" />
      </div>
      <div class="form-group" style="margin-top:12px">
        <label class="form-label">Location (optional)</label>
        <input v-model="scheduleForm.location" class="form-input" placeholder="e.g. US, Europe" />
      </div>
      <div class="form-group" style="margin-top:12px">
        <label class="form-label">Frequency</label>
        <select v-model="scheduleForm.frequency" class="form-input">
          <option value="weekly">Weekly</option>
          <option value="biweekly">Every 2 Weeks</option>
          <option value="monthly">Monthly</option>
        </select>
      </div>
      <div class="form-group" style="margin-top:12px">
        <label class="form-label">Providers</label>
        <div class="provider-checks">
          <label v-for="p in availableProviders" :key="p.value" class="check-label">
            <input type="checkbox" :value="p.value" v-model="scheduleForm.providers" />
            {{ p.label }}
          </label>
        </div>
      </div>
      <p v-if="scheduleError" class="form-error" style="margin-top:8px">{{ scheduleError }}</p>
      <template #footer>
        <button v-if="schedule" class="btn btn-danger" @click="deleteSchedule" style="margin-right:auto">Remove Schedule</button>
        <button class="btn btn-secondary" @click="showScheduleModal = false">Cancel</button>
        <button class="btn btn-primary" @click="saveSchedule" :disabled="savingSchedule">
          {{ savingSchedule ? 'Saving...' : 'Save Schedule' }}
        </button>
      </template>
    </BaseModal>

    <!-- Cap-exceeded modal: HTTP 402 from /audits/. Surfaces as a clear
         action ("raise the cap") instead of a generic error banner. -->
    <BaseModal
      v-if="capExceededModal"
      :model-value="!!capExceededModal"
      title="Monthly AI spend cap reached"
      @update:model-value="capExceededModal = null"
      @close="capExceededModal = null"
    >
      <div class="cap-modal-body">
        <p class="cap-modal-msg">
          Month-to-date AI spend
          <strong>${{ Number(capExceededModal.spent).toFixed(2) }}</strong>
          has reached your cap of
          <strong>${{ Number(capExceededModal.cap).toFixed(2) }}</strong>.
        </p>
        <p class="cap-modal-help">
          {{ capExceededModal.detail }}
        </p>
      </div>
      <template #footer>
        <button class="btn btn-secondary" @click="capExceededModal = null">Close</button>
        <router-link class="btn btn-primary" to="/settings" @click="capExceededModal = null">
          Go to Settings
        </router-link>
      </template>
    </BaseModal>
    </template>

    <CitationsDrawer
      v-model:open="citationsDrawerOpen"
      :citations="citationsDrawerCitations"
      :provider="citationsDrawerProvider"
      :prompt="citationsDrawerPrompt"
    />
  </div>
</template>

<script setup>
import { ref, shallowRef, computed, onMounted, onBeforeUnmount, markRaw, nextTick, watch } from 'vue'
import {
  Activity, Bot, CalendarClock, Coins, FileText, Globe, History,
  Link2, Play, TrendingUp, UploadCloud,
} from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { useAppStore } from '@/stores/app'
import llmRankingApi from '@/api/llm_ranking'
import websitesApi from '@/api/websites'
import promptLibraryApi from '@/api/promptLibrary'
import BaseModal from '@/components/ui/BaseModal.vue'
import PromptHeatmap from '@/components/llm_ranking/PromptHeatmap.vue'
import ProviderAgreement from '@/components/llm_ranking/ProviderAgreement.vue'
import PromptSourceToggle from '@/components/llm_ranking/PromptSourceToggle.vue'
import PromptPreviewDrawer from '@/components/llm_ranking/PromptPreviewDrawer.vue'
import citationsApi from '@/api/citations'
import CitationsDrawer from '@/components/citations/CitationsDrawer.vue'
import { Line, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, Filler, Tooltip, Legend,
} from 'chart.js'

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, Filler, Tooltip, Legend,
)

ChartJS.defaults.color = '#8a8a9a'
ChartJS.defaults.font.family = "'Inter', 'SF Pro Display', system-ui, sans-serif"
ChartJS.defaults.font.size = 11

const route = useRoute()
const router = useRouter()
const websiteId = route.params.websiteId
const toast = useToast()
const appStore = useAppStore()
const activeWebsite = computed(() => appStore.activeWebsite)

const audits = shallowRef([])
const history = shallowRef([])
const providerHealth = shallowRef({ providers: [], configured_count: 0, total: 0 })
const loading = ref(true)
const running = ref(false)
const showRunForm = ref(false)
const auditError = ref('')
const capExceededModal = ref(null)
const selectedAuditId = ref(null)
const latestBreakdown = shallowRef([])
const recommendations = shallowRef([])
const auditDetail = shallowRef(null)
// Citations state (Phase 2). Populated by loadCitations() on audit selection.
const citationsByResult = shallowRef(new Map())
const auditSourceInfluence = shallowRef(null)
const citationsDrawerOpen = ref(false)
const citationsDrawerCitations = ref([])
const citationsDrawerProvider = ref('')
const citationsDrawerPrompt = ref('')
const showFindings = ref(true)
const showMethodology = ref(false)
const showPrompts = ref(true)
const showAuditLog = ref(true)
const showSystemsDropdown = ref(false)
const showScoreDetail = ref(false)
const expandedAuditId = ref(null)
const confirmDeleteId = ref(null)
const historyData = ref([])
const runningAuditId = ref(null)

// Prompt source dispatcher state for the Run Audit wizard.
const promptSource = ref('hybrid')
const previewOpen = ref(false)
const previewedPrompts = ref([])

function onPreviewConfirm(payload) {
  // PromptPreviewDrawer emits { prompts, seed } on confirm.
  previewedPrompts.value = payload?.prompts || []
}

function formatLabel(label) {
  if (!label) return 'Vault'
  const [head, tail] = String(label).split(':')
  if (head === 'library') {
    if (tail === 'reddit') return 'Library · Reddit'
    if (tail === 'llm_synth') return 'Library · Synth'
    return tail ? `Library · ${tail}` : 'Library'
  }
  if (head === 'custom') return 'Custom'
  return 'Vault'
}

function badgeClass(label) {
  const head = String(label || 'vault').split(':')[0]
  if (head === 'library') return 'badge-library'
  if (head === 'custom') return 'badge-custom'
  return 'badge-vault'
}

// ── Prompt Results ──
const promptResultsData = shallowRef(null)
const promptFilterProvider = ref('')
const promptFilterType = ref('')

// ── Provider Detail ──
const showProviderDetail = ref(false)
const providerDetailData = shallowRef(null)
const providerDetailLoading = ref(false)

// ── Usage Meter ──
const usageData = shallowRef(null)
const usageDays = ref(30)

async function loadPromptResults() {
  const audit = latestAudit.value
  if (!audit || audit.status !== 'completed') return
  try {
    const params = {}
    if (promptFilterProvider.value) params.provider = promptFilterProvider.value
    if (promptFilterType.value) params.type = promptFilterType.value
    const { data } = await llmRankingApi.promptResults(websiteId, audit.id, params)
    promptResultsData.value = data?.data || data
  } catch (e) {
    console.warn('Failed to load prompt results:', e)
  }
}

async function openProviderDetail(provider) {
  const audit = latestAudit.value
  if (!audit || audit.status !== 'completed') return
  showProviderDetail.value = true
  providerDetailLoading.value = true
  providerDetailData.value = null
  try {
    const { data } = await llmRankingApi.providerDetail(websiteId, audit.id, provider)
    providerDetailData.value = data?.data || data
  } catch (e) {
    console.warn('Failed to load provider detail:', e)
    toast.error('Failed to load provider report')
  } finally {
    providerDetailLoading.value = false
  }
}

async function loadUsage() {
  try {
    const { data } = await llmRankingApi.usage(websiteId, { days: usageDays.value })
    usageData.value = data?.data || data
  } catch (e) {
    console.warn('Failed to load usage:', e)
  }
}

function visTier(pct) {
  if (pct >= 60) return 'vis-high'
  if (pct >= 30) return 'vis-mid'
  return 'vis-low'
}

function promptStatusBadge(st) {
  if (st === 'completed') return 'badge-success'
  if (st === 'failed') return 'badge-danger'
  if (st === 'partial') return 'badge-warning'
  return 'badge-neutral'
}

function sentPct(detail, type) {
  const s = detail.summary.sentiments
  const total = (s.positive || 0) + (s.neutral || 0) + (s.negative || 0)
  if (!total) return 0
  return Math.round((s[type] || 0) / total * 100)
}

function formatTokens(n) {
  if (!n) return '0'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

async function executeAuditJob(audit) {
  if (runningAuditId.value) return
  runningAuditId.value = audit.id
  // Optimistically set status to running
  audit.status = 'running'
  toast.info(`Running audit for "${audit.business_name}"…`)
  try {
    const { data } = await llmRankingApi.executeAudit(websiteId, audit.id)
    const result = data?.data || data
    // Update the audit in the list with results
    const idx = audits.value.findIndex(a => a.id === audit.id)
    if (idx >= 0) {
      audits.value[idx] = { ...audits.value[idx], ...result }
    }
    toast.success(`Audit completed! Score: ${result.overall_score}/100`)
    // Auto-select and expand
    await selectAudit(audits.value[idx] || result)
    expandedAuditId.value = audit.id
  } catch (err) {
    audit.status = 'failed'
    audit.error_message = err.displayMessage || err.message || 'Audit failed'
    toast.error(err.displayMessage || 'Audit execution failed. Check API keys.')
  } finally {
    runningAuditId.value = null
  }
}

function toggleAuditExpand(audit) {
  if (expandedAuditId.value === audit.id) {
    expandedAuditId.value = null
  } else {
    expandedAuditId.value = audit.id
    selectAudit(audit)
  }
}

function getPromptMentioned(audit, promptIndex) {
  // Check if this prompt got a mention in any provider's results
  if (!auditDetail.value || !auditDetail.value.results) return false
  const prompt = (audit.prompts || [])[promptIndex]
  if (!prompt) return false
  return auditDetail.value.results.some(r =>
    r.prompt === prompt && r.is_mentioned
  )
}

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
function classifyIntent(prompt) {
  // Old audits stored prompts as plain strings; new audits store
  // {text, type, funnel_stage, rationale} dicts. Handle both.
  if (prompt && typeof prompt === 'object') {
    return prompt.type || classifyIntent(prompt.text || '')
  }
  const lower = String(prompt || '').toLowerCase()
  for (const { intent, keywords } of INTENT_PATTERNS) {
    if (keywords.some(k => lower.includes(k))) return intent
  }
  return 'custom'
}

// Extract the plain text out of a stored prompt entry so v-text rendering
// never produces "[object Object]" for new-format dict prompts.
function promptText(prompt) {
  if (prompt && typeof prompt === 'object') return prompt.text || ''
  return String(prompt || '')
}

// Extract the rationale (or empty string) — only present on prompts
// generated after the funnel-stage tagging change.
function promptRationale(prompt) {
  return prompt && typeof prompt === 'object' ? (prompt.rationale || '') : ''
}

// Funnel-stage label. Prefer the stored value, fall back to the
// intent → stage mapping for old-format prompts.
const STAGE_TO_LABEL = {
  bottom: 'Bottom of Funnel',
  mid:    'Mid Funnel',
  top:    'Top of Funnel',
  niche:  'Niche / Long-Tail',
}
function promptStageLabel(prompt, intent) {
  let stage
  if (prompt && typeof prompt === 'object' && prompt.funnel_stage) {
    stage = prompt.funnel_stage
  } else {
    stage = INTENT_TO_FUNNEL[intent] || 'niche'
  }
  return STAGE_TO_LABEL[stage] || ''
}
const promptIntents = computed(() =>
  (latestAudit.value?.prompts || []).map(classifyIntent)
)
let pollTimer = null

// Schedule state
const schedule = ref(null)
const scheduleETA = ref(null)
const runNowBusy = ref(false)
let scheduleETATimer = null
const showScheduleModal = ref(false)
const savingSchedule = ref(false)
const scheduleError = ref('')
const scheduleForm = ref({
  business_name: '',
  industry: '',
  location: '',
  frequency: 'weekly',
  providers: ['claude', 'gpt4', 'gemini', 'perplexity'],
})

const customPromptsText = ref('')
// Pre-filled from the route's website on mount. The user does NOT enter
// a URL here — that's the WebsitesListPage's job. We surface the same
// website that the route is for, plus any sub-paths the user wants to
// scan as additional context.
const auditForm = ref({
  business_name: '',
  industry: '',
  location: '',
  region: 'global',
  description: '',
  themes: ['recommendation', 'comparison', 'use_case', 'persona'],
  providers: ['claude', 'gpt4', 'gemini', 'perplexity'],
  selectedTopics: [],
  competitors: [],
})

// The website attached to ``:websiteId`` — falls back to a direct fetch
// if the global store doesn't have it (deep link from email, etc.).
const currentWebsite = ref(null)
const homepageUrl = computed(() => currentWebsite.value?.url || '')
const websiteName = computed(() =>
  currentWebsite.value?.name || currentWebsite.value?.url || 'this website',
)
const homepageOrigin = computed(() => {
  const u = homepageUrl.value
  if (!u) return ''
  try {
    return new URL(u.startsWith('http') ? u : `https://${u}`).origin
  } catch (_) {
    return ''
  }
})

// Sub-paths the user has opted into for this audit. Stored as full URLs,
// validated to be on the same origin as the homepage so we can't
// accidentally turn this into a third-party scrape.
const extraPaths = ref([])              // [{url, label, error}]
const extraPathInput = ref('')

function addExtraPath() {
  const raw = (extraPathInput.value || '').trim()
  if (!raw) return
  let full
  if (raw.startsWith('http://') || raw.startsWith('https://')) {
    full = raw
  } else {
    // Treat as a path or sub-path of the homepage.
    const path = raw.startsWith('/') ? raw : `/${raw}`
    full = `${homepageOrigin.value}${path}`
  }
  let parsed
  try {
    parsed = new URL(full)
  } catch (_) {
    toast.error('Not a valid URL or path.')
    return
  }
  if (parsed.origin !== homepageOrigin.value) {
    toast.error(`Only paths on ${homepageOrigin.value} can be added here.`)
    return
  }
  if (extraPaths.value.some(p => p.url === parsed.href)) {
    return  // already added
  }
  extraPaths.value.push({
    url: parsed.href,
    label: parsed.pathname + (parsed.search || '') || '/',
  })
  extraPathInput.value = ''
}

function removeExtraPath(url) {
  extraPaths.value = extraPaths.value.filter(p => p.url !== url)
}

function removeContextUrl(url) {
  contextUrls.value = contextUrls.value.filter(c => c.url !== url)
}

// Wizard "Compare against prompts" panel ------------------------------------
// Single-input adder that routes a raw value to either the same-domain
// sub-paths list or the external context scanner based on its origin.
const agentScanPermission = ref(false)
const quickPageInput = ref('')
const quickPageError = ref('')
const quickPagePlaceholder = computed(() => homepageOrigin.value
  ? `/pricing or https://blog.example.com/...`
  : 'https://example.com/page')

async function addQuickPage() {
  const raw = (quickPageInput.value || '').trim()
  if (!raw) return
  quickPageError.value = ''

  const origin = homepageOrigin.value
  let isExternal = false
  let normalized = raw
  if (raw.startsWith('http://') || raw.startsWith('https://')) {
    try {
      const parsed = new URL(raw)
      isExternal = !origin || parsed.origin !== origin
      normalized = raw
    } catch (_) {
      quickPageError.value = 'That URL is not valid.'
      return
    }
  } else if (!origin) {
    quickPageError.value = 'Add the project URL first, or paste a full https:// link.'
    return
  }

  if (isExternal) {
    if (contextUrls.value.length >= 5) {
      quickPageError.value = 'You can add up to 5 external sources.'
      return
    }
    contextUrlInput.value = normalized
    await addContextUrl()
  } else {
    if (extraPaths.value.length >= 20) {
      quickPageError.value = 'You can add up to 20 same-site pages.'
      return
    }
    extraPathInput.value = normalized
    addExtraPath()
  }
  quickPageInput.value = ''
}

// Mirror importedCount for use inside the wizard so the two surfaces stay
// in lockstep without coupling templates.
const wizardImportedCount = computed(() =>
  extraPaths.value.length + contextUrls.value.filter(c => c.success).length + uploadedDocsReady.value.length,
)

// Description "Upload brief" — slurps a small text/markdown file into the
// textarea so the user doesn't have to retype an existing brief. Capped
// at the same 500 chars the textarea enforces; anything longer is
// truncated with a clear status line.
const descriptionUploadInput = ref(null)
const descriptionUploadStatus = ref(null)
const DESCRIPTION_MAX = 500
function triggerDescriptionUpload() {
  descriptionUploadInput.value?.click()
}
async function onDescriptionUpload(event) {
  const file = event.target?.files?.[0]
  event.target.value = ''
  if (!file) return
  if (file.size > 256 * 1024) {
    descriptionUploadStatus.value = { error: true, message: 'File is over 256 KB — paste a shorter brief.' }
    return
  }
  try {
    const text = await file.text()
    const clean = text.replace(/\s+/g, ' ').trim()
    const truncated = clean.length > DESCRIPTION_MAX
    auditForm.value.description = clean.slice(0, DESCRIPTION_MAX)
    descriptionUploadStatus.value = {
      error: false,
      message: truncated
        ? `Loaded ${file.name} — trimmed to ${DESCRIPTION_MAX} characters.`
        : `Loaded ${file.name} (${clean.length} characters).`,
    }
  } catch (_) {
    descriptionUploadStatus.value = { error: true, message: 'Could not read the file.' }
  }
}

// Context Sources — cloud connector cards. The OAuth backend isn't wired
// yet, but the UI surfaces the roadmap so users know it's coming and we
// have a place to attach handlers when integrations ship.
const cloudConnectors = Object.freeze([
  {
    key: 'google-drive',
    name: 'Google Drive',
    desc: 'Docs, sheets, briefs',
    enabled: false,
    logo: '<svg width="20" height="20" viewBox="0 0 87 76" fill="none"><path d="M6.6 66.9l3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8H0c0 1.55.4 3.1 1.2 4.5z" fill="#0066DA"/><path d="M43.65 25l-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44A9 9 0 0 0 0 53.05h27.5z" fill="#00AC47"/><path d="M73 76.85c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.5l5.85 11.5z" fill="#EA4335"/><path d="M43.65 25L57.4 1.2A8.9 8.9 0 0 0 52.9 0h-18.5c-1.55 0-3.1.45-4.5 1.2z" fill="#00832D"/><path d="M59.75 53.05h-32.2L13.8 76.85c1.4.8 2.95 1.2 4.5 1.2h50.85c1.55 0 3.1-.45 4.5-1.2z" fill="#2684FC"/><path d="M73 26.5l-12.7-22a9 9 0 0 0-3.3-3.3l-13.75 23.8L59.75 53.05h27.45c0-1.55-.4-3.1-1.2-4.5z" fill="#FFBA00"/></svg>',
  },
  {
    key: 'dropbox',
    name: 'Dropbox',
    desc: 'PDFs, brand kits',
    enabled: false,
    logo: '<svg width="20" height="20" viewBox="0 0 42 40" fill="#0061FF"><path d="M10.5 0L0 6.75l10.5 6.75L21 6.75 10.5 0zm21 0L21 6.75 31.5 13.5 42 6.75 31.5 0zM0 20.25L10.5 27l10.5-6.75-10.5-6.75L0 20.25zm31.5-6.75L21 20.25 31.5 27 42 20.25l-10.5-6.75zM10.5 28.5L21 35.25l10.5-6.75L21 21.75 10.5 28.5z"/></svg>',
  },
  {
    key: 'notion',
    name: 'Notion',
    desc: 'Docs and wikis',
    enabled: false,
    logo: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M4.5 4.4l13.5-1c1.6-.1 2 0 3.1.8L24 6.4c.7.5.9.6.9 1.2v17.1c0 1.2-.4 1.9-1.9 2L8.5 27.6c-1.1.1-1.7-.1-2.3-.9L1.1 20.2C.5 19.3.2 18.7.2 17.9V6.6c0-1 .4-1.8 1.6-1.9 0 0 2.7-.3 2.7-.3z" fill="#fff" transform="scale(0.83)"/><path d="M18 3.4L4.5 4.4c-1.2.1-1.6.9-1.6 1.9l.1 11.3c0 .8.3 1.4.9 2.3l5.1 6.5c.6.8 1.2 1 2.3.9l14.5-.9c1.5-.1 1.9-.8 1.9-2V7.6c0-.6-.2-.7-.9-1.2l-2.9-2.1c-1.1-.8-1.5-.9-3.1-.9zM8.7 7.2c-1.5.1-1.8.1-2.6-.5L4 5c-.2-.2-.1-.4.4-.5L17.4 3.5c1.2-.1 1.9.4 2.4.8l2.4 1.7c.1.1.4.4 0 .4L8.7 7.2zM7.1 24V8.7c0-.7.2-1 .8-1.1l16.1-.9c.6 0 .8.3.8 1V23c0 .7-.1 1.2-1 1.3l-15.4.9c-.9 0-1.3-.3-1.3-1.2zm15.1-14.4c.1.4 0 .8-.4.8l-.7.1V21c-.6.3-1.2.5-1.7.5-.8 0-1-.3-1.6-1l-5-7.7v7.4l1.5.4s0 .8-1.2.8l-3.2.2c-.1-.2 0-.7.4-.8l1-.3V12.6l-1.4-.1c-.1-.4.1-1 .8-1.1l3.4-.2 4.7 7.1V12l-1.2-.1c-.1-.5.3-.9.8-.9l3.8-.2z" fill="#000" transform="scale(0.83)"/></svg>',
  },
  {
    key: 'onedrive',
    name: 'OneDrive',
    desc: 'SharePoint files',
    enabled: false,
    logo: '<svg width="20" height="20" viewBox="0 0 32 32" fill="none"><path d="M22 13a6 6 0 0 0-11.6-2A5 5 0 0 0 6 16a4 4 0 0 0 .5 8h17.4a4.5 4.5 0 0 0 .5-9 4.6 4.6 0 0 0-2.4-2z" fill="#0364B8"/></svg>',
  },
])
function onConnectorClick(conn) {
  // OAuth-backed cloud sync is on the roadmap; for now every connector
  // routes through the same local file picker so the user can still pull
  // a real document into the audit.
  toast.info(`${conn.name} OAuth sync is coming soon. Pick a local file for now.`)
  triggerContextUpload()
}

// Context Sources: local file uploader -----------------------------------
// Reads small text files client-side and stores the extracted body so
// the backend can read it on the audit payload's inline_documents field.
const uploadDragging = ref(false)
const contextUploadInput = ref(null)
const uploadedDocuments = ref([]) // {id, name, size, content, charCount, error}
const UPLOAD_MAX_BYTES = 256 * 1024
const UPLOAD_ACCEPT = /\.(txt|md|csv|json|html?)$/i

let _uploadCounter = 0
function triggerContextUpload() {
  contextUploadInput.value?.click()
}
function onContextFilePick(event) {
  const files = Array.from(event.target?.files || [])
  event.target.value = ''
  ingestUploadedFiles(files)
}
function onContextFileDrop(event) {
  uploadDragging.value = false
  const files = Array.from(event.dataTransfer?.files || [])
  ingestUploadedFiles(files)
}
async function ingestUploadedFiles(files) {
  for (const file of files) {
    const id = `upload-${++_uploadCounter}-${Date.now()}`
    const entry = { id, name: file.name, size: file.size, content: '', charCount: 0, error: '' }
    if (!UPLOAD_ACCEPT.test(file.name)) {
      entry.error = 'Unsupported file type'
      uploadedDocuments.value.push(entry)
      continue
    }
    if (file.size > UPLOAD_MAX_BYTES) {
      entry.error = 'File over 256 KB'
      uploadedDocuments.value.push(entry)
      continue
    }
    try {
      const text = await file.text()
      entry.content = text
      entry.charCount = text.length
    } catch (_) {
      entry.error = 'Could not read file'
    }
    uploadedDocuments.value.push(entry)
  }
}
function removeUploadedDoc(id) {
  uploadedDocuments.value = uploadedDocuments.value.filter(d => d.id !== id)
}
function formatBytes(n) {
  if (!n) return '0 B'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}
const uploadedDocsReady = computed(() => uploadedDocuments.value.filter(d => !d.error && d.content))

// Competitor auto-suggestions — pulled from `competitors_mentioned` on
// prior audit responses. Capped at 8 so the chip strip stays readable;
// already-added competitors are filtered out so users never see "+ X"
// for someone they already track.
const suggestedCompetitors = computed(() => {
  const counts = new Map()
  const results = auditDetail.value?.results || []
  for (const r of results) {
    for (const c of (r.competitors_mentioned || [])) {
      if (!c?.name) continue
      counts.set(c.name, (counts.get(c.name) || 0) + 1)
    }
  }
  const have = new Set((auditForm.value.competitors || []).map(c => (c.name || '').toLowerCase()))
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .filter(c => !have.has(c.name.toLowerCase()))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8)
})
function addSuggestedCompetitor(c) {
  if (auditForm.value.competitors.length >= 20) return
  auditForm.value.competitors.push({ name: c.name, domain: '' })
}

// Review flow stages: estimate the prompt count using preflight when we
// have it, otherwise fall back to a simple "topics × intents" sketch so
// the diagram never shows blank counts.
const flowPromptCount = computed(() => {
  if (preflight.value?.queries && auditForm.value.providers.length) {
    return Math.max(1, Math.round(preflight.value.queries / auditForm.value.providers.length))
  }
  const topics = auditForm.value.selectedTopics.length || 0
  const intents = (auditForm.value.themes || []).length || 1
  return Math.max(topics * intents, 0)
})
const flowQueryCount = computed(() => {
  if (preflight.value?.queries) return preflight.value.queries
  return flowPromptCount.value * Math.max(auditForm.value.providers.length, 1)
})

// Sample prompts shown so the user can mentally compare their app/pages
// against what the AIs will be asked. We surface real prompts when the
// wizard has generated them; otherwise we synthesise three buyer-style
// queries from the current industry/business name so the panel is never
// empty.
const samplePrompts = computed(() => {
  // Real prompts (preview from the dispatcher, if any) take precedence.
  if (previewedPrompts.value?.length) {
    return previewedPrompts.value.slice(0, 3).map(p => ({
      text: p.text || p.prompt || '',
      intent: p.intent || 'recommendation',
      funnel: p.funnel || p.funnel_stage || 'bottom funnel',
    }))
  }
  const industry = (auditForm.value.industry || 'industry').toLowerCase()
  const name = auditForm.value.business_name || 'your business'
  return [
    { text: `What are the best ${industry} tools available right now?`, intent: 'recommendation', funnel: 'bottom funnel' },
    { text: `Compare the top 5 ${industry} platforms and explain their strengths.`, intent: 'comparison', funnel: 'mid funnel' },
    { text: `I need to ${industry}. What tools should I consider for ${name.toLowerCase()}-like needs?`, intent: 'use case', funnel: 'mid funnel' },
  ]
})

// Region catalogue mirrors apps/llm_ranking/services/regions.py. Adding a
// new entry here requires a backend change too — kept short to make the
// drift obvious.
const REGION_OPTIONS = [
  { code: 'global', label: 'Global (no geo bias)' },
  { code: 'us', label: 'United States' },
  { code: 'ca', label: 'Canada' },
  { code: 'in', label: 'India' },
  { code: 'uk', label: 'United Kingdom' },
  { code: 'de', label: 'Germany' },
  { code: 'au', label: 'Australia' },
]
function regionLabel(code) {
  const r = REGION_OPTIONS.find(x => x.code === code)
  return r ? r.label : code
}

// ISO-2 country code -> human label + flag emoji. Kept short — names match
// the keys produced by apps.llm_ranking.services.citation_geo.
const COUNTRY_LABELS = {
  US: 'United States', CA: 'Canada', GB: 'United Kingdom', IN: 'India',
  AU: 'Australia', DE: 'Germany', FR: 'France', ES: 'Spain', IT: 'Italy',
  NL: 'Netherlands', SE: 'Sweden', NO: 'Norway', DK: 'Denmark', FI: 'Finland',
  PL: 'Poland', BR: 'Brazil', MX: 'Mexico', AR: 'Argentina', JP: 'Japan',
  KR: 'South Korea', CN: 'China', RU: 'Russia', TR: 'Turkey', IL: 'Israel',
  AE: 'UAE', SA: 'Saudi Arabia', ZA: 'South Africa', IE: 'Ireland',
  PT: 'Portugal', CH: 'Switzerland', BE: 'Belgium', AT: 'Austria',
  NZ: 'New Zealand', SG: 'Singapore', MY: 'Malaysia', ID: 'Indonesia',
  TH: 'Thailand', VN: 'Vietnam', PH: 'Philippines',
}
function countryLabel(code) {
  return COUNTRY_LABELS[code] || code
}
// Flag emoji from ISO-2 by mapping each letter to its Regional Indicator
// Symbol code point. Pure cosmetic — graceful degrade if the font lacks
// the glyph.
function countryFlag(code) {
  if (!code || code.length !== 2) return ''
  const offset = 0x1F1A5
  return String.fromCodePoint(
    code.toUpperCase().charCodeAt(0) + offset,
    code.toUpperCase().charCodeAt(1) + offset,
  )
}

// ── Wizard state ──
const wizardStep = ref(0)
const wizardTopics = ref([])
const generatingTopics = ref(false)
const competitorInput = ref('')
const competitorDomainInput = ref('')
// scanning + scanResult removed with Step 0 — the wizard no longer
// scans an arbitrary URL; the website's URL is read from the route.

// ── Context Sources state ──
const contextUrls = ref([])      // [{url, title, summary, success, scanning, error}]
const contextUrlInput = ref('')
const scanningContextUrl = ref(false)

async function addContextUrl() {
  const url = contextUrlInput.value.trim()
  if (!url || contextUrls.value.length >= 5) return
  // Prevent duplicates
  if (contextUrls.value.some(c => c.url === url)) return

  const entry = { url, title: '', summary: '', success: false, scanning: true, error: '' }
  contextUrls.value.push(entry)
  contextUrlInput.value = ''
  scanningContextUrl.value = true

  try {
    const { data } = await llmRankingApi.scanUrl(websiteId, url)
    const result = data?.data || data
    entry.success = result.success
    entry.title = result.business_name || ''
    entry.summary = (result.content_summary || result.description || '').slice(0, 200)
    entry.error = result.error || ''
  } catch (err) {
    entry.success = false
    entry.error = 'Failed to scan URL'
  } finally {
    entry.scanning = false
    scanningContextUrl.value = false
  }
}

// Step 0 ("Website") was removed in favour of pre-filling from the
// route's website. The first user-facing step is now the Pages picker —
// the user opts into which sub-paths of the same domain to scan.
const wizardSteps = Object.freeze([
  { id: 'pages', label: 'Pages' },
  { id: 'description', label: 'Description' },
  { id: 'context', label: 'Context Sources' },
  { id: 'topics', label: 'Topics' },
  { id: 'competitors', label: 'Competitors' },
  { id: 'providers', label: 'Models' },
  { id: 'review', label: 'Review' },
])

// scanDomain() removed — the website's URL is read from the route's
// website object via ``loadWebsite()`` below. Scan-on-demand for
// individual sub-paths still happens server-side via ``llmRankingApi.scanUrl``
// in the Context Sources step (separate from this Pages step).

async function loadWebsite() {
  // Prefer the global app store (already loaded during initial nav);
  // fall back to a direct fetch when the user lands here via deep link.
  const fromStore = activeWebsite.value
  if (fromStore && fromStore.id === websiteId) {
    currentWebsite.value = fromStore
  } else {
    try {
      const { data } = await websitesApi.get(websiteId)
      currentWebsite.value = data?.data || data
    } catch (_) {
      currentWebsite.value = null
    }
  }
  // Pre-fill the audit form from the loaded website so the user
  // doesn't have to re-type business name / industry / description.
  const w = currentWebsite.value
  if (w) {
    auditForm.value.business_name = w.name || w.business_name || ''
    auditForm.value.industry = w.industry || ''
    auditForm.value.description = w.description || ''
  }
}

// First-run gate: user lands here before any audit data exists for this
// website. The empty-state card now branches on whether they've already
// saved prompts — if yes, push the Run-Audit CTA; if no, push the
// Prompt Library.
const showFirstRun = computed(() => !loading.value && audits.value.length === 0)
const savedPromptsCount = ref(0)
async function loadSavedPromptsCount() {
  try {
    const { data } = await promptLibraryApi.listBrandPrompts(websiteId)
    const rows = data?.data || data?.results || data || []
    savedPromptsCount.value = Array.isArray(rows) ? rows.length : (rows?.count || 0)
  } catch (_) {
    savedPromptsCount.value = 0
  }
}

// Re-check when this route becomes active again (e.g. after the user
// saves a prompt in the Library tab — keep-alive may keep this page
// mounted, so onMounted alone is not enough).
watch(
  () => route.fullPath,
  (path) => {
    if (path && path.startsWith(`/llm-ranking/${websiteId}`) && !path.includes('/prompts')) {
      loadSavedPromptsCount()
    }
  },
)

// Tabs split the dashboard's two roles: dense Overview (kept as-is) and
// a chart-first Performance view for reading model-by-model results.
const activeTab = ref('overview')

// Performance tab needs a completed audit to chart against. We surface
// whatever the latest one produced rather than guarding on `running`,
// because a partially-failed audit still has plottable provider data.
const perfHasData = computed(() => {
  const a = latestAudit.value
  if (!a) return false
  if (a.status !== 'completed') return false
  return latestBreakdown.value.length > 0
})

const perfKpis = computed(() => {
  const a = latestAudit.value || {}
  const bd = latestBreakdown.value || []
  const succeeded = bd.filter(p => (p.succeeded || 0) > 0)
  const top = [...bd].sort((x, y) => (y.mention_rate || 0) - (x.mention_rate || 0))[0]
  // Trend: compare overall score to the previous completed audit so users
  // can see whether the latest run improved or regressed.
  const completed = (historyData.value || []).filter(h => typeof h.overall_score === 'number')
  const prev = completed.length > 1 ? completed[completed.length - 2] : null
  const delta = prev ? (a.overall_score || 0) - (prev.overall_score || 0) : null
  let scoreTrendLabel = 'First completed audit'
  let scoreTrendClass = 'perf-trend-flat'
  if (delta !== null) {
    if (delta > 0) { scoreTrendLabel = `+${delta.toFixed(1)} vs previous`; scoreTrendClass = 'perf-trend-up' }
    else if (delta < 0) { scoreTrendLabel = `${delta.toFixed(1)} vs previous`; scoreTrendClass = 'perf-trend-down' }
    else { scoreTrendLabel = 'No change vs previous' }
  }
  return {
    overallScore: Math.round(a.overall_score || 0),
    mentionRate: Math.round(a.mention_rate || 0),
    totalQueries: a.total_queries || 0,
    providerCount: (a.providers_queried || []).length || bd.length,
    successfulProviders: succeeded.length,
    topProvider: top ? (top.provider_display || providerLabel(top.provider)) : '',
    topProviderRate: top ? Math.round(top.mention_rate || 0) : 0,
    scoreTrendLabel,
    scoreTrendClass,
  }
})
const promptLibraryRoute = computed(() => `/llm-ranking/${websiteId}/prompts`)
const promptLibraryRepoRoute = computed(() => `/llm-ranking/${websiteId}/prompts?tab=repository`)

// Overview tab helpers ------------------------------------------------------
const showAllAudits = ref(false)
const visibleAudits = computed(() => showAllAudits.value ? audits.value : audits.value.slice(0, 5))

function capitalize(s) {
  if (!s) return ''
  return String(s).charAt(0).toUpperCase() + String(s).slice(1)
}

function modelMentionRate(key) {
  const hit = (latestBreakdown.value || []).find(p => p.provider === key)
  if (!hit || hit.mention_rate == null) return null
  return Math.round(hit.mention_rate)
}

function auditStatusClass(status) {
  return {
    pending: 'ov-status-pending',
    running: 'ov-status-running',
    completed: 'ov-status-success',
    failed: 'ov-status-failed',
  }[status] || 'ov-status-pending'
}

// Alias so the Recent Audits row can re-trigger a stuck pending/failed run
// using the same execute path the legacy table used.
const runAuditNow = (audit) => executeAuditJob(audit)

// Pages tab: count of external sources that finished scanning successfully,
// plus the total number of URLs the next audit will pull in (root is always
// implicit, so the count here covers only the *additional* imports). Local
// uploads count too once they parse cleanly.
const scannedContextCount = computed(() => contextUrls.value.filter(c => c.success).length)
const importedCount = computed(() =>
  extraPaths.value.length + scannedContextCount.value + uploadedDocsReady.value.length,
)

function handleAuditStarted(audit) {
  // The new audit record is now live — add it to the list, select it, and
  // begin polling. This swaps the view out of first-run into the dashboard.
  if (audit?.id) {
    audits.value.unshift(audit)
    selectedAuditId.value = audit.id
  }
  toast.success('Audit started. Results will appear as each LLM responds.')
}

async function regenerateTopics() {
  generatingTopics.value = true
  let gotTopics = false
  try {
    const { data } = await llmRankingApi.suggestContext({
      business_name: auditForm.value.business_name,
      description: auditForm.value.description,
      industry: auditForm.value.industry,
      domain: homepageUrl.value || '',
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
  // Step 0: Pages — homepage is always included, sub-paths are
  // optional. No gating beyond having a known website (we wouldn't
  // have rendered the modal if we didn't).
  // Step 1: Description
  if (wizardStep.value === 1) {
    if (!auditForm.value.business_name) { auditError.value = 'Business name is required.'; return }
    if (!auditForm.value.industry) { auditError.value = 'Industry is required.'; return }
    // If no topics were loaded from scan, fetch them now and wait
    if (!wizardTopics.value.length) {
      await regenerateTopics()
    }
  }
  // Step 2: Context Sources — optional, no validation needed
  // Step 3: Topics
  if (wizardStep.value === 3) {
    if (!auditForm.value.selectedTopics.length) {
      auditError.value = 'Select at least one topic.'
      return
    }
  }
  wizardStep.value++
  // Fetch a cost estimate when we land on the review step so the user
  // sees what the audit will cost BEFORE clicking Start.
  if (wizardStep.value === 6) {
    fetchPreflight()
  }
}

const preflight = ref(null)
const preflightLoading = ref(false)

async function fetchPreflight() {
  preflight.value = null
  preflightLoading.value = true
  try {
    // Estimate using the chosen prompt count (custom prompts override the
    // default-generated set, otherwise the wizard targets up to 10 prompts).
    const customCount = (customPromptsText.value || '')
      .split('\n').map(s => s.trim()).filter(Boolean).length
    const promptCount = customCount > 0
      ? customCount
      : Math.max(1, Math.min(10, auditForm.value.selectedTopics.length || 5))
    const { data } = await llmRankingApi.preflight(websiteId, {
      prompt_count: promptCount,
      providers: auditForm.value.providers,
    })
    preflight.value = data?.data || data
  } catch (e) {
    // Pre-flight is informational — fail silently if the endpoint is unavailable
    preflight.value = null
  } finally {
    preflightLoading.value = false
  }
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

// Diagnostics section gates on having at least one successful result —
// otherwise the heatmap / radar / scatter would render empty cards.
const diagnosticsHaveData = computed(() => {
  const rs = auditDetail.value?.results || []
  return rs.some(r => r && r.query_succeeded)
})

const isAuditRunning = computed(() => {
  const s = latestAudit.value?.status
  return s === 'running' || s === 'pending'
})

// ── Prompt Activity ──────────────────────────────────────────────────────
//
// Replaces the old terminal-style Pipeline Log + Live Results ticker. We
// derive a chronological per-query view directly from auditDetail.results
// — no separate /logs/ poll. The audit-level status poll already brings
// new results in, so this card stays in sync without a second timer.
//
// Each row shows: time we sent the prompt, provider, the actual model
// name we hit, the prompt text, and the outcome (mentioned / miss / error).

// Audit-side provider key -> model identifier sent on the wire. Mirrors
// the .model attribute on each provider class in apps.llm_ranking.providers.
// Kept in sync manually — adding a provider here without a backend change
// is harmless (it just shows the wrong label until corrected).
const PROVIDER_MODELS = {
  claude: 'claude-sonnet-4-20250514',
  gpt4: 'gpt-4o-mini',
  gemini: 'gemini-1.5-flash',
  perplexity: 'llama-3.1-sonar-small-128k-online',
}

function providerModel(key) {
  return PROVIDER_MODELS[key] || key
}

function providerColor(key) {
  // Lightweight visual distinguisher — same scheme as the rankings table.
  const colors = {
    claude: '#d97706',
    gpt4: '#10b981',
    gemini: '#3b82f6',
    perplexity: '#8b5cf6',
  }
  return colors[key] || '#6b7280'
}

function formatPromptTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleTimeString(undefined, {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

// All queries this audit ran, oldest first. Renders the same data
// during a running audit (partial — fewer rows) and after completion.
const promptActivity = computed(() => {
  const list = auditDetail.value?.results || []
  return [...list].sort((a, b) =>
    (a.created_at || '').localeCompare(b.created_at || ''),
  )
})

// ── Prompt Activity filters ─────────────────────────────────────────────
//
// Client-side filtering against the full ``promptActivity`` list. The
// Status poll keeps the underlying array fresh while the user keeps
// their filter selection — important during a running audit so the
// view doesn't reset every two seconds.
const paFilters = ref({
  search: '',
  provider: '',
  status: '',     // '', 'mentioned', 'not_mentioned', 'error'
  sort: 'time_asc',
})

const paFiltersActive = computed(() => {
  const f = paFilters.value
  return !!(f.search || f.provider || f.status || f.sort !== 'time_asc')
})

function resetPromptActivityFilters() {
  paFilters.value = { search: '', provider: '', status: '', sort: 'time_asc' }
}

// Distinct providers seen in this audit — drives the provider dropdown
// so the user only sees options that actually have rows.
const promptActivityProviders = computed(() => {
  const seen = new Set()
  for (const r of promptActivity.value) {
    if (r.provider) seen.add(r.provider)
  }
  return Array.from(seen).sort()
})

const filteredPromptActivity = computed(() => {
  const f = paFilters.value
  let rows = promptActivity.value

  if (f.search) {
    const q = f.search.toLowerCase()
    rows = rows.filter(r => (r.prompt || '').toLowerCase().includes(q))
  }
  if (f.provider) {
    rows = rows.filter(r => r.provider === f.provider)
  }
  if (f.status === 'mentioned') {
    rows = rows.filter(r => r.query_succeeded && r.is_mentioned)
  } else if (f.status === 'not_mentioned') {
    rows = rows.filter(r => r.query_succeeded && !r.is_mentioned)
  } else if (f.status === 'error') {
    rows = rows.filter(r => !r.query_succeeded)
  }

  // Apply sort. ``rows`` is already a fresh copy from the upstream sort
  // (``promptActivity`` returns a sorted clone) — but our filter chain
  // returns the same reference, so spread before sorting in place.
  const sorted = [...rows]
  switch (f.sort) {
    case 'time_desc':
      sorted.reverse()
      break
    case 'rank_asc':
      sorted.sort((a, b) => {
        const ra = (a.is_mentioned && a.mention_rank) ? a.mention_rank : 999
        const rb = (b.is_mentioned && b.mention_rank) ? b.mention_rank : 999
        return ra - rb
      })
      break
    case 'provider':
      sorted.sort((a, b) => {
        const p = (a.provider || '').localeCompare(b.provider || '')
        if (p !== 0) return p
        return (a.created_at || '').localeCompare(b.created_at || '')
      })
      break
    case 'time_asc':
    default:
      // already sorted ascending by created_at
      break
  }
  return sorted
})

// Progress used by the card subtitle. Stays at 0/0 until the running
// audit reports its planned total, which is fine.
const logProgress = computed(() => ({
  completed: latestAudit.value?.queries_completed || 0,
  total: latestAudit.value?.total_queries || 0,
}))

// ── Prompt Intelligence aggregation ─────────────────────────────────────────
const providerFilter = ref('')
// "funnel_stage" or "intent" — how the Prompts table groups its rows.
// Funnel-stage is the strategic view (Bottom/Mid/Top/Niche), topic is the
// query-shape view (Recommendation/Comparison/Use Case/etc.).
const groupBy = ref('funnel_stage')
const collapsedIntents = ref(new Set())
const expandedPrompts = ref(new Set())

const FUNNEL_STAGE_LABELS = {
  bottom: 'Bottom of Funnel — High Intent',
  mid:    'Mid Funnel — Category & Comparison',
  top:    'Top of Funnel — Awareness',
  niche:  'Niche / Long-Tail',
}
// Funnel-stage sort order — bottom first because that's the most decision-
// critical stage.
const FUNNEL_STAGE_ORDER = ['bottom', 'mid', 'top', 'niche']

// Fallback for old audits where prompts weren't tagged with funnel_stage.
const INTENT_TO_FUNNEL = {
  recommendation: 'bottom',
  alternatives:   'bottom',
  review:         'bottom',
  comparison:     'mid',
  use_case:       'mid',
  category:       'mid',
  persona:        'top',
  local:          'niche',
  custom:         'niche',
}

function groupLabel(key) {
  if (groupBy.value === 'funnel_stage') {
    return FUNNEL_STAGE_LABELS[key] || 'Other'
  }
  return formatIntent(key)
}

function toggleIntent(intent) {
  const s = new Set(collapsedIntents.value)
  if (s.has(intent)) s.delete(intent)
  else s.add(intent)
  collapsedIntents.value = s
}

function togglePrompt(text) {
  const s = new Set(expandedPrompts.value)
  if (s.has(text)) s.delete(text)
  else s.add(text)
  expandedPrompts.value = s
}

// Per-(prompt, provider) "show full response" toggle. Key shape: 'prompt|provider'.
const expandedResponses = ref(new Set())
function toggleResponseExpand(key) {
  const s = new Set(expandedResponses.value)
  if (s.has(key)) s.delete(key)
  else s.add(key)
  expandedResponses.value = s
}
function isResponseExpanded(key) {
  return expandedResponses.value.has(key)
}
async function copyResponse(text) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    toast.success('Response copied')
  } catch {
    toast.error('Could not copy to clipboard')
  }
}

// Per-prompt 0-100 score. Mirrors compute_overall_score on the server so
// what the user sees per-prompt is consistent with the audit's headline
// score for the same data:
//   mention rate * 0.40 (0-40)
// + rank bonus by avg rank when mentioned (0-30; 0 when no extractable rank)
// + sentiment ((pos*20 + neu*10) / mentioned, averaged) (0-20)
// + provider coverage (10 if >=3 providers succeeded, else proportional)
function computePromptScore(results) {
  const succeeded = results.filter(r => r.query_succeeded)
  if (!succeeded.length) return 0
  const mentioned = succeeded.filter(r => r.is_mentioned)
  const mentionRate = mentioned.length / succeeded.length * 100

  // Rank bonus only when we have at least one extractable rank, matching
  // the server (rank_score stays 0 when ranks list is empty, even if some
  // responses mention the brand without giving a list position).
  let rankScore = 0
  const ranks = mentioned.map(r => r.mention_rank).filter(x => x != null)
  if (ranks.length) {
    const avg = ranks.reduce((a, b) => a + b, 0) / ranks.length
    if (avg <= 1) rankScore = 30
    else if (avg <= 3) rankScore = 20
    else if (avg <= 5) rankScore = 15
    else if (avg <= 10) rankScore = 10
    else rankScore = 5
  }

  let sentimentScore = 0
  if (mentioned.length) {
    const pos = mentioned.filter(r => r.sentiment === 'positive').length
    const neu = mentioned.filter(r => r.sentiment === 'neutral').length
    sentimentScore = (pos * 20 + neu * 10) / mentioned.length
  }

  const providerSet = new Set(succeeded.map(r => r.provider))
  const coverage = providerSet.size >= 3 ? 10 : (providerSet.size / 3) * 10

  return Math.min(100, Math.round(mentionRate * 0.40 + rankScore + sentimentScore + coverage))
}

// Escape every regex metacharacter so user-supplied keywords can be safely
// embedded in a RegExp. The previous inline character class was malformed
// and matched almost nothing, so special chars in a keyword like "C++" or
// "node.js" would either crash RegExp() or silently never match.
const REGEX_META = /[.*+?^${}()|[\]\\]/g
function escapeRegExp(s) { return s.replace(REGEX_META, '\\$&') }

// Intersect audit keywords with the lowercase mention_context across all
// providers' responses for a prompt. Returns ordered by frequency.
function computeMatchedKeywords(results, auditKeywords) {
  if (!auditKeywords?.length) return []
  const counts = new Map()
  for (const r of results) {
    if (!r.is_mentioned) continue
    const blob = ((r.mention_context || '') + ' ' + (r.response_text || '')).toLowerCase()
    for (const kw of auditKeywords) {
      const k = (kw || '').toLowerCase().trim()
      if (!k || k.length < 2) continue
      let pattern
      try {
        // Word-boundary match to avoid short keywords matching mid-word
        // (e.g. "ai" hitting "email"). Wrapped in try/catch so a single
        // malformed keyword can't poison the whole prompt's match list.
        pattern = new RegExp('(^|\\W)' + escapeRegExp(k) + '(\\W|$)', 'i')
      } catch (_) {
        continue
      }
      if (pattern.test(blob)) {
        counts.set(k, (counts.get(k) || 0) + 1)
      }
    }
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([k]) => k)
}

function dominantSentiment(results) {
  const mentioned = results.filter(r => r.is_mentioned)
  if (!mentioned.length) return 'not_mentioned'
  const counts = { positive: 0, neutral: 0, negative: 0 }
  for (const r of mentioned) {
    if (counts[r.sentiment] !== undefined) counts[r.sentiment]++
  }
  let max = 'neutral', maxCount = -1
  for (const [k, v] of Object.entries(counts)) {
    if (v > maxCount) { max = k; maxCount = v }
  }
  return max
}

function promptStatusClass(p) {
  if (p.providerDots.every(d => !d.succeeded)) return 'is-fail'
  if (p.visibility === 0) return 'is-miss'
  if (p.visibility >= 50) return 'is-ran'
  return 'is-partial'
}

function promptStatusLabel(p) {
  if (p.providerDots.every(d => !d.succeeded)) return 'API Failed'
  if (p.visibility === 0) return 'No Mention'
  if (p.providerDots.some(d => d.succeeded && !d.mentioned)) return 'Partial'
  return 'Mentioned'
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

// Map prompt text -> intent, derived once from the audit's prompts list.
// Old audits stored prompts as plain strings; new audits store
// {text, type, funnel_stage, rationale} dicts. Handle both shapes.
const promptIntentByText = computed(() => {
  const map = {}
  const prompts = latestAudit.value?.prompts || []
  prompts.forEach((p, i) => {
    if (typeof p === 'string') {
      map[p] = promptIntents.value[i] || 'custom'
    } else if (p && p.text) {
      map[p.text] = p.type || promptIntents.value[i] || 'custom'
    }
  })
  return map
})

// Map prompt text -> {funnel_stage, rationale}. Falls back to the
// intent → stage table when the audit doesn't carry the new fields.
const promptMetaByText = computed(() => {
  const map = {}
  const prompts = latestAudit.value?.prompts || []
  prompts.forEach((p, i) => {
    if (typeof p === 'string') {
      const intent = promptIntents.value[i] || 'custom'
      map[p] = {
        funnel_stage: INTENT_TO_FUNNEL[intent] || 'niche',
        rationale: '',
      }
    } else if (p && p.text) {
      const intent = p.type || 'custom'
      map[p.text] = {
        funnel_stage: p.funnel_stage || INTENT_TO_FUNNEL[intent] || 'niche',
        rationale: p.rationale || '',
      }
    }
  })
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

    const auditKeywords = latestAudit.value?.keywords || auditDetail.value?.keywords || []
    const meta = promptMetaByText.value[text] || {}
    const intent = promptIntentByText.value[text] || 'custom'
    rows.push({
      text,
      intent,
      funnel_stage: meta.funnel_stage || INTENT_TO_FUNNEL[intent] || 'niche',
      rationale: meta.rationale || '',
      visibility,
      avgRank,
      score: computePromptScore(results),
      matchedKeywords: computeMatchedKeywords(results, auditKeywords),
      dominantSentiment: dominantSentiment(results),
      providerDots,
      topCompetitors,
      responses: results.filter(r => r.query_succeeded && r.response_text),
    })
  }
  return rows
})

const intentGroups = computed(() => {
  // The "intent" key on each group is the grouping key — funnel stage by
  // default, intent label when the user picks "Group by topic". The Vue
  // template keeps using `group.intent` so we don't have to touch it.
  const key = groupBy.value === 'funnel_stage' ? 'funnel_stage' : 'intent'
  const groups = {}
  for (const row of promptRows.value) {
    const k = row[key] || 'custom'
    if (!groups[k]) groups[k] = []
    groups[k].push(row)
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
      const avgScore = prompts.length
        ? Math.round(prompts.reduce((a, p) => a + p.score, 0) / prompts.length)
        : 0
      // Top keywords across all prompts in this topic, ranked by frequency.
      const kwCounts = new Map()
      for (const p of prompts) {
        for (const kw of p.matchedKeywords) {
          kwCounts.set(kw, (kwCounts.get(kw) || 0) + 1)
        }
      }
      const topKeywords = [...kwCounts.entries()]
        .sort((a, b) => b[1] - a[1])
        .map(([k]) => k)
      return { intent, prompts, avgVisibility, avgScore, providerSummary, topKeywords }
    })
    .sort((a, b) => {
      // Funnel-stage groups: sort top→bottom of funnel (Bottom first because
      // it's the most decision-critical stage).
      if (groupBy.value === 'funnel_stage') {
        const ai = FUNNEL_STAGE_ORDER.indexOf(a.intent)
        const bi = FUNNEL_STAGE_ORDER.indexOf(b.intent)
        return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi)
      }
      // Intent groups: highest-scoring topic first.
      return b.avgScore - a.avgScore
    })
})

// ── GEO domain tagger ────────────────────────────────────────────────────
//
// Tags each prompt with one of the 7 categories from the GEO paper
// (Aggarwal et al., KDD '24) and surfaces the highest-lift GEO tactic
// for that domain. Backend call batches up to 200 prompts; cached
// server-side per prompt-hash, so reloading an audit is a no-op.

const geoTagsByPrompt = ref({})
const geoTagsLoading = ref(false)
let _geoTagsLastKey = ''

async function fetchGeoTagsForPrompts(texts) {
  const unique = [...new Set(texts.filter(Boolean))]
  if (!unique.length) return
  const key = unique.slice().sort().join('|')
  if (key === _geoTagsLastKey) return
  _geoTagsLastKey = key
  geoTagsLoading.value = true
  try {
    const { data } = await llmRankingApi.geoTags(websiteId, unique)
    geoTagsByPrompt.value = data?.tags || {}
  } catch (e) {
    // Non-fatal: ranking UI still works without the GEO badge column.
    geoTagsByPrompt.value = {}
  } finally {
    geoTagsLoading.value = false
  }
}

watch(
  () => (promptRows.value || []).map(r => r.text),
  texts => { if (texts.length) fetchGeoTagsForPrompts(texts) },
  { immediate: true },
)

function geoTagFor(promptText) {
  return geoTagsByPrompt.value[promptText] || null
}

function geoTopRecommendation(promptText) {
  const t = geoTagFor(promptText)
  return t?.recommendations?.[0] || null
}

// Tailwind-ish hue per category so badges stay readable across themes.
const GEO_CATEGORY_COLORS = Object.freeze({
  debate:         { bg: '#fef3c7', fg: '#92400e' },
  facts:          { bg: '#dbeafe', fg: '#1e40af' },
  law_gov:        { bg: '#e0e7ff', fg: '#3730a3' },
  people_society: { bg: '#fce7f3', fg: '#9d174d' },
  explanation:    { bg: '#d1fae5', fg: '#065f46' },
  history:        { bg: '#ede9fe', fg: '#5b21b6' },
  opinion:        { bg: '#ffedd5', fg: '#9a3412' },
})

function geoCategoryStyle(category) {
  const c = GEO_CATEGORY_COLORS[category] || { bg: '#e5e7eb', fg: '#374151' }
  return { backgroundColor: c.bg, color: c.fg }
}

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
  if (!a) return { value: 0, raw: 0, basis: 0, ciLow: 0, ciHigh: 0 }
  // When a platform filter is set, recompute against just that provider's
  // responses; otherwise fall back to the audit-level smoothed mention_rate.
  if (filters.value.platform && filters.value.platform !== 'all') {
    const results = platformFilteredResults.value.filter(r => r.query_succeeded)
    if (!results.length) return { value: 0, raw: 0, basis: 0, ciLow: 0, ciHigh: 0 }
    const mentioned = results.filter(r => r.is_mentioned).length
    const raw = Math.round(mentioned / results.length * 100)
    return {
      value: raw,
      raw,
      basis: results.length,
      ciLow: 0,
      ciHigh: 0,
    }
  }
  // Prefer the Beta-Binomial smoothed value when the backend provides it
  // (it does for any audit run after the smoothing migration). Falls back
  // to raw mention_rate for older audits so historical data still renders.
  const smoothed = a.mention_rate_smoothed
  const raw = Math.round(a.mention_rate || 0)
  return {
    value: smoothed != null ? Math.round(smoothed) : raw,
    raw,
    basis: a.queries_completed || a.total_queries || 0,
    ciLow: Math.round(a.mention_rate_ci_lower || 0),
    ciHigh: Math.round(a.mention_rate_ci_upper || 0),
  }
})

// Confidence tier for the visibility KPI based on CI width. Drives the
// dot indicator next to the headline number — wide intervals signal a
// volatile estimate (more queries / providers needed).
function visibilityConfidence(kpi) {
  if (!kpi || !(kpi.ciHigh > 0)) return null
  const width = kpi.ciHigh - kpi.ciLow
  if (width < 15) return 'high'
  if (width < 30) return 'med'
  return 'low'
}

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
  // Combine you + competitors from the leaderboard. When Plackett-Luce
  // strengths are available on the audit (post-migration), use those as
  // the primary sort key — it's a calibrated cross-response strength
  // rather than a raw mention count. Falls back to mention-count
  // visibility for older audits with no brand_strengths.
  const a = latestAudit.value
  const yourName = a?.business_name || 'You'
  const yourVis = Math.round(a?.mention_rate || 0)
  const strengths = a?.brand_strengths || {}
  const hasStrengths = Object.keys(strengths).length > 0

  const rows = [{
    name: yourName,
    visibility: yourVis,
    strength: strengths[yourName] != null ? strengths[yourName] : null,
    mention_count: 0,
    is_you: true,
  }]
  for (const c of competitorLeaderboard.value || []) {
    rows.push({
      name: c.name,
      visibility: uniquePromptCount.value
        ? Math.round(c.promptCount / uniquePromptCount.value * 100)
        : 0,
      strength: strengths[c.name] != null ? strengths[c.name] : null,
      mention_count: c.promptCount,
      avg_rank: c.avgRank,
      is_you: false,
    })
  }
  if (hasStrengths) {
    // Sort by Plackett-Luce strength first, falling back to visibility
    // for any brand that didn't appear with a position (strength=null).
    rows.sort((x, y) => {
      const sx = x.strength != null ? x.strength : -1
      const sy = y.strength != null ? y.strength : -1
      if (sx !== sy) return sy - sx
      return y.visibility - x.visibility
    })
  } else {
    rows.sort((x, y) => y.visibility - x.visibility)
  }
  return rows.map((r, i) => ({ ...r, rank: i + 1 }))
})

// Citation footprint = country breakdown of all citations in this audit.
// Rendered in the "Citation Footprint by Country" card. Sorted descending
// by count, with shares normalized to 100%.
const citationFootprint = computed(() => {
  const a = latestAudit.value
  const counts = (a && a.citation_countries) || {}
  const entries = Object.entries(counts)
    .map(([country, count]) => ({ country, count: Number(count) || 0 }))
    .filter(e => e.count > 0)
  if (!entries.length) return []
  const total = entries.reduce((s, e) => s + e.count, 0) || 1
  entries.sort((a, b) => b.count - a.count)
  return entries.map(e => ({
    country: e.country,
    label: countryLabel(e.country),
    flag: countryFlag(e.country),
    count: e.count,
    share: Math.round(e.count / total * 100),
  }))
})

const usingBrandStrengths = computed(() => {
  const a = latestAudit.value
  return !!(a && a.brand_strengths && Object.keys(a.brand_strengths).length > 0)
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

// Score factor breakdown (must sum to ~overall_score). The backend
// scores against the Beta-Binomial smoothed mention rate so we mirror
// that here when available; older audits without the smoothed value
// fall back to raw mention_rate so historical breakdowns still render.
const mentionPts = computed(() => {
  const a = latestAudit.value
  if (!a) return 0
  const rate = a.mention_rate_smoothed != null ? a.mention_rate_smoothed : (a.mention_rate || 0)
  return Math.round(rate * 0.4)
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

// Prompt-source coverage across the current audit's results.
const coverage = computed(() => {
  const results = auditDetail.value?.results || []
  const total = results.length || 1
  const buckets = { library: 0, vault: 0, custom: 0 }
  for (const r of results) {
    const src = String(r.prompt_source_label || 'vault').split(':')[0]
    if (src === 'library' || src === 'vault' || src === 'custom') buckets[src]++
  }
  const pct = (n) => Math.round((n / total) * 100)
  return `${pct(buckets.library)}% library / ${pct(buckets.vault)}% vault / ${pct(buckets.custom)}% custom`
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

// ── Chart Data ─────────────────────────────────────────────────────────────

const PROVIDER_COLORS = {
  claude: '#A78BFA',
  gpt4: '#34D399',
  gemini: '#5B8DEF',
  perplexity: '#F59E0B',
}

const providerChartData = computed(() => {
  const bd = latestBreakdown.value.filter(p => p.succeeded > 0)
  return {
    labels: bd.map(p => p.provider_display || providerLabel(p.provider)),
    datasets: [{
      label: 'Mention Rate (%)',
      data: bd.map(p => p.mention_rate),
      backgroundColor: bd.map(p => PROVIDER_COLORS[p.provider] || '#6B7280'),
      borderRadius: 6,
      barThickness: 36,
    }],
  }
})

const providerChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#1e1e2e',
      padding: 10,
      cornerRadius: 8,
      callbacks: {
        label: (ctx) => `${ctx.parsed.y}% mention rate`,
      },
    },
  },
  scales: {
    y: {
      min: 0,
      max: 100,
      grid: { color: 'rgba(255,255,255,0.04)' },
      ticks: { callback: (v) => v + '%' },
    },
    x: {
      grid: { display: false },
    },
  },
}

const trendChartData = computed(() => {
  const history = historyData.value
  return {
    labels: history.map(h => {
      const d = new Date(h.completed_at)
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    }),
    datasets: [
      {
        label: 'Overall Score',
        data: history.map(h => h.overall_score),
        borderColor: '#A78BFA',
        backgroundColor: 'rgba(167,139,250,0.08)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#A78BFA',
      },
      {
        label: 'Mention Rate (%)',
        data: history.map(h => h.mention_rate),
        borderColor: '#34D399',
        backgroundColor: 'rgba(52,211,153,0.06)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointBackgroundColor: '#34D399',
        borderDash: [4, 4],
      },
    ],
  }
})

const trendChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      position: 'bottom',
      labels: { usePointStyle: true, pointStyle: 'circle', padding: 16 },
    },
    tooltip: {
      backgroundColor: '#1e1e2e',
      padding: 10,
      cornerRadius: 8,
    },
  },
  scales: {
    y: {
      min: 0,
      max: 100,
      grid: { color: 'rgba(255,255,255,0.04)' },
      ticks: { callback: (v) => v },
    },
    x: {
      grid: { display: false },
    },
  },
}

// ── Helpers ─────────────────────────────────────────────────────────────────

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
  const pct = rate || 0
  return pct >= 60 ? 'badge-success' : pct >= 30 ? 'badge-warning' : 'badge-neutral'
}

function scoreColor(score) {
  if (!score && score !== 0) return 'var(--text-muted)'
  if (score >= 70) return '#10B981'
  if (score >= 40) return '#F59E0B'
  return '#EF4444'
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
  }
  // Re-prefill from the loaded website so the user keeps the
  // pre-populated business name / industry / description.
  if (currentWebsite.value) {
    auditForm.value.business_name = currentWebsite.value.name || ''
    auditForm.value.industry = currentWebsite.value.industry || ''
    auditForm.value.description = currentWebsite.value.description || ''
  }
  wizardStep.value = 0
  wizardTopics.value = []
  competitorInput.value = ''
  competitorDomainInput.value = ''
  extraPaths.value = []
  extraPathInput.value = ''
  contextUrls.value = []
  contextUrlInput.value = ''
  scanningContextUrl.value = false
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
      region: auditForm.value.region || 'global',
      providers: auditForm.value.providers,
      themes: auditForm.value.themes || [],
      keywords: auditForm.value.selectedTopics || [],
      competitors: (auditForm.value.competitors || []).map(c => typeof c === 'string' ? c : c.name),
      // Same-domain sub-paths from Step 0 ("Pages") and external context
      // URLs from the Context Sources step both flow into the backend's
      // ``context_urls`` field; the audit's enrichment treats them
      // uniformly. Keep external sources first since they're often the
      // user's most curated picks; sub-paths are supplementary.
      // The compare-against-prompts permission gate strips the extra
      // URLs when the user hasn't explicitly opted in — the project's
      // root URL is always included by the backend's enrichment.
      context_urls: agentScanPermission.value
        ? [
            ...contextUrls.value.filter(c => c.success).map(c => c.url),
            ...extraPaths.value.map(p => p.url),
          ]
        : [],
      // Locally-uploaded documents (.txt / .md / .csv / .json / .html)
      // travel as their extracted text body. The backend can opt in to
      // using these as additional grounding; unknown fields are ignored
      // safely by the audit serializer.
      inline_documents: agentScanPermission.value
        ? uploadedDocsReady.value.map(d => ({ name: d.name, content: d.content }))
        : [],
    }
    if (customPromptsText.value.trim()) {
      payload.custom_prompts = customPromptsText.value.split('\n').map(s => s.trim()).filter(Boolean)
    }
    payload.prompt_source = promptSource.value
    if (previewedPrompts.value.length) {
      payload.prompt_ids = previewedPrompts.value.map(p => p.id)
    }
    const { data } = await llmRankingApi.runAudit(websiteId, payload)
    const audit = data?.data || data
    audits.value = [audit, ...audits.value]
    selectedAuditId.value = audit.id
    // Show the prompts panel immediately so the user sees what's being asked
    auditDetail.value = audit
    showRunForm.value = false
    // Reset prompt-source dispatcher state for the next run.
    promptSource.value = 'hybrid'
    previewOpen.value = false
    previewedPrompts.value = []
    toast.success('Audit queued. Results will appear once complete.')
    // Status polling brings in new results — the Prompt Activity card
    // re-renders from auditDetail.results, no separate log poll needed.
    startPolling()
  } catch (err) {
    // Per-user monthly AI spend cap reached — show a friendly modal instead
    // of the generic banner so the user knows what to do.
    const status = err?.response?.status
    const body = err?.response?.data?.data || err?.response?.data
    if (status === 402 && body?.error === 'monthly_ai_cost_cap_exceeded') {
      capExceededModal.value = {
        spent: body?.cap_status?.spent_usd ?? 0,
        cap: body?.cap_status?.cap_usd ?? 0,
        detail: body?.detail || '',
      }
      showRunForm.value = false
    } else {
      auditError.value = err.displayMessage || 'Failed to start audit.'
    }
  } finally {
    running.value = false
  }
}

async function selectAudit(audit) {
  selectedAuditId.value = audit.id
  latestBreakdown.value = []
  recommendations.value = []
  auditDetail.value = null

  // Pipeline log polling removed — Prompt Activity reads directly from
  // auditDetail.results, which the status poll keeps fresh.

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

  // Phase 2: load citations + source influence (non-blocking).
  loadCitations(audit.id)
  // Phase 3: count of content briefs created from this audit (non-blocking).
  loadContentBriefsForAudit(audit)
}


// Phase 2 helpers ----------------------------------------------------
async function loadCitations(auditId) {
  citationsByResult.value = new Map()
  auditSourceInfluence.value = null
  try {
    const [cRes, sRes] = await Promise.all([
      citationsApi.auditCitations(auditId),
      citationsApi.auditSourceInfluence(auditId),
    ])
    const cBody = cRes.data?.data || cRes.data || {}
    const rows = cBody.results || cBody || []
    const map = new Map()
    for (const c of rows) {
      const rid = c.result
      if (!rid) continue
      if (!map.has(rid)) map.set(rid, [])
      map.get(rid).push(c)
    }
    citationsByResult.value = map
    auditSourceInfluence.value = sRes.data?.data || sRes.data || null
  } catch (e) {
    console.warn('Failed to load citations', e)
  }
}

function citationsForResult(resultId) {
  return citationsByResult.value.get(resultId) || []
}

function openCitationsDrawer(result) {
  const list = citationsForResult(result.id)
  citationsDrawerCitations.value = list
  citationsDrawerProvider.value = result.provider || ''
  citationsDrawerPrompt.value = result.prompt || ''
  citationsDrawerOpen.value = true
}

const totalAuditCitations = computed(() => {
  let total = 0
  for (const arr of citationsByResult.value.values()) total += arr.length
  return total
})

function gotoSourceInfluence() {
  router.push(`/llm-ranking/${websiteId}/source-influence`)
}

function gotoContentStudio() {
  router.push({
    path: `/llm-ranking/${websiteId}/content`,
    query: selectedAuditId.value ? { from_audit: selectedAuditId.value } : {},
  })
}

// Phase 4: Content Studio integration. Count of content briefs created
// from (or after) the currently selected audit. Soft-fails if endpoint
// or response shape isn't available — the tile still renders with 0.
const contentBriefsForAudit = ref(0)

async function loadContentBriefsForAudit(audit) {
  contentBriefsForAudit.value = 0
  if (!audit) return
  try {
    const contentStudioApi = (await import('@/api/contentStudio')).default
    const { data } = await contentStudioApi.briefs(websiteId, { from_audit: audit.id, _silentError: true })
    const body = data?.data || data || {}
    const list = body.results || body || []
    if (Array.isArray(list) && list.length) {
      // Backend may not filter by from_audit. Fall back to created_at >= audit.created_at.
      const auditTs = audit.created_at ? new Date(audit.created_at).getTime() : 0
      const filtered = auditTs
        ? list.filter((b) => b.created_at && new Date(b.created_at).getTime() >= auditTs)
        : list
      contentBriefsForAudit.value = filtered.length || list.length
    } else {
      contentBriefsForAudit.value = 0
    }
  } catch {
    contentBriefsForAudit.value = 0
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
  if (!websiteId) return
  try {
    const { data } = await llmRankingApi.providerHealth(websiteId)
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

// ── Schedule Functions ─────────────────────────────────────────────────────

function formatRelative(dt) {
  if (!dt) return '—'
  const d = new Date(dt)
  const now = new Date()
  const diffMs = d - now
  if (diffMs < 0) return 'any moment now'
  const diffDays = Math.ceil(diffMs / 86400000)
  if (diffDays <= 1) return 'tomorrow'
  if (diffDays <= 7) return `in ${diffDays} days`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

async function fetchSchedule() {
  try {
    const { data } = await llmRankingApi.getSchedule(websiteId)
    schedule.value = data?.data?.schedule || data?.schedule || null
    if (schedule.value) {
      scheduleForm.value = {
        business_name: schedule.value.business_name || '',
        industry: schedule.value.industry || '',
        location: schedule.value.location || '',
        frequency: schedule.value.frequency || 'weekly',
        providers: schedule.value.providers?.length ? schedule.value.providers : ['claude', 'gpt4', 'gemini', 'perplexity'],
      }
      fetchScheduleETA()
      startScheduleETAPolling()
    } else {
      stopScheduleETAPolling()
      scheduleETA.value = null
    }
  } catch (e) {
    console.error('Schedule fetch error', e)
  }
}

async function fetchScheduleETA() {
  if (!schedule.value) return
  try {
    const { data } = await llmRankingApi.scheduleETA(websiteId)
    scheduleETA.value = data?.data || data || null
  } catch (e) {
    // ETA is best-effort — keep stale value rather than wipe
  }
}

function startScheduleETAPolling() {
  stopScheduleETAPolling()
  scheduleETATimer = setInterval(fetchScheduleETA, 15000)
}
function stopScheduleETAPolling() {
  if (scheduleETATimer) {
    clearInterval(scheduleETATimer)
    scheduleETATimer = null
  }
}

const scheduleProgressPct = computed(() => {
  const p = scheduleETA.value && scheduleETA.value.in_flight_progress
  if (!p || !p.total) return 0
  return Math.min(100, Math.round((p.completed / p.total) * 100))
})

function formatDuration(seconds) {
  if (seconds == null) return '—'
  const s = Math.max(0, Math.round(seconds))
  if (s < 90) return `${s}s`
  if (s < 3600) return `${Math.round(s / 60)}m`
  if (s < 86400) return `${Math.round(s / 3600)}h`
  return `${Math.round(s / 86400)}d`
}

async function runScheduleNow() {
  if (runNowBusy.value) return
  runNowBusy.value = true
  try {
    await llmRankingApi.runScheduleNow(websiteId)
    toast.success('Scheduled audit kicked off.')
    await fetchScheduleETA()
    fetchData()
  } catch (err) {
    toast.error(err.displayMessage || 'Could not start audit now.')
  } finally {
    runNowBusy.value = false
  }
}

async function saveSchedule() {
  if (!scheduleForm.value.business_name) { scheduleError.value = 'Business name is required.'; return }
  if (!scheduleForm.value.industry) { scheduleError.value = 'Industry is required.'; return }
  savingSchedule.value = true
  scheduleError.value = ''
  try {
    const { data } = await llmRankingApi.saveSchedule(websiteId, {
      ...scheduleForm.value,
      is_enabled: true,
    })
    schedule.value = data?.data?.schedule || data?.schedule || null
    showScheduleModal.value = false
    toast.success('Schedule saved! Audits will run automatically.')
  } catch (err) {
    scheduleError.value = err.displayMessage || 'Failed to save schedule.'
  } finally {
    savingSchedule.value = false
  }
}

async function disableSchedule() {
  try {
    await llmRankingApi.deleteSchedule(websiteId)
    schedule.value = null
    toast.success('Schedule disabled.')
  } catch (err) {
    toast.error(err.displayMessage || 'Failed to disable schedule.')
  }
}

async function deleteSchedule() {
  try {
    await llmRankingApi.deleteSchedule(websiteId)
    schedule.value = null
    showScheduleModal.value = false
    toast.success('Schedule removed.')
  } catch (err) {
    toast.error(err.displayMessage || 'Failed to remove schedule.')
  }
}

onMounted(() => {
  // Load the website object first so the audit form is pre-filled
  // before the user opens the wizard.
  loadWebsite()
  loadSavedPromptsCount()
  Promise.all([fetchData(), fetchHistory(), fetchSchedule()]).then(() => {
    loadPromptResults()
    loadUsage()
  })
  document.addEventListener('click', onDocClick)
  // If the user creates prompts in another tab then comes back, refresh
  // the count so the empty state flips to the Run-audit CTA.
  window.addEventListener('focus', loadSavedPromptsCount)
})

onBeforeUnmount(() => {
  stopPolling()
  stopScheduleETAPolling()
  document.removeEventListener('click', onDocClick)
  window.removeEventListener('focus', loadSavedPromptsCount)
})
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }

/* ───────────────────────────────────────────────────────────────────────────
   Modern Overview tab
   Clean dashboard-style layout: KPI strip, two-column main grid, recent
   audits table, usage card. Sits inside .lr-overview.
   ─────────────────────────────────────────────────────────────────────── */
.lr-overview { display: flex; flex-direction: column; gap: 20px; }

.ov-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 12px;
  background: linear-gradient(90deg, rgba(255,107,53,0.07), rgba(255,107,53,0.02));
  border: 1px solid rgba(255,107,53,0.18);
  font-size: 0.875rem;
  color: var(--text-primary);
}
.ov-banner.paused {
  background: var(--bg-subtle, #fafafa);
  border-color: var(--border-color, #e5e7eb);
}
.ov-banner-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(255,107,53,0.12);
  color: var(--brand-accent, #ff6b35);
  flex-shrink: 0;
}
.ov-banner.paused .ov-banner-icon { background: var(--border-color, #e5e7eb); color: var(--text-muted); }
.ov-banner-text { flex: 1; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.ov-banner-text strong { color: var(--text-primary); font-weight: 600; }

.ov-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 60px 20px;
  color: var(--text-muted);
  font-size: 0.9rem;
}
.ov-spinner {
  width: 18px; height: 18px;
  border: 2px solid var(--border-color, #e5e7eb);
  border-top-color: var(--brand-accent, #ff6b35);
  border-radius: 50%;
  animation: ov-spin 0.8s linear infinite;
}
@keyframes ov-spin { to { transform: rotate(360deg); } }

/* KPI cards ─────────────────────────────────────────────────────────────── */
.ov-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}
@media (max-width: 900px) { .ov-kpis { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 540px) { .ov-kpis { grid-template-columns: 1fr; } }
.ov-kpi {
  background: var(--bg-card, #ffffff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
  padding: 18px 20px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.ov-kpi:hover {
  border-color: var(--border-strong, #d4d4d8);
  box-shadow: 0 6px 18px -10px rgba(20,23,24,0.10);
}
.ov-kpi-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  min-height: 18px;
}
.ov-kpi-label {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
}
.ov-kpi-badge {
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 2px 8px;
  border-radius: 999px;
}
.ov-kpi-badge.pill-green { background: rgba(16,185,129,0.12); color: #047857; }
.ov-kpi-badge.pill-yellow { background: rgba(245,158,11,0.14); color: #b45309; }
.ov-kpi-badge.pill-red { background: rgba(239,68,68,0.12); color: #b91c1c; }
.ov-kpi-badge.pill-neutral { background: var(--bg-subtle, #f4f4f5); color: var(--text-muted); }
.ov-kpi-value {
  font-size: 1.9rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: var(--text-primary);
  line-height: 1.05;
}
.ov-kpi-value-sm { font-size: 1.15rem; font-weight: 600; }
.ov-kpi-unit { font-size: 0.85rem; font-weight: 500; color: var(--text-muted); margin-left: 2px; }
.ov-kpi-sub { font-size: 0.78rem; color: var(--text-muted); margin-top: 8px; }
.perf-trend-up { color: #10b981; }
.perf-trend-down { color: #ef4444; }
.perf-trend-flat { color: var(--text-muted); }

/* Cards & grid ──────────────────────────────────────────────────────────── */
.ov-grid { display: grid; gap: 16px; }
.ov-grid-2 { grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); }
@media (max-width: 1024px) { .ov-grid-2 { grid-template-columns: 1fr; } }
.ov-card {
  padding: 18px 22px 22px;
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: box-shadow 0.18s ease, border-color 0.18s ease;
}
.ov-card:hover { box-shadow: 0 4px 16px -8px rgba(15, 23, 42, 0.12), 0 1px 2px rgba(15, 23, 42, 0.04); }
.page-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  background: rgba(255, 107, 53, 0.10);
  color: var(--brand-accent, #ff6b35);
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 10px;
}
.page-context { display: inline-flex; align-items: center; gap: 6px; }
.page-context svg { color: var(--text-muted); }
.ov-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.ov-card-title {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}
.ov-card-sub { margin: 4px 0 0; font-size: 0.78rem; color: var(--text-muted); }
.ov-select {
  appearance: none;
  background: var(--bg-input, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 8px;
  padding: 6px 28px 6px 10px;
  font-size: 0.8rem;
  color: var(--text-primary);
  cursor: pointer;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' fill='%236b7280' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
}

.ov-chart { position: relative; height: 260px; }
.ov-empty-inline {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 100%;
  min-height: 140px;
  color: var(--text-muted);
  font-size: 0.85rem;
  text-align: center;
}
.ov-empty-inline svg { color: var(--text-muted); opacity: 0.6; }
.ov-empty-inline p { margin: 0; }

/* Model coverage list ───────────────────────────────────────────────────── */
.ov-models { display: flex; flex-direction: column; gap: 4px; }
.ov-model-row {
  display: grid;
  grid-template-columns: 12px 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border-radius: 10px;
  transition: background 0.15s ease;
}
.ov-model-row:hover { background: var(--bg-subtle, #fafafa); }
.ov-model-row.off { opacity: 0.65; }
.ov-model-dot { width: 10px; height: 10px; border-radius: 50%; }
.ov-model-name { font-size: 0.88rem; font-weight: 500; color: var(--text-primary); }
.ov-model-meta { font-size: 0.78rem; color: var(--text-muted); }
.ov-model-rate {
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
.ov-tag {
  font-size: 0.7rem;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.ov-tag-warn { background: rgba(245,158,11,0.14); color: #b45309; }
.ov-tag-muted { background: var(--bg-subtle, #f4f4f5); color: var(--text-muted); }

/* Recent audits table ───────────────────────────────────────────────────── */
.ov-audit-table {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.ov-audit-head, .ov-audit-row {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr 1fr 1fr 0.9fr auto;
  gap: 14px;
  align-items: center;
  padding: 10px 12px;
  font-size: 0.85rem;
}
.ov-audit-head {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  padding-bottom: 12px;
  margin-bottom: 4px;
}
.ov-audit-row {
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s ease;
}
.ov-audit-row:hover { background: var(--bg-subtle, #fafafa); }
.ov-audit-row.selected {
  background: rgba(255,107,53,0.06);
  outline: 1px solid rgba(255,107,53,0.25);
}
.ov-audit-date { color: var(--text-primary); font-weight: 500; }
.ov-audit-score strong {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
.ov-audit-actions { display: flex; gap: 4px; justify-content: flex-end; }
.ov-audit-delete {
  width: 26px;
  height: 26px;
  padding: 0 !important;
  font-size: 1.1rem;
  line-height: 1;
  color: var(--text-muted);
}
.ov-audit-delete:hover { color: #ef4444; background: rgba(239,68,68,0.08); }

.ov-status {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.ov-status-success { background: rgba(16,185,129,0.12); color: #047857; }
.ov-status-running { background: rgba(245,158,11,0.14); color: #b45309; }
.ov-status-pending { background: var(--bg-subtle, #f4f4f5); color: var(--text-muted); }
.ov-status-failed { background: rgba(239,68,68,0.12); color: #b91c1c; }

/* Usage card ────────────────────────────────────────────────────────────── */
.ov-usage-totals {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 22px;
}
@media (max-width: 700px) { .ov-usage-totals { grid-template-columns: repeat(2, 1fr); } }
.ov-usage-cell {
  padding: 14px 16px;
  background: var(--bg-subtle, #fafafa);
  border-radius: 10px;
}
.ov-usage-val {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.01em;
  font-variant-numeric: tabular-nums;
}
.ov-usage-label {
  font-size: 0.72rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-top: 4px;
}
.ov-usage-models { display: flex; flex-direction: column; gap: 1px; }
.ov-usage-models-head, .ov-usage-models-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 14px;
  padding: 10px 12px;
  font-size: 0.85rem;
  align-items: center;
}
.ov-usage-models-head {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-color, #e5e7eb);
}
.ov-usage-models-row { border-radius: 8px; font-variant-numeric: tabular-nums; }
.ov-usage-models-row:hover { background: var(--bg-subtle, #fafafa); }
.ov-usage-model-name { font-weight: 500; color: var(--text-primary); }

/* ───────────────────────────────────────────────────────────────────────────
   Pages tab — same-site + external sources picker
   ─────────────────────────────────────────────────────────────────────── */
.lr-pages { display: flex; flex-direction: column; gap: 20px; }
.lr-tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  margin-left: 6px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--brand-accent, #ff6b35);
  color: #fff;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0;
}

.pages-project {
  padding: 18px 22px;
  border-radius: 14px;
}
.pages-project-head {
  display: flex;
  align-items: center;
  gap: 14px;
}
.pages-project-icon {
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: rgba(255,107,53,0.10);
  color: var(--brand-accent, #ff6b35);
  flex-shrink: 0;
}
.pages-project-body { flex: 1; min-width: 0; }
.pages-project-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 4px;
}
.pages-project-url {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  word-break: break-all;
}
.pages-project-url a {
  color: var(--text-primary);
  text-decoration: none;
  border-bottom: 1px solid transparent;
}
.pages-project-url a:hover { border-bottom-color: var(--brand-accent, #ff6b35); }
.pages-project-meta { font-size: 0.8rem; color: var(--text-secondary); margin-top: 4px; }

.pages-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr) auto;
  gap: 14px;
  align-items: center;
  background: var(--bg-card, #ffffff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
  padding: 14px 18px;
}
@media (max-width: 900px) {
  .pages-summary { grid-template-columns: repeat(2, 1fr); }
  .pages-summary-cta { grid-column: 1 / -1; }
}
.pages-summary-cell { display: flex; flex-direction: column; gap: 2px; }
.pages-summary-val {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
.pages-summary-label {
  font-size: 0.72rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}
.pages-summary-cell-strong .pages-summary-val { color: var(--brand-accent, #ff6b35); }

.pages-count {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-muted);
  background: var(--bg-subtle, #fafafa);
  padding: 4px 10px;
  border-radius: 999px;
}

.pages-input-row {
  display: flex;
  align-items: stretch;
  gap: 8px;
  margin-bottom: 14px;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 10px;
  background: var(--bg-input, #fff);
  padding: 4px 4px 4px 12px;
}
.pages-input-row:focus-within {
  border-color: var(--text-primary);
  box-shadow: var(--shadow-glow);
}
.pages-input-prefix {
  display: inline-flex;
  align-items: center;
  font-size: 0.85rem;
  color: var(--text-muted);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.pages-input.form-input {
  flex: 1;
  border: none;
  box-shadow: none;
  padding: 8px 4px;
  min-width: 0;
  background: transparent;
}
.pages-input.form-input:focus { box-shadow: none; }
.pages-input-row .btn { align-self: center; }

.pages-list { display: flex; flex-direction: column; gap: 6px; }
.pages-list-row {
  display: grid;
  grid-template-columns: 22px 1fr auto;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 10px;
  background: var(--bg-card, #ffffff);
  align-items: center;
  transition: border-color 0.15s ease;
}
.pages-list-row:hover { border-color: var(--border-strong, #d4d4d8); }
.pages-list-row-tall { align-items: flex-start; }
.pages-list-row-tall .pages-list-icon { margin-top: 2px; }
.pages-list-row.scanning { border-style: dashed; }
.pages-list-row.errored { border-color: rgba(239,68,68,0.35); background: rgba(239,68,68,0.03); }
.pages-list-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px; height: 22px;
  border-radius: 6px;
  background: var(--bg-subtle, #fafafa);
  color: var(--text-muted);
}
.pages-list-row.errored .pages-list-icon { background: rgba(239,68,68,0.10); color: #b91c1c; }
.pages-list-row:not(.scanning):not(.errored) .pages-list-icon { color: #047857; background: rgba(16,185,129,0.10); }
.pages-list-spinner {
  width: 12px; height: 12px;
  border: 2px solid var(--border-color, #e5e7eb);
  border-top-color: var(--brand-accent, #ff6b35);
  border-radius: 50%;
  animation: ov-spin 0.8s linear infinite;
}
.pages-list-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.pages-list-label {
  font-size: 0.88rem;
  font-weight: 500;
  color: var(--text-primary);
  word-break: break-word;
}
.pages-list-url {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-decoration: none;
  word-break: break-all;
}
.pages-list-url:hover { color: var(--text-primary); }
.pages-list-summary {
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-top: 4px;
  line-height: 1.4;
}
.pages-list-error {
  font-size: 0.78rem;
  color: #b91c1c;
  margin-top: 4px;
}
.pages-list-remove {
  appearance: none;
  background: transparent;
  border: none;
  width: 24px; height: 24px;
  border-radius: 6px;
  font-size: 1.1rem;
  line-height: 1;
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.pages-list-remove:hover { background: rgba(239,68,68,0.10); color: #ef4444; }

.pages-note {
  font-size: 0.82rem;
  color: var(--text-secondary);
  background: var(--bg-subtle, #fafafa);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 10px;
  padding: 12px 16px;
  margin: 0;
  line-height: 1.5;
}
.pages-note strong { color: var(--text-primary); font-weight: 600; }

/* ───────────────────────────────────────────────────────────────────────────
   Wizard "Compare against prompts" panel — embedded in Step 1 so the user
   can attach pages, grant permission, and see sample prompts side-by-side.
   ─────────────────────────────────────────────────────────────────────── */
.wizard-compare {
  margin-top: 22px;
  border-top: 1px solid var(--border-color, #e5e7eb);
  padding-top: 20px;
}
.wizard-compare-head { margin-bottom: 14px; }
.wizard-compare-title {
  margin: 0 0 4px;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
}
.wizard-compare-sub {
  margin: 0;
  font-size: 0.82rem;
  color: var(--text-secondary);
  line-height: 1.5;
}
.wizard-compare-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 880px) { .wizard-compare-grid { grid-template-columns: 1fr; } }
.wizard-compare-col {
  background: var(--bg-subtle, #fafafa);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.wizard-compare-col-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.wizard-compare-col-label {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
}

.wizard-scan-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 220px;
  overflow-y: auto;
}
.wizard-scan-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 8px;
  font-size: 0.82rem;
}
.wizard-scan-row-root { background: rgba(255,107,53,0.05); border-color: rgba(255,107,53,0.20); }
.wizard-scan-row.scanning { border-style: dashed; opacity: 0.85; }
.wizard-scan-row.errored { border-color: rgba(239,68,68,0.30); background: rgba(239,68,68,0.04); }
.wizard-scan-pill {
  font-size: 0.66rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--bg-subtle, #fafafa);
  color: var(--text-muted);
  white-space: nowrap;
}
.wizard-scan-row-root .wizard-scan-pill { background: rgba(255,107,53,0.14); color: #c2410c; }
.wizard-scan-pill-same { background: rgba(91,141,239,0.12); color: #1e40af; }
.wizard-scan-pill-ext { background: rgba(16,185,129,0.12); color: #047857; }
.wizard-scan-url {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
}
.wizard-scan-url a {
  color: inherit;
  text-decoration: none;
  border-bottom: 1px solid transparent;
}
.wizard-scan-url a:hover { border-bottom-color: var(--text-muted); }
.wizard-scan-error { color: #b91c1c; }
.wizard-scan-remove {
  appearance: none;
  background: transparent;
  border: none;
  width: 22px; height: 22px;
  border-radius: 6px;
  font-size: 1rem;
  line-height: 1;
  color: var(--text-muted);
  cursor: pointer;
}
.wizard-scan-remove:hover { background: rgba(239,68,68,0.10); color: #ef4444; }

.wizard-scan-add {
  display: flex;
  gap: 8px;
}
.wizard-scan-add .form-input {
  flex: 1;
  padding: 8px 12px;
  font-size: 0.85rem;
}
.wizard-scan-add .btn { flex-shrink: 0; }

.wizard-permission {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 10px;
  font-size: 0.82rem;
  line-height: 1.5;
  color: var(--text-secondary);
  cursor: pointer;
}
.wizard-permission input[type="checkbox"] {
  margin-top: 2px;
  flex-shrink: 0;
  accent-color: var(--brand-accent, #ff6b35);
  width: 16px;
  height: 16px;
}
.wizard-permission strong { color: var(--text-primary); font-weight: 600; }
.wizard-permission:has(input:checked) {
  background: rgba(16,185,129,0.04);
  border-color: rgba(16,185,129,0.30);
}
.pages-permission { margin: 0; }

.wizard-prompt-preview-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.wizard-prompt-preview-row {
  display: grid;
  grid-template-columns: 24px 1fr;
  gap: 10px;
  padding: 10px 12px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 8px;
}
.wizard-prompt-preview-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: var(--bg-subtle, #fafafa);
  color: var(--text-muted);
  font-size: 0.72rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.wizard-prompt-preview-body { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.wizard-prompt-preview-text {
  font-size: 0.85rem;
  color: var(--text-primary);
  line-height: 1.45;
}
.wizard-prompt-preview-meta {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}
.wizard-compare-foot {
  margin: 0;
  font-size: 0.78rem;
  color: var(--text-muted);
  line-height: 1.45;
}
.wizard-compare-foot strong { color: var(--text-primary); }

/* Description: upload + regenerate buttons share a row */
.wizard-textarea-actions { display: flex; gap: 8px; align-items: center; }
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Context sources: file upload zone */
.ctx-upload-zone {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  border: 1.5px dashed var(--border-color, #e5e7eb);
  border-radius: 12px;
  background: var(--bg-subtle, #fafafa);
  color: var(--text-muted);
  cursor: pointer;
  margin-bottom: 14px;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.ctx-upload-zone:hover, .ctx-upload-zone.dragging {
  border-color: var(--brand-accent, #ff6b35);
  background: rgba(255,107,53,0.04);
  color: var(--text-primary);
}
.ctx-upload-zone-text { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.ctx-upload-zone-text strong { color: var(--text-primary); font-weight: 600; font-size: 0.92rem; }
.ctx-upload-zone-text span { font-size: 0.78rem; }

.ctx-uploaded-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.ctx-uploaded-row {
  display: grid;
  grid-template-columns: 24px 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 10px;
}
.ctx-uploaded-row.errored { border-color: rgba(239,68,68,0.35); background: rgba(239,68,68,0.04); }
.ctx-uploaded-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px; height: 24px;
  border-radius: 6px;
  background: rgba(91,141,239,0.10);
  color: #1e40af;
}
.ctx-uploaded-row.errored .ctx-uploaded-icon { background: rgba(239,68,68,0.10); color: #b91c1c; }
.ctx-uploaded-body { min-width: 0; }
.ctx-uploaded-name {
  font-size: 0.88rem;
  font-weight: 500;
  color: var(--text-primary);
  word-break: break-word;
}
.ctx-uploaded-meta { font-size: 0.75rem; color: var(--text-muted); margin-top: 2px; }
.ctx-uploaded-remove {
  appearance: none;
  background: transparent;
  border: none;
  width: 24px; height: 24px;
  border-radius: 6px;
  font-size: 1.1rem;
  line-height: 1;
  color: var(--text-muted);
  cursor: pointer;
}
.ctx-uploaded-remove:hover { background: rgba(239,68,68,0.10); color: #ef4444; }

/* Context sources: cloud connectors */
.ctx-connectors {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}
@media (max-width: 640px) { .ctx-connectors { grid-template-columns: 1fr; } }
.ctx-connector {
  appearance: none;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
  background: var(--bg-card, #fff);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.ctx-connector:hover:not(:disabled) {
  border-color: var(--text-primary);
  box-shadow: 0 4px 14px -8px rgba(20,23,24,0.12);
}
.ctx-connector:disabled { cursor: not-allowed; opacity: 0.7; }
.ctx-connector-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--bg-subtle, #fafafa);
  flex-shrink: 0;
}
.ctx-connector-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.ctx-connector-name { font-size: 0.88rem; font-weight: 600; color: var(--text-primary); }
.ctx-connector-desc { font-size: 0.75rem; color: var(--text-muted); }
.ctx-connector-status {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--bg-subtle, #fafafa);
}
.ctx-connector:not(:disabled) .ctx-connector-status {
  color: #047857;
  background: rgba(16,185,129,0.12);
}
.ctx-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 8px 0 16px;
  color: var(--text-muted);
  font-size: 0.75rem;
}
.ctx-divider::before, .ctx-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-color, #e5e7eb);
}

/* Competitors: auto-suggestion chips */
.wc-suggestions {
  background: var(--bg-subtle, #fafafa);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 16px;
}
.wc-suggestions-label {
  display: block;
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 8px;
}
.wc-suggestions-chips { display: flex; gap: 6px; flex-wrap: wrap; }
.wc-suggestion-chip {
  appearance: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 999px;
  background: var(--bg-card, #fff);
  font-size: 0.8rem;
  color: var(--text-primary);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.wc-suggestion-chip:hover:not(:disabled) {
  border-color: var(--brand-accent, #ff6b35);
  background: rgba(255,107,53,0.05);
}
.wc-suggestion-chip:disabled { opacity: 0.5; cursor: not-allowed; }
.wc-suggestion-count { font-size: 0.7rem; color: var(--text-muted); }

/* Review flow visualization */
.wizard-flow {
  display: grid;
  grid-template-columns: 1fr auto 1fr auto 1fr auto 1fr;
  gap: 8px;
  align-items: stretch;
  background: var(--bg-subtle, #fafafa);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 12px;
}
@media (max-width: 900px) {
  .wizard-flow {
    grid-template-columns: 1fr;
    gap: 4px;
  }
  .wizard-flow-arrow {
    text-align: center;
    transform: rotate(90deg);
    padding: 2px 0;
  }
}
.wizard-flow-stage {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  text-align: center;
}
.wizard-flow-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  margin: 0 auto 4px;
}
.wizard-flow-icon-src { background: rgba(91,141,239,0.12); color: #1d4ed8; }
.wizard-flow-icon-prompt { background: rgba(167,139,250,0.14); color: #6d28d9; }
.wizard-flow-icon-models { background: rgba(255,107,53,0.12); color: #c2410c; }
.wizard-flow-icon-result { background: rgba(16,185,129,0.14); color: #047857; }
.wizard-flow-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}
.wizard-flow-count {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
.wizard-flow-sub {
  font-size: 0.72rem;
  color: var(--text-muted);
  line-height: 1.3;
}
.wizard-flow-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 1.1rem;
  font-weight: 300;
}
.wizard-flow-note {
  margin: 0 0 16px;
  line-height: 1.5;
}

/* Empty-state shown when the website has no audit data yet. */
.empty-dashboard {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 40px 20px;
}
.empty-dashboard-card {
  width: 100%;
  max-width: 520px;
  text-align: center;
  background: var(--bg-card, #ffffff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 16px;
  padding: 40px 32px;
  box-shadow: 0 20px 50px -28px rgba(20, 23, 24, 0.18);
}
.empty-dashboard-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: rgba(255, 107, 53, 0.10);
  color: var(--brand-accent, #ff6b35);
  margin-bottom: 18px;
}
.empty-dashboard-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 10px;
  letter-spacing: -0.01em;
}
.empty-dashboard-sub {
  font-size: 0.95rem;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0 0 24px;
}
.empty-dashboard-sub strong { color: var(--text-primary); }
.empty-dashboard-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  flex-wrap: wrap;
}

/* ── Tabs ────────────────────────────────────────────────────────────────── */
.lr-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  margin: 0 0 20px;
}
.lr-tab {
  appearance: none;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 10px 16px;
  font: inherit;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-muted, #6b7280);
  cursor: pointer;
  transition: color 0.15s ease, border-color 0.15s ease;
}
.lr-tab:hover { color: var(--text-primary); }
.lr-tab.active {
  color: var(--text-primary);
  border-bottom-color: var(--brand-accent, #ff6b35);
}
.lr-tab:focus-visible {
  outline: 2px solid var(--brand-accent, #ff6b35);
  outline-offset: 2px;
  border-radius: 4px;
}

/* ── Performance tab ─────────────────────────────────────────────────────── */
.lr-performance { display: flex; flex-direction: column; gap: 20px; }
.perf-empty {
  text-align: center;
  padding: 60px 20px;
  border: 1px dashed var(--border-color, #e5e7eb);
  border-radius: 14px;
  color: var(--text-secondary);
}
.perf-empty-icon {
  display: inline-flex;
  width: 56px; height: 56px;
  align-items: center; justify-content: center;
  border-radius: 14px;
  background: rgba(255, 107, 53, 0.10);
  color: var(--brand-accent, #ff6b35);
  margin-bottom: 14px;
}
.perf-empty h3 { margin: 0 0 6px; font-size: 1.1rem; color: var(--text-primary); }
.perf-empty p { margin: 0; font-size: 0.9rem; }

.perf-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}
@media (max-width: 900px) { .perf-kpis { grid-template-columns: repeat(2, 1fr); } }
.perf-kpi {
  background: var(--bg-card, #ffffff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
  padding: 16px 18px;
}
.perf-kpi-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  margin-bottom: 8px;
}
.perf-kpi-value {
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  line-height: 1.1;
}
.perf-kpi-value-sm { font-size: 1.15rem; font-weight: 600; }
.perf-kpi-unit { font-size: 0.85rem; font-weight: 500; color: var(--text-muted); margin-left: 2px; }
.perf-kpi-sub { font-size: 0.78rem; color: var(--text-muted); margin-top: 6px; }
.perf-trend-up { color: #10b981; }
.perf-trend-down { color: #ef4444; }
.perf-trend-flat { color: var(--text-muted); }

.perf-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
@media (max-width: 1024px) { .perf-grid { grid-template-columns: 1fr; } }
.perf-card { padding: 18px 20px 22px; }
.perf-card-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
}
.perf-card-head h3 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
}
.perf-card-sub { font-size: 0.78rem; color: var(--text-muted); }
.perf-chart { position: relative; height: 280px; }
.perf-heatmap { min-height: 200px; }
.perf-chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.perf-scorecards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}
.perf-scorecard {
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 10px;
  padding: 14px 16px;
  background: var(--bg-subtle, #fafafa);
}
.perf-scorecard-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.perf-scorecard-dot { width: 10px; height: 10px; border-radius: 50%; }
.perf-scorecard-name { font-size: 0.9rem; font-weight: 600; color: var(--text-primary); }
.perf-scorecard-metric { display: flex; align-items: baseline; gap: 6px; margin-bottom: 8px; }
.perf-scorecard-value { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); letter-spacing: -0.01em; }
.perf-scorecard-label { font-size: 0.78rem; color: var(--text-muted); }
.perf-scorecard-bar {
  height: 6px;
  border-radius: 999px;
  background: var(--border-color, #e5e7eb);
  overflow: hidden;
  margin-bottom: 8px;
}
.perf-scorecard-bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s ease;
}
.perf-scorecard-foot {
  display: flex;
  gap: 6px;
  font-size: 0.78rem;
  color: var(--text-muted);
}

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

/* Context Sources step */
.ctx-url-input-row {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.ctx-url-input-row .form-input {
  flex: 1;
}
.ctx-url-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ctx-url-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-md, 10px);
  border: 1.5px solid #10b981;
  background: rgba(16, 185, 129, 0.04);
  transition: all 0.2s;
}
.ctx-url-card.is-error {
  border-color: var(--color-danger, #EF4444);
  background: rgba(239, 68, 68, 0.04);
}
.ctx-url-scanning {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}
.ctx-url-status {
  flex-shrink: 0;
  margin-top: 2px;
}
.ctx-url-info {
  flex: 1;
  min-width: 0;
}
.ctx-url-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ctx-url-summary {
  margin-top: 2px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ctx-url-remove {
  flex-shrink: 0;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  color: var(--text-muted);
  padding: 0 4px;
  transition: color 0.2s;
}
.ctx-url-remove:hover {
  color: var(--color-danger, #EF4444);
}

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
.wizard-review-cost {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  padding: 8px 10px;
  border-radius: 6px;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}
.wizard-review-cost.over-cap {
  background: #fef2f2;
  border-color: #fecaca;
}
.wizard-review-cost-sub {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-muted);
  margin-left: 4px;
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
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 1rem;
  padding: 18px 18px 16px;
  position: relative;
  box-shadow: var(--shadow-sm);
  transition: transform 150ms ease-out, box-shadow 150ms ease-out, border-color 150ms ease-out;
}
.kpi-card:hover {
  border-color: var(--border-hover);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
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
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.bo-strength-bar {
  display: inline-block;
  width: 64px;
  height: 6px;
  border-radius: 3px;
  background: var(--bg-surface);
  overflow: hidden;
  vertical-align: middle;
}
.bo-strength-fill {
  display: block;
  height: 100%;
  background: var(--color-primary, #4f46e5);
  border-radius: 3px;
}
.bo-strength-num {
  min-width: 24px;
  text-align: right;
  font-size: 12px;
}
.kpi-conf-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}
.kpi-conf-high { background: var(--color-success, #16a34a); }
.kpi-conf-med  { background: var(--color-warning, #f59e0b); }
.kpi-conf-low  { background: var(--color-danger, #dc2626); }
.kpi-sub-muted { opacity: 0.7; margin-left: 4px; }

.bo-footprint-card { padding: 16px; }

/* Diagnostics section: heatmap stacks full-width above the
   radar+scatter row. The inner lr-grid-2 already exists and gives us
   the two-column behaviour for the lower row. */
.lr-diagnostics {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.bo-footprint-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}
.bo-footprint-row {
  display: grid;
  grid-template-columns: 28px 1fr 2fr 56px 48px;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}
.bo-footprint-flag { font-size: 18px; line-height: 1; }
.bo-footprint-name { color: var(--text-primary); font-weight: 500; }
.bo-footprint-bar {
  display: block;
  height: 8px;
  background: var(--bg-surface);
  border-radius: 4px;
  overflow: hidden;
}
.bo-footprint-fill {
  display: block;
  height: 100%;
  background: var(--color-primary, #4f46e5);
  border-radius: 4px;
}
.bo-footprint-num {
  font-variant-numeric: tabular-nums;
  text-align: right;
  color: var(--text-muted);
}
.bo-footprint-pct {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  text-align: right;
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

/* Audit Jobs — expandable rows */
.lr-audit-jobs {
  display: flex;
  flex-direction: column;
}
.lr-job-block {
  border-top: 1px solid var(--border-color);
}
.lr-job-block:first-child {
  border-top: none;
}
.lr-job-header {
  display: grid;
  grid-template-columns: 16px 100px 1fr 50px 60px 80px 80px 32px;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.15s;
  font-size: 13px;
}
.lr-job-header:hover {
  background: rgba(0,0,0,0.015);
}
.lr-job-header.is-active {
  background: rgba(79, 70, 229, 0.03);
}
.lr-job-cost-caption {
  font-size: 11.5px;
  color: var(--text-muted, #9ca3af);
  padding: 2px 0 8px 36px;
  letter-spacing: 0.02em;
}
.cap-modal-body { padding: 8px 4px 0; }
.cap-modal-msg {
  font-size: var(--font-base, 14px);
  margin: 0 0 8px;
  color: var(--text-primary);
}
.cap-modal-help {
  font-size: var(--font-sm, 13px);
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
}
.lr-job-chevron {
  transition: transform 0.2s ease;
  color: var(--text-muted);
  flex-shrink: 0;
}
.lr-job-chevron.open {
  transform: rotate(90deg);
}
.lr-job-date {
  font-size: 12px;
  color: var(--text-muted);
}
.lr-job-name {
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lr-job-score {
  text-align: center;
}
.lr-job-mention {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
}
.lr-job-queries {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
}
.lr-job-duration {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  text-align: center;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.lr-job-status {
  text-align: center;
}
.lr-run-btn {
  font-size: 11px;
  padding: 3px 10px;
  background: linear-gradient(135deg, #10b981, #059669);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  letter-spacing: 0.3px;
  transition: all 0.2s;
  white-space: nowrap;
}
.lr-run-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #059669, #047857);
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
}
.lr-run-btn:disabled {
  opacity: 0.7;
  cursor: wait;
}
.lr-job-actions {
  text-align: right;
}
.lr-job-detail {
  background: rgba(0,0,0,0.01);
  border-top: 1px solid var(--border-color);
}

/* Prompt job table inside expanded audit */
.lr-prompt-jobs {
  font-size: 12px;
}
.lr-prompt-header {
  display: grid;
  grid-template-columns: 30px 1fr 80px 100px 90px;
  gap: 8px;
  padding: 8px 16px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-color);
}
.lr-prompt-row {
  display: grid;
  grid-template-columns: 30px 1fr 80px 100px 90px;
  gap: 8px;
  padding: 8px 16px;
  align-items: center;
  border-bottom: 1px solid rgba(0,0,0,0.03);
  transition: background 0.15s;
}
.lr-prompt-row:hover {
  background: rgba(0,0,0,0.015);
}
.lr-prompt-row:last-child {
  border-bottom: none;
}
.lr-pr-num {
  font-weight: 600;
  color: var(--text-muted);
  font-size: 11px;
}
.lr-pr-prompt {
  color: var(--text-primary);
  line-height: 1.4;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.lr-pr-prompt-text { font-weight: 500; }
.lr-pr-rationale {
  font-size: 11px;
  color: var(--text-muted, #9CA3AF);
  font-style: italic;
  line-height: 1.4;
}
.lr-pr-type {
  text-align: center;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 3px;
}
.lr-pr-stage-bottom { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.lr-pr-stage-mid    { background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }
.lr-pr-stage-top    { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
.lr-pr-stage-niche  { background: #f9fafb; color: #4b5563; border: 1px solid #e5e7eb; }
.lr-pr-providers {
  display: flex;
  gap: 3px;
  flex-wrap: wrap;
}
.lr-pr-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  font-size: 8px;
  font-weight: 800;
  color: var(--text-muted);
}
.lr-pr-result {
  text-align: center;
}

/* AI Visibility Score — compact widget */
.lr-score-widget {
  padding: 0;
  overflow: hidden;
}
.lr-score-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 18px;
}
.lr-score-mini-ring {
  position: relative;
  width: 42px;
  height: 42px;
  flex-shrink: 0;
}
.lr-mini-svg {
  width: 42px;
  height: 42px;
}
.lr-mini-num {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 12px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}
.lr-score-info {
  flex: 1;
  min-width: 0;
}
.lr-score-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 3px;
}
.lr-score-sub {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}
.lr-score-progress {
  width: 120px;
  flex-shrink: 0;
}
.lr-score-detail {
  border-top: 1px solid var(--border-color);
}

/* LLM Systems compact dropdown */
.lr-systems-dropdown {
  padding: 0;
  overflow: hidden;
}
.lr-systems-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  gap: 12px;
}
.lr-systems-left {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.lr-systems-pills {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.lr-sys-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 100px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.01em;
}
.lr-sys-pill.lr-sys-on {
  background: rgba(16, 185, 129, 0.08);
  color: #059669;
  border: 1px solid rgba(16, 185, 129, 0.15);
}
.lr-sys-pill.lr-sys-on .provider-status-dot {
  background: #10B981;
}
.lr-sys-pill.lr-sys-off {
  background: rgba(107, 114, 128, 0.06);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
}
.lr-systems-chevron {
  color: var(--text-muted);
  transition: transform 0.2s ease;
  flex-shrink: 0;
}
.lr-systems-chevron.open {
  transform: rotate(180deg);
}
.lr-systems-list {
  border-top: 1px solid var(--border-color);
  padding: 8px 0;
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

.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }

/* Header actions */
.header-actions { display: flex; gap: 8px; align-items: center; }

/* Schedule banner */
.schedule-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: var(--radius-md);
  background: rgba(167, 139, 250, 0.08);
  border: 1px solid rgba(167, 139, 250, 0.2);
  margin-bottom: 20px;
  font-size: var(--font-sm);
  color: var(--text-secondary);
}
.schedule-banner strong { color: var(--text-primary); }
.btn-xs { font-size: var(--font-xs); padding: 2px 8px; }

.schedule-card {
  border: 1px solid var(--border-color);
  border-radius: 1rem;
  background: var(--bg-card);
  padding: 16px 18px;
  margin-bottom: 20px;
  box-shadow: var(--shadow-sm);
  transition: transform 150ms ease-out, box-shadow 150ms ease-out, border-color 150ms ease-out;
}
.schedule-card:hover {
  border-color: var(--border-hover);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.schedule-card-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; margin-bottom: 12px;
}
.schedule-card-title {
  display: flex; align-items: center; gap: 8px;
  font-weight: 600; color: var(--text-primary); font-size: var(--font-sm);
}
.schedule-card-actions { display: flex; gap: 6px; }
.schedule-pill {
  font-size: var(--font-xs); padding: 2px 8px; border-radius: 999px;
  background: rgba(34, 197, 94, 0.12); color: rgb(22, 163, 74);
  border: 1px solid rgba(34, 197, 94, 0.25);
}
.schedule-pill.paused {
  background: rgba(148, 163, 184, 0.18); color: var(--text-secondary);
  border-color: rgba(148, 163, 184, 0.35);
}
.schedule-card-body {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
}
@media (max-width: 720px) { .schedule-card-body { grid-template-columns: repeat(2, 1fr); } }
.schedule-cell-label {
  font-size: var(--font-xs); color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px;
}
.schedule-cell-value { font-size: var(--font-sm); color: var(--text-primary); font-weight: 600; }
.schedule-progress { margin-top: 12px; }
.schedule-progress-row {
  display: flex; justify-content: space-between;
  font-size: var(--font-xs); color: var(--text-secondary); margin-bottom: 6px;
}
.schedule-progress-bar {
  height: 6px; background: var(--border-color); border-radius: 999px; overflow: hidden;
}
.schedule-progress-fill {
  height: 100%; background: #FF6A2C; transition: width 0.5s ease;
}
.schedule-warn {
  margin-top: 10px; padding: 8px 10px;
  font-size: var(--font-xs); color: rgb(180, 83, 9);
  background: rgba(245, 158, 11, 0.10); border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: var(--radius-sm);
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
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 1rem;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  text-align: center;
  box-shadow: var(--shadow-sm);
  transition: transform 150ms ease-out, box-shadow 150ms ease-out, border-color 150ms ease-out;
}
.provider-card:hover {
  border-color: var(--border-hover);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
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

/* Charts row */
.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 20px;
}
.chart-card { overflow: hidden; }
.chart-wrap {
  padding: 16px;
  height: 260px;
}

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
  border-radius: 1rem;
  padding: 14px 18px;
  background: var(--bg-card);
  box-shadow: var(--shadow-sm);
  transition: transform 150ms ease-out, box-shadow 150ms ease-out, border-color 150ms ease-out;
}
.finding-card:hover {
  border-color: var(--border-hover);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
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
  grid-template-columns: 1fr 70px 100px 70px 130px 180px 110px;
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
  grid-template-columns: 1fr 70px 100px 70px 130px 180px 110px;
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
  grid-template-columns: 1fr 70px 100px 70px 130px 180px 110px;
  padding: 10px 20px 10px 44px;
  border-bottom: 1px solid var(--border-color, #E5E7EB);
  align-items: center;
  background: var(--bg-offset, #FAFAFA);
  font-size: 13px;
  cursor: pointer;
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
  align-items: flex-start;
}
.pt-prompt-block {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex: 1;
  min-width: 0;
}
.pt-prompt-headline {
  font-weight: 500;
  color: var(--text-primary, #111);
  font-size: 13px;
  line-height: 1.35;
}
.pt-prompt-rationale {
  font-size: 11.5px;
  font-style: italic;
  color: var(--text-muted, #9CA3AF);
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
.pt-status-pill.is-partial {
  color: #b45309;
  border-color: #fde68a;
  background: #fffbeb;
}
.pt-status-pill.is-fail {
  color: #b91c1c;
  border-color: #fecaca;
  background: #fef2f2;
}

/* Score column */
.pt-td-score {
  font-size: 14px;
  font-weight: 700;
  justify-content: center;
}
.pt-td-vis { justify-content: center; }

/* Top Keywords column */
.pt-td-keywords {
  flex-wrap: wrap;
  gap: 4px;
  overflow: hidden;
}
.pt-kw-chip {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: #eff6ff;
  color: #1e40af;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}
.pt-kw-chip-strong {
  background: #dbeafe;
  color: #1e3a8a;
  font-weight: 600;
  margin: 2px 4px 2px 0;
}
.pt-kw-empty { color: var(--text-muted, #9CA3AF); font-size: 12px; }

/* Provider rank sub-badge (e.g. "C" with #2) */
.pt-perf-rank {
  position: absolute;
  bottom: -4px;
  right: -4px;
  font-size: 8px;
  font-weight: 700;
  background: var(--text-primary, #111);
  color: #fff;
  border-radius: 8px;
  padding: 1px 4px;
  line-height: 1;
}
.pt-perf-icon { position: relative; }

/* Prompt expand chevron */
.pi-chevron-prompt {
  margin-right: 4px;
  transition: transform 0.15s;
  color: var(--text-muted);
}
.pi-chevron-prompt.open { transform: rotate(90deg); }

/* Per-prompt expansion panel */
.pt-prompt-detail {
  padding: 16px 20px 20px 44px;
  background: var(--bg-base, #fff);
  border-bottom: 1px solid var(--border-color, #E5E7EB);
  border-left: 3px solid #3b82f6;
}
.pt-detail-summary {
  display: flex;
  gap: 32px;
  padding-bottom: 14px;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--border-color, #E5E7EB);
}
.pt-detail-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.pt-detail-stat-label {
  font-size: 10.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}
.pt-detail-stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}
.pt-sentiment { font-size: 13px; text-transform: capitalize; }
.pt-sentiment-positive { color: #059669; }
.pt-sentiment-neutral { color: #4b5563; }
.pt-sentiment-negative { color: #dc2626; }
.pt-sentiment-not_mentioned { color: #9ca3af; }

/* ── GEO domain tagger (paper: arXiv 2311.09735) ───────────────── */
.pt-geo-badge {
  display: inline-flex;
  align-items: center;
  margin-left: 8px;
  padding: 1px 7px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.02em;
  vertical-align: middle;
}
.pt-geo-tactic {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 6px;
  padding: 1px 7px 1px 6px;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  background: #f8fafc;
  color: #334155;
  font-size: 11px;
  font-weight: 500;
  vertical-align: middle;
}
.pt-geo-tactic svg { color: #16a34a; flex-shrink: 0; }
.pt-geo-lift {
  margin-left: 2px;
  padding-left: 5px;
  border-left: 1px solid #e2e8f0;
  color: #16a34a;
  font-weight: 600;
}

.pt-geo-block { background: #fafbff; border-radius: 8px; padding: 12px; }
.pt-geo-block-cat {
  display: inline-flex;
  margin-left: 8px;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0;
}
.pt-geo-block-sub {
  margin: 6px 0 12px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-muted, #64748b);
}
.pt-geo-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.pt-geo-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
.pt-geo-rank {
  flex-shrink: 0;
  width: 26px;
  font-size: 12px;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: -0.02em;
}
.pt-geo-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.pt-geo-label { font-size: 13px; font-weight: 600; color: #0f172a; }
.pt-geo-summary { font-size: 12px; line-height: 1.45; color: #475569; }
.pt-geo-lift-pill {
  flex-shrink: 0;
  align-self: center;
  padding: 3px 8px;
  border-radius: 999px;
  background: #ecfdf5;
  color: #047857;
  font-size: 11px;
  font-weight: 700;
}

.pt-detail-section {
  margin-top: 12px;
}
.pt-detail-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 8px;
}
.pt-detail-row {
  display: grid;
  grid-template-columns: 110px 90px 1fr;
  gap: 12px;
  padding: 6px 0;
  font-size: 12.5px;
  align-items: baseline;
}
.pt-detail-prov { font-weight: 600; color: var(--text-primary); }
.pt-detail-rank { font-weight: 600; color: #059669; }
.pt-detail-rank.pt-detail-miss { color: var(--text-muted); font-weight: 500; }
.pt-detail-rank.pt-detail-fail { color: #dc2626; font-weight: 500; }
.pt-detail-context {
  color: var(--text-secondary);
  font-style: italic;
  line-height: 1.45;
}

/* Per-provider response card (expandable + copyable) */
.pt-resp-card {
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 8px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.pt-resp-card:hover { border-color: rgba(255, 107, 53, 0.35); box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04); }
.pt-resp-head {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  margin-bottom: 8px;
}
.pt-resp-prov-dot {
  width: 8px; height: 8px; border-radius: 9999px;
  background: #cbd5e1;
  flex-shrink: 0;
}
.pt-resp-prov-dot.isclaude   { background: #d97706; }
.pt-resp-prov-dot.isgpt4     { background: #10b981; }
.pt-resp-prov-dot.isgemini   { background: #4285f4; }
.pt-resp-prov-dot.isperplexity { background: #5b6cff; }
.pt-resp-prov {
  font-weight: 600;
  font-size: 13px;
  color: #0f172a;
}
.pt-resp-badge {
  display: inline-flex; align-items: center;
  padding: 2px 9px;
  font-size: 11px; font-weight: 600;
  border-radius: 9999px;
  text-transform: lowercase;
  letter-spacing: 0.01em;
}
.pt-resp-badge.is-hit { background: rgba(16, 185, 129, 0.12); color: #047857; }
.pt-resp-badge.is-miss { background: rgba(15, 23, 42, 0.06); color: #64748b; }
.pt-resp-badge.is-fail { background: rgba(220, 38, 38, 0.10); color: #b91c1c; }
.pt-resp-badge.pt-sentiment-positive { background: rgba(16, 185, 129, 0.12); color: #047857; }
.pt-resp-badge.pt-sentiment-neutral  { background: rgba(15, 23, 42, 0.06);  color: #475569; }
.pt-resp-badge.pt-sentiment-negative { background: rgba(220, 38, 38, 0.10); color: #b91c1c; }
.pt-resp-actions {
  margin-left: auto;
  display: inline-flex; gap: 6px;
}
.pt-resp-btn {
  border: 1px solid rgba(15, 23, 42, 0.10);
  background: #ffffff;
  color: #1f2937;
  font-size: 11.5px;
  font-weight: 600;
  border-radius: 7px;
  padding: 4px 10px;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.pt-resp-btn:hover {
  background: #ff6b35;
  border-color: #ff6b35;
  color: #ffffff;
}
.pt-resp-body {
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px 12px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  max-height: 96px;
  overflow: hidden;
  position: relative;
  transition: max-height 0.25s ease;
}
.pt-resp-body.is-expanded {
  max-height: none;
}
.pt-resp-body:not(.is-expanded)::after {
  content: '';
  position: absolute; left: 0; right: 0; bottom: 0; height: 32px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0) 0%, rgba(248, 250, 252, 1) 100%);
  pointer-events: none;
}
.pt-resp-text {
  font-size: 12.5px;
  line-height: 1.55;
  color: #334155;
  white-space: pre-wrap;
}
.pt-resp-empty {
  font-size: 12px;
  color: #94a3b8;
  font-style: italic;
}

.pt-comp-chip {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 4px;
  background: var(--bg-offset, #f3f4f6);
  color: var(--text-primary);
  font-size: 11.5px;
  margin: 2px 4px 2px 0;
}
.pt-comp-chip sub {
  font-size: 9px;
  color: var(--text-muted);
  margin-left: 3px;
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
/* Prompt Activity — chronological per-query record */
.prompt-activity-head,
.prompt-activity-row {
  display: grid;
  grid-template-columns: 84px 110px 200px 1fr 130px;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  font-size: 13px;
}
.prompt-activity-head {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-color);
  padding-top: 12px;
  padding-bottom: 8px;
}
.prompt-activity-list {
  max-height: 480px;
  overflow-y: auto;
}
.prompt-activity-row {
  border-bottom: 1px solid var(--border-color);
  border-left: 3px solid transparent;
}
.prompt-activity-row:last-child { border-bottom: none; }
.prompt-activity-row:hover { background: var(--bg-surface); }
.prompt-activity-row.pa-hit { border-left-color: var(--color-success, #10B981); }
.prompt-activity-row.pa-fail { border-left-color: var(--color-danger, #DC2626); opacity: 0.85; }
.pa-time {
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
  font-size: 12px;
}
.pa-provider {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: var(--text-primary);
}
.pa-provider-dot {
  width: 8px; height: 8px; border-radius: 50%;
  display: inline-block;
}
.pa-model {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pa-prompt {
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pa-status { text-align: right; }

/* Prompt Activity filters */
.pa-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-base);
  flex-wrap: wrap;
}
.pa-filter-search {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 200px;
  max-width: 360px;
}
.pa-filter-search svg {
  position: absolute;
  left: 10px;
  color: var(--text-muted);
  pointer-events: none;
}
.pa-filter-input {
  width: 100%;
  padding: 6px 10px 6px 30px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  font-size: 13px;
  color: var(--text-primary);
}
.pa-filter-input:focus {
  outline: none;
  border-color: var(--brand-accent, #4F46E5);
}
.pa-filter-select {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  font-size: 13px;
  color: var(--text-primary);
  cursor: pointer;
}
.pa-filter-clear {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: transparent;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
}
.pa-filter-clear:hover {
  background: var(--bg-surface);
  color: var(--text-primary);
}
.pa-empty {
  padding: 32px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
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

/* ═══ Prompt Results Table ═══ */
.pr-filters { display: flex; gap: 8px; margin-left: auto; }
.pr-select {
  font-size: 12px; padding: 4px 8px; border-radius: 6px;
  border: 1px solid var(--border-color); background: #fff;
  color: var(--text-primary); cursor: pointer;
}
.pr-table-wrap { overflow-x: auto; }
.pr-table { width: 100%; border-collapse: collapse; }
.pr-table th {
  text-align: left; font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--text-muted); padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
}
.pr-row { border-bottom: 1px solid rgba(0,0,0,0.04); transition: background 0.15s; }
.pr-row:hover { background: rgba(0,0,0,0.015); }
.pr-row td { padding: 10px 12px; font-size: 13px; vertical-align: middle; }
.pr-num { font-weight: 600; color: var(--text-muted); font-size: 11px; }
.pr-prompt { max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pr-vis-wrap { display: flex; align-items: center; gap: 6px; }
.pr-vis-bar { width: 48px; height: 5px; background: rgba(0,0,0,0.06); border-radius: 3px; overflow: hidden; }
.pr-vis-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.pr-vis-fill.vis-high { background: linear-gradient(90deg, #10B981, #34D399); }
.pr-vis-fill.vis-mid  { background: linear-gradient(90deg, #F59E0B, #FBBF24); }
.pr-vis-fill.vis-low  { background: linear-gradient(90deg, #EF4444, #F87171); }
.pr-vis-pct { font-size: 11px; font-weight: 700; }
.pr-vis-pct.vis-high { color: #059669; }
.pr-vis-pct.vis-mid  { color: #D97706; }
.pr-vis-pct.vis-low  { color: #DC2626; }
.pr-providers { display: flex; gap: 3px; flex-wrap: wrap; }
.pr-prov-pill {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: 4px; font-size: 10px;
  font-weight: 700; cursor: pointer; transition: all 0.15s;
  background: rgba(0,0,0,0.06); color: var(--text-muted);
}
.pr-prov-pill.mentioned { background: #D1FAE5; color: #059669; }
.pr-prov-pill.failed { background: #FEE2E2; color: #DC2626; }
.pr-prov-pill:hover { transform: scale(1.15); box-shadow: 0 2px 8px rgba(0,0,0,0.12); }

/* ═══ Usage Meter ═══ */
.usage-grid {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 16px; padding: 16px;
}
.usage-stat { text-align: center; }
.usage-val { font-size: 22px; font-weight: 700; color: var(--text-primary); }
.usage-label { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.usage-models { padding: 0 16px 16px; }
.usage-model-header {
  display: grid; grid-template-columns: 2fr 1fr 1fr 1fr;
  font-size: 10px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--text-muted);
  padding: 6px 0; border-bottom: 1px solid var(--border-color);
}
.usage-model-row {
  display: grid; grid-template-columns: 2fr 1fr 1fr 1fr;
  font-size: 12px; padding: 8px 0;
  border-bottom: 1px solid rgba(0,0,0,0.03);
}
.usage-model-name { font-weight: 600; color: var(--text-primary); font-family: 'SF Mono', monospace; font-size: 11px; }

/* ═══ Provider Detail Modal ═══ */
.pd-content { padding: 0 4px; }
.pd-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
.pd-stat { text-align: center; padding: 12px; border-radius: 8px; background: rgba(0,0,0,0.02); }
.pd-stat-val { font-size: 24px; font-weight: 700; }
.pd-stat-val.vis-high { color: #059669; }
.pd-stat-val.vis-mid { color: #D97706; }
.pd-stat-val.vis-low { color: #DC2626; }
.pd-stat-label { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.pd-section { margin-bottom: 20px; }
.pd-section-title { font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
.pd-sentiment-bar {
  display: flex; height: 24px; border-radius: 6px; overflow: hidden;
  background: rgba(0,0,0,0.04); font-size: 11px; font-weight: 600;
}
.pd-sent-seg {
  display: flex; align-items: center; justify-content: center;
  color: #fff; min-width: 24px; transition: width 0.3s ease;
}
.pd-sent-seg.positive { background: #10B981; }
.pd-sent-seg.neutral  { background: #F59E0B; }
.pd-sent-seg.negative { background: #EF4444; }
.pd-comp-list { display: flex; flex-wrap: wrap; gap: 8px; }
.pd-comp {
  display: flex; align-items: center; gap: 4px; padding: 4px 10px;
  border-radius: 6px; background: rgba(0,0,0,0.04); font-size: 12px;
}
.pd-comp-name { font-weight: 600; }
.pd-comp-count { color: var(--text-muted); font-size: 11px; }
.text-center { text-align: center; }

/* Page context line under the page-subtitle */
.page-context {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}
.page-context-link {
  margin-left: 8px;
  font-size: 12px;
  color: var(--brand-accent, #4F46E5);
  text-decoration: none;
}
.page-context-link:hover { text-decoration: underline; }

/* Pages-to-scan step (Step 0 of the run-audit wizard) */
.wizard-link-inline {
  margin-left: 6px;
  font-size: 12px;
  color: var(--brand-accent, #4F46E5);
  text-decoration: none;
}
.wizard-link-inline:hover { text-decoration: underline; }

.wizard-pages-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}
.wizard-page-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
}
.wizard-page-row.is-homepage {
  border-style: dashed;
  background: var(--bg-base);
}
.wizard-page-icon {
  width: 20px; text-align: center;
  font-size: 14px;
  color: var(--text-muted);
}
.wizard-page-meta { flex: 1; min-width: 0; }
.wizard-page-url {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wizard-page-remove {
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 16px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}
.wizard-page-remove:hover {
  background: var(--bg-base);
  color: var(--color-danger, #DC2626);
}

/* Prompt-source provenance badges (Phase 1 prompt_library wiring). */
.badge-source {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 500;
  vertical-align: middle;
  line-height: 1.4;
}
.badge-library {
  background: rgba(59, 130, 246, 0.10);
  color: #1d4ed8;
}
.badge-vault {
  background: rgba(107, 114, 128, 0.12);
  color: #4b5563;
}
.badge-custom {
  background: rgba(139, 92, 246, 0.12);
  color: #6d28d9;
}
.badge-citation {
  background: rgba(236, 72, 153, 0.12);
  color: #be185d;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 500;
}
.badge-citation:hover {
  background: rgba(236, 72, 153, 0.2);
}
</style>
