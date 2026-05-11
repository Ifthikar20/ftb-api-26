<template>
  <div class="mt-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Model Test</h1>
        <p class="page-subtitle">
          Bundle a set of prompts into a <strong>test environment</strong>, then run
          a timed audit to see whether <strong>{{ brandLabel }}</strong> surfaces in
          each model's answer.
        </p>
      </div>
    </div>

    <!-- ── Env header (top-level campaign bar) ─────────────────────── -->
    <section class="mt-env-bar" :class="{ 'is-empty': !activeEnv }">
      <div class="mt-env-bar-left">
        <span class="mt-env-eyebrow">Test environment</span>
        <div class="mt-env-bar-row">
          <div class="mt-env-picker" @click.stop="envMenuOpen = !envMenuOpen">
            <span class="mt-env-pick-name">
              {{ activeEnv ? activeEnv.name : 'No environment selected' }}
            </span>
            <span v-if="activeEnv" class="mt-env-pick-count">
              {{ activeEnvPromptCount }} prompts
            </span>
            <svg class="mt-env-caret" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 4l3 4 3-4" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <div v-if="envMenuOpen" class="mt-env-menu" @click.stop>
              <div class="mt-env-menu-h">Switch environment</div>
              <button v-if="activeEnv" class="mt-env-menu-item is-clear" @click="clearActiveEnv">
                <span>Run without an environment</span>
              </button>
              <button
                v-for="env in envs"
                :key="env.id"
                class="mt-env-menu-item"
                :class="{ 'is-current': selectedEnvId === env.id }"
                @click="applyEnvSelection(env)"
              >
                <span>{{ env.name }}</span>
                <span class="mt-env-menu-count">{{ env.prompt_count || (env.prompt_ids || []).length }}</span>
              </button>
              <div v-if="!envs.length" class="mt-env-menu-empty">No envs yet</div>
              <div class="mt-env-menu-divider"></div>
              <button class="mt-env-menu-item is-primary" @click="promptCreateEnv">+ New environment</button>
            </div>
          </div>
          <div v-if="activeEnv" class="mt-env-bar-actions">
            <button class="mt-env-bar-tool" @click="renameActiveEnv">Rename</button>
            <button class="mt-env-bar-tool is-danger" @click="deleteActiveEnv">Delete</button>
          </div>
        </div>
        <p v-if="!activeEnv" class="mt-env-hint">
          Pick an environment to load its bundled prompts, or
          <button class="mt-env-link" @click="promptCreateEnv">create a new one</button>
          to start a fresh campaign. You can also run ad-hoc without saving.
        </p>
        <p v-else class="mt-env-hint">
          This is your campaign bundle. Add prompts from your library, type new ones,
          or upload a markdown file — every addition is saved to <strong>{{ activeEnv.name }}</strong>.
        </p>
      </div>
    </section>

    <!-- Step 1: prompts -->
    <section class="mt-section">
      <div class="mt-step-head">
        <span class="mt-step-num">1</span>
        <div>
          <div class="mt-step-h">Pick prompts</div>
          <div class="mt-step-sub">{{ promptCount }} selected · max 25</div>
        </div>
      </div>

      <div class="mt-tabs">
        <button
          v-for="t in promptTabs"
          :key="t.value"
          type="button"
          class="mt-tab"
          :class="{ 'is-active': promptTab === t.value }"
          @click="promptTab = t.value"
        >{{ t.label }}</button>
      </div>

      <div v-if="promptTab === 'saved'" class="mt-saved">
        <div v-if="loadingSaved" class="mt-muted">Loading saved prompts…</div>
        <div v-else-if="!savedPrompts.length" class="mt-empty">
          No saved prompts yet. Save some from the Prompt Library, or use Custom / Upload.
        </div>
        <ul v-else class="mt-saved-list">
          <li
            v-for="p in savedPrompts"
            :key="p.id"
            class="mt-saved-item"
            :class="{ 'is-on': selectedSavedIds.has(p.id) }"
            @click="toggleSaved(p)"
          >
            <span class="mt-check">
              <svg v-if="selectedSavedIds.has(p.id)" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 6l3 3 5-6" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </span>
            <span class="mt-saved-text">{{ p.text }}</span>
            <span v-if="p.style" class="mt-saved-tag">{{ p.style }}</span>
          </li>
        </ul>
      </div>

      <div v-else-if="promptTab === 'custom'" class="mt-custom">
        <textarea
          v-model="customDraft"
          class="mt-textarea"
          rows="4"
          placeholder="Type a prompt and press Add. One per add."
        />
        <button class="mt-btn-secondary" :disabled="!customDraft.trim()" @click="addCustom">
          Add prompt
        </button>
      </div>

      <div v-else class="mt-upload">
        <label class="mt-drop">
          <input
            ref="mdInput"
            type="file"
            accept=".md,.txt,text/markdown,text/plain"
            multiple
            @change="onMarkdownUpload"
          />
          <div class="mt-drop-inner">
            <div class="mt-drop-h">Drop .md or .txt files</div>
            <div class="mt-drop-sub">
              Each non-empty line (or paragraph) becomes one prompt. Headings and
              <code>&gt;</code>/<code>-</code>/<code>*</code> bullets are stripped.
            </div>
          </div>
        </label>
      </div>

      <!-- Selected pool (always visible) -->
      <div v-if="selectedPrompts.length" class="mt-pool">
        <div class="mt-pool-head">
          <span>{{ selectedPrompts.length }} prompt{{ selectedPrompts.length === 1 ? '' : 's' }} ready</span>
          <div class="mt-pool-actions">
            <button v-if="canSaveAsEnv" class="mt-pool-save" @click="saveSelectionAsEnv">
              Save as environment
            </button>
            <button class="mt-pool-clear" @click="clearAll">Clear all</button>
          </div>
        </div>
        <ul class="mt-pool-list">
          <li v-for="(p, i) in selectedPrompts" :key="p.uid" class="mt-pool-item">
            <span class="mt-pool-num">{{ i + 1 }}</span>
            <span class="mt-pool-text">{{ p.text }}</span>
            <button class="mt-pool-remove" @click="removeSelected(p.uid)">×</button>
          </li>
        </ul>
      </div>
    </section>

    <!-- Step 2: models -->
    <section class="mt-section">
      <div class="mt-step-head">
        <span class="mt-step-num">2</span>
        <div>
          <div class="mt-step-h">Pick models</div>
          <div class="mt-step-sub">{{ enabledProviderCount }} of {{ providerOptions.length }} available</div>
        </div>
      </div>

      <div class="mt-models">
        <label
          v-for="opt in providerOptions"
          :key="opt.key"
          class="mt-model"
          :class="{ 'is-on': selectedProviders.includes(opt.key), 'is-off': !opt.available }"
        >
          <input
            type="checkbox"
            :value="opt.key"
            :checked="selectedProviders.includes(opt.key)"
            :disabled="!opt.available"
            @change="toggleProvider(opt.key)"
          />
          <div class="mt-model-body">
            <div class="mt-model-head">
              <span class="mt-model-dot" :class="'is-' + opt.key"></span>
              <span class="mt-model-name">{{ opt.label }}</span>
              <span v-if="!opt.available" class="mt-model-soon">needs API key</span>
            </div>
            <div class="mt-model-sub">{{ opt.tag }}</div>
          </div>
        </label>
      </div>
    </section>

    <!-- Step 3: run -->
    <section class="mt-section mt-run">
      <div class="mt-run-summary">
        <div>
          <div class="mt-run-num">{{ totalQueries }}</div>
          <div class="mt-run-label">total queries · {{ promptCount }} × {{ selectedProviders.length || 0 }} models</div>
        </div>
        <button
          class="mt-btn-run"
          :disabled="!canRun || running"
          @click="runProbe"
        >
          <span v-if="running">
            <span class="mt-spinner"></span>
            Probing… ({{ liveCompleted }}/{{ liveTotal }})
          </span>
          <span v-else>Build &amp; run audit</span>
        </button>
      </div>
      <div v-if="errorMsg" class="mt-error">{{ errorMsg }}</div>

      <!-- Live progress strip — visible while the background job runs -->
      <div v-if="running && liveRun" class="mt-live">
        <div class="mt-live-bar">
          <div class="mt-live-fill" :style="{ width: livePct + '%' }"></div>
        </div>
        <div class="mt-live-meta">
          <span class="mt-live-pct">{{ livePct }}%</span>
          <span class="mt-live-text">{{ liveCurrentLabel || 'Queueing on worker…' }}</span>
        </div>
      </div>
    </section>

    <!-- Results — show streaming as they arrive, then full set on complete -->
    <section v-if="lastRun || (liveRun && liveRun.prompt_rows && liveRun.prompt_rows.length)" class="mt-results">
      <div class="mt-results-head">
        <h2 class="mt-results-h">{{ lastRun ? 'Results' : 'Results — streaming' }}</h2>
        <div class="mt-results-meta">
          <span v-if="displayRun?.summary" class="mt-discovery">
            <strong>{{ displayRun.summary.discovery_rate }}%</strong>
            discovery
            <em>({{ displayRun.summary.prompts_with_hit }} of {{ displayRun.summary.prompts }} prompts found {{ brandLabel }})</em>
          </span>
          <span v-else class="mt-discovery">
            <em>{{ (displayRun?.prompt_rows?.length || 0) }} of {{ displayRun?.prompts?.length || 0 }} prompts done</em>
          </span>
        </div>
      </div>

      <div v-for="(row, idx) in displayRun.prompt_rows" :key="idx" class="mt-result-card">
        <div class="mt-result-prompt">
          <span class="mt-result-num">#{{ idx + 1 }}</span>
          <span class="mt-result-text">{{ row.prompt }}</span>
          <span class="mt-result-pill" :class="rowHitClass(row)">
            {{ rowHitLabel(row) }}
          </span>
        </div>
        <div v-for="r in row.responses" :key="r.provider" class="mt-resp">
          <div class="mt-resp-head">
            <span class="mt-resp-dot" :class="'is-' + r.provider"></span>
            <span class="mt-resp-name">{{ providerLabel(r.provider) }}</span>
            <span v-if="r.brand_mentioned" class="mt-resp-badge is-hit">brand found</span>
            <span v-else-if="r.succeeded" class="mt-resp-badge is-miss">not found</span>
            <span v-else class="mt-resp-badge is-fail">{{ r.error || 'failed' }}</span>
            <span v-if="r.duration_ms" class="mt-resp-time">{{ Math.round(r.duration_ms) }} ms</span>
          </div>
          <div v-if="r.response_text" class="mt-resp-body">
            <span v-html="highlightBrand(r.response_text)"></span>
          </div>
          <div v-else-if="!r.succeeded && r.error" class="mt-resp-empty">{{ r.error }}</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
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

// ── Step 1: prompts ──────────────────────────────────────────────
const promptTabs = [
  { value: 'saved',  label: 'From saved' },
  { value: 'custom', label: 'Custom' },
  { value: 'upload', label: 'Upload .md' },
]
const promptTab = ref('saved')

const savedPrompts = ref([])     // [{ id (brand_prompt_id), text, style }]
const loadingSaved = ref(true)
const selectedSavedIds = ref(new Set())
const selectedPrompts = ref([])  // {uid, text, source, savedId?}
let _uid = 0
const nextUid = () => ++_uid

// Test environments
const envs = ref([])
const loadingEnvs = ref(false)
const selectedEnvId = ref(null)
const envMenuOpen = ref(false)

const activeEnv = computed(() =>
  envs.value.find((e) => e.id === selectedEnvId.value) || null,
)
const activeEnvPromptCount = computed(() => {
  const e = activeEnv.value
  if (!e) return 0
  return e.prompt_count ?? (e.prompt_ids || []).length
})

// Patch a single env row in-place after the backend returns the
// updated payload from add/remove/rename. Keeps every consumer (the
// menu, the pool count, the bar) in sync from one source of truth.
function _patchEnv(updated) {
  if (!updated || !updated.id) return
  envs.value = envs.value.map((e) => e.id === updated.id ? { ...e, ...updated } : e)
}

function clearActiveEnv() {
  envMenuOpen.value = false
  selectedEnvId.value = null
  selectedSavedIds.value = new Set()
  selectedPrompts.value = []
}

async function promptCreateEnv() {
  envMenuOpen.value = false
  const name = window.prompt('Name this environment:', `Env ${envs.value.length + 1}`)
  if (!name || !name.trim()) return
  try {
    const { data } = await promptLibrary.createTestEnvironment(websiteId, name.trim(), [])
    const env = data?.data || data
    envs.value = [env, ...envs.value]
    selectedEnvId.value = env.id
    selectedSavedIds.value = new Set()
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
  loadingSaved.value = true
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
  } finally {
    loadingSaved.value = false
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

// Replace the current selection with whatever is in `env`. Treats the
// env's prompt_ids as authoritative; anything not loaded into
// savedPrompts is silently skipped (e.g. if the user deleted the
// underlying BrandPrompt after creating the env).
function applyEnvSelection(env) {
  if (!env) return
  selectedEnvId.value = env.id
  const ids = new Set(env.prompt_ids || [])
  const matched = savedPrompts.value.filter((p) => ids.has(p.id))
  selectedSavedIds.value = new Set(matched.map((p) => p.id))
  selectedPrompts.value = matched.map((p) => ({
    uid: nextUid(), text: p.text, source: 'env', savedId: p.id,
  }))
  if (matched.length === 0) {
    toast.info('This environment has no saved prompts.')
  }
}

// Preselect prompts from a `?prompts=<csv>` query — set by the Saved
// page's 'Run as Model Test' bulk action.
function applyQueryPreselect() {
  const raw = (route.query.prompts || '').toString().trim()
  if (!raw) return
  const ids = new Set(raw.split(',').filter(Boolean))
  if (!ids.size) return
  const matched = savedPrompts.value.filter((p) => ids.has(p.id))
  if (!matched.length) return
  selectedSavedIds.value = new Set(matched.map((p) => p.id))
  selectedPrompts.value = matched.map((p) => ({
    uid: nextUid(), text: p.text, source: 'env', savedId: p.id,
  }))
  if (route.query.env) selectedEnvId.value = route.query.env.toString()
}

async function saveSelectionAsEnv() {
  const savedIds = selectedPrompts.value
    .map((p) => p.savedId).filter(Boolean)
  if (!savedIds.length) {
    toast.error('Select at least one saved prompt before saving as env.')
    return
  }
  const name = window.prompt('Name this environment:', `Env ${envs.value.length + 1}`)
  if (!name || !name.trim()) return
  try {
    const { data } = await promptLibrary.createTestEnvironment(
      websiteId, name.trim(), savedIds,
    )
    const env = data?.data || data
    envs.value = [env, ...envs.value]
    selectedEnvId.value = env.id
    toast.success(`Saved "${env.name}".`)
  } catch (e) {
    const msg = e.response?.status === 409
      ? 'An environment with that name already exists.'
      : (e.displayMessage || 'Could not save env.')
    toast.error(msg)
  }
}

async function toggleSaved(p) {
  const next = new Set(selectedSavedIds.value)
  const wasOn = next.has(p.id)
  if (wasOn) {
    next.delete(p.id)
    selectedPrompts.value = selectedPrompts.value.filter((x) => x.savedId !== p.id)
  } else {
    if (selectedPrompts.value.length >= 25) {
      toast.error('Max 25 prompts per run.')
      return
    }
    next.add(p.id)
    selectedPrompts.value.push({ uid: nextUid(), text: p.text, source: 'saved', savedId: p.id })
  }
  selectedSavedIds.value = next
  // When an env is active, keep its membership in sync with the pool.
  if (activeEnv.value) {
    try {
      if (wasOn) {
        await promptLibrary.removePromptsFromEnv(websiteId, activeEnv.value.id, [p.id])
      } else {
        await promptLibrary.addPromptsToEnv(websiteId, activeEnv.value.id, [p.id])
      }
      envs.value = envs.value.map((e) => {
        if (e.id !== activeEnv.value.id) return e
        const ids = new Set(e.prompt_ids || [])
        wasOn ? ids.delete(p.id) : ids.add(p.id)
        return { ...e, prompt_ids: Array.from(ids), prompt_count: ids.size }
      })
    } catch (e) {
      toast.error('Could not sync environment.')
    }
  }
}

const customDraft = ref('')
async function addCustom() {
  const t = customDraft.value.trim()
  if (!t) return
  if (selectedPrompts.value.length >= 25) {
    toast.error('Max 25 prompts per run.')
    return
  }
  // If an env is active, persist the prompt to the website's library
  // (auto-creates a BrandPrompt) and stitch it into the env. Without an
  // env we keep ad-hoc behavior: the prompt only lives in this run.
  if (activeEnv.value) {
    try {
      const bpId = await _persistTextAsBrandPrompt(t)
      if (bpId) {
        await promptLibrary.addPromptsToEnv(websiteId, activeEnv.value.id, [bpId])
        selectedSavedIds.value = new Set([...selectedSavedIds.value, bpId])
        selectedPrompts.value.push({ uid: nextUid(), text: t, source: 'custom', savedId: bpId })
        // Refresh env count + saved list so the picker stays accurate.
        _bumpEnvPromptCount(activeEnv.value.id, [bpId])
        await loadSaved()
        customDraft.value = ''
        return
      }
    } catch (e) {
      toast.error(e.displayMessage || 'Could not save to environment.')
      return
    }
  }
  selectedPrompts.value.push({ uid: nextUid(), text: t, source: 'custom' })
  customDraft.value = ''
}

// Helpers for env-mode persistence -------------------------------
async function _persistTextAsBrandPrompt(text) {
  // The Prompt+BrandPrompt get_or_create on the backend keeps this
  // idempotent — duplicate text returns the same BrandPrompt id.
  const { data } = await promptLibrary.createWebsitePrompt(websiteId, {
    template_text: text,
    text,
    style: 'question',
    intent_bucket: 'category',
  })
  const payload = data?.data || data || {}
  return payload.brand_prompt_id || null
}

function _bumpEnvPromptCount(envId, newIds) {
  envs.value = envs.value.map((e) => {
    if (e.id !== envId) return e
    const ids = new Set([...(e.prompt_ids || []), ...newIds])
    return { ...e, prompt_ids: Array.from(ids), prompt_count: ids.size }
  })
}

const mdInput = ref(null)
function parseMarkdown(text) {
  // Strip headings, bullets, blockquotes, blanks; keep one prompt per line.
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
          selectedPrompts.value.push({ uid: nextUid(), text: line, source: 'upload', savedId: bpId })
        }
      }
      if (newIds.length) {
        await promptLibrary.addPromptsToEnv(websiteId, activeEnv.value.id, newIds)
        selectedSavedIds.value = new Set([...selectedSavedIds.value, ...newIds])
        _bumpEnvPromptCount(activeEnv.value.id, newIds)
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
    selectedPrompts.value.push({ uid: nextUid(), text: line, source: 'upload' })
  }
  toast.success(`Imported ${lines.length} prompt${lines.length === 1 ? '' : 's'}`)
}

async function removeSelected(uid) {
  const removed = selectedPrompts.value.find((p) => p.uid === uid)
  selectedPrompts.value = selectedPrompts.value.filter((p) => p.uid !== uid)
  if (removed?.savedId) {
    const next = new Set(selectedSavedIds.value)
    next.delete(removed.savedId)
    selectedSavedIds.value = next
    if (activeEnv.value) {
      try {
        await promptLibrary.removePromptsFromEnv(websiteId, activeEnv.value.id, [removed.savedId])
        envs.value = envs.value.map((e) => {
          if (e.id !== activeEnv.value.id) return e
          const ids = (e.prompt_ids || []).filter((id) => id !== removed.savedId)
          return { ...e, prompt_ids: ids, prompt_count: ids.length }
        })
      } catch (e) {
        toast.error('Could not sync environment.')
      }
    }
  }
}
function clearAll() {
  selectedPrompts.value = []
  selectedSavedIds.value = new Set()
}

const promptCount = computed(() => selectedPrompts.value.length)

// Only meaningful when every selected prompt has a BrandPrompt id —
// custom-typed and md-uploaded prompts can't be stored in an env yet.
const canSaveAsEnv = computed(
  () => selectedPrompts.value.length > 0
    && selectedPrompts.value.every((p) => !!p.savedId),
)

// ── Step 2: models ───────────────────────────────────────────────
const providerOptions = ref([
  { key: 'claude',     label: 'Claude (Anthropic)', tag: '~3s · structured replies', available: true },
  { key: 'gpt4',       label: 'GPT-4 (OpenAI)',     tag: 'coming soon',              available: false },
  { key: 'gemini',     label: 'Gemini (Google)',    tag: 'coming soon',              available: false },
  { key: 'perplexity', label: 'Perplexity',         tag: 'coming soon',              available: false },
])
const enabledProviderCount = computed(() => providerOptions.value.filter((o) => o.available).length)
const selectedProviders = ref(['claude'])
function toggleProvider(key) {
  const opt = providerOptions.value.find((o) => o.key === key)
  if (!opt?.available) return
  if (selectedProviders.value.includes(key)) {
    selectedProviders.value = selectedProviders.value.filter((k) => k !== key)
  } else {
    selectedProviders.value = [...selectedProviders.value, key]
  }
}

const totalQueries = computed(() => promptCount.value * (selectedProviders.value.length || 0))
const canRun = computed(() => totalQueries.value > 0)

// ── Step 3: run (background job + poll) ──────────────────────────
const running = ref(false)
const errorMsg = ref('')
const lastRun = ref(null)        // final state once complete
const liveRun = ref(null)        // streaming state from polls
const runId = ref(null)
let pollTimer = null

function providerLabel(key) {
  return (providerOptions.value.find((o) => o.key === key)?.label) || key
}

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
  return `Running prompt ${pIdx} of ${s.prompts?.length || 0} on ${providerLabel(s.current_provider || '')} — "${pText}${pText.length >= 70 ? '…' : ''}"`
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
  running.value = true
  try {
    const { data } = await llmRanking.modelTest(websiteId, {
      prompts: selectedPrompts.value.map((p) => p.text),
      providers: selectedProviders.value,
    })
    runId.value = (data?.data || data)?.run_id
    if (!runId.value) throw new Error('No run id returned.')
    // Kick off polling — first call immediately, then every 1.5s.
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

const displayRun = computed(() => lastRun.value || liveRun.value)

function rowHitLabel(row) {
  const hit = row.responses.some((r) => r.brand_mentioned)
  if (hit) return 'discovered'
  if (row.responses.every((r) => !r.succeeded)) return 'all failed'
  return 'not discovered'
}
function rowHitClass(row) {
  const hit = row.responses.some((r) => r.brand_mentioned)
  if (hit) return 'is-hit'
  if (row.responses.every((r) => !r.succeeded)) return 'is-fail'
  return 'is-miss'
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

function _closeEnvMenuOnDocClick() { envMenuOpen.value = false }
onMounted(async () => {
  await Promise.all([loadSaved(), loadEnvs()])
  applyQueryPreselect()
  document.addEventListener('click', _closeEnvMenuOnDocClick)
})
onBeforeUnmount(() => document.removeEventListener('click', _closeEnvMenuOnDocClick))
</script>

<style scoped>
.mt-page {
  color: var(--text-primary);
}
.mt-page .page-subtitle strong { color: var(--text-primary); font-weight: 600; }

/* ── Top-level env header (campaign bundle) ───────────────────── */
.mt-env-bar {
  display: flex;
  gap: 24px;
  padding: 22px 24px;
  margin-bottom: 22px;
  background: linear-gradient(135deg, rgba(255, 107, 53, 0.06) 0%, rgba(255, 87, 34, 0.04) 100%);
  border: 1px solid rgba(255, 107, 53, 0.25);
  border-radius: 16px;
}
.mt-env-bar.is-empty {
  background: var(--bg-card, #fff);
  border: 1px dashed rgba(15, 23, 42, 0.20);
}
.mt-env-bar-left { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px; }
.mt-env-eyebrow {
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.12em;
  text-transform: uppercase; color: #ff6b35;
}
.mt-env-bar-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.mt-env-picker {
  position: relative;
  display: inline-flex; align-items: center; gap: 10px;
  padding: 10px 14px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 10px;
  cursor: pointer;
  min-width: 280px;
}
.mt-env-picker:hover { border-color: #ff6b35; }
.mt-env-pick-name { font-size: 16px; font-weight: 600; color: #0f172a; flex: 1; }
.mt-env-pick-count {
  font-size: 11.5px; font-weight: 600;
  padding: 2px 10px;
  background: rgba(255, 107, 53, 0.12); color: #c2410c;
  border-radius: 9999px;
}
.mt-env-caret { color: #94a3b8; }
.mt-env-menu {
  position: absolute; top: calc(100% + 6px); left: 0;
  min-width: 320px;
  max-height: 360px;
  overflow-y: auto;
  padding: 8px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 12px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.14);
  z-index: 30;
  cursor: default;
}
.mt-env-menu-h {
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.10em;
  text-transform: uppercase; color: #94a3b8;
  padding: 6px 10px;
}
.mt-env-menu-item {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  width: 100%;
  padding: 9px 10px;
  border: 0; background: transparent;
  font-size: 13.5px; text-align: left; cursor: pointer;
  border-radius: 8px; color: #0f172a;
}
.mt-env-menu-item:hover { background: rgba(15, 23, 42, 0.04); }
.mt-env-menu-item.is-current { background: rgba(255, 107, 53, 0.08); color: #c2410c; font-weight: 600; }
.mt-env-menu-item.is-primary { color: #ff6b35; font-weight: 600; }
.mt-env-menu-item.is-clear { color: #475569; font-style: italic; }
.mt-env-menu-count {
  font-size: 11px; font-weight: 600; padding: 1px 8px;
  background: rgba(15, 23, 42, 0.06); color: #475569;
  border-radius: 9999px;
}
.mt-env-menu-divider { height: 1px; background: rgba(15, 23, 42, 0.08); margin: 6px 0; }
.mt-env-menu-empty { padding: 8px 10px; font-size: 12px; color: #94a3b8; }
.mt-env-bar-actions { display: inline-flex; gap: 6px; }
.mt-env-bar-tool {
  padding: 6px 12px;
  border: 1px solid rgba(15, 23, 42, 0.10);
  background: #fff; color: #475569;
  border-radius: 9999px;
  font-size: 12px; font-weight: 500; cursor: pointer;
}
.mt-env-bar-tool:hover { border-color: #ff6b35; color: #ff6b35; }
.mt-env-bar-tool.is-danger:hover { border-color: #ef4444; color: #ef4444; }
.mt-env-hint { font-size: 13px; color: #475569; margin: 0; }
.mt-env-hint strong { color: #0f172a; font-weight: 600; }
.mt-env-link {
  background: none; border: 0; padding: 0;
  color: #ff6b35; font-weight: 600; cursor: pointer;
  text-decoration: underline; text-underline-offset: 2px;
}

/* Section */
.mt-section {
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 16px;
  padding: 22px;
  margin-bottom: 18px;
}
.mt-step-head {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 16px;
}
.mt-step-num {
  width: 28px; height: 28px; border-radius: 9px;
  display: inline-flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #ff6b35 0%, #ff5722 100%);
  color: #fff; font-weight: 700; font-size: 14px;
  box-shadow: 0 4px 12px rgba(255, 107, 53, 0.25);
}
.mt-step-h { font-size: 16px; font-weight: 700; color: #0f172a; }
.mt-step-sub { font-size: 12px; color: #64748b; margin-top: 2px; }

/* Tabs */
.mt-tabs { display: inline-flex; gap: 4px; padding: 4px; background: #f1f5f9; border-radius: 10px; margin-bottom: 16px; }
.mt-tab {
  padding: 7px 14px; border: 0; background: transparent;
  font-size: 13px; font-weight: 600; color: #64748b;
  border-radius: 7px; cursor: pointer; transition: all 0.15s;
}
.mt-tab.is-active { background: #fff; color: #0f172a; box-shadow: 0 1px 2px rgba(15,23,42,0.06); }

/* Saved list */
.mt-muted { color: #64748b; font-size: 13px; padding: 10px 0; }
.mt-empty { color: #64748b; font-size: 13px; padding: 16px; background: #f8fafc; border-radius: 10px; }
.mt-saved-list { list-style: none; margin: 0; padding: 0; max-height: 360px; overflow: auto; }
.mt-saved-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; margin-bottom: 6px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 10px;
  cursor: pointer; transition: all 0.15s;
  background: #fff;
}
.mt-saved-item:hover { border-color: rgba(255, 107, 53, 0.30); }
.mt-saved-item.is-on { border-color: #ff6b35; background: rgba(255, 107, 53, 0.04); }
.mt-check {
  width: 18px; height: 18px; border-radius: 5px;
  border: 1.5px solid #cbd5e1;
  display: inline-flex; align-items: center; justify-content: center;
  background: #fff; color: #fff; flex-shrink: 0;
}
.mt-saved-item.is-on .mt-check { background: #ff6b35; border-color: #ff6b35; }
.mt-saved-text { flex: 1; font-size: 13.5px; color: #0f172a; }
.mt-saved-tag {
  font-size: 10.5px; font-weight: 600; padding: 2px 8px;
  border-radius: 9999px; background: rgba(59, 130, 246, 0.10); color: #1d4ed8;
}

/* Custom */
.mt-textarea {
  width: 100%;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 10px;
  padding: 12px 14px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  margin-bottom: 10px;
}
.mt-textarea:focus { outline: none; border-color: #ff6b35; box-shadow: 0 0 0 3px rgba(255,107,53,0.15); }

/* Upload */
.mt-drop {
  display: block;
  border: 2px dashed rgba(255, 107, 53, 0.30);
  border-radius: 12px;
  padding: 24px;
  cursor: pointer;
  text-align: center;
  background: rgba(255, 107, 53, 0.03);
  transition: all 0.15s;
}
.mt-drop:hover { background: rgba(255, 107, 53, 0.06); }
.mt-drop input { display: none; }
.mt-drop-h { font-size: 14px; font-weight: 600; color: #ff6b35; }
.mt-drop-sub { font-size: 12px; color: #64748b; margin-top: 4px; }
.mt-drop-sub code { padding: 1px 4px; background: #f1f5f9; border-radius: 4px; font-size: 11px; }

/* Pool */
.mt-pool {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed rgba(15, 23, 42, 0.10);
}
.mt-pool-head {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 12px; font-weight: 600; color: #64748b;
  margin-bottom: 10px;
}
.mt-pool-clear {
  border: 0; background: transparent; color: #ef4444;
  font-size: 11.5px; font-weight: 600; cursor: pointer;
}
.mt-pool-actions { display: inline-flex; align-items: center; gap: 14px; }
.mt-pool-save {
  border: 1px solid #ff6b35; background: transparent; color: #ff6b35;
  padding: 4px 12px; border-radius: 9999px;
  font-size: 11.5px; font-weight: 600; cursor: pointer;
}
.mt-pool-save:hover { background: rgba(255, 107, 53, 0.08); }

/* Env tab list */
.mt-pool-list { list-style: none; margin: 0; padding: 0; }
.mt-pool-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; margin-bottom: 4px;
  background: #f8fafc; border-radius: 8px;
}
.mt-pool-num { font-size: 11px; font-weight: 700; color: #94a3b8; width: 18px; }
.mt-pool-text { flex: 1; font-size: 13px; color: #1f2937; }
.mt-pool-remove {
  border: 0; background: transparent; color: #94a3b8;
  font-size: 18px; line-height: 1; cursor: pointer; padding: 0 6px;
}
.mt-pool-remove:hover { color: #ef4444; }

/* Models */
.mt-models { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
.mt-model {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 12px 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  cursor: pointer;
  background: #fff;
  transition: all 0.15s;
}
.mt-model:hover:not(.is-off) { border-color: rgba(255, 107, 53, 0.30); }
.mt-model.is-on { border-color: #ff6b35; background: rgba(255, 107, 53, 0.04); }
.mt-model.is-off { opacity: 0.55; cursor: not-allowed; background: #f8fafc; }
.mt-model input { margin-top: 3px; accent-color: #ff6b35; }
.mt-model-body { flex: 1; min-width: 0; }
.mt-model-head { display: flex; align-items: center; gap: 8px; }
.mt-model-dot { width: 8px; height: 8px; border-radius: 9999px; background: #cbd5e1; }
.mt-model-dot.is-claude     { background: #d97706; }
.mt-model-dot.is-gpt4       { background: #10b981; }
.mt-model-dot.is-gemini     { background: #4285f4; }
.mt-model-dot.is-perplexity { background: #5b6cff; }
.mt-model-name { font-size: 13.5px; font-weight: 600; color: #0f172a; }
.mt-model-soon {
  font-size: 10px; font-weight: 600; padding: 1px 7px;
  background: rgba(15, 23, 42, 0.06); color: #64748b;
  border-radius: 9999px; text-transform: uppercase;
  letter-spacing: 0.04em; margin-left: auto;
}
.mt-model-sub { font-size: 11.5px; color: #64748b; margin-top: 2px; }

/* Run */
.mt-run-summary {
  display: flex; justify-content: space-between; align-items: center; gap: 16px;
}
.mt-run-num { font-size: 28px; font-weight: 700; color: #0f172a; line-height: 1; }
.mt-run-label { font-size: 12px; color: #64748b; margin-top: 4px; }
.mt-btn-run {
  padding: 12px 24px;
  background: linear-gradient(135deg, #ff6b35 0%, #ff5722 100%);
  color: #fff; border: 0; border-radius: 10px;
  font-size: 14px; font-weight: 700;
  cursor: pointer; transition: all 0.15s;
  box-shadow: 0 6px 16px rgba(255, 107, 53, 0.25);
}
.mt-btn-run:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 10px 22px rgba(255, 107, 53, 0.35); }
.mt-btn-run:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }
.mt-spinner {
  display: inline-block; width: 12px; height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 9999px;
  margin-right: 6px;
  animation: mt-spin 0.7s linear infinite;
  vertical-align: -2px;
}
@keyframes mt-spin { to { transform: rotate(360deg); } }
.mt-btn-secondary {
  padding: 8px 16px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 9px;
  font-size: 13px; font-weight: 600; color: #1f2937;
  cursor: pointer;
}
.mt-btn-secondary:hover:not(:disabled) {
  background: #ff6b35; border-color: #ff6b35; color: #fff;
}
.mt-btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
.mt-live {
  margin-top: 16px;
  padding: 14px 16px;
  background: linear-gradient(135deg, rgba(255, 107, 53, 0.06) 0%, rgba(255, 87, 34, 0.04) 100%);
  border: 1px solid rgba(255, 107, 53, 0.20);
  border-radius: 12px;
}
.mt-live-bar {
  width: 100%; height: 6px;
  background: rgba(15, 23, 42, 0.06);
  border-radius: 9999px; overflow: hidden;
  margin-bottom: 8px;
}
.mt-live-fill {
  height: 100%;
  background: linear-gradient(90deg, #ff6b35 0%, #ff5722 100%);
  border-radius: 9999px;
  transition: width 0.4s ease;
}
.mt-live-meta { display: flex; align-items: baseline; gap: 10px; font-size: 12.5px; }
.mt-live-pct { font-weight: 700; color: #ff6b35; min-width: 38px; }
.mt-live-text { color: #475569; flex: 1; }
.mt-error {
  margin-top: 12px; padding: 10px 14px;
  background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.20);
  border-radius: 10px; color: #b91c1c; font-size: 13px;
}

/* Results */
.mt-results { margin-top: 28px; }
.mt-results-head {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 14px;
}
.mt-results-h { font-size: 18px; font-weight: 700; margin: 0; color: #0f172a; }
.mt-discovery {
  font-size: 13px; color: #475569;
}
.mt-discovery strong { color: #ff6b35; font-size: 18px; font-weight: 700; }
.mt-discovery em { font-style: normal; color: #64748b; margin-left: 4px; font-size: 12px; }

.mt-result-card {
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  padding: 16px 18px;
  margin-bottom: 12px;
}
.mt-result-prompt {
  display: flex; align-items: center; gap: 10px;
  padding-bottom: 12px;
  margin-bottom: 12px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}
.mt-result-num { font-size: 11px; font-weight: 700; color: #94a3b8; }
.mt-result-text { flex: 1; font-size: 14px; font-weight: 600; color: #0f172a; }
.mt-result-pill {
  font-size: 11px; font-weight: 700; padding: 3px 10px;
  border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.04em;
}
.mt-result-pill.is-hit  { background: rgba(16, 185, 129, 0.12); color: #047857; }
.mt-result-pill.is-miss { background: rgba(15, 23, 42, 0.08);   color: #475569; }
.mt-result-pill.is-fail { background: rgba(239, 68, 68, 0.12);  color: #b91c1c; }

.mt-resp { margin-top: 10px; padding: 12px; background: #f8fafc; border-radius: 10px; }
.mt-resp-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.mt-resp-dot { width: 8px; height: 8px; border-radius: 9999px; background: #cbd5e1; }
.mt-resp-dot.is-claude     { background: #d97706; }
.mt-resp-dot.is-gpt4       { background: #10b981; }
.mt-resp-dot.is-gemini     { background: #4285f4; }
.mt-resp-dot.is-perplexity { background: #5b6cff; }
.mt-resp-name { font-size: 13px; font-weight: 600; color: #0f172a; }
.mt-resp-badge {
  font-size: 10.5px; font-weight: 600; padding: 2px 8px;
  border-radius: 9999px; text-transform: lowercase; letter-spacing: 0.02em;
}
.mt-resp-badge.is-hit  { background: rgba(16, 185, 129, 0.14); color: #047857; }
.mt-resp-badge.is-miss { background: rgba(15, 23, 42, 0.06);   color: #64748b; }
.mt-resp-badge.is-fail { background: rgba(239, 68, 68, 0.10);  color: #b91c1c; }
.mt-resp-time { font-size: 10.5px; color: #94a3b8; margin-left: auto; }
.mt-resp-body {
  font-size: 12.5px; line-height: 1.55; color: #334155;
  white-space: pre-wrap;
}
.mt-resp-empty { font-size: 12px; color: #b91c1c; font-style: italic; }

:deep(.mt-mark) {
  background: rgba(255, 107, 53, 0.22);
  color: #c2410c;
  padding: 0 3px;
  border-radius: 3px;
  font-weight: 700;
}

@media (max-width: 880px) {
  .mt-run-summary { flex-direction: column; align-items: stretch; }
}
</style>
