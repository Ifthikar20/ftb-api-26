<template>
  <div class="mt-page fade-in">
    <!-- ── Hero ──────────────────────────────────────────────────── -->
    <div class="page-header">
      <div>
        <div class="mt-title-line">
          <h1 class="page-title">Model Test</h1>
          <span class="mt-audit-type" :title="auditTypeBlurb">
            <span class="mt-audit-type-dot"></span>
            {{ auditTypeLabel }}
          </span>
        </div>
        <p class="page-subtitle">
          Pick an environment, edit the prompts, choose the models, and run.
          See whether <strong>{{ brandLabel }}</strong> surfaces — and compare
          how each model performs side by side.
        </p>
      </div>
    </div>

    <!-- ── Status + Results (top of page once a run exists) ─────── -->
    <template v-if="hasActiveRun">
      <!-- Verbose status panel -->
      <section class="mt-card mt-status-card">
        <div class="mt-status-head">
          <span class="mt-status-tag" :class="'is-' + (displayRun?.status || 'queued')">
            {{ statusLabel }}
          </span>
          <div class="mt-status-headline">
            <div class="mt-status-headline-main">
              {{ statusHeadline }}
              <span class="mt-audit-type is-inline" :title="auditTypeBlurb">
                <span class="mt-audit-type-dot"></span>
                {{ auditTypeLabel }}
              </span>
            </div>
            <div class="mt-status-headline-sub">{{ statusSub }}</div>
          </div>
          <div class="mt-status-meta">
            <div class="mt-status-meta-num">{{ liveCompleted }}/{{ liveTotal || totalQueries }}</div>
            <div class="mt-status-meta-cap">calls done</div>
          </div>
          <button
            v-if="!running"
            class="mt-btn-soft mt-btn-sm mt-status-new"
            @click="startNewAudit"
            title="Configure and run a new audit"
          >+ New audit</button>
        </div>

        <div class="mt-live-bar">
          <div class="mt-live-fill" :style="{ width: livePct + '%' }"></div>
        </div>

        <!-- Latest response peek — visible during a live run so the
             user sees content land cell-by-cell without scrolling. -->
        <div v-if="running && latestCompletedResponse" class="mt-livepeek">
          <div class="mt-livepeek-h">
            <span class="mt-livepeek-tag">Just in</span>
            <span class="mt-model-dot" :class="'is-' + providerKeyOf(latestCompletedResponse.provider)"></span>
            <span class="mt-livepeek-model">{{ variantLabel(latestCompletedResponse.provider) }}</span>
            <span class="mt-pivot-pill" :class="latestCompletedResponse.cls">
              {{ latestCompletedResponse.label }}
            </span>
            <span v-if="latestCompletedResponse.duration_ms" class="mt-livepeek-ms">
              {{ Math.round(latestCompletedResponse.duration_ms) }} ms
            </span>
            <span class="mt-livepeek-prompt">— prompt #{{ latestCompletedResponse.prompt_idx + 1 }}</span>
          </div>
          <div v-if="latestCompletedResponse.text" class="mt-livepeek-body">
            <span v-html="renderResponse(latestCompletedResponse.text, latestCompletedResponse.raw)"></span>
          </div>
          <div v-else-if="latestCompletedResponse.error" class="mt-livepeek-err">
            {{ latestCompletedResponse.error }}
          </div>
        </div>

        <!-- Verbose run log: every (prompt, model) cell as a line item -->
        <div v-if="statusLog.length" class="mt-status-log">
          <div class="mt-status-log-h">Run log</div>
          <ul class="mt-status-log-list">
            <li
              v-for="ev in statusLog"
              :key="ev.key"
              class="mt-status-log-item"
              :class="ev.cls"
            >
              <span class="mt-status-log-step">{{ ev.step }}</span>
              <span class="mt-status-log-text">{{ ev.text }}</span>
              <span v-if="ev.ms" class="mt-status-log-ms">{{ ev.ms }} ms</span>
              <span class="mt-status-log-state">{{ ev.state }}</span>
            </li>
          </ul>
        </div>

        <!-- Post-processing sub-status -->
        <div v-if="showPostProcessing" class="mt-post-strip">
          <div
            class="mt-post-step"
            :class="'is-' + (displayRun?.sentiment_status || 'queued')"
          >
            <span class="mt-post-icon">
              <span v-if="(displayRun?.sentiment_status || '') === 'running'" class="mt-spinner is-dark"></span>
              <svg v-else-if="(displayRun?.sentiment_status || '') === 'complete'" width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7l3 3 5-6" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <svg v-else-if="(displayRun?.sentiment_status || '') === 'failed'" width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3l8 8M11 3l-8 8" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <span v-else-if="(displayRun?.sentiment_status || '') === 'skipped'" class="mt-post-dash">—</span>
            </span>
            <span class="mt-post-label">Sentiment classification</span>
            <span class="mt-post-sub">{{ sentimentStatusText }}</span>
          </div>
          <div
            class="mt-post-step"
            :class="'is-' + (displayRun?.analysis_status || 'queued')"
          >
            <span class="mt-post-icon">
              <span v-if="(displayRun?.analysis_status || '') === 'running'" class="mt-spinner is-dark"></span>
              <svg v-else-if="(displayRun?.analysis_status || '') === 'complete'" width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7l3 3 5-6" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <svg v-else-if="(displayRun?.analysis_status || '') === 'failed'" width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3l8 8M11 3l-8 8" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <span v-else-if="(displayRun?.analysis_status || '') === 'skipped'" class="mt-post-dash">—</span>
            </span>
            <span class="mt-post-label">Synthesis analysis</span>
            <span class="mt-post-sub">{{ analysisStatusText }}</span>
          </div>
          <div
            class="mt-post-step"
            :class="'is-' + (displayRun?.grounding_status || 'queued')"
          >
            <span class="mt-post-icon">
              <span v-if="(displayRun?.grounding_status || '') === 'running'" class="mt-spinner is-dark"></span>
              <svg v-else-if="(displayRun?.grounding_status || '') === 'complete'" width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7l3 3 5-6" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <svg v-else-if="(displayRun?.grounding_status || '') === 'failed'" width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3l8 8M11 3l-8 8" stroke-linecap="round" stroke-linejoin="round"/></svg>
              <span v-else-if="(displayRun?.grounding_status || '') === 'skipped'" class="mt-post-dash">—</span>
            </span>
            <span class="mt-post-label">Web grounding via Gemini</span>
            <span class="mt-post-sub">{{ groundingStatusText }}</span>
          </div>
        </div>
      </section>

      <!-- Synthesis (verbose Markdown) -->
      <section v-if="displayRun?.analysis?.markdown" class="mt-card mt-synth">
        <div class="mt-card-head">
          <div>
            <div class="mt-card-eyebrow">Synthesis</div>
            <h2 class="mt-card-h">What the models told us about {{ brandLabel }}</h2>
            <p class="mt-card-sub">
              Generated by <strong>{{ displayRun.analysis.provider || 'synthesis model' }}</strong>
              from every response in this run. Quotes are pulled verbatim
              from the raw replies above.
            </p>
          </div>
        </div>
        <div class="mt-md" v-html="renderMarkdown(displayRun.analysis.markdown)"></div>
      </section>

      <!-- Google grounding -->
      <section v-if="displayRun?.google_grounding?.markdown" class="mt-card mt-ground">
        <div class="mt-card-head">
          <div>
            <div class="mt-card-eyebrow">Web grounding</div>
            <h2 class="mt-card-h">What the live web says</h2>
            <p class="mt-card-sub">
              Gemini was given the open web to research <strong>{{ brandLabel }}</strong>
              fresh, independent of the models above.
              <span v-if="displayRun.google_grounding.grounded === false">
                <em>(grounding tool unavailable — answered from memory)</em>
              </span>
            </p>
          </div>
        </div>
        <div class="mt-md" v-html="renderMarkdown(displayRun.google_grounding.markdown)"></div>
        <div v-if="(displayRun.google_grounding.citations || []).length" class="mt-citations">
          <div class="mt-citations-h">Sources</div>
          <ul>
            <li
              v-for="(c, i) in displayRun.google_grounding.citations"
              :key="i"
            >
              <a :href="c.url" target="_blank" rel="noopener">{{ c.title || c.url }}</a>
            </li>
          </ul>
        </div>
      </section>

      <!-- Per-model scorecards -->
      <section v-if="displayRun?.prompt_rows?.length" class="mt-card">
        <div class="mt-card-head">
          <div>
            <div class="mt-card-eyebrow">Results</div>
            <h2 class="mt-card-h">How each model performed</h2>
            <p class="mt-card-sub">
              <strong>Signal rate</strong> is the % of prompts where the
              model either named <strong>{{ brandLabel }}</strong> directly
              or described its offering / category. The breakdown below
              shows where each model lands across direct / near-miss /
              category. Latency is the median over completed calls.
            </p>
          </div>
        </div>

        <div class="mt-scorecards">
          <div
            v-for="m in perModelStats"
            :key="m.provider"
            class="mt-scorecard"
            :class="'is-' + providerKeyOf(m.provider)"
          >
            <div class="mt-scorecard-head">
              <span class="mt-model-dot" :class="'is-' + providerKeyOf(m.provider)"></span>
              <span class="mt-scorecard-name">{{ variantLabel(m.provider) }}</span>
            </div>
            <div class="mt-scorecard-big">{{ m.signal_rate }}%</div>
            <div class="mt-scorecard-cap">any signal</div>

            <!-- Mini stacked bar: direct + near + cat / total -->
            <div class="mt-sc-bar" v-if="m.attempts">
              <div
                class="mt-sc-bar-seg is-hit"
                :style="{ width: (m.hits / m.attempts * 100) + '%' }"
                :title="`${m.hits} direct hit(s)`"
              ></div>
              <div
                class="mt-sc-bar-seg is-near"
                :style="{ width: (m.near_miss / m.attempts * 100) + '%' }"
                :title="`${m.near_miss} near miss(es)`"
              ></div>
              <div
                class="mt-sc-bar-seg is-cat"
                :style="{ width: (m.category_match / m.attempts * 100) + '%' }"
                :title="`${m.category_match} category match(es)`"
              ></div>
            </div>

            <div class="mt-scorecard-grid">
              <div>
                <div class="mt-mini-num">{{ m.hits }}<span class="mt-mini-of">/{{ m.attempts }}</span></div>
                <div class="mt-mini-cap mt-mini-hit">direct</div>
              </div>
              <div>
                <div class="mt-mini-num">{{ m.near_miss }}<span class="mt-mini-of">/{{ m.attempts }}</span></div>
                <div class="mt-mini-cap mt-mini-near">near miss</div>
              </div>
              <div>
                <div class="mt-mini-num">{{ m.category_match }}<span class="mt-mini-of">/{{ m.attempts }}</span></div>
                <div class="mt-mini-cap mt-mini-cat">category</div>
              </div>
              <div>
                <div class="mt-mini-num">{{ m.median_ms }} <span class="mt-mini-of">ms</span></div>
                <div class="mt-mini-cap">median latency</div>
              </div>
              <div>
                <div class="mt-mini-num">{{ m.failures }}</div>
                <div class="mt-mini-cap">failures</div>
              </div>
              <div>
                <div class="mt-mini-num">{{ m.unique_finds }}</div>
                <div class="mt-mini-cap">solo finds</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Per-prompt highlights — accordion table -->
      <section v-if="displayRun?.prompt_rows?.length" class="mt-card mt-pm-wrap">
        <div class="mt-card-head">
          <div>
            <h2 class="mt-card-h">Per-prompt highlights</h2>
            <p class="mt-card-sub">
              One row per prompt with the metrics that matter for a
              discovery audit. Click any row to expand and read each
              model's response for that prompt.
            </p>
          </div>
          <div class="mt-card-head-actions">
            <button class="mt-link" @click="togglePromptExpandAll">
              {{ allPromptsOpen ? 'Collapse all' : 'Expand all' }}
            </button>
          </div>
        </div>

        <div class="mt-pm-scroll">
          <table class="mt-pm-tbl">
            <thead>
              <tr>
                <th class="mt-pm-h-caret"></th>
                <th class="mt-pm-h-num">#</th>
                <th class="mt-pm-h-prompt">Prompt</th>
                <th class="mt-pm-h-num-cell">Discovery</th>
                <th class="mt-pm-h-num-cell">Mentions</th>
                <th class="mt-pm-h-num-cell">Prominence</th>
                <th class="mt-pm-h-num-cell">List rank</th>
                <th class="mt-pm-h-num-cell">Avg ms</th>
                <th class="mt-pm-h-best">Best model</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="m in perPromptMetrics" :key="m.index">
                <tr
                  class="mt-pm-row"
                  :class="{ 'is-open': promptOpen[m.index], 'is-hit': m.discovery_count > 0, 'is-miss': m.discovery_count === 0 }"
                  @click="togglePromptRow(m.index)"
                >
                  <td class="mt-pm-caret">
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5" :style="{ transform: promptOpen[m.index] ? 'rotate(90deg)' : 'none' }">
                      <path d="M3 2l4 3-4 3" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </td>
                  <td class="mt-pm-num-cell">{{ m.index + 1 }}</td>
                  <td class="mt-pm-prompt-cell" :title="m.prompt">{{ m.prompt }}</td>
                  <td class="mt-pm-num-cell">
                    <span class="mt-pm-pill" :class="m.coverage_cls">
                      {{ m.discovery_count }} / {{ m.total_models }}
                    </span>
                    <div v-if="m.near_miss_count || m.category_match_count" class="mt-pm-softline">
                      <span v-if="m.near_miss_count" class="mt-pm-rel is-near_miss">+{{ m.near_miss_count }} near</span>
                      <span v-if="m.category_match_count" class="mt-pm-rel is-category_match">+{{ m.category_match_count }} cat</span>
                    </div>
                  </td>
                  <td class="mt-pm-num-cell">{{ m.total_mentions }}</td>
                  <td class="mt-pm-num-cell">{{ m.best_prominence_pct ? m.best_prominence_pct + '%' : '—' }}</td>
                  <td class="mt-pm-num-cell">
                    <span v-if="m.best_list_rank">#{{ m.best_list_rank }}<span class="mt-pm-of"> / {{ m.best_list_size }}</span></span>
                    <span v-else>—</span>
                  </td>
                  <td class="mt-pm-num-cell">{{ m.avg_latency_ms || '—' }}</td>
                  <td class="mt-pm-best-cell">
                    <span v-if="m.best_model">{{ m.best_model }}</span>
                    <span v-else class="mt-pm-best-none">none</span>
                  </td>
                </tr>
                <tr v-if="promptOpen[m.index]" class="mt-pm-detail-row">
                  <td colspan="9" class="mt-pm-detail">
                    <div class="mt-pm-detail-inner">
                    <!-- Per-model performance breakdown for THIS prompt -->
                    <table class="mt-pm-perf">
                      <thead>
                        <tr>
                          <th>Model</th>
                          <th>Outcome</th>
                          <th>Relevance</th>
                          <th>Sentiment</th>
                          <th class="mt-pm-num-cell">First mention</th>
                          <th class="mt-pm-num-cell">Prominence</th>
                          <th class="mt-pm-num-cell">List rank</th>
                          <th class="mt-pm-num-cell">Mentions</th>
                          <th class="mt-pm-num-cell">Chars</th>
                          <th class="mt-pm-num-cell">ms</th>
                          <th>Delta vs best</th>
                        </tr>
                      </thead>
                      <tbody>
                        <template v-for="perf in perPromptModelMetrics(m.index)" :key="perf.provider">
                        <tr
                          class="mt-pm-perf-row"
                          :class="cellClass(displayRun.prompt_rows[m.index], perf.provider)"
                          @click.stop="toggleRespBody(m.index, perf.provider)"
                        >
                          <td>
                            <span class="mt-model-dot" :class="'is-' + providerKeyOf(perf.provider)"></span>
                            {{ variantLabel(perf.provider) }}
                          </td>
                          <td>
                            <span class="mt-pm-pill" :class="cellClass(displayRun.prompt_rows[m.index], perf.provider)">
                              {{ cellLabel(displayRun.prompt_rows[m.index], perf.provider) }}
                            </span>
                          </td>
                          <td>
                            <span v-if="perf.relevance" class="mt-pm-rel" :class="'is-' + perf.relevance">
                              {{ relevanceLabel(perf.relevance) }}
                            </span>
                            <span v-else class="mt-pm-best-none">—</span>
                          </td>
                          <td>
                            <span v-if="perf.sentiment" class="mt-pm-sent" :class="'is-' + perf.sentiment">
                              {{ sentimentLabel(perf.sentiment) }}
                            </span>
                            <span v-else class="mt-pm-best-none">—</span>
                          </td>
                          <td class="mt-pm-num-cell">{{ perf.first_pos === null ? '—' : perf.first_pos }}</td>
                          <td class="mt-pm-num-cell">{{ perf.first_pos === null ? '—' : perf.prominence_pct + '%' }}</td>
                          <td class="mt-pm-num-cell">
                            <span v-if="perf.list_rank">#{{ perf.list_rank }}<span class="mt-pm-of"> / {{ perf.list_size }}</span></span>
                            <span v-else>—</span>
                          </td>
                          <td class="mt-pm-num-cell">{{ perf.mentions }}</td>
                          <td class="mt-pm-num-cell">{{ perf.chars || '—' }}</td>
                          <td class="mt-pm-num-cell">{{ perf.latency || '—' }}</td>
                          <td class="mt-pm-delta">
                            <span v-if="perf.delta_label" :class="perf.delta_cls">{{ perf.delta_label }}</span>
                            <span v-else class="mt-pm-best-none">—</span>
                          </td>
                        </tr>
                        <tr v-if="perf.evidence_phrase" class="mt-pm-evidence-row">
                          <td colspan="11" class="mt-pm-evidence">
                            <span class="mt-pm-evidence-label">Closest phrase in this response:</span>
                            <span class="mt-pm-evidence-quote">"{{ perf.evidence_phrase }}"</span>
                          </td>
                        </tr>
                        </template>
                      </tbody>
                    </table>

                    <!-- Full response bodies — opened on row click -->
                    <div
                      v-for="r in (displayRun.prompt_rows[m.index].responses || [])"
                      :key="r.provider"
                      v-show="isRespBodyOpen(m.index, r.provider)"
                      class="mt-pm-resp"
                      :class="cellClass(displayRun.prompt_rows[m.index], r.provider)"
                    >
                      <div class="mt-pm-resp-head">
                        <span class="mt-model-dot" :class="'is-' + providerKeyOf(r.provider)"></span>
                        <span class="mt-pm-resp-name">{{ variantLabel(r.provider) }}</span>
                        <span class="mt-pm-pill" :class="cellClass(displayRun.prompt_rows[m.index], r.provider)">
                          {{ cellLabel(displayRun.prompt_rows[m.index], r.provider) }}
                        </span>
                        <span v-if="r.duration_ms" class="mt-pm-resp-ms">{{ Math.round(r.duration_ms) }} ms</span>
                      </div>
                      <div v-if="r.response_text" class="mt-pm-resp-body">
                        <span v-html="renderResponse(r.response_text, r)"></span>
                      </div>
                      <div v-else-if="r.error" class="mt-pm-resp-err">{{ r.error }}</div>
                    </div>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Pivot comparison table -->
      <section v-if="displayRun?.prompt_rows?.length" class="mt-card mt-pivot-wrap">
        <div class="mt-card-head">
          <div>
            <h2 class="mt-card-h">Prompt-by-prompt comparison</h2>
            <p class="mt-card-sub">
              Each row is a prompt; each column is a model. Click a cell to
              read the full response.
            </p>
          </div>
        </div>

        <div class="mt-pivot-scroll">
          <table class="mt-pivot">
            <thead>
              <tr>
                <th class="mt-pivot-num-h">#</th>
                <th class="mt-pivot-prompt-h">Prompt</th>
                <th
                  v-for="prov in resultsProviders"
                  :key="prov"
                  class="mt-pivot-prov-h"
                >
                  <span class="mt-model-dot" :class="'is-' + providerKeyOf(prov)"></span>
                  {{ variantLabel(prov) }}
                </th>
                <th class="mt-pivot-agg-h">Agreement</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in displayRun.prompt_rows" :key="idx">
                <td class="mt-pivot-num">{{ idx + 1 }}</td>
                <td class="mt-pivot-prompt">{{ row.prompt }}</td>
                <td
                  v-for="prov in resultsProviders"
                  :key="prov"
                  class="mt-pivot-cell"
                  :class="cellClass(row, prov)"
                  @click="toggleResponse(idx, prov)"
                >
                  <div class="mt-pivot-cell-top">
                    <span class="mt-pivot-pill" :class="cellClass(row, prov)">
                      {{ cellLabel(row, prov) }}
                    </span>
                    <span v-if="cellLatency(row, prov)" class="mt-pivot-ms">
                      {{ cellLatency(row, prov) }} ms
                    </span>
                  </div>
                  <div
                    v-if="isResponseOpen(idx, prov)"
                    class="mt-pivot-body"
                    @click.stop
                  >
                    <span v-html="renderResponse(cellText(row, prov), cellResponse(row, prov))"></span>
                  </div>
                </td>
                <td class="mt-pivot-agg">
                  <span class="mt-agg-pill" :class="aggClass(row)">
                    {{ aggHitCount(row) }}/{{ resultsProviders.length }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Difference matrices -->
      <section
        v-if="displayRun?.prompt_rows?.length && resultsProviders.length >= 2"
        class="mt-card"
      >
        <div class="mt-card-head">
          <div>
            <h2 class="mt-card-h">Model-vs-model differences</h2>
            <p class="mt-card-sub">
              <strong>Disagreement</strong>: percentage of prompts where the
              row and column models gave opposite verdicts.
              <strong>Discovery delta</strong>: row model's discovery rate
              minus column model's, in percentage points.
            </p>
          </div>
        </div>

        <div class="mt-matrix-pair">
          <div class="mt-matrix-block">
            <div class="mt-matrix-h">Disagreement rate</div>
            <table class="mt-matrix">
              <thead>
                <tr>
                  <th></th>
                  <th v-for="prov in resultsProviders" :key="prov">
                    {{ variantLabel(prov) }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="rowProv in resultsProviders" :key="rowProv">
                  <th>{{ variantLabel(rowProv) }}</th>
                  <td
                    v-for="colProv in resultsProviders"
                    :key="colProv"
                    :class="['mt-matrix-cell', rowProv === colProv ? 'is-self' : disagreeClass(rowProv, colProv)]"
                  >
                    <span v-if="rowProv === colProv">—</span>
                    <span v-else>{{ disagreePct(rowProv, colProv) }}%</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="mt-matrix-block">
            <div class="mt-matrix-h">Discovery delta (pp)</div>
            <table class="mt-matrix">
              <thead>
                <tr>
                  <th></th>
                  <th v-for="prov in resultsProviders" :key="prov">
                    {{ variantLabel(prov) }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="rowProv in resultsProviders" :key="rowProv">
                  <th>{{ variantLabel(rowProv) }}</th>
                  <td
                    v-for="colProv in resultsProviders"
                    :key="colProv"
                    :class="['mt-matrix-cell', rowProv === colProv ? 'is-self' : deltaClass(rowProv, colProv)]"
                  >
                    <span v-if="rowProv === colProv">—</span>
                    <span v-else>{{ deltaSigned(rowProv, colProv) }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </template>

    <!-- Config sections (env / prompts / models / run) hide once a run
         is active. The "New audit" button in the status panel brings
         them back. -->
    <template v-if="!hasActiveRun">

    <!-- ── 1. Environment picker (compact strip) ────────────────── -->
    <section class="mt-card mt-env-card">
      <div class="mt-env-line">
        <span class="mt-env-step">Step 1 · Environment</span>

        <div class="mt-env-strip">
          <button
            type="button"
            class="mt-env-chip"
            :class="{ 'is-on': !selectedEnvId }"
            @click="clearActiveEnv"
          >Ad-hoc</button>
          <button
            v-for="env in envs"
            :key="env.id"
            type="button"
            class="mt-env-chip"
            :class="{ 'is-on': selectedEnvId === env.id }"
            @click="applyEnvSelection(env)"
            :title="`${env.prompt_count ?? (env.prompt_ids || []).length} prompts`"
          >
            {{ env.name }}
            <span class="mt-env-chip-count">
              {{ env.prompt_count ?? (env.prompt_ids || []).length }}
            </span>
          </button>
          <span v-if="loadingEnvs" class="mt-muted">Loading…</span>
        </div>

        <div class="mt-env-actions">
          <button v-if="activeEnv" class="mt-link" @click="renameActiveEnv">Rename</button>
          <button v-if="activeEnv" class="mt-link is-danger" @click="deleteActiveEnv">Delete</button>
          <button class="mt-btn-soft mt-btn-sm" @click="promptCreateEnv">+ New</button>
        </div>
      </div>
    </section>

    <!-- ── 2. Prompts — auto-loaded, editable ───────────────────── -->
    <section class="mt-card">
      <div class="mt-card-head">
        <div>
          <div class="mt-card-eyebrow">Step 2</div>
          <h2 class="mt-card-h">Prompts</h2>
          <p class="mt-card-sub">
            <span v-if="activeEnv">
              Loaded from <strong>{{ activeEnv.name }}</strong>. Click any prompt
              to edit — changes save to the environment.
            </span>
            <span v-else>
              Add prompts to run an ad-hoc test, or pick an environment above.
            </span>
            <span class="mt-counter">{{ selectedPrompts.length }} / 25</span>
          </p>
        </div>
        <div class="mt-card-head-actions">
          <button class="mt-btn-soft" @click="$refs.mdInput.click()">Import .md</button>
          <input
            ref="mdInput"
            type="file"
            accept=".md,.txt,text/markdown,text/plain"
            multiple
            class="mt-hidden"
            @change="onMarkdownUpload"
          />
        </div>
      </div>

      <ul v-if="selectedPrompts.length" class="mt-prompts">
        <li
          v-for="(p, i) in selectedPrompts"
          :key="p.uid"
          class="mt-prompt-row"
          :class="{ 'is-editing': editingUid === p.uid }"
        >
          <span class="mt-prompt-num">{{ i + 1 }}</span>
          <template v-if="editingUid === p.uid">
            <textarea
              v-model="editingDraft"
              class="mt-prompt-edit"
              rows="2"
              @keydown.enter.prevent="commitEdit(p)"
              @keydown.esc="cancelEdit"
              ref="editFieldRef"
            />
            <div class="mt-prompt-edit-actions">
              <button class="mt-btn-soft" @click="cancelEdit">Cancel</button>
              <button class="mt-btn-primary" @click="commitEdit(p)">Save</button>
            </div>
          </template>
          <template v-else>
            <span class="mt-prompt-text" @click="startEdit(p)">{{ p.text }}</span>
            <span v-if="p.savedId" class="mt-prompt-badge">saved</span>
            <span v-else class="mt-prompt-badge is-ghost">ad-hoc</span>
            <button class="mt-prompt-icon" title="Edit" @click="startEdit(p)">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 2.5l2.5 2.5L4 12.5H1.5V10L9 2.5z" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
            <button class="mt-prompt-icon" title="Remove" @click="removeSelected(p.uid)">×</button>
          </template>
        </li>
      </ul>
      <div v-else class="mt-empty">
        No prompts yet. Add one below, import a markdown file, or pick an
        environment above.
      </div>

      <!-- inline add -->
      <div class="mt-prompt-add">
        <input
          v-model="customDraft"
          class="mt-input"
          placeholder="Add a new prompt and press Enter"
          @keydown.enter="addCustom"
        />
        <button class="mt-btn-primary" :disabled="!customDraft.trim()" @click="addCustom">
          Add
        </button>
      </div>
    </section>

    <!-- ── 3. Models ────────────────────────────────────────────── -->
    <section class="mt-card mt-models-card">
      <div class="mt-models-line">
        <span class="mt-env-step">Step 3 · Models</span>
        <span class="mt-pickcount">{{ selectedVariantIds.length }} selected</span>
      </div>

      <div class="mt-providers">
        <div
          v-for="prov in providerRows"
          :key="prov.key"
          class="mt-provider-row"
          :class="{ 'is-off': !prov.configured }"
        >
          <div class="mt-provider-side">
            <span class="mt-model-dot" :class="'is-' + prov.key"></span>
            <span class="mt-provider-name">{{ prov.label }}</span>
            <span v-if="!prov.configured" class="mt-model-soon">needs API key</span>
          </div>

          <div class="mt-variant-dd" @click.stop>
            <button
              type="button"
              class="mt-variant-btn"
              :disabled="!prov.configured"
              @click="toggleDropdown(prov.key)"
            >
              <span v-if="!selectedForProvider(prov.key).length" class="mt-variant-btn-empty">
                Select models…
              </span>
              <span v-else class="mt-variant-btn-list">
                <span
                  v-for="v in selectedForProvider(prov.key)"
                  :key="v.id"
                  class="mt-variant-pill"
                >
                  {{ v.label }}
                  <span class="mt-variant-pill-x" @click.stop="toggleVariant(v.id)">×</span>
                </span>
              </span>
              <svg class="mt-variant-caret" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 4l3 4 3-4" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>

            <div v-if="dropdownOpen === prov.key" class="mt-variant-menu">
              <div class="mt-variant-menu-h">{{ prov.label }} models</div>
              <button
                v-for="v in prov.variants"
                :key="v.id"
                type="button"
                class="mt-variant-menu-item"
                :class="{ 'is-on': selectedVariantIds.includes(v.id) }"
                @click="toggleVariant(v.id)"
              >
                <span class="mt-variant-check">
                  <svg v-if="selectedVariantIds.includes(v.id)" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M2 6l3 3 5-6" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </span>
                <span class="mt-variant-menu-label">{{ v.label }}</span>
                <span v-if="v.is_default" class="mt-variant-default">default</span>
                <span class="mt-variant-menu-id">{{ v.model_id }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── 4. Run ───────────────────────────────────────────────── -->
    <section class="mt-card mt-run-card">
      <div class="mt-run-info">
        <div class="mt-run-num">{{ totalQueries }}</div>
        <div>
          <div class="mt-run-label">total queries</div>
          <div class="mt-run-sub">
            {{ promptCount }} prompt{{ promptCount === 1 ? '' : 's' }}
            × {{ selectedVariantIds.length }} model{{ selectedVariantIds.length === 1 ? '' : 's' }}
            · ~{{ etaSeconds }}s
          </div>
        </div>
      </div>
      <button
        class="mt-btn-run"
        :disabled="!canRun || running"
        @click="runProbe"
      >
        <span v-if="running">
          <span class="mt-spinner"></span>
          Running… {{ liveCompleted }}/{{ liveTotal }}
        </span>
        <span v-else>Run audit</span>
      </button>
    </section>

    <div class="mt-runmode">
      <span class="mt-runmode-tag">Run mode</span>
      <span class="mt-runmode-text">
        <strong>Sequential discovery probe.</strong>
        Each prompt is sent to each selected model one at a time —
        prompt&nbsp;1 → model&nbsp;A → model&nbsp;B → …, then prompt&nbsp;2, and
        so on. Results stream in live so you can read them as the run
        progresses. No retries; failed calls show up as
        <em>failed</em> cells. The brand-mention check is a
        case-insensitive substring scan against your business name and
        aliases on each model's response.
      </span>
    </div>

    </template> <!-- /v-if="!hasActiveRun" -->

    <div v-if="errorMsg" class="mt-error">{{ errorMsg }}</div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useToast } from '@/composables/useToast'
import llmRanking from '@/api/llm_ranking'
import promptLibrary from '@/api/promptLibrary'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const toast = useToast()
const websiteId = route.params.websiteId

const brandLabel = computed(() => {
  const w = appStore.activeWebsite
  return (w?.business_name || w?.name || 'your brand').trim()
})

// Audit type — surfaced as a chip in the page header + the status
// panel so users always see what kind of probe this is. "Discovery"
// is the only mode today; keeping it computed leaves room for future
// modes (e.g. "Ranking", "Competitor mapping") without template edits.
const auditTypeLabel = 'Discovery probe'
const auditTypeBlurb = (
  'Sequential discovery probe — every prompt is sent to every selected '
  + 'model one at a time. A case-insensitive substring match against your '
  + 'brand name and aliases determines whether each response counts as a '
  + '"mention". No retries; failed calls are recorded but not re-tried.'
)

// ── State: prompts ────────────────────────────────────────────────
const savedPrompts = ref([])     // [{ id, text, style }]
const selectedPrompts = ref([])  // { uid, text, savedId? }
let _uid = 0
const nextUid = () => ++_uid

const promptCount = computed(() => selectedPrompts.value.length)

// ── State: environments ──────────────────────────────────────────
const envs = ref([])
const loadingEnvs = ref(false)
const selectedEnvId = ref(null)

const activeEnv = computed(() =>
  envs.value.find((e) => e.id === selectedEnvId.value) || null,
)

function _patchEnv(updated) {
  if (!updated || !updated.id) return
  envs.value = envs.value.map((e) => e.id === updated.id ? { ...e, ...updated } : e)
}

function _setEnvPromptIds(envId, ids) {
  envs.value = envs.value.map((e) =>
    e.id === envId ? { ...e, prompt_ids: ids, prompt_count: ids.length } : e,
  )
}

function clearActiveEnv() {
  selectedEnvId.value = null
  selectedPrompts.value = []
}

async function promptCreateEnv() {
  const name = window.prompt('Name this environment:', `Env ${envs.value.length + 1}`)
  if (!name || !name.trim()) return
  try {
    const { data } = await promptLibrary.createTestEnvironment(websiteId, name.trim(), [])
    const env = data?.data || data
    envs.value = [env, ...envs.value]
    selectedEnvId.value = env.id
    selectedPrompts.value = []
    toast.success(`Created "${env.name}".`)
  } catch (e) {
    const msg = e.response?.status === 409
      ? 'An environment with that name already exists.'
      : (e.displayMessage || 'Could not create env.')
    toast.error(msg)
  }
}

async function renameActiveEnv() {
  if (!activeEnv.value) return
  const name = window.prompt('Rename environment:', activeEnv.value.name)
  if (!name || !name.trim() || name.trim() === activeEnv.value.name) return
  try {
    const { data } = await promptLibrary.renameTestEnvironment(
      websiteId, activeEnv.value.id, name.trim(),
    )
    _patchEnv(data?.data || data)
  } catch (e) {
    toast.error(e.displayMessage || 'Could not rename.')
  }
}

async function deleteActiveEnv() {
  if (!activeEnv.value) return
  if (!window.confirm(`Delete "${activeEnv.value.name}"? Prompts inside stay saved.`)) return
  try {
    await promptLibrary.deleteTestEnvironment(websiteId, activeEnv.value.id)
    const removed = activeEnv.value.id
    envs.value = envs.value.filter((e) => e.id !== removed)
    clearActiveEnv()
    toast.success('Environment deleted.')
  } catch (e) {
    toast.error('Could not delete.')
  }
}

async function loadSaved() {
  try {
    const { data } = await promptLibrary.listBrandPrompts(websiteId)
    const rows = (data?.data || data || []).map((bp) => ({
      id: bp.id || bp.brand_prompt_id || bp.prompt?.id,
      text: (bp.prompt?.template_text || bp.prompt?.text || bp.text || '').trim(),
      style: bp.prompt?.style || '',
    })).filter((p) => p.text)
    savedPrompts.value = rows
  } catch {
    savedPrompts.value = []
  }
}

async function loadEnvs() {
  loadingEnvs.value = true
  try {
    const { data } = await promptLibrary.listTestEnvironments(websiteId)
    const rows = data?.data || data || []
    envs.value = Array.isArray(rows) ? rows : []
  } catch {
    envs.value = []
  } finally {
    loadingEnvs.value = false
  }
}

function applyEnvSelection(env) {
  if (!env) return
  selectedEnvId.value = env.id
  const ids = new Set(env.prompt_ids || [])
  const matched = savedPrompts.value.filter((p) => ids.has(p.id))
  selectedPrompts.value = matched.map((p) => ({
    uid: nextUid(), text: p.text, savedId: p.id,
  }))
  if (matched.length === 0 && (env.prompt_ids || []).length === 0) {
    toast.info('This environment is empty — add prompts to get started.')
  }
}

// ── State: prompt editing ────────────────────────────────────────
const editingUid = ref(null)
const editingDraft = ref('')
const editFieldRef = ref(null)

function startEdit(p) {
  editingUid.value = p.uid
  editingDraft.value = p.text
  nextTick(() => {
    const el = Array.isArray(editFieldRef.value) ? editFieldRef.value[0] : editFieldRef.value
    el?.focus?.()
  })
}

function cancelEdit() {
  editingUid.value = null
  editingDraft.value = ''
}

async function commitEdit(p) {
  const next = editingDraft.value.trim()
  if (!next) { cancelEdit(); return }
  if (next === p.text) { cancelEdit(); return }

  // Ad-hoc prompts (no savedId, no env): just update in place locally.
  if (!p.savedId || !activeEnv.value) {
    selectedPrompts.value = selectedPrompts.value.map((x) =>
      x.uid === p.uid ? { ...x, text: next } : x,
    )
    cancelEdit()
    return
  }

  // Saved-and-in-env: backend prompts are dedupe-by-hash. To "edit" we
  // create a new BrandPrompt for the new text, swap it into the env,
  // and drop the old one from the env.
  try {
    const newBpId = await _persistTextAsBrandPrompt(next)
    if (!newBpId) throw new Error('Could not save edit.')
    const envId = activeEnv.value.id
    const oldBpId = p.savedId
    if (newBpId !== oldBpId) {
      await promptLibrary.addPromptsToEnv(websiteId, envId, [newBpId])
      await promptLibrary.removePromptsFromEnv(websiteId, envId, [oldBpId])
      const ids = new Set(activeEnv.value.prompt_ids || [])
      ids.delete(oldBpId)
      ids.add(newBpId)
      _setEnvPromptIds(envId, Array.from(ids))
    }
    selectedPrompts.value = selectedPrompts.value.map((x) =>
      x.uid === p.uid ? { ...x, text: next, savedId: newBpId } : x,
    )
    await loadSaved()
    cancelEdit()
  } catch (e) {
    toast.error(e.displayMessage || 'Could not save edit.')
  }
}

// ── Add / remove / import ────────────────────────────────────────
const customDraft = ref('')
async function addCustom() {
  const t = customDraft.value.trim()
  if (!t) return
  if (selectedPrompts.value.length >= 25) {
    toast.error('Max 25 prompts per run.')
    return
  }
  if (activeEnv.value) {
    try {
      const bpId = await _persistTextAsBrandPrompt(t)
      if (bpId) {
        await promptLibrary.addPromptsToEnv(websiteId, activeEnv.value.id, [bpId])
        selectedPrompts.value.push({ uid: nextUid(), text: t, savedId: bpId })
        const ids = new Set([...(activeEnv.value.prompt_ids || []), bpId])
        _setEnvPromptIds(activeEnv.value.id, Array.from(ids))
        await loadSaved()
        customDraft.value = ''
        return
      }
    } catch (e) {
      toast.error(e.displayMessage || 'Could not save to environment.')
      return
    }
  }
  selectedPrompts.value.push({ uid: nextUid(), text: t })
  customDraft.value = ''
}

async function _persistTextAsBrandPrompt(text) {
  const { data } = await promptLibrary.createWebsitePrompt(websiteId, {
    template_text: text,
    text,
    style: 'question',
    intent_bucket: 'category',
  })
  const payload = data?.data || data || {}
  return payload.brand_prompt_id || null
}

const mdInput = ref(null)
function parseMarkdown(text) {
  return (text || '')
    .split(/\r?\n/)
    .map((line) => line.replace(/^\s*([>*-]|#{1,6})\s*/, '').trim())
    .filter((line) => line.length >= 5)
}
async function onMarkdownUpload(e) {
  const files = Array.from(e.target?.files || [])
  if (!files.length) return
  const texts = await Promise.all(files.map((f) => f.text()))
  const lines = []
  for (const t of texts) {
    for (const line of parseMarkdown(t)) {
      if (selectedPrompts.value.length + lines.length >= 25) break
      lines.push(line)
    }
  }
  if (mdInput.value) mdInput.value.value = ''
  if (!lines.length) return
  if (activeEnv.value) {
    try {
      const newIds = []
      for (const line of lines) {
        const bpId = await _persistTextAsBrandPrompt(line)
        if (bpId) {
          newIds.push(bpId)
          selectedPrompts.value.push({ uid: nextUid(), text: line, savedId: bpId })
        }
      }
      if (newIds.length) {
        await promptLibrary.addPromptsToEnv(websiteId, activeEnv.value.id, newIds)
        const ids = new Set([...(activeEnv.value.prompt_ids || []), ...newIds])
        _setEnvPromptIds(activeEnv.value.id, Array.from(ids))
        await loadSaved()
      }
      toast.success(`Imported ${newIds.length} into ${activeEnv.value.name}.`)
      return
    } catch (e2) {
      toast.error(e2.displayMessage || 'Could not import into environment.')
      return
    }
  }
  for (const line of lines) {
    selectedPrompts.value.push({ uid: nextUid(), text: line })
  }
  toast.success(`Imported ${lines.length} prompt${lines.length === 1 ? '' : 's'}`)
}

async function removeSelected(uid) {
  const removed = selectedPrompts.value.find((p) => p.uid === uid)
  selectedPrompts.value = selectedPrompts.value.filter((p) => p.uid !== uid)
  if (removed?.savedId && activeEnv.value) {
    try {
      await promptLibrary.removePromptsFromEnv(websiteId, activeEnv.value.id, [removed.savedId])
      const ids = (activeEnv.value.prompt_ids || []).filter((id) => id !== removed.savedId)
      _setEnvPromptIds(activeEnv.value.id, ids)
    } catch {
      toast.error('Could not sync environment.')
    }
  }
}

// ── Models (variants per provider) ───────────────────────────────
// Each entry: { id, provider, model_id, label, is_default, configured }
const modelVariants = ref([])
const selectedVariantIds = ref([])
const dropdownOpen = ref(null)

const PROVIDER_LABELS = {
  claude: 'Claude (Anthropic)',
  gpt4: 'GPT-4 (OpenAI)',
  gemini: 'Gemini (Google)',
  perplexity: 'Perplexity',
}

// Grouped rows for the picker. Each provider gets one row with its
// available variants and a `configured` flag.
const providerRows = computed(() => {
  const groups = new Map()
  for (const v of modelVariants.value) {
    if (!groups.has(v.provider)) {
      groups.set(v.provider, {
        key: v.provider,
        label: PROVIDER_LABELS[v.provider] || v.provider,
        configured: !!v.configured,
        variants: [],
      })
    }
    groups.get(v.provider).variants.push(v)
  }
  return Array.from(groups.values())
})

const variantsById = computed(() => {
  const m = new Map()
  for (const v of modelVariants.value) m.set(v.id, v)
  return m
})

function selectedForProvider(providerKey) {
  return selectedVariantIds.value
    .map((id) => variantsById.value.get(id))
    .filter((v) => v && v.provider === providerKey)
}

function toggleVariant(id) {
  const v = variantsById.value.get(id)
  if (!v || !v.configured) return
  if (selectedVariantIds.value.includes(id)) {
    selectedVariantIds.value = selectedVariantIds.value.filter((x) => x !== id)
  } else {
    selectedVariantIds.value = [...selectedVariantIds.value, id]
  }
}

function toggleDropdown(providerKey) {
  dropdownOpen.value = dropdownOpen.value === providerKey ? null : providerKey
}

// Lookup helpers used by results. Variant id is the column key.
function variantLabel(id) {
  const v = variantsById.value.get(id)
  if (v) {
    const provLabel = (PROVIDER_LABELS[v.provider] || v.provider).split(' ')[0]
    return `${provLabel} ${v.label}`
  }
  // Legacy fallback: bare provider key (pre-variant runs).
  return PROVIDER_LABELS[id] ? PROVIDER_LABELS[id].split(' ')[0] : id
}
// Back-compat alias so existing template helpers keep working.
function providerLabel(id) { return variantLabel(id) }

function providerKeyOf(variantId) {
  const v = variantsById.value.get(variantId)
  if (v) return v.provider
  // Legacy run state used bare provider keys.
  return variantId
}

async function loadModelVariants() {
  try {
    const { data } = await llmRanking.modelVariants(websiteId)
    const items = (data?.data || data || {}).variants || []
    if (!items.length) return
    modelVariants.value = items
    // Default selection: every provider's `is_default` variant if its
    // API key is configured. Falls back to the first configured variant
    // overall so the page is usable out of the box.
    const defaults = items.filter((v) => v.is_default && v.configured).map((v) => v.id)
    if (defaults.length) {
      selectedVariantIds.value = defaults
    } else {
      const first = items.find((v) => v.configured)
      selectedVariantIds.value = first ? [first.id] : []
    }
  } catch {
    // No variants endpoint — leave empty; UI shows an empty picker.
  }
}

const totalQueries = computed(() => promptCount.value * (selectedVariantIds.value.length || 0))
const canRun = computed(() => totalQueries.value > 0)
// Rough sequential ETA: ~3s per upstream call. Inter-call pacing
// is now 250ms (kept in sync with MODEL_TEST_INTER_CALL_SLEEP_MS on
// the backend) so it doesn't materially shift the estimate.
const etaSeconds = computed(() => Math.max(1, totalQueries.value * 3))

// ── Run + poll ───────────────────────────────────────────────────
const running = ref(false)
const errorMsg = ref('')
const lastRun = ref(null)
const liveRun = ref(null)
const runId = ref(null)
let pollTimer = null

const liveCompleted = computed(() => liveRun.value?.completed || 0)
const liveTotal     = computed(() => liveRun.value?.total || 0)
const livePct = computed(() => {
  if (!liveTotal.value) return 0
  return Math.min(100, Math.round((liveCompleted.value / liveTotal.value) * 100))
})
const liveCurrentLabel = computed(() => {
  const s = liveRun.value
  if (!s || s.status !== 'running') return ''
  const pIdx = (s.current_prompt_index ?? 0) + 1
  const pText = (s.prompts?.[s.current_prompt_index] || '').slice(0, 70)
  return `Prompt ${pIdx} of ${s.prompts?.length || 0} · ${providerLabel(s.current_provider || '')} — "${pText}${pText.length >= 70 ? '…' : ''}"`
})

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function pollOnce() {
  if (!runId.value) return
  try {
    const { data } = await llmRanking.modelTestStatus(websiteId, runId.value)
    const state = data?.data || data
    liveRun.value = state
    if (state.status === 'complete') {
      lastRun.value = state
      running.value = false
      stopPolling()
      toast.success('Audit complete')
    } else if (state.status === 'failed') {
      errorMsg.value = state.error || 'Probe failed.'
      running.value = false
      stopPolling()
    }
  } catch (e) {
    errorMsg.value = e.displayMessage || e?.response?.data?.error || 'Lost connection to probe.'
    running.value = false
    stopPolling()
  }
}

async function runProbe() {
  errorMsg.value = ''
  lastRun.value = null
  liveRun.value = null
  openResponses.value = {}
  running.value = true
  try {
    const { data } = await llmRanking.modelTest(websiteId, {
      prompts: selectedPrompts.value.map((p) => p.text),
      models: selectedVariantIds.value,
    })
    runId.value = (data?.data || data)?.run_id
    if (!runId.value) throw new Error('No run id returned.')
    // Push the run_id into the URL so a page refresh lands back on
    // these results (status view falls back to the DB if Redis has
    // expired). Also makes the URL shareable.
    router.replace({ query: { ...route.query, run: runId.value } })
    await pollOnce()
    if (running.value) {
      pollTimer = setInterval(pollOnce, 1500)
    }
  } catch (e) {
    errorMsg.value = e.displayMessage || e?.response?.data?.error || 'Probe failed.'
    running.value = false
    stopPolling()
  }
}

onBeforeUnmount(stopPolling)

// Reset the page back to its configuration view. Drops the ?run=
// query param so a refresh now lands on the config view, not the
// (now-orphaned) old results.
function startNewAudit() {
  lastRun.value = null
  liveRun.value = null
  runId.value = null
  errorMsg.value = ''
  openResponses.value = {}
  const next = { ...route.query }
  delete next.run
  router.replace({ query: next })
}

// Hydrate a previous run when the page is opened with ?run=<id>.
// Used on first mount so a refresh on the results view stays on
// the results view. The status endpoint reads from Redis first,
// falling back to the persisted ModelTestRun row when Redis has
// expired — see ModelTestStatusView in apps/llm_ranking/api/v1.
async function hydrateRunFromUrl() {
  const id = (route.query.run || '').toString().trim()
  if (!id) return
  runId.value = id
  try {
    const { data } = await llmRanking.modelTestStatus(websiteId, id)
    const state = data?.data || data
    if (!state) return
    if (state.status === 'complete' || state.status === 'failed') {
      lastRun.value = state
      liveRun.value = state
      running.value = false
    } else {
      // Still in flight on the worker — pick up polling where the
      // previous tab left off.
      liveRun.value = state
      running.value = true
      pollTimer = setInterval(pollOnce, 1500)
    }
  } catch (e) {
    // 404 = run expired or never existed. Clear the stale query
    // param so the user lands on the config view cleanly.
    if (e?.response?.status === 404) {
      const next = { ...route.query }
      delete next.run
      router.replace({ query: next })
      return
    }
    errorMsg.value = e.displayMessage || 'Could not load that run.'
  }
}

// ── Results helpers ──────────────────────────────────────────────
const displayRun = computed(() => lastRun.value || liveRun.value)

// True whenever there's something worth rendering at the top of the
// page (an active run or a finished one we haven't navigated away from).
const hasActiveRun = computed(() => running.value || !!displayRun.value)

// ── Status panel (very verbose) ──────────────────────────────────
const STATUS_LABELS = {
  queued:    'Queued',
  running:   'Running',
  analyzing: 'Analyzing',
  complete:  'Complete',
  failed:    'Failed',
}
const statusLabel = computed(() => STATUS_LABELS[displayRun.value?.status] || 'Pending')

const statusHeadline = computed(() => {
  const s = displayRun.value
  if (!s) return 'Preparing your audit…'
  if (s.status === 'queued') return 'Waiting for a worker to pick this up.'
  if (s.status === 'running') {
    const pIdx = (s.current_prompt_index ?? 0) + 1
    const pCount = s.prompts?.length || 0
    return `Querying prompt ${pIdx} of ${pCount} on ${variantLabel(s.current_provider || '')}.`
  }
  if (s.status === 'analyzing') return 'Models done. Running synthesis + web grounding.'
  if (s.status === 'complete') {
    const hits = s.summary?.prompts_with_hit ?? 0
    const total = s.summary?.prompts ?? 0
    return `Complete — brand surfaced on ${hits} of ${total} prompts.`
  }
  if (s.status === 'failed') return s.error || 'Audit failed.'
  return ''
})

const statusSub = computed(() => {
  const s = displayRun.value
  if (!s) return ''
  if (s.status === 'running') {
    const pText = (s.prompts?.[s.current_prompt_index] || '').slice(0, 90)
    return pText
      ? `Currently asking: "${pText}${pText.length >= 90 ? '…' : ''}"`
      : 'Dispatching the next call…'
  }
  if (s.status === 'analyzing') {
    return 'These steps run after every model response is in. They are sequential — synthesis first, then grounding.'
  }
  return ''
})

// Show post-processing sub-status once raw model calls are done.
const showPostProcessing = computed(() => {
  const s = displayRun.value?.status
  return s === 'analyzing' || s === 'complete' || s === 'failed'
})
const sentimentStatusText = computed(() => {
  const s = displayRun.value
  if (!s) return ''
  if (s.sentiment_status === 'running') return 'Labeling each brand mention as positive / neutral / negative / aside.'
  if (s.sentiment_status === 'complete') {
    const rows = s.prompt_rows || []
    const labeled = rows.reduce(
      (acc, row) => acc + (row.responses || []).filter((r) => r.sentiment).length,
      0,
    )
    return labeled ? `Done — ${labeled} mention${labeled === 1 ? '' : 's'} classified.` : 'Done — no mentions to classify.'
  }
  if (s.sentiment_status === 'skipped') return 'Skipped — no brand mentions or no tooling provider configured.'
  if (s.sentiment_status === 'failed') return s.sentiment_error || 'Sentiment classifier failed.'
  return 'Queued.'
})

const analysisStatusText = computed(() => {
  const s = displayRun.value
  if (!s) return ''
  if (s.analysis_status === 'running') return 'Reading every response, writing the verbose report.'
  if (s.analysis_status === 'complete') {
    const p = s.analysis?.provider ? ` via ${s.analysis.provider}` : ''
    return `Done${p}.`
  }
  if (s.analysis_status === 'skipped') return s.analysis_skip_reason || 'Skipped.'
  if (s.analysis_status === 'failed') return s.analysis_error || 'Synthesis failed.'
  return 'Queued.'
})
const groundingStatusText = computed(() => {
  const s = displayRun.value
  if (!s) return ''
  if (s.grounding_status === 'running') return 'Asking Gemini to research the brand on the open web.'
  if (s.grounding_status === 'complete') {
    if (!s.google_grounding) return 'Skipped — Gemini API key not configured.'
    const cites = (s.google_grounding.citations || []).length
    return cites ? `Done — ${cites} source${cites === 1 ? '' : 's'} cited.` : 'Done.'
  }
  if (s.grounding_status === 'skipped') return s.grounding_skip_reason || 'Skipped.'
  if (s.grounding_status === 'failed') return s.grounding_error || 'Grounding failed.'
  return 'Queued.'
})

// The most-recently-arrived response cell. While the run streams,
// this is what the "Just in" peek panel shows so the user always
// sees fresh content land without scrolling.
const latestCompletedResponse = computed(() => {
  const rows = displayRun.value?.prompt_rows || []
  if (!rows.length) return null
  // Walk from the end backwards: the last row is the currently-active
  // prompt; the last response in that row is the most recent cell.
  for (let i = rows.length - 1; i >= 0; i -= 1) {
    const row = rows[i]
    const responses = row.responses || []
    if (!responses.length) continue
    const r = responses[responses.length - 1]
    const ok = !!r.succeeded
    let label, cls
    if (!ok) { label = 'failed'; cls = 'is-fail' }
    else if (r.brand_mentioned) { label = 'mentioned'; cls = 'is-hit' }
    else if (r.relevance === 'near_miss') { label = 'near miss'; cls = 'is-near' }
    else if (r.relevance === 'category_match') { label = 'category'; cls = 'is-cat' }
    else { label = 'no match'; cls = 'is-miss' }
    return {
      provider: r.provider,
      prompt_idx: i,
      text: r.response_text || '',
      error: r.error || '',
      duration_ms: r.duration_ms || 0,
      label, cls,
      raw: r,  // pass-through so renderResponse can read .entities
    }
  }
  return null
})

// Flatten prompt_rows -> a verbose event log (one row per model call).
// Newest events appear at the top so the user always sees the latest.
// Capped at 50 entries to keep the panel manageable.
const statusLog = computed(() => {
  const rows = displayRun.value?.prompt_rows || []
  const out = []
  rows.forEach((row, pi) => {
    (row.responses || []).forEach((r) => {
      const ok = !!r.succeeded
      let state, cls
      if (!ok) {
        state = r.error ? `failed: ${(r.error || '').slice(0, 60)}` : 'failed'
        cls = 'is-fail'
      } else if (r.brand_mentioned) {
        state = 'mentioned'; cls = 'is-hit'
      } else if (r.relevance === 'near_miss') {
        state = 'near miss'; cls = 'is-near'
      } else if (r.relevance === 'category_match') {
        state = 'category'; cls = 'is-cat'
      } else {
        state = 'no match'; cls = 'is-miss'
      }
      out.push({
        key: `${pi}:${r.provider}`,
        step: `${pi + 1}.${(displayRun.value?.providers || []).indexOf(r.provider) + 1}`,
        text: `${variantLabel(r.provider)} — ${(row.prompt || '').slice(0, 80)}${(row.prompt || '').length > 80 ? '…' : ''}`,
        ms: r.duration_ms ? Math.round(r.duration_ms) : 0,
        state,
        cls,
      })
    })
  })
  return out.slice(-50).reverse()
})

// Minimal Markdown -> safe HTML renderer used for synthesis + grounding
// panels. Handles headings, bold, italics, inline code, links, ordered
// and unordered lists, and paragraphs. Anything else passes through as
// escaped text. Intentionally minimal so we don't pull in a 60kB lib.
function _escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ))
}
function _inlineMd(s) {
  let t = _escapeHtml(s)
  t = t.replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
  t = t.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  t = t.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>')
  t = t.replace(/`([^`]+)`/g, '<code>$1</code>')
  return t
}
function renderMarkdown(md) {
  if (!md) return ''
  const lines = md.replace(/\r\n/g, '\n').split('\n')
  const out = []
  let inUl = false, inOl = false, inP = []

  const flushP = () => {
    if (inP.length) {
      out.push(`<p>${_inlineMd(inP.join(' '))}</p>`)
      inP = []
    }
  }
  const closeLists = () => {
    if (inUl) { out.push('</ul>'); inUl = false }
    if (inOl) { out.push('</ol>'); inOl = false }
  }

  for (const raw of lines) {
    const line = raw.trimEnd()
    if (!line.trim()) { flushP(); closeLists(); continue }

    const h = line.match(/^(#{1,4})\s+(.*)$/)
    if (h) {
      flushP(); closeLists()
      const level = h[1].length + 1   // ## -> h3 so we don't fight the card h2
      out.push(`<h${level}>${_inlineMd(h[2])}</h${level}>`)
      continue
    }
    const ol = line.match(/^\s*\d+\.\s+(.*)$/)
    if (ol) {
      flushP()
      if (inUl) { out.push('</ul>'); inUl = false }
      if (!inOl) { out.push('<ol>'); inOl = true }
      out.push(`<li>${_inlineMd(ol[1])}</li>`)
      continue
    }
    const ul = line.match(/^\s*[-*]\s+(.*)$/)
    if (ul) {
      flushP()
      if (inOl) { out.push('</ol>'); inOl = false }
      if (!inUl) { out.push('<ul>'); inUl = true }
      out.push(`<li>${_inlineMd(ul[1])}</li>`)
      continue
    }
    if (inUl || inOl) closeLists()
    inP.push(line.trim())
  }
  flushP(); closeLists()
  return out.join('\n')
}

const resultsProviders = computed(() => {
  const fromState = displayRun.value?.providers
  if (Array.isArray(fromState) && fromState.length) return fromState
  return selectedVariantIds.value
})

// Per-prompt accordion open/close state. Keyed by prompt index.
// `promptManuallyCollapsed` records rows the user has actively
// collapsed during a streaming run so the auto-expand watcher
// (below) doesn't fight them.
const promptOpen = ref({})
const promptManuallyCollapsed = ref({})

// While a run is streaming, auto-expand the most-recently-active
// prompt row so model responses appear as they land. Rows the user
// manually collapses stay collapsed for the rest of the run.
watch(
  () => ({
    pi: displayRun.value?.current_prompt_index ?? null,
    rowsLen: (displayRun.value?.prompt_rows || []).length,
    status: displayRun.value?.status,
  }),
  ({ pi, rowsLen }) => {
    if (!running.value) return
    const lastIdx = Math.max(rowsLen - 1, pi ?? -1)
    if (lastIdx < 0) return
    if (promptManuallyCollapsed.value[lastIdx]) return
    if (!promptOpen.value[lastIdx]) {
      promptOpen.value = { ...promptOpen.value, [lastIdx]: true }
    }
  },
  { immediate: true, deep: true },
)

// Inside an open prompt row, the per-model performance table lets you
// click a model row to reveal that model's full response below.
const respBodyOpen = ref({})  // `${promptIdx}:${variantId}` -> bool
function toggleRespBody(promptIdx, provider) {
  const k = `${promptIdx}:${provider}`
  respBodyOpen.value = { ...respBodyOpen.value, [k]: !respBodyOpen.value[k] }
}
function isRespBodyOpen(promptIdx, provider) {
  return !!respBodyOpen.value[`${promptIdx}:${provider}`]
}

// Per-(prompt, model) breakdown shown in the accordion expansion.
// Returns one row per model with first-mention position, mention
// count, response length, latency, and a delta column showing how
// this model's first-mention position compares to the best model
// for that prompt (negative = earlier, positive = later, "—" when
// either side never mentioned the brand).
function perPromptModelMetrics(promptIdx) {
  const row = displayRun.value?.prompt_rows?.[promptIdx]
  if (!row) return []
  const provs = resultsProviders.value

  const perfs = provs.map((prov) => {
    const r = (row.responses || []).find((x) => x.provider === prov)
    if (!r) {
      return {
        provider: prov,
        first_pos: null, mentions: 0, chars: 0, latency: 0,
        prominence_pct: 0, list_rank: null, list_size: null,
        sentiment: null,
      }
    }
    return {
      provider: prov,
      first_pos: r.first_mention_pos,
      mentions: r.mention_count || 0,
      chars: r.response_chars || (r.response_text || '').length,
      latency: r.duration_ms ? Math.round(r.duration_ms) : 0,
      prominence_pct: Math.round((r.prominence || 0) * 100),
      list_rank: r.list_rank,
      list_size: r.list_size,
      sentiment: r.sentiment || null,
      relevance: r.relevance || null,
      evidence_phrase: r.evidence_phrase || '',
    }
  })

  // "Best" = whichever hit response had the highest prominence (length-
  // normalized position). Falls back to lowest raw first_pos to break
  // ties, then to the first listed model.
  const hits = perfs.filter((p) => p.first_pos !== null)
  const bestProm = hits.length ? Math.max(...hits.map((p) => p.prominence_pct)) : null

  return perfs.map((p) => {
    let delta_label = ''
    let delta_cls = ''
    if (bestProm === null) {
      delta_label = ''
    } else if (p.first_pos === null) {
      delta_label = 'missed'
      delta_cls = 'is-neg'
    } else if (p.prominence_pct === bestProm) {
      delta_label = 'best'
      delta_cls = 'is-best'
    } else {
      const d = bestProm - p.prominence_pct
      delta_label = `−${d}pp prominence`
      delta_cls = 'is-pos'
    }
    return { ...p, delta_label, delta_cls }
  })
}

const SENTIMENT_LABELS = {
  positive: 'Positive',
  neutral: 'Neutral',
  negative: 'Negative',
  non_recommendation: 'Aside',
}
function sentimentLabel(s) { return SENTIMENT_LABELS[s] || '' }

const RELEVANCE_LABELS = {
  direct: 'Direct hit',
  near_miss: 'Near miss',
  category_match: 'Category',
  unrelated: 'Unrelated',
}
function relevanceLabel(s) { return RELEVANCE_LABELS[s] || '' }
function togglePromptRow(idx) {
  const next = !promptOpen.value[idx]
  promptOpen.value = { ...promptOpen.value, [idx]: next }
  if (!next) {
    promptManuallyCollapsed.value = { ...promptManuallyCollapsed.value, [idx]: true }
  } else {
    const cp = { ...promptManuallyCollapsed.value }
    delete cp[idx]
    promptManuallyCollapsed.value = cp
  }
}
const allPromptsOpen = computed(() => {
  const rows = displayRun.value?.prompt_rows || []
  return rows.length > 0 && rows.every((_, i) => promptOpen.value[i])
})
function togglePromptExpandAll() {
  const rows = displayRun.value?.prompt_rows || []
  if (allPromptsOpen.value) {
    promptOpen.value = {}
  } else {
    const next = {}
    for (let i = 0; i < rows.length; i += 1) next[i] = true
    promptOpen.value = next
  }
}

const openResponses = ref({}) // `${rowIdx}:${prov}` -> bool
function toggleResponse(rowIdx, prov) {
  const k = `${rowIdx}:${prov}`
  openResponses.value = { ...openResponses.value, [k]: !openResponses.value[k] }
}
function isResponseOpen(rowIdx, prov) {
  return !!openResponses.value[`${rowIdx}:${prov}`]
}

function cellResponse(row, prov) {
  return (row?.responses || []).find((r) => r.provider === prov) || null
}
// Outcome pill colour. Five buckets so an analyst sees nuance, not
// just hit/miss:
//   is-hit   — brand named verbatim
//   is-near  — relevance=near_miss (described offering without name)
//   is-cat   — relevance=category_match (in the problem space)
//   is-miss  — relevance=unrelated, or no relevance yet
//   is-fail  — call failed
//   is-pending — call hasn't completed yet
function cellClass(row, prov) {
  const r = cellResponse(row, prov)
  if (!r) return 'is-pending'
  if (!r.succeeded) return 'is-fail'
  if (r.brand_mentioned) return 'is-hit'
  if (r.relevance === 'near_miss') return 'is-near'
  if (r.relevance === 'category_match') return 'is-cat'
  return 'is-miss'
}
function cellLabel(row, prov) {
  const r = cellResponse(row, prov)
  if (!r) return 'pending'
  if (!r.succeeded) return 'failed'
  if (r.brand_mentioned) return 'mentioned'
  if (r.relevance === 'near_miss') return 'near miss'
  if (r.relevance === 'category_match') return 'category'
  return 'no match'
}
function cellLatency(row, prov) {
  const r = cellResponse(row, prov)
  return r?.duration_ms ? Math.round(r.duration_ms) : null
}
function cellText(row, prov) {
  const r = cellResponse(row, prov)
  return r?.response_text || r?.error || ''
}

function aggHitCount(row) {
  return (row?.responses || []).filter((r) => r.brand_mentioned).length
}
function aggClass(row) {
  const hits = aggHitCount(row)
  const total = resultsProviders.value.length
  if (!total) return ''
  if (hits === 0) return 'is-none'
  if (hits === total) return 'is-all'
  return 'is-some'
}

// Per-prompt aggregate metrics for the highlights table. Everything
// is precomputed on the worker — first_mention_pos, mention_count,
// prominence, list_rank, list_size, sentiment all arrive verbatim on
// each response. We only roll up here.
const perPromptMetrics = computed(() => {
  const rows = displayRun.value?.prompt_rows || []
  const totalModels = resultsProviders.value.length

  return rows.map((row, idx) => {
    const responses = row.responses || []
    const succeeded = responses.filter((r) => r.succeeded)
    const hits = responses.filter((r) => r.brand_mentioned)
    const latencies = succeeded
      .map((r) => Math.round(r.duration_ms || 0))
      .filter((x) => x > 0)
    const avg_latency_ms = latencies.length
      ? Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length)
      : 0

    const total_mentions = responses.reduce(
      (acc, r) => acc + (r.mention_count || 0), 0,
    )

    // Best model = whichever hit had the highest prominence
    // (= lowest first_mention_pos, length-normalized).
    let first_mention_pos = null
    let best_prominence = 0
    let best_model = ''
    let best_list_rank = null
    let best_list_size = null
    for (const r of responses) {
      if (!r.brand_mentioned) continue
      const p = r.prominence || 0
      if (p > best_prominence
          || (p === best_prominence
              && (first_mention_pos === null
                  || r.first_mention_pos < first_mention_pos))) {
        best_prominence = p
        first_mention_pos = r.first_mention_pos
        best_model = variantLabel(r.provider)
        best_list_rank = r.list_rank
        best_list_size = r.list_size
      }
    }

    const discovery_count = hits.length
    const discovery_pct = totalModels
      ? Math.round((discovery_count / totalModels) * 100)
      : 0

    // Soft signals: how many non-mentioning responses still
    // described the brand (near-miss) or its category. Surfacing
    // these prevents a "0/4 missed" row from looking like a total
    // wash when the underlying answers were thematically close.
    const near_miss_count = responses.filter(
      (r) => r.relevance === 'near_miss',
    ).length
    const category_match_count = responses.filter(
      (r) => r.relevance === 'category_match',
    ).length

    // Coverage pill colour reflects the strongest signal seen for
    // this prompt. A direct hit always wins; otherwise near-miss
    // upgrades a "miss" to indigo, category upgrades to amber.
    let coverage_cls = 'is-miss'
    if (discovery_count > 0) coverage_cls = 'is-hit'
    else if (near_miss_count > 0) coverage_cls = 'is-near'
    else if (category_match_count > 0) coverage_cls = 'is-cat'

    return {
      index: idx,
      prompt: row.prompt || '',
      total_models: totalModels,
      discovery_count,
      discovery_pct,
      total_mentions,
      first_mention_pos,
      best_prominence_pct: Math.round(best_prominence * 100),
      avg_latency_ms,
      best_model,
      best_list_rank,
      best_list_size,
      near_miss_count,
      category_match_count,
      coverage_cls,
    }
  })
})

// Per-model aggregate stats for the scorecards.
const perModelStats = computed(() => {
  const rows = displayRun.value?.prompt_rows || []
  const provs = resultsProviders.value
  return provs.map((prov) => {
    const cells = rows.map((row) => cellResponse(row, prov)).filter(Boolean)
    const attempts = cells.length
    const hits = cells.filter((c) => c.brand_mentioned).length
    const near_miss = cells.filter((c) => c.relevance === 'near_miss').length
    const category_match = cells.filter((c) => c.relevance === 'category_match').length
    const failures = cells.filter((c) => !c.succeeded).length
    const successes = cells.filter((c) => c.succeeded)
    const lat = successes
      .map((c) => Math.round(c.duration_ms || 0))
      .filter((x) => x > 0)
      .sort((a, b) => a - b)
    const median_ms = lat.length
      ? lat[Math.floor(lat.length / 2)]
      : 0
    let unique_finds = 0
    for (const row of rows) {
      const hitsHere = (row.responses || []).filter((r) => r.brand_mentioned)
      if (hitsHere.length === 1 && hitsHere[0].provider === prov) {
        unique_finds += 1
      }
    }
    const discovery_rate = attempts
      ? Math.round((hits / attempts) * 1000) / 10
      : 0
    // "Any signal" = direct mention OR near miss OR category match.
    // This is the headline metric when literal hits are zero — it
    // tells you whether the model is at least thinking in the right
    // neighbourhood, even if it isn't naming the brand.
    const signal_rate = attempts
      ? Math.round(((hits + near_miss + category_match) / attempts) * 1000) / 10
      : 0
    return {
      provider: prov, attempts,
      hits, near_miss, category_match,
      failures, median_ms, unique_finds,
      discovery_rate, signal_rate,
    }
  })
})

// Disagreement matrix: % of prompts where A's hit-verdict ≠ B's hit-verdict.
// Pending / failed cells are treated as "no mention" so the metric remains
// well-defined when streaming.
function _verdict(row, prov) {
  const r = cellResponse(row, prov)
  return !!(r && r.brand_mentioned)
}
function disagreePct(a, b) {
  const rows = displayRun.value?.prompt_rows || []
  if (!rows.length) return 0
  let diff = 0
  for (const row of rows) {
    if (_verdict(row, a) !== _verdict(row, b)) diff += 1
  }
  return Math.round((diff / rows.length) * 1000) / 10
}
function disagreeClass(a, b) {
  const v = disagreePct(a, b)
  if (v >= 40) return 'is-hot'
  if (v >= 20) return 'is-warm'
  if (v > 0)   return 'is-cool'
  return 'is-zero'
}

function _statsFor(prov) {
  return perModelStats.value.find((m) => m.provider === prov)
}
function deltaSigned(a, b) {
  const av = _statsFor(a)?.discovery_rate ?? 0
  const bv = _statsFor(b)?.discovery_rate ?? 0
  const d = Math.round((av - bv) * 10) / 10
  if (d > 0) return `+${d}`
  if (d < 0) return `${d}`
  return '0'
}
function deltaClass(a, b) {
  const av = _statsFor(a)?.discovery_rate ?? 0
  const bv = _statsFor(b)?.discovery_rate ?? 0
  const d = av - bv
  if (d > 10) return 'is-pos-hot'
  if (d > 0)  return 'is-pos'
  if (d < -10) return 'is-neg-hot'
  if (d < 0)  return 'is-neg'
  return 'is-zero'
}

function highlightBrand(text) {
  const terms = (displayRun.value?.brand_terms || []).filter(Boolean)
  let out = (text || '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
  for (const t of terms) {
    if (!t) continue
    const safe = t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    out = out.replace(new RegExp(`(${safe})`, 'ig'), '<mark class="mt-mark">$1</mark>')
  }
  return out
}

// Full response renderer: markdown → HTML, then layer on brand
// highlighting (yellow mark) and entity highlighting (subtle slate
// underline) for the LLM-extracted entities on this response.
function renderResponse(text, response) {
  if (!text) return ''
  let html = renderMarkdown(text)
  const terms = (displayRun.value?.brand_terms || []).filter(Boolean)
  const escForRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  // Brand highlight — yellow background, prominent. Use word
  // boundaries so we don't hit "Apple" inside "applesauce".
  for (const t of terms) {
    if (!t) continue
    html = html.replace(
      new RegExp(`(\\b${escForRe(t)}\\b)`, 'gi'),
      '<mark class="mt-mark">$1</mark>',
    )
  }
  // Entity highlight — subtle underline with hover tooltip. Skip
  // entities that are substrings of the brand to avoid double-
  // highlighting. Longest-first so multi-word entities win.
  const entities = Array.isArray(response?.entities) ? response.entities.slice() : []
  entities.sort((a, b) => b.length - a.length)
  for (const ent of entities) {
    if (!ent || ent.length < 2) continue
    if (terms.some((t) => t && t.toLowerCase().includes(ent.toLowerCase()))) continue
    html = html.replace(
      // Wrap in a non-capturing group; flag literal entity match
      // without word-boundary requirement (works for addresses,
      // multi-word names, punctuation).
      new RegExp(`(${escForRe(ent)})`, 'g'),
      '<span class="mt-ent" title="entity">$1</span>',
    )
  }
  return html
}

// ── Lifecycle ────────────────────────────────────────────────────
function applyQueryPreselect() {
  const rawEnv = (route.query.env || '').toString().trim()
  if (rawEnv) {
    const env = envs.value.find((e) => e.id === rawEnv)
    if (env) { applyEnvSelection(env); return }
  }
  const rawPrompts = (route.query.prompts || '').toString().trim()
  if (!rawPrompts) return
  const ids = new Set(rawPrompts.split(',').filter(Boolean))
  if (!ids.size) return
  const matched = savedPrompts.value.filter((p) => ids.has(p.id))
  if (!matched.length) return
  selectedPrompts.value = matched.map((p) => ({
    uid: nextUid(), text: p.text, savedId: p.id,
  }))
}

function _closeDropdownOnDocClick() { dropdownOpen.value = null }
onMounted(async () => {
  await Promise.all([loadSaved(), loadEnvs(), loadModelVariants()])
  applyQueryPreselect()
  // ?run=<id> in the URL means we're refreshing on a results view —
  // refetch and re-render so the user stays where they were.
  await hydrateRunFromUrl()
  document.addEventListener('click', _closeDropdownOnDocClick)
})
onBeforeUnmount(() => document.removeEventListener('click', _closeDropdownOnDocClick))
</script>

<style scoped>
.mt-page { color: var(--text-primary, #0f172a); }
.mt-page .page-subtitle strong { color: var(--text-primary, #0f172a); font-weight: 600; }

/* Audit-type chip — page title + status headline. */
.mt-title-line { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.mt-audit-type {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 10.5px; font-weight: 600; letter-spacing: 0.10em;
  text-transform: uppercase;
  padding: 4px 10px;
  background: transparent;
  color: #475569;
  border: 1px solid rgba(15, 23, 42, 0.14);
  border-radius: 4px;
  white-space: nowrap;
  cursor: help;
}
.mt-audit-type.is-inline { margin-left: 8px; vertical-align: 2px; }
.mt-audit-type-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: #0f172a;
}

/* ── Card surface (minimal monochrome: flat, thin borders, no shadows) */
.mt-card {
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 6px;
  padding: 28px 32px;
  margin-bottom: 16px;
  box-shadow: none;
}
.mt-card-head {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 16px; margin-bottom: 22px;
}
.mt-card-head-actions { display: flex; gap: 8px; align-items: center; }
.mt-card-eyebrow {
  font-size: 10.5px; font-weight: 600; letter-spacing: 0.14em;
  text-transform: uppercase; color: #94a3b8;
  margin-bottom: 6px;
}
.mt-card-h {
  font-size: 19px; font-weight: 600; color: #0f172a; margin: 0 0 4px;
  letter-spacing: -0.01em;
}
.mt-card-sub {
  font-size: 13.5px; color: #64748b; margin: 0; line-height: 1.6;
}
.mt-counter {
  display: inline-block; margin-left: 10px;
  font-size: 12px; font-weight: 600; color: #94a3b8;
}

/* ── Buttons / links */
.mt-btn-primary, .mt-btn-soft, .mt-btn-run {
  font: inherit; cursor: pointer; border-radius: 5px;
  padding: 9px 16px; font-weight: 500; font-size: 13px;
  border: 1px solid transparent;
  transition: background .15s ease, border-color .15s ease;
}
.mt-btn-primary { background: #0f172a; color: #fff; }
.mt-btn-primary:hover:not(:disabled) { background: #1e293b; }
.mt-btn-primary:disabled { background: #f1f5f9; color: #94a3b8; cursor: not-allowed; }
.mt-btn-soft { background: #f7f7f8; color: #0f172a; border-color: rgba(15, 23, 42, 0.08); }
.mt-btn-soft:hover { background: #efeff1; }
.mt-btn-run {
  background: #0f172a; color: #fff; padding: 12px 28px; font-size: 13.5px;
  font-weight: 500; letter-spacing: 0.02em;
  border-radius: 5px; min-width: 180px;
}
.mt-btn-run:hover:not(:disabled) { background: #1e293b; }
.mt-btn-run:disabled { background: #e2e8f0; color: #94a3b8; cursor: not-allowed; }

.mt-link {
  background: none; border: 0; padding: 0; cursor: pointer;
  color: #0f172a; font: inherit; font-size: 13px; font-weight: 500;
  text-decoration: underline; text-underline-offset: 3px;
}
.mt-link:hover { color: #475569; }
.mt-link.is-danger { color: #b91c1c; }
.mt-dot-sep {
  display: inline-block; width: 3px; height: 3px;
  background: #cbd5e1; border-radius: 50%; margin: 0 10px;
}

.mt-hidden { display: none; }
.mt-muted { color: #94a3b8; font-size: 13px; }
.mt-empty {
  padding: 28px; text-align: center;
  color: #94a3b8; font-size: 14px;
  border: 1px dashed rgba(15, 23, 42, 0.10);
  border-radius: 12px;
}

/* ── Env: compact chip strip */
.mt-env-card { padding: 14px 20px; }
.mt-env-line {
  display: flex; align-items: center; gap: 14px;
  flex-wrap: wrap;
}
.mt-env-step {
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.10em;
  text-transform: uppercase; color: #94a3b8;
  flex: none;
}
.mt-env-strip {
  display: flex; align-items: center; gap: 6px;
  flex: 1; min-width: 0;
  overflow-x: auto;
  padding: 2px 0;
}
.mt-env-strip::-webkit-scrollbar { height: 4px; }
.mt-env-strip::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 4px; }
.mt-env-chip {
  flex: none;
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 9999px;
  font: inherit; font-size: 13px; font-weight: 500; color: #0f172a;
  cursor: pointer;
  white-space: nowrap;
  transition: border-color .12s ease, background .12s ease;
}
.mt-env-chip:hover { border-color: #0f172a; }
.mt-env-chip.is-on {
  background: #0f172a; color: #fff; border-color: #0f172a;
}
.mt-env-chip-count {
  font-size: 11px; font-weight: 700;
  padding: 1px 7px;
  background: rgba(15, 23, 42, 0.08); color: #475569;
  border-radius: 9999px;
}
.mt-env-chip.is-on .mt-env-chip-count { background: rgba(255, 255, 255, 0.18); color: #fff; }
.mt-env-actions {
  display: flex; align-items: center; gap: 10px;
  flex: none;
}
.mt-btn-sm { padding: 6px 12px; font-size: 12.5px; }

/* ── Prompts list */
.mt-prompts {
  list-style: none; margin: 0; padding: 0;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  overflow: hidden;
}
.mt-prompt-row {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 16px;
  background: #fff;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
  transition: background .12s ease;
}
.mt-prompt-row:last-child { border-bottom: 0; }
.mt-prompt-row:hover { background: #fafafb; }
.mt-prompt-row.is-editing { background: #fff8f9; align-items: flex-start; }
.mt-prompt-num {
  flex: none; width: 24px; height: 24px;
  display: inline-flex; align-items: center; justify-content: center;
  background: #f1f5f9; color: #64748b;
  border-radius: 9999px;
  font-size: 11.5px; font-weight: 600;
}
.mt-prompt-text {
  flex: 1; min-width: 0;
  font-size: 14.5px; color: #0f172a; line-height: 1.5;
  cursor: text;
}
.mt-prompt-text:hover { color: #475569; }
.mt-prompt-badge {
  flex: none;
  font-size: 10.5px; font-weight: 600; letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 3px 8px; border-radius: 9999px;
  background: #ecfdf5; color: #047857;
}
.mt-prompt-badge.is-ghost { background: #f1f5f9; color: #64748b; }
.mt-prompt-icon {
  flex: none;
  width: 28px; height: 28px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent; border: 0; border-radius: 8px;
  color: #94a3b8; font-size: 18px; cursor: pointer;
}
.mt-prompt-icon:hover { background: #f1f5f9; color: #0f172a; }

.mt-prompt-edit {
  flex: 1;
  font: inherit;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.18);
  border-radius: 10px;
  resize: vertical;
  min-height: 60px;
}
.mt-prompt-edit:focus { outline: none; border-color: #0f172a; box-shadow: 0 0 0 3px rgba(15, 23, 42, 0.08); }
.mt-prompt-edit-actions { display: flex; gap: 8px; align-items: flex-start; }

.mt-prompt-add {
  display: flex; gap: 10px;
  margin-top: 12px;
}
.mt-input {
  flex: 1;
  font: inherit;
  padding: 12px 14px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 10px;
}
.mt-input:focus { outline: none; border-color: #0f172a; }

/* ── Models: provider rows with variant dropdowns */
.mt-models-card { padding: 14px 20px; }
.mt-models-line {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px;
}
.mt-pickcount {
  font-size: 11.5px; font-weight: 600; color: #94a3b8;
  padding: 3px 10px;
  background: #f1f5f9; border-radius: 9999px;
}
.mt-providers { display: flex; flex-direction: column; gap: 6px; }
.mt-provider-row {
  display: grid;
  grid-template-columns: 170px 1fr;
  align-items: center; gap: 12px;
  padding: 6px 10px;
  background: transparent;
  border: 0;
  border-radius: 8px;
}
.mt-provider-row.is-off { opacity: 0.65; }
.mt-provider-side { display: flex; align-items: center; gap: 8px; min-width: 0; }
.mt-provider-name {
  font-size: 13px; font-weight: 600; color: #0f172a;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.mt-variant-dd { position: relative; min-width: 0; }
.mt-variant-btn {
  width: 100%;
  display: flex; align-items: center; gap: 8px;
  padding: 6px 12px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 8px;
  font: inherit; font-size: 12.5px; color: #0f172a;
  cursor: pointer;
  text-align: left;
  transition: border-color .15s ease;
  min-height: 32px;
}
.mt-variant-btn:hover:not(:disabled) { border-color: #0f172a; }
.mt-variant-btn:disabled { background: #f1f5f9; color: #94a3b8; cursor: not-allowed; }
.mt-variant-btn-empty { color: #94a3b8; flex: 1; }
.mt-variant-btn-list { flex: 1; display: flex; flex-wrap: wrap; gap: 6px; }
.mt-variant-caret { color: #94a3b8; flex: none; }

.mt-variant-pill {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11.5px; font-weight: 600;
  padding: 2px 8px;
  background: #0f172a; color: #fff;
  border-radius: 9999px;
}
.mt-variant-pill-x {
  cursor: pointer; opacity: 0.7;
  font-size: 14px; line-height: 1;
}
.mt-variant-pill-x:hover { opacity: 1; }

.mt-variant-menu {
  position: absolute; top: calc(100% + 6px); left: 0; right: 0;
  z-index: 30;
  max-height: 320px; overflow-y: auto;
  padding: 6px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 12px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.14);
}
.mt-variant-menu-h {
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.10em;
  text-transform: uppercase; color: #94a3b8;
  padding: 8px 10px 6px;
}
.mt-variant-menu-item {
  width: 100%;
  display: grid;
  grid-template-columns: 20px 1fr auto;
  align-items: center; gap: 8px;
  padding: 9px 10px;
  background: transparent; border: 0;
  border-radius: 8px;
  cursor: pointer;
  font: inherit; font-size: 13px; text-align: left;
}
.mt-variant-menu-item:hover { background: #fafafb; }
.mt-variant-menu-item.is-on { background: #f1f5f9; }
.mt-variant-check {
  width: 18px; height: 18px;
  display: inline-flex; align-items: center; justify-content: center;
  border: 1.5px solid rgba(15, 23, 42, 0.18);
  border-radius: 5px;
  color: #fff;
  background: #fff;
}
.mt-variant-menu-item.is-on .mt-variant-check { background: #0f172a; border-color: #0f172a; }
.mt-variant-menu-label { font-weight: 600; color: #0f172a; }
.mt-variant-menu-id {
  font-size: 11px; color: #94a3b8; font-variant-numeric: tabular-nums;
  font-family: ui-monospace, SFMono-Regular, monospace;
  grid-column: 2 / span 2;
  margin-top: -2px;
}
.mt-variant-default {
  font-size: 10px; font-weight: 700; letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: 2px 7px;
  background: #ecfdf5; color: #047857;
  border-radius: 9999px;
}

/* legacy chip classes kept in case any reference lingers */
.mt-models { display: flex; flex-wrap: wrap; gap: 10px; }
.mt-model-chip {
  display: inline-flex; align-items: center; gap: 10px;
  padding: 10px 16px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 9999px;
  cursor: pointer;
  font-size: 14px; font-weight: 500;
}
.mt-model-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: #cbd5e1;
}
.mt-model-dot.is-claude,
.mt-model-dot.is-gpt4,
.mt-model-dot.is-gemini,
.mt-model-dot.is-perplexity { background: #0f172a; }
.mt-model-name { font-weight: 600; }
.mt-model-soon { font-size: 11px; color: #94a3b8; font-weight: 500; }

/* ── Run bar */
.mt-run-card {
  display: flex; align-items: center; justify-content: space-between;
  gap: 24px;
}
.mt-run-info { display: flex; align-items: center; gap: 16px; }
.mt-run-num {
  font-size: 32px; font-weight: 500; color: #0f172a;
  letter-spacing: -0.025em; line-height: 1;
  font-variant-numeric: tabular-nums;
}
.mt-run-label { font-size: 13px; font-weight: 600; color: #0f172a; }
.mt-run-sub { font-size: 12.5px; color: #64748b; }

.mt-spinner {
  display: inline-block; width: 12px; height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: mt-spin 0.7s linear infinite;
  margin-right: 8px; vertical-align: -1px;
}
@keyframes mt-spin { to { transform: rotate(360deg); } }

/* ── Status panel (verbose) */
.mt-status-card { padding: 18px 20px; }
.mt-status-head {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  gap: 14px; align-items: center;
  margin-bottom: 12px;
}
.mt-status-new { white-space: nowrap; }
.mt-status-tag {
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.10em;
  text-transform: uppercase;
  padding: 5px 12px;
  border-radius: 9999px;
  background: #f1f5f9; color: #475569;
  white-space: nowrap;
}
.mt-status-tag.is-queued { background: #f1f5f9; color: #475569; }
.mt-status-tag.is-running { background: #0f172a; color: #fff; }
.mt-status-tag.is-analyzing { background: #0f172a; color: #fff; }
.mt-status-tag.is-complete { background: #f1f5f9; color: #0f172a; border: 1px solid rgba(15, 23, 42, 0.10); }
.mt-status-tag.is-failed { background: #fee2e2; color: #991b1b; }
.mt-status-headline { min-width: 0; }
.mt-status-headline-main { font-size: 15px; font-weight: 600; color: #0f172a; }
.mt-status-headline-sub { font-size: 12.5px; color: #64748b; margin-top: 2px; }
.mt-status-meta { text-align: right; }
.mt-status-meta-num { font-size: 22px; font-weight: 500; color: #0f172a; font-variant-numeric: tabular-nums; line-height: 1; letter-spacing: -0.02em; }
.mt-status-meta-cap { font-size: 10.5px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 2px; }

/* Live "Just in" peek — shows the most recent cell's content
   during a streaming run so the user doesn't need to click. */
.mt-livepeek {
  margin-top: 14px;
  padding: 12px 14px;
  background: #fafafb;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 6px;
}
.mt-livepeek-h {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  font-size: 12.5px;
}
.mt-livepeek-tag {
  font-size: 10px; font-weight: 700; letter-spacing: 0.10em;
  text-transform: uppercase;
  padding: 2px 8px; border-radius: 9999px;
  background: #0f172a; color: #fff;
}
.mt-livepeek-model { font-weight: 600; color: #0f172a; }
.mt-livepeek-ms { font-size: 11.5px; color: #94a3b8; font-variant-numeric: tabular-nums; }
.mt-livepeek-prompt { color: #94a3b8; }
.mt-livepeek-body {
  margin-top: 10px;
  font-size: 12.5px; color: #334155; line-height: 1.55;
  white-space: normal;
  word-break: break-word;
  overflow-wrap: anywhere;
  max-height: 220px; overflow-y: auto;
  min-width: 0;
}
.mt-livepeek-body p { margin: 0 0 8px; }
.mt-livepeek-body p:last-child { margin-bottom: 0; }
.mt-livepeek-body ul, .mt-livepeek-body ol { margin: 6px 0 8px; padding-left: 20px; }
.mt-livepeek-body li { margin: 3px 0; }
.mt-livepeek-body strong { color: #0f172a; font-weight: 600; }
.mt-livepeek-body h3, .mt-livepeek-body h4, .mt-livepeek-body h5 {
  font-size: 13px; font-weight: 700; color: #0f172a;
  margin: 10px 0 4px;
}
.mt-livepeek-err { margin-top: 8px; font-size: 12px; color: #b91c1c; }

.mt-status-log {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
}
.mt-status-log-h {
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.10em;
  text-transform: uppercase; color: #94a3b8;
  margin-bottom: 8px;
}
.mt-status-log-list {
  list-style: none; margin: 0; padding: 0;
  max-height: 280px; overflow-y: auto;
  display: flex; flex-direction: column; gap: 2px;
}
.mt-status-log-item {
  display: grid;
  grid-template-columns: 36px 1fr auto auto;
  align-items: center; gap: 10px;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 12.5px;
  font-variant-numeric: tabular-nums;
}
.mt-status-log-item.is-hit  { background: #ecfdf5; color: #047857; }
.mt-status-log-item.is-near { background: #e0e7ff; color: #3730a3; }
.mt-status-log-item.is-cat  { background: #fef3c7; color: #92400e; }
.mt-status-log-item.is-miss { background: #fafafb; color: #475569; }
.mt-status-log-item.is-fail { background: #fef2f2; color: #b91c1c; }
.mt-status-log-step { font-weight: 700; color: #94a3b8; font-size: 11.5px; }
.mt-status-log-text {
  min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  color: #0f172a;
}
.mt-status-log-ms { font-size: 11.5px; color: #94a3b8; }
.mt-status-log-state {
  font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
  padding: 2px 8px; border-radius: 9999px;
  background: rgba(15, 23, 42, 0.04);
}

.mt-post-strip {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
}
@media (max-width: 800px) {
  .mt-post-strip { grid-template-columns: 1fr; }
}
.mt-post-step {
  display: grid;
  grid-template-columns: 18px auto 1fr;
  align-items: center; gap: 10px;
  padding: 10px 14px;
  background: #fafafb;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 10px;
}
.mt-post-step.is-running { background: #eef2ff; border-color: #c7d2fe; }
.mt-post-step.is-complete { background: #f0fdf4; border-color: #bbf7d0; }
.mt-post-step.is-failed { background: #fef2f2; border-color: #fecaca; }
.mt-post-step.is-skipped { background: #f7f7f8; border-color: rgba(15, 23, 42, 0.10); opacity: 0.85; }
.mt-post-icon {
  width: 18px; height: 18px;
  display: inline-flex; align-items: center; justify-content: center;
  color: #475569;
}
.mt-post-step.is-complete .mt-post-icon { color: #047857; }
.mt-post-step.is-failed .mt-post-icon { color: #b91c1c; }
.mt-post-label { font-size: 13px; font-weight: 600; color: #0f172a; white-space: nowrap; }
.mt-post-sub { font-size: 12px; color: #64748b; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mt-spinner.is-dark {
  border-color: rgba(15, 23, 42, 0.20);
  border-top-color: #0f172a;
}

/* ── Synthesis & grounding cards */
.mt-synth, .mt-ground { padding: 28px 32px; }
.mt-md {
  color: #334155; font-size: 13.5px; line-height: 1.65;
  max-width: 70ch;  /* keep line length readable */
}
.mt-md h3 {
  font-size: 11px; font-weight: 700; letter-spacing: 0.10em;
  text-transform: uppercase; color: #94a3b8;
  margin: 22px 0 8px;
  padding-top: 14px;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
}
.mt-md h3:first-child { padding-top: 0; border-top: 0; margin-top: 0; }
.mt-md h4 { font-size: 14px; font-weight: 600; color: #0f172a; margin: 14px 0 6px; }
.mt-md h5 { font-size: 13px; font-weight: 600; color: #0f172a; margin: 12px 0 6px; }
.mt-md p { margin: 0 0 12px; }
.mt-md ul, .mt-md ol { margin: 0 0 14px; padding-left: 22px; }
.mt-md li { margin: 6px 0; padding-left: 4px; }
.mt-md li::marker { color: #94a3b8; }
.mt-md strong { color: #0f172a; font-weight: 600; }
.mt-md em { color: #475569; }
.mt-md code {
  background: #f1f5f9; color: #334155;
  padding: 1px 6px; border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, monospace; font-size: 12.5px;
}
.mt-md a { color: #0f172a; text-decoration: underline; text-underline-offset: 3px; text-decoration-color: rgba(15, 23, 42, 0.35); }
.mt-md a:hover { color: #000; text-decoration-color: #000; }
.mt-md a:visited { color: #475569; }

.mt-citations {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
}
.mt-citations-h {
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.10em;
  text-transform: uppercase; color: #94a3b8;
  margin-bottom: 8px;
}
.mt-citations ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.mt-citations li { font-size: 13px; }
.mt-citations a { color: #0f172a; text-decoration: underline; text-underline-offset: 3px; }
.mt-citations a:hover { color: #475569; }

.mt-runmode {
  display: flex; gap: 12px; align-items: flex-start;
  margin: -8px 0 20px;
  padding: 12px 16px;
  background: #fafafb;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 12px;
  font-size: 13px; color: #475569; line-height: 1.55;
}
.mt-runmode-tag {
  flex: none;
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.10em;
  text-transform: uppercase; color: #94a3b8;
  padding: 4px 10px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 9999px;
}
.mt-runmode-text strong { color: #0f172a; font-weight: 600; }
.mt-runmode-text em { color: #b91c1c; font-style: normal; font-weight: 600; }

.mt-error {
  margin: 0 0 20px;
  padding: 12px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  border-radius: 10px;
  font-size: 13px;
}

/* ── Live progress */
.mt-live { padding: 18px 24px; }
.mt-live-bar {
  height: 6px;
  background: #f1f5f9;
  border-radius: 9999px;
  overflow: hidden;
}
.mt-live-fill {
  height: 100%;
  background: #0f172a;
  transition: width .35s ease;
}
.mt-live-meta {
  display: flex; gap: 14px; align-items: center;
  margin-top: 10px;
}
.mt-live-pct { font-size: 13px; font-weight: 700; color: #0f172a; }
.mt-live-text { font-size: 12.5px; color: #64748b; }

/* ── Scorecards */
.mt-scorecards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  border-left: 1px solid rgba(15, 23, 42, 0.08);
}
.mt-scorecard {
  padding: 20px 22px;
  background: #fff;
  border-right: 1px solid rgba(15, 23, 42, 0.08);
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 0;
}
.mt-scorecard-head { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }
.mt-scorecard-name { font-size: 12.5px; font-weight: 500; color: #475569; letter-spacing: 0.01em; }
.mt-scorecard-big {
  font-size: 34px; font-weight: 500; color: #0f172a;
  letter-spacing: -0.025em; line-height: 1;
  font-variant-numeric: tabular-nums;
}
.mt-scorecard-cap {
  font-size: 10.5px; font-weight: 600; color: #94a3b8;
  text-transform: uppercase; letter-spacing: 0.08em;
  margin: 6px 0 18px;
}
.mt-scorecard-grid {
  display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px 14px;
  padding-top: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
}
.mt-mini-of { color: #94a3b8; font-weight: 400; font-size: 12px; }

.mt-mini-cap.mt-mini-hit  { color: #047857; }
.mt-mini-cap.mt-mini-near { color: #3730a3; }
.mt-mini-cap.mt-mini-cat  { color: #92400e; }

/* Stacked signal bar: green direct + indigo near + amber category,
   grey remainder = unrelated / no signal. */
.mt-sc-bar {
  display: flex;
  height: 6px;
  margin: 8px 0 14px;
  background: #f1f5f9;
  border-radius: 9999px;
  overflow: hidden;
}
.mt-sc-bar-seg.is-hit  { background: #047857; }
.mt-sc-bar-seg.is-near { background: #4f46e5; }
.mt-sc-bar-seg.is-cat  { background: #d97706; }
.mt-mini-num { font-size: 14px; font-weight: 600; color: #0f172a; }
.mt-mini-cap { font-size: 10.5px; color: #94a3b8; }

/* ── Per-prompt highlights (accordion table) */
.mt-pm-wrap { padding: 24px 0 0; }
.mt-pm-wrap .mt-card-head { padding: 0 28px; }
.mt-pm-scroll { overflow-x: auto; }
.mt-pm-tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 820px;
  table-layout: fixed;          /* prevents wide expanded rows from
                                   forcing the whole table to reflow */
}
.mt-pm-tbl thead th {
  text-align: left;
  font-size: 10.5px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.08em;
  color: #94a3b8;
  padding: 12px 12px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.10);
  background: #fff;
}
.mt-pm-h-caret { width: 28px; padding-left: 28px !important; }
.mt-pm-h-num { width: 36px; text-align: right !important; }
.mt-pm-h-prompt { min-width: 260px; }
.mt-pm-h-num-cell { width: 110px; text-align: right !important; }
.mt-pm-h-best { min-width: 180px; }

.mt-pm-row {
  cursor: pointer;
  transition: background .12s ease;
}
.mt-pm-row td {
  padding: 12px 12px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.04);
  vertical-align: middle;
}
.mt-pm-row:hover { background: #fafafb; }
.mt-pm-row.is-open { background: #fafafb; }
.mt-pm-row.is-miss td { color: #64748b; }
.mt-pm-row.is-open td { border-bottom-color: transparent; }

.mt-pm-caret { padding-left: 28px !important; color: #94a3b8; }
.mt-pm-caret svg { transition: transform .15s ease; display: block; }
.mt-pm-num-cell {
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: #0f172a;
  font-weight: 500;
}
.mt-pm-prompt-cell {
  color: #0f172a; line-height: 1.45;
  max-width: 0;  /* enables truncation */
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.mt-pm-best-cell { color: #0f172a; font-weight: 500; padding-right: 28px !important; }
.mt-pm-best-none { color: #94a3b8; font-weight: 400; }

.mt-pm-pill {
  display: inline-block;
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 3px 9px; border-radius: 9999px;
}
.mt-pm-pill.is-hit  { background: #ecfdf5; color: #047857; }
.mt-pm-pill.is-near { background: #e0e7ff; color: #3730a3; }
.mt-pm-pill.is-cat  { background: #fef3c7; color: #92400e; }
.mt-pm-pill.is-miss { background: #f1f5f9; color: #64748b; }

/* Expanded row. The outer table is `table-layout: fixed` so the
   `<td>` width is locked to the column widths above. The inner
   div is the actual scroll container — its overflow-x: auto keeps
   the wide per-model perf table from bleeding past the card. */
.mt-pm-detail-row td { padding: 0; border-bottom: 1px solid rgba(15, 23, 42, 0.06); }
.mt-pm-detail {
  background: #fafafb;
  padding: 0;
  min-width: 0;
}
.mt-pm-detail-inner {
  padding: 14px 28px 18px 56px;
  display: flex; flex-direction: column; gap: 12px;
  min-width: 0;
  max-width: 100%;
  overflow-x: auto;
}
.mt-pm-detail-inner .mt-pm-perf {
  table-layout: auto;
  max-width: 100%;
}
/* Per-model performance breakdown table inside the expansion. */
.mt-pm-perf {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  font-size: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
}
.mt-pm-perf thead th {
  text-align: left;
  padding: 8px 8px;
  font-size: 10px; font-weight: 700; letter-spacing: 0.05em;
  text-transform: uppercase; color: #94a3b8;
  background: #fff;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  white-space: nowrap;
}
.mt-pm-perf tbody td {
  padding: 8px 8px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.04);
  vertical-align: middle;
}
.mt-pm-perf tbody tr:last-child td { border-bottom: 0; }
.mt-pm-perf-row { cursor: pointer; transition: background .12s ease; }
.mt-pm-perf-row:hover { background: #fafafb; }
.mt-pm-perf-row.is-fail { background: #fef2f2; }
.mt-pm-perf-row.is-fail:hover { background: #fee2e2; }
.mt-pm-delta {
  font-size: 11.5px; font-weight: 600;
  color: #64748b;
  white-space: nowrap;
}
.mt-pm-delta .is-best { color: #047857; text-transform: uppercase; letter-spacing: 0.06em; font-size: 10.5px; }
.mt-pm-delta .is-pos { color: #64748b; }
.mt-pm-delta .is-neg { color: #b91c1c; text-transform: uppercase; letter-spacing: 0.06em; font-size: 10.5px; }

.mt-pm-of { color: #94a3b8; font-weight: 400; }

/* Sentiment pills */
.mt-pm-sent {
  display: inline-block;
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 2px 8px; border-radius: 9999px;
}
.mt-pm-sent.is-positive { background: #ecfdf5; color: #047857; }
.mt-pm-sent.is-neutral  { background: #f1f5f9; color: #475569; }
.mt-pm-sent.is-negative { background: #fef2f2; color: #b91c1c; }
.mt-pm-sent.is-non_recommendation { background: #fef3c7; color: #92400e; }

/* Relevance pills */
.mt-pm-rel {
  display: inline-block;
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 2px 8px; border-radius: 9999px;
}
.mt-pm-rel.is-direct         { background: #ecfdf5; color: #047857; }
.mt-pm-rel.is-near_miss      { background: #e0e7ff; color: #3730a3; }
.mt-pm-rel.is-category_match { background: #fef3c7; color: #92400e; }
.mt-pm-rel.is-unrelated      { background: #f1f5f9; color: #94a3b8; }

.mt-pm-softline {
  margin-top: 4px;
  display: flex; gap: 4px; justify-content: flex-end; flex-wrap: wrap;
}

/* Evidence-phrase row inside the per-model perf table */
.mt-pm-evidence-row td.mt-pm-evidence {
  padding: 8px 12px 12px 38px;
  background: #fafafb;
  border-top: 0;
  font-size: 12px;
  color: #475569;
}
.mt-pm-evidence-label {
  font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; color: #94a3b8;
  margin-right: 8px;
}
.mt-pm-evidence-quote {
  font-style: italic; color: #0f172a;
  border-left: 2px solid #3730a3;
  padding-left: 10px;
  display: inline-block;
}
.mt-pm-resp {
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 6px;
  padding: 12px 14px;
}
.mt-pm-resp.is-fail { background: #fef2f2; border-color: #fecaca; }
.mt-pm-resp.is-hit { border-left: 3px solid #047857; }
.mt-pm-resp-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.mt-pm-resp-name { font-size: 13px; font-weight: 600; color: #0f172a; }
.mt-pm-resp-ms { font-size: 11.5px; color: #94a3b8; font-variant-numeric: tabular-nums; margin-left: auto; }
.mt-pm-resp-body {
  margin-top: 8px;
  font-size: 12.5px; color: #334155; line-height: 1.55;
  white-space: normal;        /* render markdown blocks, not raw */
  word-break: break-word;
  overflow-wrap: anywhere;
  min-width: 0;
}
.mt-pm-resp-body p { margin: 0 0 8px; }
.mt-pm-resp-body p:last-child { margin-bottom: 0; }
.mt-pm-resp-body ul, .mt-pm-resp-body ol { margin: 6px 0 8px; padding-left: 20px; }
.mt-pm-resp-body li { margin: 3px 0; }
.mt-pm-resp-body h3, .mt-pm-resp-body h4, .mt-pm-resp-body h5 {
  font-size: 12.5px; font-weight: 700; color: #0f172a;
  margin: 10px 0 4px;
}
.mt-pm-resp-body strong { color: #0f172a; font-weight: 600; }
.mt-pm-resp-body code {
  background: #f1f5f9; padding: 0 5px; border-radius: 3px;
  font-family: ui-monospace, SFMono-Regular, monospace; font-size: 12px;
}
.mt-pm-resp-err { margin-top: 6px; font-size: 12px; color: #b91c1c; }

/* ── Pivot table */
.mt-pivot-wrap { padding: 24px 0 12px; }
.mt-pivot-wrap .mt-card-head { padding: 0 28px; }
.mt-pivot-scroll { overflow-x: auto; padding: 0 28px; }
.mt-pivot {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 720px;
}
.mt-pivot thead th {
  text-align: left;
  font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.08em;
  color: #94a3b8;
  padding: 12px 12px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.10);
  background: #fff; position: sticky; top: 0;
}
.mt-pivot-num-h { width: 36px; }
.mt-pivot-prompt-h { min-width: 240px; }
.mt-pivot-prov-h { min-width: 160px; }
.mt-pivot-agg-h { width: 110px; }
.mt-pivot tbody td {
  padding: 12px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.04);
  vertical-align: top;
}
.mt-pivot-num { color: #94a3b8; font-weight: 600; }
.mt-pivot-prompt { color: #0f172a; line-height: 1.5; }
.mt-pivot-cell {
  cursor: pointer;
  border-radius: 8px;
  transition: background .12s ease;
}
.mt-pivot-cell:hover { background: #fafafb; }
.mt-pivot-cell-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.mt-pivot-ms { font-size: 11.5px; color: #94a3b8; font-variant-numeric: tabular-nums; }
.mt-pivot-pill {
  display: inline-block;
  font-size: 11px; font-weight: 700; letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 3px 9px; border-radius: 9999px;
}
.mt-pivot-pill.is-hit,   .mt-pivot-cell.is-hit   .mt-pivot-pill { background: #ecfdf5; color: #047857; }
.mt-pivot-pill.is-near,  .mt-pivot-cell.is-near  .mt-pivot-pill { background: #e0e7ff; color: #3730a3; }
.mt-pivot-pill.is-cat,   .mt-pivot-cell.is-cat   .mt-pivot-pill { background: #fef3c7; color: #92400e; }
.mt-pivot-pill.is-miss,  .mt-pivot-cell.is-miss  .mt-pivot-pill { background: #f1f5f9; color: #64748b; }
.mt-pivot-pill.is-fail,  .mt-pivot-cell.is-fail  .mt-pivot-pill { background: #fef2f2; color: #b91c1c; }
.mt-pivot-pill.is-pending, .mt-pivot-cell.is-pending .mt-pivot-pill {
  background: #fef3c7; color: #92400e;
}
.mt-pivot-body {
  margin-top: 10px;
  padding: 10px 12px;
  background: #fafafb;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 8px;
  font-size: 12.5px; color: #334155; line-height: 1.5;
  white-space: normal;
  word-break: break-word;
  overflow-wrap: anywhere;
  cursor: text;
}
.mt-pivot-body p { margin: 0 0 8px; }
.mt-pivot-body p:last-child { margin-bottom: 0; }
.mt-pivot-body ul, .mt-pivot-body ol { margin: 6px 0 8px; padding-left: 18px; }
.mt-mark { background: #fef08a; padding: 0 2px; border-radius: 3px; color: #0f172a; font-weight: 600; }
.mt-ent {
  border-bottom: 1px dashed rgba(15, 23, 42, 0.30);
  cursor: help;
}
.mt-ent:hover { background: #f1f5f9; }

.mt-pivot-agg { text-align: center; }
.mt-agg-pill {
  display: inline-block;
  font-size: 12px; font-weight: 700;
  padding: 4px 10px; border-radius: 9999px;
  background: #f1f5f9; color: #475569;
  font-variant-numeric: tabular-nums;
}
.mt-agg-pill.is-all { background: #ecfdf5; color: #047857; }
.mt-agg-pill.is-some { background: #fef3c7; color: #92400e; }
.mt-agg-pill.is-none { background: #fef2f2; color: #b91c1c; }

/* ── Difference matrices */
.mt-matrix-pair {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 24px;
}
.mt-matrix-block { min-width: 0; }
.mt-matrix-h {
  font-size: 12px; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; color: #64748b;
  margin-bottom: 10px;
}
.mt-matrix {
  width: 100%;
  border-collapse: separate;
  border-spacing: 4px;
  font-size: 12.5px;
}
.mt-matrix thead th, .mt-matrix tbody th {
  font-weight: 600; color: #0f172a;
  padding: 8px;
  text-align: center;
  background: transparent;
}
.mt-matrix tbody th { text-align: right; padding-right: 12px; }
.mt-matrix-cell {
  padding: 14px 12px;
  text-align: center;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  border-radius: 8px;
  background: #f7f7f8;
  color: #0f172a;
}
.mt-matrix-cell.is-self { background: transparent; color: #cbd5e1; font-weight: 400; }
/* Disagreement heatmap — monochrome density (darker = more disagreement). */
.mt-matrix-cell.is-zero { background: #fafafb; color: #94a3b8; }
.mt-matrix-cell.is-cool { background: #e2e8f0; color: #475569; }
.mt-matrix-cell.is-warm { background: #94a3b8; color: #fff; }
.mt-matrix-cell.is-hot  { background: #0f172a; color: #fff; }
/* Delta heatmap — neutral surface, sign carried by ▲ / ▼ glyph weight. */
.mt-matrix-cell.is-pos     { background: #f1f5f9; color: #0f172a; }
.mt-matrix-cell.is-pos-hot { background: #0f172a; color: #fff; }
.mt-matrix-cell.is-neg     { background: #f1f5f9; color: #64748b; }
.mt-matrix-cell.is-neg-hot { background: #e2e8f0; color: #0f172a; }
</style>
