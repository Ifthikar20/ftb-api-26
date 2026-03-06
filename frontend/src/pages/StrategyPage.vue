<template>
  <div class="strategy-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Strategy</h1>
        <p class="page-subtitle">AI-powered growth strategy and action plan.</p>
      </div>
      <button class="btn btn-primary btn-sm" @click="generate" :disabled="generating">{{ generating ? 'Generating...' : 'Generate Strategy' }}</button>
    </div>

    <div v-if="loading" class="loading-state">Loading strategy...</div>
    <template v-else>
      <!-- Strategy Summary -->
      <div class="card" style="margin-bottom:20px" v-if="strategy">
        <div class="card-header">
          <h3 class="card-title">Active Strategy</h3>
          <span class="badge badge-success">{{ strategy.plan_type }}-Day Plan</span>
        </div>
        <p class="text-sm" style="color:var(--text-secondary);line-height:1.7;margin-bottom:12px">{{ strategy.summary }}</p>
        <div class="progress-bar-wrap">
          <div class="progress-bar-fill" :style="{ width: strategy.completion_pct + '%' }"></div>
        </div>
        <div class="text-xs text-muted" style="margin-top:6px">{{ strategy.completion_pct }}% complete</div>
      </div>

      <!-- Actions -->
      <div class="card" style="margin-bottom:20px" v-if="actions.length">
        <div class="card-header">
          <h3 class="card-title">Action Plan</h3>
          <span class="text-sm text-muted">{{ doneCount }} of {{ actions.length }} done</span>
        </div>
        <div class="task-list">
          <div v-for="a in actions" :key="a.id" class="task-item" :class="{ done: a.status === 'done' }">
            <button class="task-toggle" @click="toggleAction(a)">{{ a.status === 'done' ? '\u25CF' : '\u25CB' }}</button>
            <div class="task-content">
              <div class="text-sm font-semibold" :class="{ 'text-muted': a.status === 'done' }">{{ a.title }}</div>
              <div class="text-xs text-muted">{{ a.description }}</div>
            </div>
            <span class="badge" :class="impactClass(a.estimated_impact)">{{ a.estimated_impact || 'medium' }}</span>
          </div>
        </div>
      </div>

      <!-- Content Calendar -->
      <div class="card" style="margin-bottom:20px" v-if="calendar.length">
        <div class="card-header"><h3 class="card-title">Content Calendar</h3></div>
        <table class="data-table">
          <thead><tr><th>Date</th><th>Title</th><th>Type</th><th>Status</th></tr></thead>
          <tbody>
            <tr v-for="entry in calendar" :key="entry.id || entry.title">
              <td class="text-sm">{{ formatDate(entry.scheduled_date) }}</td>
              <td class="font-semibold text-sm">{{ entry.title }}</td>
              <td><span class="badge badge-neutral">{{ entry.content_type }}</span></td>
              <td><span class="badge" :class="entry.status === 'published' ? 'badge-success' : 'badge-neutral'">{{ entry.status }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- AI Chat -->
      <div class="card">
        <div class="card-header"><h3 class="card-title">AI Strategy Assistant</h3></div>
        <div class="chat-container">
          <div v-for="msg in chatHistory" :key="msg.id" class="chat-msg" :class="msg.role">
            <div class="chat-bubble">{{ msg.content }}</div>
          </div>
        </div>
        <form @submit.prevent="sendChat" class="chat-input-wrap">
          <input v-model="chatInput" class="form-input" placeholder="Ask about your strategy..." style="flex:1" />
          <button type="submit" class="btn btn-primary btn-sm" :disabled="!chatInput.trim()">Send</button>
        </form>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import strategyApi from '@/api/strategy'

const route = useRoute()
const websiteId = route.params.websiteId

const loading = ref(true)
const generating = ref(false)
const strategy = ref(null)
const actions = ref([])
const calendar = ref([])
const chatHistory = ref([])
const chatInput = ref('')

const doneCount = computed(() => actions.value.filter(a => a.status === 'done').length)

function impactClass(impact) {
  const map = { high: 'badge-danger', medium: 'badge-warning', low: 'badge-neutral' }
  return map[impact] || 'badge-neutral'
}

function formatDate(d) {
  if (!d) return '--'
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

async function fetchData() {
  loading.value = true
  try {
    const [stratRes, actionsRes, calRes, chatRes] = await Promise.all([
      strategyApi.current(websiteId).catch(() => ({ data: null })),
      strategyApi.actions(websiteId).catch(() => ({ data: [] })),
      strategyApi.calendar(websiteId).catch(() => ({ data: [] })),
      strategyApi.chatHistory(websiteId).catch(() => ({ data: [] })),
    ])
    strategy.value = stratRes.data?.data || stratRes.data || null
    actions.value = actionsRes.data?.data || actionsRes.data || []
    calendar.value = calRes.data?.data || calRes.data || []
    chatHistory.value = chatRes.data?.data || chatRes.data || []
  } catch (e) {
    console.error('Strategy fetch error', e)
  } finally {
    loading.value = false
  }
}

async function toggleAction(action) {
  const newStatus = action.status === 'done' ? 'todo' : 'done'
  try {
    await strategyApi.updateAction(websiteId, action.id, { status: newStatus })
    action.status = newStatus
  } catch {}
}

async function generate() {
  generating.value = true
  try {
    await strategyApi.generate(websiteId)
    setTimeout(() => { fetchData(); generating.value = false }, 3000)
  } catch { generating.value = false }
}

async function sendChat() {
  if (!chatInput.value.trim()) return
  const msg = chatInput.value
  chatHistory.value.push({ role: 'user', content: msg })
  chatInput.value = ''
  try {
    const { data } = await strategyApi.chat(websiteId, { message: msg })
    const reply = data?.data || data
    chatHistory.value.push({ role: 'assistant', content: reply.content || reply.message || 'No response.' })
  } catch {
    chatHistory.value.push({ role: 'assistant', content: 'Sorry, something went wrong.' })
  }
}

onMounted(fetchData)
</script>

<style scoped>
.loading-state { text-align: center; padding: 80px 20px; font-size: var(--font-md); color: var(--text-muted); }

.progress-bar-wrap { width: 100%; height: 8px; background: var(--bg-input); border-radius: var(--radius-full); overflow: hidden; }
.progress-bar-fill { height: 100%; background: var(--color-success); border-radius: var(--radius-full); transition: width var(--transition-slow); }

.task-list { display: flex; flex-direction: column; }
.task-item { display: flex; align-items: flex-start; gap: 12px; padding: 14px 0; border-bottom: 1px solid var(--border-color); }
.task-item:last-child { border-bottom: none; }
.task-item.done .task-content .font-semibold { text-decoration: line-through; }
.task-content { flex: 1; }
.task-toggle { background: none; border: none; cursor: pointer; color: var(--color-success); font-size: 16px; padding: 0; }
.task-item:not(.done) .task-toggle { color: var(--text-muted); }

.chat-container { max-height: 300px; overflow-y: auto; padding: 12px 0; display: flex; flex-direction: column; gap: 10px; }
.chat-msg { display: flex; }
.chat-msg.user { justify-content: flex-end; }
.chat-bubble { max-width: 70%; padding: 10px 14px; border-radius: var(--radius-md); font-size: var(--font-sm); line-height: 1.5; }
.chat-msg.user .chat-bubble { background: var(--text-primary); color: var(--text-inverse); }
.chat-msg.assistant .chat-bubble { background: var(--bg-surface); color: var(--text-primary); }
.chat-input-wrap { display: flex; gap: 8px; margin-top: 12px; border-top: 1px solid var(--border-color); padding-top: 12px; }
</style>
