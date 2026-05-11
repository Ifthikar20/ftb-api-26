<template>
  <div class="mt-page fade-in">
    <!-- ── Hero ──────────────────────────────────────────────────── -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Model Test</h1>
        <p class="page-subtitle">
          Pick an environment, edit the prompts, choose the models, and run.
          See whether <strong>{{ brandLabel }}</strong> surfaces — and compare
          how each model performs side by side.
        </p>
      </div>
    </div>

    <!-- ── 1. Environment picker ─────────────────────────────────── -->
    <section class="mt-card">
      <div class="mt-card-head">
        <div>
          <div class="mt-card-eyebrow">Step 1</div>
          <h2 class="mt-card-h">Choose an environment</h2>
          <p class="mt-card-sub">
            An environment is a saved bundle of prompts you can re-run on a
            schedule. Edits below are saved back to the environment.
          </p>
        </div>
        <button class="mt-btn-soft" @click="promptCreateEnv">+ New environment</button>
      </div>

      <div class="mt-env-grid">
        <label class="mt-env-tile" :class="{ 'is-on': !selectedEnvId }">
          <input type="radio" :checked="!selectedEnvId" @change="clearActiveEnv" />
          <div class="mt-env-tile-body">
            <div class="mt-env-tile-name">Ad-hoc run</div>
            <div class="mt-env-tile-sub">No environment — prompts won't be saved.</div>
          </div>
        </label>
        <label
          v-for="env in envs"
          :key="env.id"
          class="mt-env-tile"
          :class="{ 'is-on': selectedEnvId === env.id }"
        >
          <input
            type="radio"
            :checked="selectedEnvId === env.id"
            @change="applyEnvSelection(env)"
          />
          <div class="mt-env-tile-body">
            <div class="mt-env-tile-name">
              {{ env.name }}
              <span class="mt-env-tile-count">{{ env.prompt_count ?? (env.prompt_ids || []).length }}</span>
            </div>
            <div class="mt-env-tile-sub">
              {{ (env.prompt_count ?? (env.prompt_ids || []).length) }} prompts ·
              tap to load
            </div>
          </div>
        </label>
        <div v-if="loadingEnvs" class="mt-muted mt-env-loading">Loading environments…</div>
      </div>

      <div v-if="activeEnv" class="mt-env-toolbar">
        <button class="mt-link" @click="renameActiveEnv">Rename</button>
        <span class="mt-dot-sep"></span>
        <button class="mt-link is-danger" @click="deleteActiveEnv">Delete environment</button>
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
    <section class="mt-card">
      <div class="mt-card-head">
        <div>
          <div class="mt-card-eyebrow">Step 3</div>
          <h2 class="mt-card-h">Choose models to compare</h2>
          <p class="mt-card-sub">
            Pick one or more variants from each provider — e.g. Sonnet 4
            vs Sonnet 4.5. Each variant becomes its own column in the
            results. Providers without an API key are greyed out.
          </p>
        </div>
        <div class="mt-card-head-actions">
          <span class="mt-pickcount">
            {{ selectedVariantIds.length }} selected
          </span>
        </div>
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

    <div v-if="errorMsg" class="mt-error">{{ errorMsg }}</div>

    <!-- live progress -->
    <section v-if="running && liveRun" class="mt-card mt-live">
      <div class="mt-live-bar">
        <div class="mt-live-fill" :style="{ width: livePct + '%' }"></div>
      </div>
      <div class="mt-live-meta">
        <span class="mt-live-pct">{{ livePct }}%</span>
        <span class="mt-live-text">{{ liveCurrentLabel || 'Queueing on worker…' }}</span>
      </div>
    </section>

    <!-- ── 5. Results ───────────────────────────────────────────── -->
    <template v-if="displayRun && (displayRun.prompt_rows?.length || displayRun.summary)">
      <!-- 5a. Per-model scorecards -->
      <section class="mt-card">
        <div class="mt-card-head">
          <div>
            <div class="mt-card-eyebrow">Results</div>
            <h2 class="mt-card-h">How each model performed</h2>
            <p class="mt-card-sub">
              Discovery rate is the % of prompts where the brand appeared in
              that model's answer. Latency is the median over completed calls.
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
            <div class="mt-scorecard-big">{{ m.discovery_rate }}%</div>
            <div class="mt-scorecard-cap">discovery</div>
            <div class="mt-scorecard-grid">
              <div>
                <div class="mt-mini-num">{{ m.hits }}/{{ m.attempts }}</div>
                <div class="mt-mini-cap">hits</div>
              </div>
              <div>
                <div class="mt-mini-num">{{ m.median_ms }} ms</div>
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

      <!-- 5b. Pivot comparison table -->
      <section class="mt-card mt-pivot-wrap">
        <div class="mt-card-head">
          <div>
            <h2 class="mt-card-h">Prompt-by-prompt comparison</h2>
            <p class="mt-card-sub">
              Each row is a prompt; each column is a model. Click a cell to
              read the full response. The agreement column shows how many
              models mentioned the brand for that prompt.
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
                    <span v-html="highlightBrand(cellText(row, prov))"></span>
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

      <!-- 5c. Difference matrices -->
      <section v-if="resultsProviders.length >= 2" class="mt-card">
        <div class="mt-card-head">
          <div>
            <h2 class="mt-card-h">Model-vs-model differences</h2>
            <p class="mt-card-sub">
              <strong>Disagreement</strong>: percentage of prompts where the
              row model and column model gave opposite verdicts on whether
              your brand was mentioned.
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
                    {{ providerLabel(prov) }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="rowProv in resultsProviders" :key="rowProv">
                  <th>{{ providerLabel(rowProv) }}</th>
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
                    {{ providerLabel(prov) }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="rowProv in resultsProviders" :key="rowProv">
                  <th>{{ providerLabel(rowProv) }}</th>
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
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useToast } from '@/composables/useToast'
import llmRanking from '@/api/llm_ranking'
import promptLibrary from '@/api/promptLibrary'

const route = useRoute()
const appStore = useAppStore()
const toast = useToast()
const websiteId = route.params.websiteId

const brandLabel = computed(() => {
  const w = appStore.activeWebsite
  return (w?.business_name || w?.name || 'your brand').trim()
})

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

// ── Results helpers ──────────────────────────────────────────────
const displayRun = computed(() => lastRun.value || liveRun.value)

const resultsProviders = computed(() => {
  const fromState = displayRun.value?.providers
  if (Array.isArray(fromState) && fromState.length) return fromState
  return selectedVariantIds.value
})

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
function cellClass(row, prov) {
  const r = cellResponse(row, prov)
  if (!r) return 'is-pending'
  if (!r.succeeded) return 'is-fail'
  return r.brand_mentioned ? 'is-hit' : 'is-miss'
}
function cellLabel(row, prov) {
  const r = cellResponse(row, prov)
  if (!r) return 'pending'
  if (!r.succeeded) return 'failed'
  return r.brand_mentioned ? 'mentioned' : 'no mention'
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

// Per-model aggregate stats for the scorecards.
const perModelStats = computed(() => {
  const rows = displayRun.value?.prompt_rows || []
  const provs = resultsProviders.value
  return provs.map((prov) => {
    const cells = rows.map((row) => cellResponse(row, prov)).filter(Boolean)
    const attempts = cells.length
    const hits = cells.filter((c) => c.brand_mentioned).length
    const failures = cells.filter((c) => !c.succeeded).length
    const successes = cells.filter((c) => c.succeeded)
    const lat = successes
      .map((c) => Math.round(c.duration_ms || 0))
      .filter((x) => x > 0)
      .sort((a, b) => a - b)
    const median_ms = lat.length
      ? lat[Math.floor(lat.length / 2)]
      : 0
    // "Solo finds" = prompts where ONLY this model found the brand
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
    return { provider: prov, attempts, hits, failures, median_ms, unique_finds, discovery_rate }
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
  document.addEventListener('click', _closeDropdownOnDocClick)
})
onBeforeUnmount(() => document.removeEventListener('click', _closeDropdownOnDocClick))
</script>

<style scoped>
.mt-page { color: var(--text-primary, #0f172a); }
.mt-page .page-subtitle strong { color: var(--text-primary, #0f172a); font-weight: 600; }

/* ── Card surface (Airbnb-style: white, soft shadow, generous radius) */
.mt-card {
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 16px;
  padding: 24px 28px;
  margin-bottom: 20px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.mt-card-head {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 16px; margin-bottom: 18px;
}
.mt-card-head-actions { display: flex; gap: 8px; align-items: center; }
.mt-card-eyebrow {
  font-size: 11px; font-weight: 700; letter-spacing: 0.10em;
  text-transform: uppercase; color: #ff385c;
  margin-bottom: 4px;
}
.mt-card-h {
  font-size: 22px; font-weight: 600; color: #0f172a; margin: 0 0 4px;
  letter-spacing: -0.01em;
}
.mt-card-sub {
  font-size: 14px; color: #64748b; margin: 0; line-height: 1.55;
}
.mt-counter {
  display: inline-block; margin-left: 10px;
  font-size: 12px; font-weight: 600; color: #94a3b8;
}

/* ── Buttons / links */
.mt-btn-primary, .mt-btn-soft, .mt-btn-run {
  font: inherit; cursor: pointer; border-radius: 10px;
  padding: 10px 16px; font-weight: 600; font-size: 14px;
  border: 1px solid transparent;
  transition: transform .05s ease, background .15s ease, border-color .15s ease;
}
.mt-btn-primary { background: #ff385c; color: #fff; }
.mt-btn-primary:hover:not(:disabled) { background: #e31c5f; }
.mt-btn-primary:disabled { background: #f1f5f9; color: #94a3b8; cursor: not-allowed; }
.mt-btn-soft { background: #f7f7f8; color: #0f172a; border-color: rgba(15, 23, 42, 0.08); }
.mt-btn-soft:hover { background: #efeff1; }
.mt-btn-run {
  background: #0f172a; color: #fff; padding: 14px 28px; font-size: 15px;
  border-radius: 12px; min-width: 180px;
}
.mt-btn-run:hover:not(:disabled) { background: #1e293b; }
.mt-btn-run:disabled { background: #e2e8f0; color: #94a3b8; cursor: not-allowed; }

.mt-link {
  background: none; border: 0; padding: 0; cursor: pointer;
  color: #0f172a; font: inherit; font-size: 13px; font-weight: 500;
  text-decoration: underline; text-underline-offset: 3px;
}
.mt-link:hover { color: #ff385c; }
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

/* ── Env tiles */
.mt-env-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
.mt-env-tile {
  position: relative;
  display: flex; gap: 12px;
  padding: 16px 18px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 12px;
  cursor: pointer;
  transition: border-color .15s ease, box-shadow .15s ease;
}
.mt-env-tile input { position: absolute; opacity: 0; pointer-events: none; }
.mt-env-tile:hover { border-color: #0f172a; }
.mt-env-tile.is-on {
  border-color: #0f172a; border-width: 2px; padding: 15px 17px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}
.mt-env-tile-body { display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 1; }
.mt-env-tile-name {
  font-size: 15px; font-weight: 600; color: #0f172a;
  display: flex; align-items: center; gap: 8px;
}
.mt-env-tile-count {
  font-size: 11px; font-weight: 600;
  padding: 2px 8px;
  background: #f1f5f9; color: #475569;
  border-radius: 9999px;
}
.mt-env-tile-sub { font-size: 12.5px; color: #64748b; }
.mt-env-loading { grid-column: 1 / -1; }

.mt-env-toolbar {
  display: flex; align-items: center;
  margin-top: 16px; padding-top: 16px;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
}

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
.mt-prompt-text:hover { color: #ff385c; }
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
.mt-prompt-edit:focus { outline: none; border-color: #ff385c; box-shadow: 0 0 0 3px rgba(255, 56, 92, 0.12); }
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
.mt-pickcount {
  font-size: 12px; font-weight: 600; color: #94a3b8;
  padding: 4px 10px;
  background: #f1f5f9; border-radius: 9999px;
}
.mt-providers { display: flex; flex-direction: column; gap: 10px; }
.mt-provider-row {
  display: grid;
  grid-template-columns: 200px 1fr;
  align-items: center; gap: 16px;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
}
.mt-provider-row.is-off { background: #f7f7f8; }
.mt-provider-side { display: flex; align-items: center; gap: 10px; }
.mt-provider-name { font-size: 14.5px; font-weight: 600; color: #0f172a; }

.mt-variant-dd { position: relative; min-width: 0; }
.mt-variant-btn {
  width: 100%;
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 10px;
  font: inherit; font-size: 13px; color: #0f172a;
  cursor: pointer;
  text-align: left;
  transition: border-color .15s ease;
}
.mt-variant-btn:hover:not(:disabled) { border-color: #0f172a; }
.mt-variant-btn:disabled { background: #f1f5f9; color: #94a3b8; cursor: not-allowed; }
.mt-variant-btn-empty { color: #94a3b8; flex: 1; }
.mt-variant-btn-list { flex: 1; display: flex; flex-wrap: wrap; gap: 6px; }
.mt-variant-caret { color: #94a3b8; flex: none; }

.mt-variant-pill {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600;
  padding: 3px 10px;
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
.mt-model-dot.is-claude { background: #d97706; }
.mt-model-dot.is-gpt4 { background: #10a37f; }
.mt-model-dot.is-gemini { background: #4285f4; }
.mt-model-dot.is-perplexity { background: #6366f1; }
.mt-model-name { font-weight: 600; }
.mt-model-soon { font-size: 11px; color: #94a3b8; font-weight: 500; }

/* ── Run bar */
.mt-run-card {
  display: flex; align-items: center; justify-content: space-between;
  gap: 24px;
}
.mt-run-info { display: flex; align-items: center; gap: 16px; }
.mt-run-num {
  font-size: 36px; font-weight: 700; color: #0f172a;
  letter-spacing: -0.02em; line-height: 1;
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
  background: linear-gradient(90deg, #ff385c, #ff6b35);
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
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}
.mt-scorecard {
  padding: 18px 20px;
  background: #fafafb;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 14px;
}
.mt-scorecard-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.mt-scorecard-name { font-size: 13.5px; font-weight: 600; color: #0f172a; }
.mt-scorecard-big {
  font-size: 32px; font-weight: 700; color: #0f172a;
  letter-spacing: -0.02em; line-height: 1.05;
}
.mt-scorecard-cap {
  font-size: 11.5px; font-weight: 600; color: #94a3b8;
  text-transform: uppercase; letter-spacing: 0.06em;
  margin-bottom: 14px;
}
.mt-scorecard-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
  padding-top: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
}
.mt-mini-num { font-size: 14px; font-weight: 600; color: #0f172a; }
.mt-mini-cap { font-size: 10.5px; color: #94a3b8; }

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
.mt-pivot-pill.is-hit, .mt-pivot-cell.is-hit .mt-pivot-pill { background: #ecfdf5; color: #047857; }
.mt-pivot-pill.is-miss, .mt-pivot-cell.is-miss .mt-pivot-pill { background: #f1f5f9; color: #64748b; }
.mt-pivot-pill.is-fail, .mt-pivot-cell.is-fail .mt-pivot-pill { background: #fef2f2; color: #b91c1c; }
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
  white-space: pre-wrap;
  cursor: text;
}
.mt-mark { background: #fef08a; padding: 0 2px; border-radius: 3px; color: #0f172a; }

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
/* Disagreement heatmap (red scale) */
.mt-matrix-cell.is-zero { background: #f0fdf4; color: #047857; }
.mt-matrix-cell.is-cool { background: #fef9c3; color: #854d0e; }
.mt-matrix-cell.is-warm { background: #fed7aa; color: #9a3412; }
.mt-matrix-cell.is-hot  { background: #fecaca; color: #991b1b; }
/* Delta heatmap (diverging) */
.mt-matrix-cell.is-pos     { background: #d1fae5; color: #047857; }
.mt-matrix-cell.is-pos-hot { background: #6ee7b7; color: #064e3b; }
.mt-matrix-cell.is-neg     { background: #fed7d7; color: #9b2c2c; }
.mt-matrix-cell.is-neg-hot { background: #fc8181; color: #7c2d12; }
</style>
