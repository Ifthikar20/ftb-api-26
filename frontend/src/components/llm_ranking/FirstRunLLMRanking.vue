<template>
  <div class="first-run">
    <header class="first-run-header">
      <h1>Run your first AI visibility audit</h1>
      <p class="sub">
        We'll ask Claude, GPT-4, Gemini, and Perplexity about your industry and see how
        often your business is mentioned.
      </p>
    </header>

    <section class="step-card">
      <div class="step-head">
        <span class="step-num">1</span>
        <h2>Business context</h2>
      </div>
      <div class="context-grid">
        <div>
          <div class="field-label">Business</div>
          <div class="field-value">{{ website?.name || '—' }}</div>
        </div>
        <div>
          <div class="field-label">Website</div>
          <div class="field-value">{{ website?.url || '—' }}</div>
        </div>
        <div>
          <div class="field-label">Industry</div>
          <div class="field-value">{{ website?.industry || 'Not set' }}</div>
        </div>
        <div v-if="website?.description">
          <div class="field-label">Description</div>
          <div class="field-value">{{ website.description }}</div>
        </div>
      </div>
      <router-link
        v-if="website?.id"
        :to="`/onboarding/${website.id}`"
        class="edit-link"
      >Edit business info</router-link>
    </section>

    <section class="step-card">
      <div class="step-head">
        <span class="step-num">2</span>
        <h2>Prompts we'll ask</h2>
      </div>
      <div v-if="loadingPrompts" class="muted">Loading suggested prompts…</div>
      <div v-else-if="prompts.length === 0" class="muted">
        No prompts yet. Set an industry on your website first.
      </div>
      <ul v-else class="prompt-list">
        <li v-for="(p, i) in prompts" :key="i" class="prompt-item">
          <span class="prompt-text">{{ p }}</span>
          <button type="button" class="prompt-remove" @click="removePrompt(i)" title="Remove">×</button>
        </li>
      </ul>
      <div class="add-prompt">
        <input
          v-model="newPrompt"
          type="text"
          placeholder="Add your own prompt (optional)"
          @keyup.enter="addPrompt"
          class="prompt-input"
        />
        <button type="button" class="prompt-add-btn" @click="addPrompt" :disabled="!newPrompt.trim()">Add</button>
      </div>
    </section>

    <section class="step-card">
      <div class="step-head">
        <span class="step-num">3</span>
        <h2>Which AIs should we ask?</h2>
      </div>
      <div class="provider-grid">
        <label v-for="p in PROVIDERS" :key="p.value" class="provider-option">
          <input type="checkbox" :value="p.value" v-model="selectedProviders" />
          <span class="provider-name">{{ p.label }}</span>
          <span class="provider-hint">~{{ p.cost }} · {{ p.latency }}</span>
        </label>
      </div>
      <div class="estimate">
        <strong>{{ estimatedQueries }}</strong> total queries · estimated ~{{ estimatedDuration }}
      </div>
    </section>

    <div v-if="error" class="error-banner">{{ error }}</div>

    <div class="actions">
      <button
        type="button"
        class="run-btn"
        :disabled="!canRun || running"
        @click="runAudit"
      >
        <span v-if="running">Starting…</span>
        <span v-else>Run my first audit</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import llmRankingApi from '@/api/llm_ranking'

const props = defineProps({
  website: { type: Object, required: true },
})
const emit = defineEmits(['audit-started'])

const PROVIDERS = [
  { value: 'claude', label: 'Claude (Anthropic)', cost: '$0.02/prompt', latency: '3s' },
  { value: 'gpt4', label: 'GPT-4 (OpenAI)', cost: '$0.03/prompt', latency: '4s' },
  { value: 'gemini', label: 'Gemini (Google)', cost: '$0.01/prompt', latency: '2s' },
  { value: 'perplexity', label: 'Perplexity', cost: '$0.02/prompt', latency: '3s' },
]

const prompts = ref([])
const newPrompt = ref('')
const loadingPrompts = ref(true)
const selectedProviders = ref(['claude', 'gpt4', 'gemini', 'perplexity'])
const running = ref(false)
const error = ref('')

const estimatedQueries = computed(() => prompts.value.length * selectedProviders.value.length)
const estimatedDuration = computed(() => {
  const seconds = Math.max(estimatedQueries.value * 3, 10)
  if (seconds < 60) return `${seconds}s`
  return `${Math.ceil(seconds / 60)}m`
})
const canRun = computed(() =>
  prompts.value.length > 0 &&
  selectedProviders.value.length > 0 &&
  !!props.website?.id
)

onMounted(loadPrompts)

async function loadPrompts() {
  if (!props.website?.id) {
    loadingPrompts.value = false
    return
  }
  try {
    const res = await llmRankingApi.previewPrompts(props.website.id)
    const data = res.data?.data || res.data
    prompts.value = data?.prompts || []
  } catch (e) {
    error.value = 'Could not load suggested prompts. You can add your own below.'
  } finally {
    loadingPrompts.value = false
  }
}

function removePrompt(i) {
  prompts.value.splice(i, 1)
}

function addPrompt() {
  const text = newPrompt.value.trim()
  if (!text) return
  if (prompts.value.length >= 10) {
    error.value = 'Maximum 10 prompts per audit.'
    return
  }
  prompts.value.push(text)
  newPrompt.value = ''
}

async function runAudit() {
  error.value = ''
  running.value = true
  try {
    const res = await llmRankingApi.runAudit(props.website.id, {
      custom_prompts: prompts.value,
      providers: selectedProviders.value,
    })
    const data = res.data?.data || res.data
    emit('audit-started', data)
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.response?.data?.error || 'Something went wrong.'
  } finally {
    running.value = false
  }
}
</script>

<style scoped>
.first-run {
  max-width: 780px;
  margin: 0 auto;
  padding: 32px 20px;
}

.first-run-header {
  text-align: center;
  margin-bottom: 32px;
}

.first-run-header h1 {
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0 0 10px;
}

.sub {
  color: var(--text-muted);
  margin: 0;
}

.step-card {
  background: var(--bg-surface, #15181f);
  border: 1px solid var(--border-subtle, #2a2f3a);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 16px;
}

.step-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.step-num {
  display: inline-flex;
  width: 28px;
  height: 28px;
  align-items: center;
  justify-content: center;
  background: var(--color-primary, #6366f1);
  color: white;
  border-radius: 50%;
  font-size: 0.85rem;
  font-weight: 700;
}

.step-head h2 {
  margin: 0;
  font-size: 1.15rem;
  color: var(--text-primary);
}

.context-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 12px;
}

.field-label {
  font-size: 0.78rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 4px;
}

.field-value {
  color: var(--text-primary);
  font-size: 0.95rem;
}

.edit-link {
  font-size: 0.85rem;
  color: var(--color-primary, #6366f1);
  text-decoration: underline;
}

.prompt-list {
  list-style: none;
  padding: 0;
  margin: 0 0 12px;
}

.prompt-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  margin-bottom: 6px;
  background: var(--bg-primary, #0b0d12);
  border: 1px solid var(--border-subtle, #2a2f3a);
  border-radius: 8px;
  gap: 12px;
}

.prompt-text {
  color: var(--text-primary);
  font-size: 0.92rem;
  flex: 1;
}

.prompt-remove {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0 6px;
}

.prompt-remove:hover { color: var(--color-danger, #ef4444); }

.add-prompt { display: flex; gap: 8px; }

.prompt-input {
  flex: 1;
  padding: 8px 12px;
  background: var(--bg-primary, #0b0d12);
  border: 1px solid var(--border-subtle, #2a2f3a);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 0.92rem;
}

.prompt-add-btn {
  padding: 8px 14px;
  background: var(--bg-primary, #0b0d12);
  border: 1px solid var(--border-subtle, #2a2f3a);
  border-radius: 8px;
  color: var(--text-primary);
  font-weight: 600;
  cursor: pointer;
}

.prompt-add-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.provider-option {
  display: flex;
  flex-direction: column;
  padding: 10px 12px;
  background: var(--bg-primary, #0b0d12);
  border: 1px solid var(--border-subtle, #2a2f3a);
  border-radius: 8px;
  cursor: pointer;
}

.provider-option input[type="checkbox"] { margin-right: 6px; }

.provider-name {
  display: inline;
  color: var(--text-primary);
  font-weight: 600;
  font-size: 0.9rem;
}

.provider-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 4px;
}

.estimate {
  font-size: 0.88rem;
  color: var(--text-muted);
}

.error-banner {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.4);
  color: var(--color-danger, #ef4444);
  padding: 10px 14px;
  border-radius: 8px;
  margin: 16px 0;
  font-size: 0.9rem;
}

.muted { color: var(--text-muted); font-size: 0.9rem; }

.actions {
  text-align: center;
  margin-top: 24px;
}

.run-btn {
  padding: 14px 32px;
  background: var(--color-primary, #6366f1);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
}

.run-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
