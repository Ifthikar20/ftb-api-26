<script setup>
import { computed, ref } from 'vue'
import AirCard from '@/components/ui/AirCard.vue'
import AirChip from '@/components/ui/AirChip.vue'
import AirButton from '@/components/ui/AirButton.vue'
import EffectivenessMeter from './EffectivenessMeter.vue'
import VariableChip from './VariableChip.vue'

const props = defineProps({
  prompt: { type: Object, required: true },
  variables: { type: Object, default: () => ({}) },
  actionMode: { type: String, default: 'manage' }, // 'manage' | 'save'
  saved: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
})

const emit = defineEmits(['select', 'edit', 'smoke-test', 'disable', 'delete', 'preview', 'request-edit-variables', 'save', 'remove'])

const menuOpen = ref(false)

function closeMenu() { menuOpen.value = false }

const styleVariantMap = {
  story: 'primary',
  question: 'info',
  comparison: 'warning',
  local: 'success',
  how_to: 'neutral',
  listicle: 'neutral',
}

const styleLabel = computed(() => {
  const s = props.prompt.style || 'question'
  const map = {
    story: 'Story',
    question: 'Question',
    comparison: 'Comparison',
    local: 'Local',
    how_to: 'How-to',
    listicle: 'Listicle',
  }
  return map[s] || s
})

const styleVariant = computed(() => styleVariantMap[props.prompt.style] || 'neutral')

const score = computed(() => {
  const v = props.prompt.effectiveness_score
  return typeof v === 'number' ? v : 0
})
const components = computed(() => props.prompt.effectiveness_components || {})
const stable = computed(() => Boolean(components.value?.stable) || (props.prompt.runs_count || 0) >= 3)

// Body: walk template_text or text and split on {{ var }} placeholders.
const TEMPLATE_RE = /\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}/g
const segments = computed(() => {
  const body = (props.prompt.template_text || props.prompt.text || '').toString()
  if (!body) return [{ kind: 'text', value: '' }]
  const out = []
  let last = 0
  let m
  TEMPLATE_RE.lastIndex = 0
  while ((m = TEMPLATE_RE.exec(body)) !== null) {
    if (m.index > last) {
      out.push({ kind: 'text', value: body.slice(last, m.index) })
    }
    out.push({ kind: 'var', value: m[1] })
    last = m.index + m[0].length
  }
  if (last < body.length) out.push({ kind: 'text', value: body.slice(last) })
  return out
})

function variableValue(name) {
  return props.variables ? props.variables[name] ?? null : null
}

function relTime(iso) {
  if (!iso) return null
  try {
    const ms = Date.now() - new Date(iso).getTime()
    const d = Math.round(ms / 86400000)
    if (d <= 0) return 'today'
    if (d === 1) return 'yesterday'
    if (d < 30) return `${d}d ago`
    const mo = Math.round(d / 30)
    return `${mo}mo ago`
  } catch { return null }
}

const lastUsedLabel = computed(() => relTime(props.prompt.last_used_at))
const runsLabel = computed(() => {
  const r = props.prompt.runs_count || 0
  if (!r) return null
  const m = Math.round(r * (components.value?.visibility_hit_rate || 0))
  return `${m}/${r} runs`
})
</script>

<template>
  <AirCard interactive size="md" class="pc-card" @click="emit('select', prompt)">
    <div class="pc-top">
      <AirChip :variant="styleVariant" size="xs">{{ styleLabel }}</AirChip>
      <EffectivenessMeter
        :score="score"
        :stable="stable"
        :components="components"
        @click.stop
      />
    </div>

    <div class="pc-body">
      <template v-for="(seg, i) in segments" :key="i">
        <span v-if="seg.kind === 'text'">{{ seg.value }}</span>
        <VariableChip
          v-else
          :name="seg.value"
          :value="variableValue(seg.value)"
          @request-edit="(n) => emit('request-edit-variables', n)"
          @click.stop
        />
      </template>
    </div>

    <div class="pc-stats">
      <span v-if="lastUsedLabel">Last used {{ lastUsedLabel }}</span>
      <span v-if="lastUsedLabel && runsLabel"> · </span>
      <span v-if="runsLabel">{{ runsLabel }}</span>
      <span v-if="!lastUsedLabel && !runsLabel">No runs yet</span>
    </div>

    <div v-if="actionMode === 'save'" class="pc-actions" @click.stop>
      <AirChip v-if="saved" variant="success" size="sm">Saved</AirChip>
      <AirButton
        v-if="!saved"
        variant="primary"
        size="sm"
        :loading="saving"
        @click="emit('save', prompt)"
      >Save to my prompts</AirButton>
      <AirButton
        v-else
        variant="ghost"
        size="sm"
        @click="emit('remove', prompt)"
      >Remove</AirButton>
    </div>

    <div v-else class="pc-actions" @click.stop>
      <AirButton variant="ghost" size="sm" @click="emit('preview', prompt)">Preview filled</AirButton>
      <AirButton variant="ghost" size="sm" @click="emit('edit', prompt)">Edit</AirButton>
      <div class="pc-kebab-wrap">
        <button
          type="button"
          class="pc-kebab"
          aria-label="More actions"
          @click="menuOpen = !menuOpen"
        >&#x22EF;</button>
        <div v-if="menuOpen" class="pc-menu" @click.stop>
          <button type="button" class="pc-menu-item" @click="closeMenu(); emit('smoke-test', prompt)">Smoke test</button>
          <button type="button" class="pc-menu-item" @click="closeMenu(); emit('disable', prompt)">
            {{ prompt.is_active ? 'Disable' : 'Enable' }}
          </button>
          <button type="button" class="pc-menu-item pc-menu-danger" @click="closeMenu(); emit('delete', prompt)">Delete</button>
        </div>
      </div>
    </div>
  </AirCard>
</template>

<style scoped>
.pc-card { display: flex; flex-direction: column; gap: 12px; height: 100%; }
.pc-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.pc-body {
  font-size: 14px;
  line-height: 1.55;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  display: inline;
}
.pc-stats {
  font-size: 11px;
  color: var(--text-muted);
}
.pc-actions {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  position: relative;
}
.pc-kebab-wrap { margin-left: auto; position: relative; }
.pc-kebab {
  width: 28px;
  height: 28px;
  border-radius: 9999px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}
.pc-kebab:hover { background: var(--bg-card-hover); border-color: var(--border-color); }
.pc-menu {
  position: absolute;
  right: 0;
  top: 100%;
  margin-top: 4px;
  min-width: 140px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
  padding: 4px;
  z-index: 20;
}
.pc-menu-item {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 0;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--text-primary);
  border-radius: 6px;
  cursor: pointer;
}
.pc-menu-item:hover { background: var(--bg-card-hover); }
.pc-menu-danger { color: var(--color-danger, #dc2626); }
</style>
