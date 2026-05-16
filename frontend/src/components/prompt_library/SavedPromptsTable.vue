<template>
  <div class="spt-wrap">
    <!-- Compact stat strip — only the three numbers worth seeing.
         The tab badge already shows the saved count; here we focus
         on the testing state which is what the user is acting on. -->
    <div v-if="prompts.length" class="spt-stat-strip">
      <div class="spt-stat-cell"><span class="spt-stat-label">Saved</span><span class="spt-stat-val">{{ prompts.length }}</span></div>
      <div class="spt-stat-cell"><span class="spt-stat-label">Tested</span><span class="spt-stat-val">{{ testedCount }}</span></div>
      <div class="spt-stat-cell"><span class="spt-stat-label">Untested</span><span class="spt-stat-val">{{ untestedCount }}</span></div>
    </div>

    <!-- Environment filter strip — every env + "Unassigned" + "All".
         Tapping a chip filters the table below to that env's prompts
         and reveals the env-level actions on the right. Replaces the
         3 stacked tables the previous design had. -->
    <div v-if="prompts.length" class="spt-envrow">
      <div class="spt-envchips">
        <button
          type="button"
          class="spt-envchip"
          :class="{ 'is-on': envFilter === 'all' }"
          @click="envFilter = 'all'"
        >All <span class="spt-envchip-count">{{ prompts.length }}</span></button>
        <button
          v-for="env in envs"
          :key="env.id"
          type="button"
          class="spt-envchip"
          :class="{ 'is-on': envFilter === env.id }"
          @click="envFilter = env.id"
        >
          {{ env.name }}
          <span class="spt-envchip-count">{{ (env.prompt_ids || []).length }}</span>
        </button>
        <button
          type="button"
          class="spt-envchip"
          :class="{ 'is-on': envFilter === '__unassigned__' }"
          @click="envFilter = '__unassigned__'"
        >Unassigned <span class="spt-envchip-count">{{ unassignedCount }}</span></button>
        <button class="spt-envchip is-add" @click="openCreateEnv">+ New environment</button>
      </div>

      <!-- Env-level actions appear only when a specific env is selected. -->
      <div v-if="activeEnv" class="spt-envactions">
        <button class="spt-envaction" @click="runEnvAsTest(activeEnv)">Run as Model Test</button>
        <button class="spt-envaction" @click="renameEnv(activeEnv)">Rename</button>
        <button class="spt-envaction is-danger" @click="deleteEnv(activeEnv)">Delete</button>
      </div>
    </div>

    <!-- Search + style + run-audit shortcut -->
    <div v-if="prompts.length" class="spt-filters">
      <input v-model="search" type="search" class="spt-search" placeholder="Filter prompts…" />
      <label class="spt-select-wrap">
        <span class="spt-select-label">Style</span>
        <select v-model="styleFilter" class="spt-select">
          <option value="">All</option>
          <option v-for="s in styleOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
      </label>
      <AirButton variant="primary" size="sm" :as="'router-link'" :to="`/llm-ranking/${websiteId}`">
        Run audit
      </AirButton>
    </div>

    <AirCard size="md" :padded="false">
      <div v-if="loading" class="spt-state">Loading saved prompts…</div>
      <div v-else-if="!prompts.length" class="spt-empty">
        <div class="spt-empty-icon" aria-hidden="true">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="spt-empty-title">No saved prompts yet</div>
        <p class="spt-empty-sub">
          Run a search and click <strong>Save</strong> on any prompt to add it
          here, then group prompts into a <strong>test environment</strong> to
          run as a batch on the Model Test page.
        </p>
        <AirButton variant="primary" size="sm" @click="$emit('go-search')">
          Search prompts
        </AirButton>
      </div>

      <!-- One unified table. Env membership is a column, not a section. -->
      <table v-else-if="visibleRows.length" class="spt-table">
        <thead>
          <tr>
            <th style="width: 36px">
              <input
                type="checkbox"
                :checked="allVisibleSelected"
                :indeterminate.prop="someVisibleSelected"
                @change="toggleAllVisible"
              />
            </th>
            <th style="width: 110px">ID</th>
            <th style="width: 120px">Style</th>
            <th>Prompt</th>
            <th style="width: 200px">Environments</th>
            <th style="width: 130px">Status</th>
            <th style="width: 110px" class="text-right">Action</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in visibleRows"
            :key="row._brand_prompt_id"
            class="spt-row"
            :class="{ 'is-selected': selectedIds.has(row._brand_prompt_id) }"
          >
            <td>
              <input
                type="checkbox"
                :checked="selectedIds.has(row._brand_prompt_id)"
                @change="toggleRow(row)"
              />
            </td>
            <td><span class="spt-id-pill">{{ formatId(row._brand_prompt_id) }}</span></td>
            <td><AirChip size="xs" variant="neutral">{{ titleCase(row.style) }}</AirChip></td>
            <td class="spt-prompt-cell"><div class="spt-prompt-text">{{ row.text || row.template_text }}</div></td>
            <td>
              <div v-if="envsForPrompt(row).length" class="spt-envtags">
                <span
                  v-for="e in envsForPrompt(row)"
                  :key="e.id"
                  class="spt-envtag"
                >{{ e.name }}</span>
              </div>
              <span v-else class="spt-muted">—</span>
            </td>
            <td>
              <span v-if="!row.runs_count" class="spt-status spt-status-untested">Untested</span>
              <span v-else-if="(row.effectiveness_score || 0) >= 0.7" class="spt-status spt-status-good">Top</span>
              <span v-else-if="(row.effectiveness_score || 0) >= 0.4" class="spt-status spt-status-mid">Steady</span>
              <span v-else class="spt-status spt-status-low">Underperforming</span>
            </td>
            <td class="text-right">
              <button class="spt-action-btn" :disabled="testingId === row.id" @click="onTest(row)" title="Smoke test against Claude">
                <span v-if="testingId === row.id" class="spt-spinner"></span>
                <span v-else>Test</span>
              </button>
              <button class="spt-action-btn spt-action-btn-ghost" @click="onRemove(row)" title="Remove from saved">×</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="spt-empty-filter">
        No prompts match these filters.
      </div>
    </AirCard>

    <!-- Sticky bulk-action bar (unchanged) -->
    <transition name="spt-bar">
      <div v-if="selectedIds.size > 0" class="spt-bar">
        <div class="spt-bar-info">
          <strong>{{ selectedIds.size }}</strong> selected
          <button class="spt-bar-link" @click="clearSelection">Clear</button>
        </div>
        <div class="spt-bar-actions">
          <div class="spt-add-wrap" @click.stop>
            <button class="spt-bar-btn" @click="addMenuOpen = !addMenuOpen">
              Add to env
              <svg width="10" height="6" viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M1 1l4 4 4-4" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
            <div v-if="addMenuOpen" class="spt-add-menu">
              <button v-for="env in envs" :key="env.id" class="spt-add-item"
                      @click="bulkAddToEnv(env)">{{ env.name }}</button>
              <div v-if="!envs.length" class="spt-add-empty">No envs yet</div>
              <div class="spt-add-divider"></div>
              <button class="spt-add-item is-primary" @click="bulkCreateEnvFromSelection">+ Create new env from selection</button>
            </div>
          </div>
          <button class="spt-bar-btn" :disabled="!canBulkRemove" @click="bulkRemoveFromEnv">Remove from env</button>
          <button class="spt-bar-btn is-primary" @click="runSelectionAsTest">Run as Model Test</button>
        </div>
      </div>
    </transition>

    <BaseModal v-model="smokeOpen" title="Test result" subtitle="Single-provider smoke test" wide>
      <SmokeTestResult v-if="smokeResult" :result="smokeResult" @try-provider="(p) => runSmoke(activeSmokePromptId, p)" />
      <div v-else class="spt-state">Running…</div>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import promptLibrary from '@/api/promptLibrary'
import AirCard from '@/components/ui/AirCard.vue'
import AirChip from '@/components/ui/AirChip.vue'
import AirButton from '@/components/ui/AirButton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import SmokeTestResult from '@/components/prompt_library/SmokeTestResult.vue'

const props = defineProps({
  websiteId: { type: String, required: true },
})
defineEmits(['go-search'])

const toast = useToast()
const router = useRouter()

const prompts = ref([])           // BrandPrompt rows, flattened
const envs = ref([])              // TestEnvironment rows
const loading = ref(false)
const search = ref('')
const styleFilter = ref('')
const testingId = ref(null)
const smokeOpen = ref(false)
const smokeResult = ref(null)
const activeSmokePromptId = ref(null)
const selectedIds = ref(new Set())   // brand_prompt_ids
const addMenuOpen = ref(false)
// 'all' | '__unassigned__' | env.id
const envFilter = ref('all')

const styleOptions = [
  { value: 'story', label: 'Story' },
  { value: 'question', label: 'Question' },
  { value: 'recommendation', label: 'Recommendation' },
  { value: 'skeptical', label: 'Skeptical' },
  { value: 'comparison', label: 'Comparison' },
  { value: 'local', label: 'Local' },
  { value: 'how_to', label: 'How-to' },
  { value: 'discovery', label: 'Discovery' },
  { value: 'problem', label: 'Problem' },
  { value: 'verification', label: 'Verification' },
  { value: 'experience', label: 'Experience' },
  { value: 'listicle', label: 'Listicle' },
]

// ── Loading ─────────────────────────────────────────────────────
async function load() {
  if (!props.websiteId) return
  loading.value = true
  try {
    const [promptResp, envResp] = await Promise.all([
      promptLibrary.listBrandPrompts(props.websiteId),
      promptLibrary.listTestEnvironments(props.websiteId).catch(() => ({ data: [] })),
    ])
    const rows = promptResp?.data?.data || promptResp?.data || []
    const list = Array.isArray(rows) ? rows : []
    prompts.value = list.map(item => item.prompt
      ? { ...item.prompt, _brand_prompt_id: item.id, notes: item.notes }
      : item
    )
    const envRows = envResp?.data?.data || envResp?.data || []
    envs.value = Array.isArray(envRows) ? envRows : []
    // Default: every env expanded so the user sees their groups.
    // No-op — kept for parity with old behaviour. Env tabs replace
    // the expand/collapse state entirely.
  } catch (e) {
    prompts.value = []
    envs.value = []
    toast.error('Could not load saved prompts.')
  } finally {
    loading.value = false
  }
}

// ── Filter + grouping ───────────────────────────────────────────
const filteredPrompts = computed(() => {
  const q = search.value.trim().toLowerCase()
  return prompts.value.filter(p => {
    if (styleFilter.value && p.style !== styleFilter.value) return false
    if (q) {
      const t = (p.text || p.template_text || '').toLowerCase()
      if (!t.includes(q)) return false
    }
    return true
  })
})

// All env ids that contain each prompt. Used both for the
// "Environments" column on each row and for the env filter logic.
const envIdsByPrompt = computed(() => {
  const map = new Map()
  for (const env of envs.value) {
    for (const id of (env.prompt_ids || [])) {
      if (!map.has(id)) map.set(id, [])
      map.get(id).push(env.id)
    }
  }
  return map
})
function envsForPrompt(row) {
  const ids = envIdsByPrompt.value.get(row._brand_prompt_id) || []
  return envs.value.filter((e) => ids.includes(e.id))
}

const unassignedCount = computed(() => {
  return prompts.value.filter(
    (p) => !envIdsByPrompt.value.has(p._brand_prompt_id),
  ).length
})

const activeEnv = computed(() => {
  if (envFilter.value === 'all' || envFilter.value === '__unassigned__') return null
  return envs.value.find((e) => e.id === envFilter.value) || null
})

// Flat list of rows visible right now. Applies the env-filter on
// top of the search/style filter computed above.
const visibleRows = computed(() => {
  const rows = filteredPrompts.value
  if (envFilter.value === 'all') return rows
  if (envFilter.value === '__unassigned__') {
    return rows.filter((p) => !envIdsByPrompt.value.has(p._brand_prompt_id))
  }
  const env = envs.value.find((e) => e.id === envFilter.value)
  if (!env) return rows
  const ids = new Set(env.prompt_ids || [])
  return rows.filter((p) => ids.has(p._brand_prompt_id))
})

// Select-all helpers operate on the currently visible row set.
const allVisibleSelected = computed(() => {
  if (!visibleRows.value.length) return false
  return visibleRows.value.every((r) => selectedIds.value.has(r._brand_prompt_id))
})
const someVisibleSelected = computed(() => {
  if (!visibleRows.value.length) return false
  const any = visibleRows.value.some((r) => selectedIds.value.has(r._brand_prompt_id))
  return any && !allVisibleSelected.value
})
function toggleAllVisible() {
  const next = new Set(selectedIds.value)
  if (allVisibleSelected.value) {
    for (const r of visibleRows.value) next.delete(r._brand_prompt_id)
  } else {
    for (const r of visibleRows.value) next.add(r._brand_prompt_id)
  }
  selectedIds.value = next
}

// ── Selection ───────────────────────────────────────────────────
function toggleRow(row) {
  const next = new Set(selectedIds.value)
  const id = row._brand_prompt_id
  next.has(id) ? next.delete(id) : next.add(id)
  selectedIds.value = next
}
function clearSelection() { selectedIds.value = new Set() }

const canBulkRemove = computed(() => {
  // Only meaningful when every selected prompt sits in at least one env.
  // For the MVP we light it up whenever there is any env to remove from.
  return envs.value.length > 0
})

// ── Bulk actions ────────────────────────────────────────────────
async function bulkAddToEnv(env) {
  addMenuOpen.value = false
  const ids = Array.from(selectedIds.value)
  if (!ids.length) return
  try {
    const { data } = await promptLibrary.addPromptsToEnv(props.websiteId, env.id, ids)
    const fresh = data?.data || data
    envs.value = envs.value.map(e => e.id === env.id ? { ...e, ...fresh } : e)
    toast.success(`Added ${ids.length} to ${env.name}.`)
    clearSelection()
  } catch (e) {
    toast.error(e.displayMessage || 'Could not add to env.')
  }
}
async function bulkRemoveFromEnv() {
  const ids = Array.from(selectedIds.value)
  if (!ids.length) return
  // We try to remove from EVERY env the selection touches. The backend
  // is a no-op when the prompt isn't in that env, so this is safe.
  const touched = envs.value.filter(env =>
    (env.prompt_ids || []).some(id => ids.includes(id))
  )
  if (!touched.length) {
    toast.info('None of these prompts are in an environment.')
    return
  }
  try {
    for (const env of touched) {
      const { data } = await promptLibrary.removePromptsFromEnv(props.websiteId, env.id, ids)
      const fresh = data?.data || data
      envs.value = envs.value.map(e => e.id === env.id ? { ...e, ...fresh } : e)
    }
    toast.success(`Removed ${ids.length} from ${touched.length} env${touched.length === 1 ? '' : 's'}.`)
    clearSelection()
  } catch (e) {
    toast.error(e.displayMessage || 'Could not remove.')
  }
}
async function bulkCreateEnvFromSelection() {
  addMenuOpen.value = false
  const ids = Array.from(selectedIds.value)
  if (!ids.length) return
  const name = window.prompt('Name this environment:', `Env ${envs.value.length + 1}`)
  if (!name || !name.trim()) return
  try {
    const { data } = await promptLibrary.createTestEnvironment(
      props.websiteId, name.trim(), ids,
    )
    const env = data?.data || data
    envs.value = [env, ...envs.value]
    envFilter.value = env.id
    toast.success(`Created "${env.name}".`)
    clearSelection()
  } catch (e) {
    const msg = e.response?.status === 409
      ? 'An environment with that name already exists.'
      : (e.displayMessage || 'Could not create env.')
    toast.error(msg)
  }
}
function runSelectionAsTest() {
  const ids = Array.from(selectedIds.value)
  if (!ids.length) return
  router.push({
    path: `/llm-ranking/${props.websiteId}/source-influence`,
    query: { prompts: ids.join(',') },
  })
}

// ── Env CRUD from group headers ─────────────────────────────────
async function openCreateEnv() {
  const name = window.prompt('Name this environment:', `Env ${envs.value.length + 1}`)
  if (!name || !name.trim()) return
  try {
    const { data } = await promptLibrary.createTestEnvironment(props.websiteId, name.trim(), [])
    const env = data?.data || data
    envs.value = [env, ...envs.value]
    envFilter.value = env.id
  } catch (e) {
    const msg = e.response?.status === 409
      ? 'An environment with that name already exists.'
      : (e.displayMessage || 'Could not create env.')
    toast.error(msg)
  }
}
async function renameEnv(env) {
  const name = window.prompt('Rename environment:', env.name)
  if (!name || !name.trim() || name.trim() === env.name) return
  try {
    const { data } = await promptLibrary.renameTestEnvironment(props.websiteId, env.id, name.trim())
    const fresh = data?.data || data
    envs.value = envs.value.map(e => e.id === env.id ? fresh : e)
  } catch (e) {
    toast.error(e.displayMessage || 'Could not rename.')
  }
}
async function deleteEnv(env) {
  if (!window.confirm(`Delete environment "${env.name}"? The prompts inside stay saved.`)) return
  try {
    await promptLibrary.deleteTestEnvironment(props.websiteId, env.id)
    envs.value = envs.value.filter(e => e.id !== env.id)
  } catch (e) {
    toast.error('Could not delete.')
  }
}
function runEnvAsTest(env) {
  const ids = env.prompt_ids || []
  if (!ids.length) {
    toast.info('This environment is empty.')
    return
  }
  router.push({
    path: `/llm-ranking/${props.websiteId}/source-influence`,
    query: { prompts: ids.join(','), env: env.id },
  })
}

// ── Per-row single-prompt actions (unchanged behavior) ──────────
async function runSmoke(promptId, provider = 'claude') {
  if (!promptId) return
  testingId.value = promptId
  smokeOpen.value = true
  smokeResult.value = null
  activeSmokePromptId.value = promptId
  try {
    const { data } = await promptLibrary.smokeTest(promptId, { provider, website_id: props.websiteId })
    smokeResult.value = data?.data || data
  } catch (e) {
    smokeOpen.value = false
    toast.error(e.displayMessage || 'Smoke test failed.')
  } finally {
    testingId.value = null
  }
}
function onTest(row) { runSmoke(row.id, 'claude') }

async function onRemove(row) {
  if (!row._brand_prompt_id) return
  if (!window.confirm('Remove this prompt from your saved set?')) return
  try {
    await promptLibrary.removeBrandPrompt(row._brand_prompt_id)
    prompts.value = prompts.value.filter(p => p._brand_prompt_id !== row._brand_prompt_id)
    const id = row._brand_prompt_id
    envs.value = envs.value.map(e => ({
      ...e,
      prompt_ids: (e.prompt_ids || []).filter(pid => pid !== id),
      prompt_count: Math.max(0, (e.prompt_count || 0) - ((e.prompt_ids || []).includes(id) ? 1 : 0)),
    }))
    toast.success('Removed.')
  } catch (e) {
    toast.error('Could not remove.')
  }
}

// ── Stats ───────────────────────────────────────────────────────
const testedCount = computed(() => prompts.value.filter(p => (p.runs_count || 0) > 0).length)
const untestedCount = computed(() => prompts.value.length - testedCount.value)
const avgTrend = computed(() => {
  if (!prompts.value.length) return '—'
  const scores = prompts.value
    .map(p => Number(p.effectiveness_score) ? Math.round(Number(p.effectiveness_score) * 100) : null)
    .filter(s => s !== null)
  if (!scores.length) return '—'
  return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
})

function titleCase(value) {
  if (!value) return '—'
  return String(value).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}
function formatId(uuid) {
  return String(uuid || '').replace(/-/g, '').slice(0, 5).toUpperCase()
}
function formatRelative(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  const sec = Math.floor((Date.now() - d.getTime()) / 1000)
  if (sec < 60) return 'just now'
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`
  if (sec < 86400 * 7) return `${Math.floor(sec / 86400)}d ago`
  return d.toLocaleDateString()
}

// Click-outside for the Add-to-env menu.
function onDocClick() { addMenuOpen.value = false }
onMounted(() => {
  load()
  document.addEventListener('click', onDocClick)
})
onUnmounted(() => document.removeEventListener('click', onDocClick))
watch(() => props.websiteId, load)

defineExpose({ load, count: computed(() => prompts.value.length) })
</script>

<style scoped>
.spt-wrap { display: flex; flex-direction: column; gap: 16px; padding-bottom: 80px; }

/* Compact stat strip, same pattern as Prompt Library page */
.spt-stat-strip {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 22px;
  padding: 10px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  font-size: 12px;
}
.spt-stat-cell { display: inline-flex; align-items: baseline; gap: 6px; }
.spt-stat-cell + .spt-stat-cell { padding-left: 22px; border-left: 1px solid var(--border-color); }
.spt-stat-label { font-size: 11.5px; font-weight: 500; color: var(--text-secondary); }
.spt-stat-val { font-size: 13px; font-weight: 600; color: var(--text-primary); font-variant-numeric: tabular-nums; }
@media (max-width: 600px) {
  .spt-stat-cell + .spt-stat-cell { padding-left: 0; border-left: 0; }
  .spt-stat-strip { gap: 12px 18px; }
}

/* Environment filter strip */
.spt-envrow {
  display: flex; gap: 14px; align-items: center;
  flex-wrap: wrap;
}
.spt-envchips {
  display: flex; gap: 6px; flex-wrap: wrap;
  flex: 1; min-width: 0;
}
.spt-envchip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 11px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 9999px;
  font-size: 12.5px; font-weight: 500; color: #0f172a;
  cursor: pointer; white-space: nowrap;
  transition: background .12s ease, border-color .12s ease;
}
.spt-envchip:hover { border-color: #0f172a; }
.spt-envchip.is-on {
  background: #0f172a; color: #fff; border-color: #0f172a;
}
.spt-envchip.is-add {
  border-style: dashed; color: #475569;
}
.spt-envchip-count {
  font-size: 11px; font-weight: 700;
  padding: 1px 6px;
  background: rgba(15, 23, 42, 0.08); color: #475569;
  border-radius: 9999px;
}
.spt-envchip.is-on .spt-envchip-count {
  background: rgba(255, 255, 255, 0.18); color: #fff;
}
.spt-envactions {
  display: flex; gap: 6px; flex: none;
}
.spt-envaction {
  background: transparent; border: 0;
  padding: 5px 10px;
  font: inherit; font-size: 12.5px; color: #475569;
  cursor: pointer;
  border-radius: 6px;
}
.spt-envaction:hover { background: #f1f5f9; color: #0f172a; }
.spt-envaction.is-danger { color: #b91c1c; }
.spt-envaction.is-danger:hover { background: #fef2f2; }

/* Environment tags inside the table column */
.spt-envtags { display: flex; flex-wrap: wrap; gap: 4px; }
.spt-envtag {
  font-size: 11px; font-weight: 500;
  padding: 2px 8px;
  background: #f1f5f9; color: #475569;
  border-radius: 9999px;
  white-space: nowrap;
}

.spt-filters { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.spt-search {
  flex: 1; min-width: 220px;
  padding: 8px 14px; border: 1px solid var(--border-color); border-radius: 9999px;
  background: var(--bg-card); color: var(--text-primary); font-size: 14px; outline: none;
}
.spt-search:focus-visible { border-color: var(--brand-accent); box-shadow: 0 0 0 3px var(--brand-accent-glow); }
.spt-select-wrap { display: inline-flex; align-items: center; gap: 8px; }
.spt-select-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); }
.spt-select {
  appearance: none; -webkit-appearance: none;
  background-color: var(--bg-card);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6' fill='none'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%2364748b' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 10px center;
  border: 1px solid var(--border-color); border-radius: 9999px;
  color: var(--text-primary); padding: 6px 30px 6px 12px;
  font-size: 13px; cursor: pointer;
}
.spt-new-env-btn {
  padding: 6px 14px; border: 1px dashed var(--border-color); border-radius: 9999px;
  background: transparent; color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer;
}
.spt-new-env-btn:hover { border-color: var(--brand-accent); color: var(--brand-accent); }

/* Groups */
.spt-groups { display: flex; flex-direction: column; }
.spt-group { border-bottom: 1px solid var(--border-color); }
.spt-group:last-child { border-bottom: 0; }
.spt-group-head {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 18px; background: var(--bg-surface, rgba(15, 23, 42, 0.02));
}
.spt-group-check input { accent-color: var(--brand-accent); cursor: pointer; }
.spt-group-title {
  display: inline-flex; align-items: center; gap: 8px;
  border: 0; background: transparent; cursor: pointer;
  font-size: 14px; font-weight: 600; color: var(--text-primary);
  padding: 4px 0;
}
.spt-caret { transition: transform 0.15s ease; flex-shrink: 0; color: var(--text-muted); }
.spt-caret.is-open { transform: rotate(0deg); }
.spt-caret:not(.is-open) { transform: rotate(-90deg); }
.spt-group-name { letter-spacing: -0.01em; }
.spt-group-count {
  font-size: 11px; font-weight: 500;
  padding: 1px 8px; border-radius: 9999px;
  background: rgba(15, 23, 42, 0.06); color: var(--text-secondary);
}
.spt-group-tools { margin-left: auto; display: inline-flex; gap: 6px; }
.spt-group-tool {
  font-size: 12px; padding: 5px 12px; border: 1px solid var(--border-color);
  background: var(--bg-card); color: var(--text-secondary);
  border-radius: 9999px; cursor: pointer;
}
.spt-group-tool:hover { border-color: var(--brand-accent); color: var(--brand-accent); }
.spt-group-tool.is-danger:hover { border-color: var(--color-danger, #dc2626); color: var(--color-danger, #dc2626); }
.spt-group-body { padding: 0; }

.spt-table { width: 100%; border-collapse: separate; border-spacing: 0; }
.spt-table thead th {
  padding: 12px 16px; font-size: 11.5px; font-weight: 500;
  color: var(--text-muted); text-align: left;
  border-bottom: 1px solid var(--border-color);
}
.spt-table tbody td {
  padding: 12px 16px; border-top: 1px solid var(--border-color);
  font-size: 14px; vertical-align: middle; color: var(--text-primary);
}
.spt-row.is-selected td { background: rgba(91, 141, 239, 0.06); }
.spt-row:hover td { background: var(--bg-surface, rgba(0, 0, 0, 0.02)); }
.spt-prompt-cell { max-width: 56rem; }
.spt-prompt-text {
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; line-height: 1.5;
}
.spt-id-pill {
  display: inline-flex; align-items: center; padding: 4px 12px;
  border-radius: 9999px; border: 1px solid var(--border-color);
  background: var(--bg-card); font-size: 12px;
  font-variant-numeric: tabular-nums; color: var(--text-secondary);
}
.spt-muted { color: var(--text-muted); font-size: 13px; }

.spt-status { display: inline-flex; align-items: center; padding: 3px 10px; border-radius: 9999px; font-size: 11.5px; font-weight: 500; }
.spt-status-untested { background: rgba(180, 83, 9, 0.10); color: var(--color-warning, #b45309); }
.spt-status-good { background: rgba(16, 185, 129, 0.12); color: var(--color-success, #059669); }
.spt-status-mid { background: rgba(91, 141, 239, 0.12); color: var(--brand-accent); }
.spt-status-low { background: rgba(220, 38, 38, 0.10); color: #b91c1c; }

.spt-action-btn {
  display: inline-flex; align-items: center; justify-content: center;
  height: 30px; padding: 0 14px;
  background: var(--brand-accent); color: #fff; border: 0;
  border-radius: 9999px;
  font-size: 13px; font-weight: 500; cursor: pointer;
  transition: filter 0.15s ease, opacity 0.15s ease;
}
.spt-action-btn:hover:not(:disabled) { filter: brightness(0.96); }
.spt-action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.spt-action-btn-ghost {
  background: transparent; color: var(--text-muted);
  margin-left: 4px; width: 28px; padding: 0;
  font-size: 18px; line-height: 1;
}
.spt-action-btn-ghost:hover { background: var(--bg-surface, rgba(0, 0, 0, 0.04)); color: var(--color-danger, #dc2626); }
.spt-spinner {
  width: 12px; height: 12px;
  border: 2px solid currentColor; border-right-color: transparent;
  border-radius: 50%; animation: spt-spin 0.7s linear infinite;
}
@keyframes spt-spin { to { transform: rotate(360deg); } }

.spt-state, .spt-empty-filter {
  padding: 28px 24px; text-align: center; font-size: 13px; color: var(--text-muted);
}
.spt-empty {
  display: flex; flex-direction: column; align-items: center;
  text-align: center; padding: 56px 24px; gap: 8px;
}
.spt-empty-icon {
  width: 64px; height: 64px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 9999px;
  background: var(--bg-surface, rgba(0, 0, 0, 0.04));
  color: var(--text-muted); margin-bottom: 6px;
}
.spt-empty-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.spt-empty-sub { font-size: 14px; color: var(--text-muted); max-width: 32rem; line-height: 1.55; margin: 0 0 12px; }

/* Sticky bulk-action bar */
.spt-bar {
  position: fixed; left: 50%; transform: translateX(-50%);
  bottom: 24px; z-index: 50;
  display: flex; align-items: center; gap: 16px;
  padding: 12px 18px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.14), 0 1px 2px rgba(15, 23, 42, 0.06);
}
.spt-bar-info { font-size: 13px; color: var(--text-secondary); }
.spt-bar-info strong { color: var(--text-primary); font-weight: 700; margin-right: 6px; }
.spt-bar-link { background: none; border: 0; color: var(--brand-accent); font-size: 12px; cursor: pointer; margin-left: 8px; }
.spt-bar-actions { display: inline-flex; gap: 8px; }
.spt-bar-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 14px;
  background: var(--bg-card); color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: 9999px;
  font-size: 13px; font-weight: 500; cursor: pointer;
}
.spt-bar-btn:hover:not(:disabled) { border-color: var(--brand-accent); color: var(--brand-accent); }
.spt-bar-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.spt-bar-btn.is-primary {
  background: var(--brand-accent); color: #fff; border-color: var(--brand-accent);
}
.spt-bar-btn.is-primary:hover { filter: brightness(0.96); color: #fff; }

.spt-add-wrap { position: relative; }
.spt-add-menu {
  position: absolute; bottom: calc(100% + 6px); right: 0;
  min-width: 220px;
  padding: 6px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
  display: flex; flex-direction: column;
  max-height: 260px; overflow-y: auto;
}
.spt-add-item {
  text-align: left; padding: 7px 10px;
  border: 0; background: transparent;
  font-size: 13px; color: var(--text-primary);
  cursor: pointer; border-radius: 8px;
}
.spt-add-item:hover { background: var(--bg-surface, rgba(15, 23, 42, 0.04)); }
.spt-add-item.is-primary { color: var(--brand-accent); font-weight: 600; }
.spt-add-divider { height: 1px; background: var(--border-color); margin: 4px 0; }
.spt-add-empty { padding: 8px 10px; font-size: 12px; color: var(--text-muted); }

.spt-bar-enter-active, .spt-bar-leave-active { transition: transform 0.18s ease, opacity 0.18s ease; }
.spt-bar-enter-from, .spt-bar-leave-to { transform: translate(-50%, 12px); opacity: 0; }
</style>
