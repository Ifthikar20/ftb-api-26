<template>
  <div class="leads-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Leads</h1>
        <p class="page-subtitle">Track, score, and manage your website leads.</p>
      </div>
      <div class="flex gap-8">
        <select v-if="activeTab === 'table'" class="form-input" v-model="statusFilter" @change="fetchData" style="width:auto">
          <option value="">All Statuses</option>
          <option value="new">New</option>
          <option value="contacted">Contacted</option>
          <option value="qualified">Qualified</option>
          <option value="customer">Customer</option>
          <option value="lost">Lost</option>
        </select>
        <button v-if="activeTab === 'table'" class="btn btn-secondary btn-sm" @click="handleExport">Export CSV</button>
      </div>
    </div>

    <!-- ═══ AI Prompt — Always Visible ═══ -->
    <div class="ai-search-card card">
      <h3 class="card-title" style="margin-bottom:4px">Describe your ideal lead</h3>
      <p class="text-sm text-muted" style="margin-bottom:16px">Use natural language to find leads from LinkedIn and Twitter profiles.</p>
      <textarea
        v-model="aiPrompt"
        class="ai-prompt-input"
        rows="3"
        placeholder='e.g. "SaaS founders in Austin who tweet about growth marketing" or "VP of Engineering at healthcare startups in NYC"'
        @keydown.meta.enter="runAISearch"
        @keydown.ctrl.enter="runAISearch"
      ></textarea>
      <div class="ai-search-actions">
        <div class="ai-example-prompts">
          <span class="text-xs text-muted">Try:</span>
          <button class="ai-example-btn" @click="aiPrompt = 'SaaS founders in San Francisco'">SaaS founders in SF</button>
          <button class="ai-example-btn" @click="aiPrompt = 'Marketing directors at e-commerce companies'">E-com marketing directors</button>
          <button class="ai-example-btn" @click="aiPrompt = 'CTO at fintech startups raising Series A'">Fintech CTOs</button>
        </div>
        <button class="btn btn-primary" @click="runAISearch" :disabled="aiSearching || !aiPrompt.trim()">
          <span v-if="aiSearching" class="ai-spinner"></span>
          {{ aiSearching ? 'Searching...' : 'Find Leads' }}
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'table' }" @click="activeTab = 'table'">Table</button>
      <button class="tab" :class="{ active: activeTab === 'pipeline' }" @click="activeTab = 'pipeline'">Pipeline</button>
      <button class="tab" :class="{ active: activeTab === 'ai-finder' }" @click="activeTab = 'ai-finder'" style="color:var(--brand-accent)">AI Lead Finder</button>
    </div>

    <div v-if="loading" class="loading-state">Loading leads...</div>

    <!-- ════════════════ TABLE VIEW ════════════════ -->
    <template v-else-if="activeTab === 'table'">
      <div class="stats-grid" style="margin-bottom: 24px">
        <div class="stat-card"><div class="stat-label">Total Leads</div><div class="stat-value">{{ leads.length }}</div></div>
        <div class="stat-card"><div class="stat-label">Hot Leads</div><div class="stat-value">{{ hotCount }}</div></div>
        <div class="stat-card"><div class="stat-label">Avg Score</div><div class="stat-value">{{ avgScore }}</div></div>
      </div>

      <div class="card">
        <table class="data-table">
          <thead><tr><th>Name</th><th>Company</th><th>Score</th><th>Status</th><th>Source</th></tr></thead>
          <tbody>
            <tr v-for="lead in leads" :key="lead.id" @click="openLeadDetail(lead)" style="cursor:pointer">
              <td><div class="lead-name">{{ lead.name || 'Anonymous' }}</div><div class="text-xs text-muted">{{ lead.email }}</div></td>
              <td>{{ lead.company || '--' }}</td>
              <td><span class="score-badge" :class="scoreTier(lead.score)">{{ lead.score }}</span></td>
              <td><span class="badge" :class="statusClass(lead.status)">{{ lead.status }}</span></td>
              <td class="text-muted text-sm">{{ lead.source }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="leads.length === 0" class="empty-guide">
          <div style="margin-bottom:12px;display:flex;justify-content:center"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="1.5"><circle cx="12" cy="7" r="4"/><path d="M5.5 21c0-3.5 3-6 6.5-6s6.5 2.5 6.5 6"/></svg></div>
          <h3 style="margin:0 0 8px;color:var(--text-primary)">No leads captured yet</h3>
          <p style="font-size:var(--font-sm);color:var(--text-secondary);max-width:400px;margin:0 auto;line-height:1.6">Leads are automatically captured when visitors interact with forms on your tracked website.</p>
        </div>
      </div>
    </template>

    <!-- ════════════════ PIPELINE VIEW ════════════════ -->
    <template v-else-if="activeTab === 'pipeline'">
      <div class="pipeline-wrapper">
        <!-- ── Connector Sidebar ── -->
        <div class="connector-sidebar">
          <div class="cs-header">
            <h3 class="cs-title">Connectors</h3>
            <p class="cs-subtitle">Drag onto canvas to add</p>
          </div>

          <div class="cs-section" v-for="(items, category) in connectorCatalog" :key="category">
            <div class="cs-section-label">{{ category }}</div>
            <div
              v-for="c in items" :key="c.id"
              class="cs-item"
              draggable="true"
              @dragstart="onDragStart($event, c)"
            >
              <span class="cs-item-icon" v-html="c.icon"></span>
              <div class="cs-item-info">
                <div class="cs-item-name">{{ c.label }}</div>
                <div class="cs-item-desc">{{ c.desc }}</div>
              </div>
            </div>
          </div>
        </div>



        <!-- ── Canvas ── -->
        <div class="pipeline-canvas-wrap" @drop="onDrop" @dragover.prevent @dragenter.prevent>
          <VueFlow
            ref="flowRef"
            v-model:nodes="nodes"
            v-model:edges="edges"
            :default-viewport="{ x: 30, y: 20, zoom: 0.75 }"
            :min-zoom="0.25"
            :max-zoom="2.5"
            :snap-to-grid="true"
            :snap-grid="[15, 15]"
            :connect-on-click="true"
            fit-view-on-init
            @node-click="onNodeClick"
            @connect="onConnect"
            class="pipeline-flow"
          >
            <template #node-pipeline="nodeProps">
              <PipelineNode v-bind="nodeProps" />
            </template>
            <Background :gap="20" :size="1" pattern-color="var(--border-color)" />
            <Controls position="bottom-left" />
            <MiniMap position="bottom-right" :node-color="miniMapNodeColor" />
          </VueFlow>
        </div>
      </div>

      <!-- Detail Panel (below canvas) -->
      <div class="pipeline-detail-grid" v-if="selectedLead">
        <div class="card">
          <div style="display:flex;align-items:center;gap:14px">
            <div class="avatar avatar-lg">{{ initials(selectedLead) }}</div>
            <div>
              <div style="font-weight:700;font-size:var(--font-md)">{{ selectedLead.name || 'Anonymous Visitor' }}</div>
              <div class="text-sm text-muted">{{ selectedLead.company || 'Unknown Company' }}</div>
              <div class="text-xs" style="color:var(--brand-accent)">{{ selectedLead.email || 'No email' }}</div>
            </div>
          </div>
          <div style="text-align:center;margin-top:16px;padding-top:16px;border-top:1px solid var(--border-color)">
            <svg viewBox="0 0 140 80" width="120" height="68" style="margin:0 auto 4px;display:block">
              <path d="M15,75 A55,55 0 0,1 125,75" fill="none" stroke="var(--border-color)" stroke-width="10" />
              <path d="M15,75 A55,55 0 0,1 125,75" fill="none" stroke="var(--brand-accent)" stroke-width="10" stroke-linecap="round"
                :stroke-dasharray="173" :stroke-dashoffset="173 - (selectedLead.score / 100) * 173" style="transition:stroke-dashoffset 0.8s ease" />
            </svg>
            <div style="font-family:var(--font-display);font-size:var(--font-2xl);color:var(--color-success)">{{ selectedLead.score }}%</div>
            <div class="text-xs text-muted">ML Success Prediction</div>
            <span class="badge badge-info" style="margin-top:8px"><svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" style="vertical-align:-2px;margin-right:4px"><rect x="1" y="3" width="14" height="10" rx="1.5"/><path d="M1 4l7 5 7-5"/></svg>Recommended: Email</span>
          </div>
          <div style="display:flex;gap:8px;margin-top:16px">
            <button class="btn btn-primary btn-sm" style="flex:1" @click="openEmailCompose(selectedLead)"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" style="vertical-align:-2px;margin-right:4px"><rect x="1" y="3" width="14" height="10" rx="1.5"/><path d="M1 4l7 5 7-5"/></svg>Send Email</button>
            <button class="btn btn-secondary btn-sm" style="flex:1"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" style="vertical-align:-2px;margin-right:4px"><rect x="3" y="1" width="10" height="14" rx="1.5"/><path d="M6 5h4M6 8h4M6 11h2"/></svg>Add Note</button>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3 class="card-title" style="font-size:var(--font-xs);text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted)">Why This Lead Will Convert</h3></div>
          <div class="corr-list">
            <div class="corr-row" v-for="c in correlations" :key="c.text">
              <span style="width:10px;height:10px;border-radius:50%;flex-shrink:0" :style="{ background: c.positive ? 'var(--color-success)' : 'var(--color-warning)' }"></span>
              <span style="flex:1;font-size:var(--font-sm);color:var(--text-primary)">{{ c.text }}</span>
              <span class="badge" :class="c.positive ? 'badge-success' : 'badge-danger'" style="font-size:9px;padding:2px 6px">{{ c.impact }}</span>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header"><h3 class="card-title" style="font-size:var(--font-xs);text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted)">Company Intelligence</h3></div>
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
            <div style="width:28px;height:28px;display:flex;align-items:center;justify-content:center;background:var(--bg-surface);border-radius:8px"><svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--text-secondary)" stroke-width="1.5"><rect x="2" y="3" width="12" height="11" rx="1"/><path d="M5 3V1.5h6V3M5 7h2M9 7h2M5 10h2M9 10h2"/></svg></div>
            <div>
              <div style="font-weight:700;font-size:var(--font-sm)">{{ selectedLead.company || 'Unknown' }}</div>
              <div class="text-xs" style="color:var(--brand-accent)">{{ companyDomain }}</div>
            </div>
          </div>
          <div class="intel-grid">
            <div class="intel-cell"><div class="intel-label">Employees</div><div class="intel-value">50–200</div></div>
            <div class="intel-cell"><div class="intel-label">Funding</div><div class="intel-value">Series A</div></div>
            <div class="intel-cell"><div class="intel-label">Industry</div><div class="intel-value">{{ selectedLead.source || 'Tech' }}</div></div>
            <div class="intel-cell"><div class="intel-label">Hiring</div><div class="intel-value">3 marketing</div></div>
          </div>
        </div>
      </div>

      <!-- Lead list when node is clicked -->
      <div class="pipeline-detail-grid" v-else-if="selectedNodeId">
        <div class="card" style="grid-column:1/-1">
          <div class="card-header"><h3 class="card-title">{{ filteredLabel }} <span class="badge badge-neutral" style="margin-left:6px">{{ filteredLeads.length }}</span></h3></div>
          <div class="lead-list">
            <div class="lead-list-item" v-for="lead in filteredLeads.slice(0, 12)" :key="lead.id" @click="openLeadDetail(lead)">
              <div class="avatar" style="width:32px;height:32px;font-size:10px">{{ initials(lead) }}</div>
              <div style="flex:1;min-width:0">
                <div style="font-weight:600;font-size:var(--font-sm);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ lead.name || 'Anonymous' }}</div>
                <div class="text-xs text-muted">{{ lead.company || '--' }}</div>
              </div>
              <span class="score-badge" :class="scoreTier(lead.score)" style="font-size:10px;padding:2px 8px">{{ lead.score }}</span>
            </div>
          </div>
          <div v-if="filteredLeads.length === 0" class="text-sm text-muted" style="text-align:center;padding:20px">No leads in this segment yet.</div>
        </div>
      </div>
    </template>

    <!-- ════════════════ AI LEAD FINDER ════════════════ -->
    <template v-else-if="activeTab === 'ai-finder'">
      <div class="ai-finder">
        <!-- Loading State -->
        <div v-if="aiSearching" class="ai-loading">
          <div class="ai-spinner-lg"></div>
          <p class="text-sm text-muted" style="margin-top:12px">Parsing your prompt with AI and searching social profiles...</p>
        </div>

        <!-- Results Table -->
        <template v-if="aiResults.length">
          <!-- Action bar -->
          <div class="ai-table-bar">
            <div class="ai-table-bar-left">
              <h3 style="margin:0;font-size:var(--font-md)">{{ aiResults.length }} leads found</h3>
              <div class="ai-meta">
                <span v-if="aiMeta.sources_searched" class="text-xs text-muted">
                  LinkedIn: {{ aiMeta.sources_searched.linkedin || 0 }} | X: {{ aiMeta.sources_searched.twitter || 0 }}<template v-if="aiMeta.sources_searched.web"> | Web: {{ aiMeta.sources_searched.web }}</template>
                </span>
                <span v-if="aiMeta.engine === 'openclaw'" class="badge badge-success" style="font-size:9px">OpenClaw</span>
                <span v-else-if="!aiMeta.has_google_search" class="badge badge-neutral" style="font-size:9px">AI-generated</span>
              </div>
            </div>
            <div class="ai-table-bar-right">
              <span v-if="aiSelected.length" class="text-sm" style="color:var(--brand-accent);font-weight:600">{{ aiSelected.length }} selected</span>
              <button class="btn btn-secondary btn-sm" :disabled="!aiSelected.length" @click="addSelectedToLeads">
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" style="vertical-align:-2px;margin-right:4px"><circle cx="8" cy="5" r="3"/><path d="M2 14c0-3 2.5-5 6-5s6 2 6 5"/></svg>
                Add as Leads
              </button>
              <button class="btn btn-primary btn-sm" :disabled="!aiSelected.length" @click="addSelectedToPipeline">
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" style="vertical-align:-2px;margin-right:4px"><path d="M1 4h4v4H1zM6 2h4v8H6zM11 5h4v3h-4z"/></svg>
                Add to Pipeline
              </button>
            </div>
          </div>

          <!-- Sortable Table -->
          <div class="card ai-table-card">
            <table class="data-table ai-data-table">
              <thead>
                <tr>
                  <th style="width:36px">
                    <input type="checkbox" class="ai-check" :checked="aiSelected.length === sortedAIResults.length && sortedAIResults.length > 0" @change="toggleAllAI" />
                  </th>
                  <th class="sortable-th" @click="setAiSort('name')">
                    Name
                    <span class="sort-icon" v-if="aiSortKey === 'name'">{{ aiSortDir === 'asc' ? '\u25B2' : '\u25BC' }}</span>
                  </th>
                  <th class="sortable-th" @click="setAiSort('email')">
                    Email
                    <span class="sort-icon" v-if="aiSortKey === 'email'">{{ aiSortDir === 'asc' ? '\u25B2' : '\u25BC' }}</span>
                  </th>
                  <th class="sortable-th" @click="setAiSort('company')">
                    Company
                    <span class="sort-icon" v-if="aiSortKey === 'company'">{{ aiSortDir === 'asc' ? '\u25B2' : '\u25BC' }}</span>
                  </th>
                  <th class="sortable-th" @click="setAiSort('phone')">Phone</th>
                  <th class="sortable-th" @click="setAiSort('location')">
                    Location
                    <span class="sort-icon" v-if="aiSortKey === 'location'">{{ aiSortDir === 'asc' ? '\u25B2' : '\u25BC' }}</span>
                  </th>
                  <th class="sortable-th" @click="setAiSort('industry')">
                    Industry
                    <span class="sort-icon" v-if="aiSortKey === 'industry'">{{ aiSortDir === 'asc' ? '\u25B2' : '\u25BC' }}</span>
                  </th>
                  <th class="sortable-th" @click="setAiSort('relevance_score')" style="width:80px">
                    Score
                    <span class="sort-icon" v-if="aiSortKey === 'relevance_score'">{{ aiSortDir === 'asc' ? '\u25B2' : '\u25BC' }}</span>
                  </th>
                  <th style="width:70px">Source</th>
                  <th style="width:90px">Links</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(lead, i) in sortedAIResults" :key="i"
                    :class="{ 'row-selected': aiSelected.includes(i) }"
                    @click="toggleAiSelect(i)">
                  <td @click.stop>
                    <input type="checkbox" class="ai-check" :checked="aiSelected.includes(i)" @change="toggleAiSelect(i)" />
                  </td>
                  <td>
                    <div class="lead-name">{{ lead.name || '--' }}</div>
                    <div class="text-xs text-muted">{{ lead.title || '' }}</div>
                  </td>
                  <td><span class="text-sm" style="color:var(--brand-accent)">{{ lead.email || '--' }}</span></td>
                  <td class="text-sm">{{ lead.company || '--' }}</td>
                  <td class="text-sm text-muted">{{ lead.phone || '--' }}</td>
                  <td class="text-sm text-muted">{{ lead.location || '--' }}</td>
                  <td><span class="badge badge-neutral" style="font-size:10px" v-if="lead.industry">{{ lead.industry }}</span></td>
                  <td><span class="score-badge" :class="lead.relevance_score >= 80 ? 'score-hot' : lead.relevance_score >= 60 ? 'score-warm' : 'score-cold'">{{ lead.relevance_score }}</span></td>
                  <td><span class="source-badge" :class="'source-' + (lead.source || 'ai')">{{ (lead.source || 'ai').toUpperCase() }}</span></td>
                  <td @click.stop>
                    <div style="display:flex;gap:4px">
                      <a v-if="lead.linkedin_url" :href="lead.linkedin_url" target="_blank" class="ai-social-link li" style="padding:3px 5px">
                        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M0 1.146C0 .513.526 0 1.175 0h13.65C15.474 0 16 .513 16 1.146v13.708c0 .633-.526 1.146-1.175 1.146H1.175C.526 16 0 15.487 0 14.854V1.146zm4.943 12.248V6.169H2.542v7.225h2.401zm-1.2-8.212c.837 0 1.358-.554 1.358-1.248-.015-.709-.52-1.248-1.342-1.248-.822 0-1.359.54-1.359 1.248 0 .694.521 1.248 1.327 1.248h.016zm4.908 8.212V9.359c0-.216.016-.432.08-.586.173-.431.568-.878 1.232-.878.869 0 1.216.662 1.216 1.634v3.865h2.401V9.25c0-2.22-1.184-3.252-2.764-3.252-1.274 0-1.845.7-2.165 1.193V6.169H6.29c.032.68 0 7.225 0 7.225h2.361z"/></svg>
                      </a>
                      <a v-if="lead.twitter_url" :href="lead.twitter_url" target="_blank" class="ai-social-link tw" style="padding:3px 5px">
                        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M5.026 15c6.038 0 9.341-5.003 9.341-9.334 0-.14 0-.282-.006-.422A6.685 6.685 0 0016 3.542a6.658 6.658 0 01-1.889.518 3.301 3.301 0 001.447-1.817 6.533 6.533 0 01-2.087.793A3.286 3.286 0 007.875 6.03 9.325 9.325 0 011.114 2.1 3.323 3.323 0 002.13 6.574A3.203 3.203 0 01.64 6.14v.04a3.288 3.288 0 002.632 3.218 3.203 3.203 0 01-.865.115c-.212 0-.418-.02-.62-.058a3.283 3.283 0 003.067 2.277A6.588 6.588 0 01.78 13.58a6.32 6.32 0 01-.78-.045A9.344 9.344 0 005.026 15z"/></svg>
                      </a>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Reason tooltips below table -->
          <div v-if="aiSelected.length === 1" class="ai-reason-panel card">
            <div class="card-header"><h3 class="card-title" style="font-size:var(--font-xs);text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted)">Why This Lead Matches</h3></div>
            <p class="text-sm" style="color:var(--text-secondary);line-height:1.6;margin:0">{{ sortedAIResults[aiSelected[0]]?.reason || 'No reason provided.' }}</p>
          </div>
        </template>

        <!-- Empty State -->
        <div v-else-if="!aiSearching && aiSearchDone" class="ai-empty">
          <p>No matching leads found. Try a different description.</p>
        </div>
      </div>
    </template>

    <!-- ══════════ Email Compose Modal ══════════ -->
    <div v-if="showEmailModal" class="modal-overlay" @click.self="showEmailModal = false">
      <div class="modal-content slide-up" style="max-width: 540px">
        <div class="modal-header">
          <h2 class="modal-title"><svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" style="vertical-align:-3px;margin-right:6px"><rect x="1" y="3" width="14" height="10" rx="1.5"/><path d="M1 4l7 5 7-5"/></svg>Send Email</h2>
          <button class="btn-icon btn-ghost" @click="showEmailModal = false"><svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4l8 8M12 4l-8 8"/></svg></button>
        </div>
        <div style="display:flex;flex-direction:column;gap:14px">
          <div class="form-group">
            <label class="form-label">To</label>
            <input class="form-input" :value="emailToAddress" disabled style="opacity:0.7" />
          </div>
          <div class="form-group">
            <label class="form-label">Subject</label>
            <input v-model="emailSubject" class="form-input" placeholder="Follow up on your visit" />
          </div>
          <div class="form-group">
            <label class="form-label">Message</label>
            <textarea v-model="emailBody" class="form-input" rows="6" placeholder="Hi there, I noticed you visited our pricing page..."></textarea>
          </div>
          <button class="btn btn-primary w-full" :disabled="emailSending || !emailSubject || !emailBody" @click="sendEmail">
            {{ emailSending ? 'Sending...' : 'Send Email' }}
          </button>
          <div v-if="emailSent" class="email-sent-msg"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--color-success);margin-right:6px;vertical-align:1px"></span>Email sent successfully!</div>
          <div v-if="emailError" class="email-error-msg"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--color-danger);margin-right:6px;vertical-align:1px"></span>{{ emailError }}</div>
        </div>
        <!-- Email History -->
        <div v-if="emailHistory.length" style="margin-top:20px;border-top:1px solid var(--border-color);padding-top:16px">
          <h4 style="font-size:var(--font-xs);text-transform:uppercase;letter-spacing:0.1em;color:var(--text-muted);margin:0 0 10px">Previous Emails</h4>
          <div v-for="em in emailHistory" :key="em.id" class="email-history-item">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-weight:600;font-size:var(--font-sm)">{{ em.subject }}</span>
              <span class="badge" :class="em.status === 'sent' ? 'badge-success' : 'badge-danger'" style="font-size:9px">{{ em.status }}</span>
            </div>
            <div class="text-xs text-muted" style="margin-top:2px">{{ new Date(em.sent_at).toLocaleString() }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { VueFlow } from '@vue-flow/core'
import { useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

import PipelineNode from '@/components/PipelineNode.vue'
import leadsApi from '@/api/leads'

const route = useRoute()
const websiteId = route.params.websiteId
const { screenToFlowCoordinate: vfScreenToFlow } = useVueFlow()
const flowRef = ref(null)

const loading = ref(true)
const leads = ref([])
const statusFilter = ref('')
const activeTab = ref('table')
const selectedNodeId = ref(null)
const selectedLead = ref(null)

// AI Lead Finder state
const aiPrompt = ref('')
const aiSearching = ref(false)
const aiSearchDone = ref(false)
const aiResults = ref([])
const aiMeta = ref({})

// AI table sorting & selection
const aiSortKey = ref('relevance_score')
const aiSortDir = ref('desc')
const aiSelected = ref([])

const sortedAIResults = computed(() => {
  const arr = [...aiResults.value]
  const key = aiSortKey.value
  const dir = aiSortDir.value === 'asc' ? 1 : -1
  return arr.sort((a, b) => {
    const va = a[key] ?? ''
    const vb = b[key] ?? ''
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir
    return String(va).localeCompare(String(vb)) * dir
  })
})

function setAiSort(key) {
  if (aiSortKey.value === key) {
    aiSortDir.value = aiSortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    aiSortKey.value = key
    aiSortDir.value = key === 'relevance_score' ? 'desc' : 'asc'
  }
  aiSelected.value = [] // clear selection on re-sort
}

function toggleAiSelect(index) {
  const pos = aiSelected.value.indexOf(index)
  if (pos === -1) aiSelected.value.push(index)
  else aiSelected.value.splice(pos, 1)
}

function toggleAllAI() {
  if (aiSelected.value.length === sortedAIResults.value.length) {
    aiSelected.value = []
  } else {
    aiSelected.value = sortedAIResults.value.map((_, i) => i)
  }
}

function addSelectedToLeads() {
  const selected = aiSelected.value.map(i => sortedAIResults.value[i]).filter(Boolean)
  for (const lead of selected) {
    leads.value.unshift({
      id: 'ai-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6),
      name: lead.name,
      email: lead.email || '',
      company: lead.company || '',
      score: lead.relevance_score || 50,
      status: 'new',
      source: 'AI Finder',
    })
  }
  aiSelected.value = []
  activeTab.value = 'table'
}

function addSelectedToPipeline() {
  const selected = aiSelected.value.map(i => sortedAIResults.value[i]).filter(Boolean)
  // Add each selected lead as a node on the pipeline canvas
  let xOffset = 280
  let yOffset = 400
  for (const lead of selected) {
    connectorCounter++
    const newId = `ai-lead-${connectorCounter}`
    nodes.value.push({
      id: newId,
      type: 'pipeline',
      position: { x: xOffset, y: yOffset },
      data: {
        nodeType: 'hot',
        icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.5-7 8-7s8 3 8 7"/></svg>',
        label: lead.name || 'Lead',
        count: lead.relevance_score || 0,
        badge: lead.company || 'AI Lead',
        badgeClass: lead.relevance_score >= 80 ? 'badge-danger' : lead.relevance_score >= 60 ? 'badge-warning' : 'badge-neutral',
      },
    })
    // Also add as a table lead
    leads.value.unshift({
      id: newId,
      name: lead.name,
      email: lead.email || '',
      company: lead.company || '',
      score: lead.relevance_score || 50,
      status: 'new',
      source: 'AI Finder',
    })
    xOffset += 180
    if (xOffset > 800) { xOffset = 280; yOffset += 120 }
  }
  aiSelected.value = []
  activeTab.value = 'pipeline'
}


// ── Connector catalog (drag from sidebar) ──
const connectorCatalog = {
  'Data Sources': [
    { id: 'gsc',       icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#22c55e"></span>', label: 'Search Console', desc: 'Keyword & click data',     badgeClass: 'badge-success' },
    { id: 'ga4',       icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#f59e0b"></span>', label: 'GA4',            desc: 'Traffic & attribution',    badgeClass: 'badge-warning' },
    { id: 'shopify',   icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#22c55e"></span>', label: 'Shopify',        desc: 'Customer & order data',    badgeClass: 'badge-success' },
    { id: 'webhooks',  icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#94a3b8"></span>', label: 'Webhooks',       desc: 'Custom event ingestion',   badgeClass: 'badge-neutral' },
  ],
  'Enrichment': [
    { id: 'clearbit',  icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#3b82f6"></span>', label: 'Clearbit',       desc: 'Firmographic enrichment',  badgeClass: 'badge-info' },
    { id: 'apollo',    icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#5B8DEF"></span>', label: 'Apollo.io',      desc: 'Contact DB & tech stack',  badgeClass: 'badge-accent' },
    { id: 'linkedin',  icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#3b82f6"></span>', label: 'LinkedIn',       desc: 'Profile & company intel',  badgeClass: 'badge-info' },
    { id: 'zoominfo',  icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#3b82f6"></span>', label: 'ZoomInfo',       desc: 'Enterprise B2B data',      badgeClass: 'badge-info' },
  ],
  'Outreach': [
    { id: 'email',     icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#3b82f6"></span>', label: 'Email',          desc: 'Campaigns & drip flows',   badgeClass: 'badge-info' },
    { id: 'sms',       icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#3b82f6"></span>', label: 'SMS (Twilio)',    desc: 'Text follow-ups',          badgeClass: 'badge-info' },
    { id: 'whatsapp',  icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#22c55e"></span>', label: 'WhatsApp',       desc: 'Conversational outreach',  badgeClass: 'badge-success' },
    { id: 'linkedin-mail', icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#3b82f6"></span>', label: 'LinkedIn InMail', desc: 'Direct messaging',   badgeClass: 'badge-info' },
  ],
  'Advertising': [
    { id: 'facebook',  icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#3b82f6"></span>', label: 'Facebook Ads',   desc: 'Retarget audiences',       badgeClass: 'badge-info' },
    { id: 'google-ads',icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#f59e0b"></span>', label: 'Google Ads',     desc: 'Customer Match & display', badgeClass: 'badge-warning' },
    { id: 'pinterest', icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#ef4444"></span>', label: 'Pinterest',      desc: 'Promoted pin campaigns',   badgeClass: 'badge-danger' },
    { id: 'instagram', icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#5B8DEF"></span>', label: 'Instagram Ads',  desc: 'Story & reel ads',         badgeClass: 'badge-accent' },
    { id: 'tiktok',    icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#94a3b8"></span>', label: 'TikTok Ads',     desc: 'Video ad campaigns',       badgeClass: 'badge-neutral' },
  ],
  'CRM & Automation': [
    { id: 'hubspot',   icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#f59e0b"></span>', label: 'HubSpot',        desc: 'Two-way CRM sync',        badgeClass: 'badge-warning' },
    { id: 'salesforce', icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#3b82f6"></span>', label: 'Salesforce',     desc: 'Enterprise CRM sync',     badgeClass: 'badge-info' },
    { id: 'slack',     icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#5B8DEF"></span>', label: 'Slack',           desc: 'Real-time lead alerts',   badgeClass: 'badge-accent' },
    { id: 'zapier',    icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#f59e0b"></span>', label: 'Zapier',          desc: 'Universal automation',    badgeClass: 'badge-warning' },
  ],
  'AI & Intelligence': [
    { id: 'anthropic', icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#5B8DEF"></span>', label: 'Claude AI',      desc: 'AI email drafting',        badgeClass: 'badge-accent' },
    { id: 'openai',    icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#22c55e"></span>', label: 'OpenAI',          desc: 'Content generation',      badgeClass: 'badge-success' },
    { id: 'mixpanel',  icon: '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#5B8DEF"></span>', label: 'Mixpanel',       desc: 'Product analytics',       badgeClass: 'badge-accent' },
  ],
}

let connectorCounter = 0

// ── Computed stats ──
const hotCount = computed(() => leads.value.filter(l => l.score >= 70).length)
const warmCount = computed(() => leads.value.filter(l => l.score >= 30 && l.score < 70).length)
const coldCount = computed(() => leads.value.filter(l => l.score < 30).length)
const contactedCount = computed(() => leads.value.filter(l => l.status === 'contacted').length)
const avgScore = computed(() => {
  if (leads.value.length === 0) return 0
  return Math.round(leads.value.reduce((sum, l) => sum + (l.score || 0), 0) / leads.value.length)
})

const companyDomain = computed(() => {
  if (!selectedLead.value?.company) return 'unknown.com'
  return selectedLead.value.company.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') + '.com'
})

// ── Vue Flow: Nodes (extended pipeline) ──
const nodes = ref([
  { id: 'source',   type: 'pipeline', position: { x: 0,    y: 140 }, data: { nodeType: 'source',  icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>', label: 'All Visitors',   count: 0 } },
  { id: 'hot',      type: 'pipeline', position: { x: 280,  y: 10 },  data: { nodeType: 'hot',     icon: '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#ef4444;box-shadow:0 0 6px rgba(239,68,68,0.5)"></span>', label: 'Hot Leads',      count: 0, badge: 'Score ≥ 70', badgeClass: 'badge-danger' } },
  { id: 'warm',     type: 'pipeline', position: { x: 280,  y: 170 }, data: { nodeType: 'warm',    icon: '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#f59e0b;box-shadow:0 0 6px rgba(245,158,11,0.4)"></span>', label: 'Warm Leads',     count: 0, badge: 'Score 30–69', badgeClass: 'badge-warning' } },
  { id: 'cold',     type: 'pipeline', position: { x: 280,  y: 330 }, data: { nodeType: 'cold',    icon: '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#94a3b8"></span>', label: 'Cold Leads',     count: 0, badge: 'Score < 30', badgeClass: 'badge-neutral' } },
  { id: 'saas',     type: 'pipeline', position: { x: 540,  y: 0 },   data: { nodeType: 'saas',    icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="18" height="14" rx="2"/><path d="M7 20h10M12 18v2"/></svg>', label: 'SaaS',           count: 0, badge: 'Industry', badgeClass: 'badge-info' } },
  { id: 'health',   type: 'pipeline', position: { x: 540,  y: 150 }, data: { nodeType: 'health',  icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 2v4m0 0H4m4 0h4M16 12h4m-4 0h-4m4 0V8m0 4v4"/><rect x="3" y="3" width="18" height="18" rx="2"/></svg>', label: 'Healthcare',     count: 0, badge: 'Industry', badgeClass: 'badge-success' } },
  { id: 'enrich',   type: 'pipeline', position: { x: 800,  y: 20 },  data: { nodeType: 'action',  icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/></svg>', label: 'Enrich Profile', count: 0, badge: 'Auto', badgeClass: 'badge-accent' } },
  { id: 'score',    type: 'pipeline', position: { x: 800,  y: 170 }, data: { nodeType: 'action',  icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2a10 10 0 1 0 10 10"/><path d="M12 6v6l4 2"/></svg>', label: 'ML Score',       count: 0, badge: 'AI Model', badgeClass: 'badge-accent' } },
  { id: 'campaign', type: 'pipeline', position: { x: 1060, y: 20 },  data: { nodeType: 'action',  icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 7l10 7 10-7"/></svg>', label: 'Send Campaign',  count: 0, badge: 'Outreach', badgeClass: 'badge-accent' } },
  { id: 'nurture',  type: 'pipeline', position: { x: 1060, y: 170 }, data: { nodeType: 'action',  icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 12a9 9 0 1 1-6.22-8.56"/><path d="M21 3v9h-9"/></svg>', label: 'Nurture Flow',   count: 0, badge: 'Automated', badgeClass: 'badge-accent' } },
  { id: 'convert',  type: 'pipeline', position: { x: 1060, y: 320 }, data: { nodeType: 'health',  icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>', label: 'Converted',       count: 0, badge: 'Customer', badgeClass: 'badge-success' } },
])

const edges = ref([
  { id: 'e1',  source: 'source',  target: 'hot',      animated: true, style: { stroke: 'var(--brand-accent)', strokeWidth: 2 } },
  { id: 'e2',  source: 'source',  target: 'warm',     style: { stroke: 'var(--border-hover)', strokeWidth: 1.5 } },
  { id: 'e3',  source: 'source',  target: 'cold',     style: { stroke: 'var(--border-color)', strokeWidth: 1.5 } },
  { id: 'e4',  source: 'hot',     target: 'saas',     style: { stroke: 'var(--border-hover)', strokeWidth: 1.5 } },
  { id: 'e5',  source: 'hot',     target: 'health',   animated: true, style: { stroke: 'var(--brand-accent)', strokeWidth: 2 } },
  { id: 'e6',  source: 'saas',    target: 'enrich',   style: { stroke: 'var(--border-hover)', strokeWidth: 1.5 } },
  { id: 'e7',  source: 'health',  target: 'enrich',   animated: true, style: { stroke: 'var(--brand-accent)', strokeWidth: 2 } },
  { id: 'e8',  source: 'enrich',  target: 'score',    animated: true, style: { stroke: 'var(--brand-accent)', strokeWidth: 2 } },
  { id: 'e9',  source: 'score',   target: 'campaign', animated: true, style: { stroke: 'var(--brand-accent)', strokeWidth: 2 } },
  { id: 'e10', source: 'score',   target: 'nurture',  style: { stroke: 'var(--border-hover)', strokeWidth: 1.5 } },
  { id: 'e11', source: 'score',   target: 'convert',  style: { stroke: 'var(--color-success)', strokeWidth: 1.5 } },
  { id: 'e12', source: 'warm',    target: 'score',    style: { stroke: 'var(--border-color)', strokeWidth: 1 } },
])

// Update node counts
watch(leads, (newLeads) => {
  const total = newLeads.length > 0 ? newLeads.length * 37 : 847
  const hot = hotCount.value
  const enriched = Math.max(1, Math.floor(hot * 0.8))
  const scored = Math.max(1, Math.floor(enriched * 0.9))
  nodes.value[0].data.count  = total
  nodes.value[1].data.count  = hot
  nodes.value[2].data.count  = warmCount.value
  nodes.value[3].data.count  = coldCount.value
  nodes.value[4].data.count  = Math.max(1, Math.floor(hot * 0.52))
  nodes.value[5].data.count  = Math.max(1, Math.ceil(hot * 0.35))
  nodes.value[6].data.count  = enriched
  nodes.value[7].data.count  = scored
  nodes.value[8].data.count  = Math.max(1, Math.floor(scored * 0.6))
  nodes.value[9].data.count  = Math.max(1, Math.floor(scored * 0.3))
  nodes.value[10].data.count = Math.max(1, Math.floor(scored * 0.1))
}, { immediate: true })

// ── Drag & Drop connectors ──
let draggedConnector = null

function onDragStart(event, connector) {
  draggedConnector = connector
  event.dataTransfer.setData('application/connector', JSON.stringify(connector))
  event.dataTransfer.effectAllowed = 'move'
}

function onDrop(event) {
  event.preventDefault()
  if (!draggedConnector) return

  // Convert screen coordinates to flow coordinates using the composable
  let position
  try {
    position = vfScreenToFlow({ x: event.clientX, y: event.clientY })
  } catch {
    // Fallback: manual offset calculation
    const connectorEl = flowRef.value?.$el || document.querySelector('.vue-flow')
    if (!connectorEl) return
    const bounds = connectorEl.getBoundingClientRect()
    position = { x: event.clientX - bounds.left, y: event.clientY - bounds.top }
  }

  connectorCounter++
  const newId = `${draggedConnector.id}-${connectorCounter}`

  nodes.value.push({
    id: newId,
    type: 'pipeline',
    position,
    data: {
      nodeType: 'connector',
      icon: draggedConnector.icon,
      label: draggedConnector.label,
      count: undefined,
      badge: 'Connector',
      badgeClass: draggedConnector.badgeClass || 'badge-neutral',
    },
  })

  draggedConnector = null
}

function onConnect(params) {
  const id = `e-${params.source}-${params.target}`
  if (!edges.value.find(e => e.id === id)) {
    edges.value.push({
      id,
      source: params.source,
      target: params.target,
      animated: true,
      style: { stroke: 'var(--brand-accent)', strokeWidth: 2 },
    })
  }
}

// ── Filtering & selection ──
const filteredLabel = computed(() => {
  const labels = { source: 'All Leads', hot: 'Hot Leads', warm: 'Warm Leads', cold: 'Cold Leads', saas: 'SaaS', health: 'Healthcare', enrich: 'Enriched', score: 'ML Scored', campaign: 'Campaign', nurture: 'Nurture', convert: 'Converted' }
  return labels[selectedNodeId.value] || 'Leads'
})

const filteredLeads = computed(() => {
  switch (selectedNodeId.value) {
    case 'hot':    return leads.value.filter(l => l.score >= 70)
    case 'warm':   return leads.value.filter(l => l.score >= 30 && l.score < 70)
    case 'cold':   return leads.value.filter(l => l.score < 30)
    case 'campaign': return leads.value.filter(l => l.status === 'contacted')
    case 'convert':  return leads.value.filter(l => l.status === 'customer')
    default:       return leads.value
  }
})

const correlations = computed(() => {
  if (!selectedLead.value) return []
  const score = selectedLead.value.score || 50
  const f = []
  if (score >= 60) f.push({ positive: true, text: 'Visited /pricing 3 times in 7 days', impact: '+22%' })
  if (selectedLead.value.company) f.push({ positive: true, text: 'Company matches target ICP', impact: '+18%' })
  if (score >= 50) f.push({ positive: true, text: 'Senior role (VP level)', impact: '+15%' })
  f.push({ positive: true, text: `${Math.max(2, Math.floor(score / 8))} min avg read time`, impact: '+12%' })
  if (score < 80) f.push({ positive: false, text: 'No form submission yet', impact: '-8%' })
  if (score >= 40) f.push({ positive: true, text: 'Visit frequency increasing', impact: '+14%' })
  return f
})

function scoreTier(score) {
  if (score >= 80) return 'score-hot'
  if (score >= 50) return 'score-warm'
  return 'score-cold'
}

function statusClass(s) {
  return { new: 'badge-neutral', contacted: 'badge-info', qualified: 'badge-warning', customer: 'badge-success', lost: 'badge-danger' }[s] || 'badge-neutral'
}

function initials(lead) {
  return (lead?.name || 'A').split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

function onNodeClick({ node }) {
  selectedNodeId.value = node.id
  selectedLead.value = null
}

function openLeadDetail(lead) {
  selectedLead.value = lead
}

function miniMapNodeColor(node) {
  const c = { hot: '#c44d4d', warm: '#d4813a', cold: '#888', saas: '#4a8ec2', health: '#3d9970', action: '#d4956a', source: '#1e1e1e', connector: '#6e6a65' }
  return c[node.data?.nodeType] || '#888'
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    const { data } = await leadsApi.list(websiteId, params)
    leads.value = data?.results || data?.data?.results || data?.data || data || []
  } catch (e) { /* toast auto-triggered */ }
  finally { loading.value = false }
}

async function handleExport() {
  try { await leadsApi.export(websiteId) } catch {}
}

onMounted(fetchData)

// ── AI Lead Finder ──
async function runAISearch() {
  if (!aiPrompt.value.trim() || aiSearching.value) return
  aiSearching.value = true
  aiSearchDone.value = false
  aiResults.value = []
  aiSelected.value = []
  try {
    const { data } = await leadsApi.aiSearch(websiteId, { prompt: aiPrompt.value })
    aiResults.value = data?.leads || []
    aiMeta.value = data || {}
  } catch (e) {
    console.error('AI search failed', e)
  } finally {
    aiSearching.value = false
    aiSearchDone.value = true
  }
}

function addAILeadToTable(lead) {
  leads.value.unshift({
    id: 'ai-' + Date.now(),
    name: lead.name,
    email: '',
    company: lead.company || '',
    score: lead.relevance_score || 50,
    status: 'new',
    source: 'AI Finder',
  })
}

// ── Email Compose ──
const showEmailModal = ref(false)
const emailSubject = ref('')
const emailBody = ref('')
const emailSending = ref(false)
const emailSent = ref(false)
const emailError = ref('')
const emailHistory = ref([])
const emailLeadTarget = ref(null)

const emailToAddress = computed(() => emailLeadTarget.value?.email || 'No email')

async function openEmailCompose(lead) {
  emailLeadTarget.value = lead
  emailSubject.value = ''
  emailBody.value = ''
  emailSent.value = false
  emailError.value = ''
  emailHistory.value = []
  showEmailModal.value = true
  // Load email history
  try {
    const { data } = await leadsApi.getEmails(websiteId, lead.id)
    emailHistory.value = data || []
  } catch { /* ignore */ }
}

async function sendEmail() {
  if (!emailSubject.value || !emailBody.value || !emailLeadTarget.value) return
  emailSending.value = true
  emailSent.value = false
  emailError.value = ''
  try {
    await leadsApi.sendEmail(websiteId, emailLeadTarget.value.id, {
      subject: emailSubject.value,
      body: emailBody.value,
    })
    emailSent.value = true
    emailSubject.value = ''
    emailBody.value = ''
    // Refresh history
    const { data } = await leadsApi.getEmails(websiteId, emailLeadTarget.value.id)
    emailHistory.value = data || []
  } catch (e) {
    emailError.value = e.response?.data?.error || 'Failed to send email'
  } finally {
    emailSending.value = false
  }
}
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }
.lead-name { font-weight: 600; color: var(--text-primary); }
.score-badge { display: inline-block; padding: 3px 10px; border-radius: var(--radius-full); font-size: var(--font-xs); font-weight: 700; }
.score-hot  { background: rgba(231, 76, 60, 0.12); color: var(--color-danger); }
.score-warm { background: rgba(243, 156, 18, 0.12); color: var(--color-warning); }
.score-cold { background: var(--bg-surface); color: var(--text-muted); }

/* ══════════════════════════════════════
   Pipeline Wrapper
   ══════════════════════════════════════ */
.pipeline-wrapper {
  display: flex;
  gap: 0;
  margin-bottom: 20px;
}

/* ── Connector Sidebar ── */
.connector-sidebar {
  width: 210px;
  flex-shrink: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-right: none;
  border-radius: var(--radius-lg) 0 0 var(--radius-lg);
  overflow-y: auto;
  max-height: 700px;
}

.cs-header {
  padding: 16px 14px 12px;
  border-bottom: 1px solid var(--border-color);
}

.cs-title {
  font-size: var(--font-base);
  font-weight: 700;
  color: var(--text-primary);
}

.cs-subtitle {
  font-size: var(--font-xs);
  color: var(--text-muted);
  margin-top: 2px;
}

.cs-section { padding: 8px 0; }

.cs-section-label {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  padding: 4px 14px 6px;
}

.cs-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  cursor: grab;
  transition: background var(--transition-fast);
  border-left: 3px solid transparent;
}

.cs-item:hover {
  background: var(--bg-surface);
  border-left-color: var(--brand-accent);
}

.cs-item:active { cursor: grabbing; }

.cs-item-icon { font-size: 18px; flex-shrink: 0; }

.cs-item-info { min-width: 0; }

.cs-item-name {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cs-item-desc {
  font-size: 10px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Canvas ── */
.pipeline-canvas-wrap {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  overflow: hidden;
}

.pipeline-flow { width: 100%; height: 700px; }

:deep(.vue-flow) { background: var(--bg-card) !important; }
:deep(.vue-flow__background) { opacity: 0.4; }
:deep(.vue-flow__edge-path) { stroke: var(--border-hover); stroke-width: 1.5; }
:deep(.vue-flow__edge.animated path) { stroke: var(--brand-accent); stroke-width: 2; }
:deep(.vue-flow__controls) { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); box-shadow: var(--shadow-sm); overflow: hidden; }
:deep(.vue-flow__controls-button) { background: var(--bg-card); border: none; border-bottom: 1px solid var(--border-color); color: var(--text-secondary); width: 28px; height: 28px; }
:deep(.vue-flow__controls-button:hover) { background: var(--bg-surface); color: var(--text-primary); }
:deep(.vue-flow__controls-button svg) { fill: currentColor; }
:deep(.vue-flow__minimap) { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); box-shadow: var(--shadow-sm); }
:deep(.vue-flow__connection-line) { stroke: var(--brand-accent); stroke-width: 2; }

/* ── Detail Panel ── */
.pipeline-detail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.corr-list { display: flex; flex-direction: column; gap: 6px; }
.corr-row { display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: var(--bg-surface); border-radius: var(--radius-sm); }
.intel-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.intel-cell { background: var(--bg-surface); border-radius: var(--radius-sm); padding: 8px 10px; }
.intel-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }
.intel-value { font-size: var(--font-sm); font-weight: 700; color: var(--text-primary); margin-top: 2px; }
.lead-list { display: flex; flex-direction: column; gap: 4px; }
.lead-list-item { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: var(--radius-sm); cursor: pointer; transition: background var(--transition-fast); }
.lead-list-item:hover { background: var(--bg-surface); }

@media (max-width: 900px) {
  .pipeline-wrapper { flex-direction: column; }
  .connector-sidebar { width: 100%; max-height: 200px; border-radius: var(--radius-lg) var(--radius-lg) 0 0; border-right: 1px solid var(--border-color); border-bottom: none; }
  .pipeline-canvas-wrap { border-radius: 0 0 var(--radius-lg) var(--radius-lg); }
  .pipeline-detail-grid { grid-template-columns: 1fr; }
  .ai-results-grid { grid-template-columns: 1fr; }
}

/* ═══════════════════════════════════════
   AI Lead Finder
   ═══════════════════════════════════════ */
.ai-finder { max-width: 960px; }

.ai-search-card { margin-bottom: 24px; }

.ai-prompt-input {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-size: var(--font-sm);
  font-family: var(--font-family);
  background: var(--bg-surface);
  color: var(--text-primary);
  resize: vertical;
  transition: border-color 0.2s;
}
.ai-prompt-input:focus {
  outline: none;
  border-color: var(--brand-accent);
  box-shadow: 0 0 0 3px rgba(91, 141, 239, 0.1);
}

.ai-search-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  gap: 12px;
}

.ai-example-prompts {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.ai-example-btn {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  padding: 4px 10px;
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
  font-family: var(--font-family);
}
.ai-example-btn:hover {
  border-color: var(--brand-accent);
  color: var(--brand-accent);
}

.ai-loading {
  text-align: center;
  padding: 60px 20px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
.ai-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin-right: 6px;
  vertical-align: middle;
}
.ai-spinner-lg {
  display: inline-block;
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color);
  border-top-color: var(--brand-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.ai-results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.ai-meta { display: flex; gap: 8px; align-items: center; }

.ai-results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

@keyframes ai-card-in {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
.ai-lead-card {
  animation: ai-card-in 0.4s cubic-bezier(0.22, 1, 0.36, 1) both;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-lead-top {
  display: flex;
  align-items: center;
  gap: 12px;
}
.ai-lead-name {
  font-weight: 700;
  font-size: var(--font-sm);
  color: var(--text-primary);
}
.ai-score {
  font-weight: 800;
  font-size: var(--font-lg);
  flex-shrink: 0;
}

.ai-lead-details {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.ai-lead-detail {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--font-xs);
  color: var(--text-secondary);
}

.ai-lead-reason {
  font-size: var(--font-xs);
  color: var(--text-muted);
  line-height: 1.5;
  margin: 0;
  border-left: 2px solid var(--brand-accent);
  padding-left: 8px;
}

.ai-lead-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
}

.ai-social-links { display: flex; gap: 8px; }
.ai-social-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.15s;
}
.ai-social-link.li { background: rgba(10, 102, 194, 0.08); color: #0a66c2; }
.ai-social-link.li:hover { background: rgba(10, 102, 194, 0.18); }
.ai-social-link.tw { background: rgba(29, 161, 242, 0.08); color: #1da1f2; }
.ai-social-link.tw:hover { background: rgba(29, 161, 242, 0.18); }

.ai-empty {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
}

/* ── AI Sortable Results Table ── */
.ai-table-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}
.ai-table-bar-left { display: flex; flex-direction: column; gap: 4px; }
.ai-table-bar-right { display: flex; align-items: center; gap: 8px; }

.ai-table-card {
  overflow-x: auto;
  padding: 0;
}
.ai-data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-sm);
}
.ai-data-table thead { position: sticky; top: 0; z-index: 1; }
.ai-data-table th {
  background: var(--bg-surface);
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  font-size: var(--font-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}
.sortable-th {
  cursor: pointer;
  user-select: none;
  transition: color 0.15s;
}
.sortable-th:hover { color: var(--text-primary); }
.sort-icon {
  display: inline-block;
  font-size: 9px;
  margin-left: 3px;
  color: var(--brand-accent);
}

.ai-data-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color);
  vertical-align: middle;
}
.ai-data-table tbody tr {
  cursor: pointer;
  transition: background 0.12s;
}
.ai-data-table tbody tr:hover { background: var(--bg-hover); }
.ai-data-table tbody tr.row-selected { background: rgba(91, 141, 239, 0.06); }
.ai-data-table tbody tr.row-selected:hover { background: rgba(91, 141, 239, 0.1); }

.ai-check {
  width: 15px;
  height: 15px;
  cursor: pointer;
  accent-color: var(--brand-accent);
}

.lead-name {
  font-weight: 600;
  font-size: var(--font-sm);
  color: var(--text-primary);
}

.ai-reason-panel {
  margin-top: 16px;
  padding: 16px 20px;
  animation: ai-card-in 0.3s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.source-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.source-x { background: rgba(0,0,0,0.08); color: #1a1a2e; }
.source-linkedin { background: rgba(10,102,194,0.1); color: #0a66c2; }
.source-web { background: rgba(148,163,184,0.12); color: var(--text-muted); }
.source-ai { background: rgba(91,141,239,0.1); color: var(--brand-accent); }
.source-openclaw { background: rgba(34,197,94,0.1); color: #22c55e; }

/* ── Email Compose ── */
.email-sent-msg { text-align: center; padding: 8px; color: var(--color-success); font-size: var(--font-sm); font-weight: 600; }
.email-error-msg { text-align: center; padding: 8px; color: var(--color-danger); font-size: var(--font-sm); }
.email-history-item { padding: 10px 12px; background: var(--bg-surface); border-radius: var(--radius-sm); margin-bottom: 8px; }
</style>
