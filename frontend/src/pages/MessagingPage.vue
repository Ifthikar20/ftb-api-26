<template>
  <div class="msg-page">
    <!-- ── Header ── -->
    <div class="msg-header">
      <div class="msg-header-left">
        <h1>Messaging</h1>
        <span class="msg-header-count">{{ conversations.length }} conversations</span>
      </div>
      <div class="msg-header-actions">
        <button class="msg-btn msg-btn-outline" @click="seedDemo" :disabled="seeding">
          {{ seeding ? 'Loading...' : 'Load Demo Data' }}
        </button>
      </div>
    </div>

    <!-- ── 3-Panel Layout ── -->
    <div class="msg-layout">

      <!-- ── Left: Conversation List ── -->
      <div class="msg-sidebar">
        <div class="msg-search">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          <input v-model="searchQuery" placeholder="Search conversations..." />
        </div>

        <div class="msg-filters">
          <button v-for="f in statusFilters" :key="f.key"
            :class="['msg-filter-btn', { active: activeFilter === f.key }]"
            @click="activeFilter = f.key">
            {{ f.label }}
            <span class="msg-filter-count">{{ f.count }}</span>
          </button>
        </div>

        <div class="msg-conv-list">
          <div v-for="conv in filteredConversations" :key="conv.id"
            :class="['msg-conv-item', { active: activeConversation?.id === conv.id }]"
            @click="selectConversation(conv)">
            <div class="msg-conv-avatar">
              {{ getInitials(conv.contact_name) }}
              <span class="msg-channel-dot" :class="conv.channel_type"></span>
            </div>
            <div class="msg-conv-info">
              <div class="msg-conv-row">
                <span class="msg-conv-name">{{ conv.contact_name || 'Unknown' }}</span>
                <span class="msg-conv-time">{{ formatTime(conv.last_message_at) }}</span>
              </div>
              <div class="msg-conv-preview">{{ conv.last_message_preview || 'No messages yet' }}</div>
            </div>
            <div v-if="conv.unread_count" class="msg-unread-badge">{{ conv.unread_count }}</div>
          </div>

          <div v-if="!filteredConversations.length" class="msg-empty-state">
            <p>No conversations found</p>
          </div>
        </div>
      </div>

      <!-- ── Center: Chat View ── -->
      <div class="msg-chat" v-if="activeConversation">
        <div class="msg-chat-header">
          <div class="msg-chat-header-left">
            <div class="msg-chat-avatar">{{ getInitials(activeConversation.contact?.name) }}</div>
            <div>
              <div class="msg-chat-name">{{ activeConversation.contact?.name || 'Unknown' }}</div>
              <div class="msg-chat-channel">
                <span class="msg-channel-icon" :class="activeConversation.channel?.channel_type">●</span>
                {{ activeConversation.channel?.channel_type_display || 'Web Chat' }}
                <span v-if="activeConversation.ai_enabled" class="msg-ai-badge">AI ON</span>
                <span v-else class="msg-ai-badge off">AI OFF</span>
              </div>
            </div>
          </div>
          <div class="msg-chat-header-right">
            <button class="msg-icon-btn" @click="toggleAI" :title="activeConversation.ai_enabled ? 'Disable AI' : 'Enable AI'">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="m2 14 6-6 6 6"/></svg>
              {{ activeConversation.ai_enabled ? 'AI ✓' : 'AI ✗' }}
            </button>
            <button class="msg-icon-btn" @click="generateAIReply" :disabled="aiGenerating">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m5 12 7-7 7 7"/><path d="M12 19V5"/></svg>
              {{ aiGenerating ? 'Thinking...' : 'AI Reply' }}
            </button>
          </div>
        </div>

        <div class="msg-messages" ref="messagesContainer">
          <div v-for="msg in activeConversation.messages" :key="msg.id"
            :class="['msg-bubble-row', msg.direction]">
            <div :class="['msg-bubble', msg.direction, msg.sent_by]"
                 @click="msg.ai_audit && selectAuditMessage(msg)">
              <div class="msg-bubble-content">{{ msg.content }}</div>
              <div class="msg-bubble-meta">
                <span v-if="msg.sent_by === 'ai'" class="msg-bubble-ai">⚡ AI</span>
                <span v-if="msg.ai_audit" class="msg-bubble-audit-hint">📋</span>
                <span>{{ formatTime(msg.created_at) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="msg-input-bar">
          <input v-model="messageText" placeholder="Type a message..."
            @keydown.enter.prevent="sendMessage" class="msg-input" />
          <button class="msg-send-btn" @click="sendMessage" :disabled="!messageText.trim()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/></svg>
          </button>
        </div>
      </div>

      <div class="msg-chat msg-no-chat" v-else>
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <h3>Select a conversation</h3>
        <p>Choose from the list or start a new chat</p>
      </div>

      <!-- ── Right: Tabbed Panel ── -->
      <div class="msg-right-panel" v-if="activeConversation">
        <div class="msg-panel-tabs">
          <button v-for="tab in panelTabs" :key="tab.key"
            :class="['msg-panel-tab', { active: activePanel === tab.key }]"
            @click="activePanel = tab.key">
            {{ tab.label }}
          </button>
        </div>

        <!-- ── Tab: Contact ── -->
        <div v-if="activePanel === 'contact'" class="msg-panel-content">
          <div class="msg-contact-header">
            <div class="msg-contact-big-avatar">{{ getInitials(activeConversation.contact?.name) }}</div>
            <h3>{{ activeConversation.contact?.name }}</h3>
            <p>{{ activeConversation.contact?.email }}</p>
          </div>

          <div class="msg-contact-section">
            <h4>Lead Score</h4>
            <div class="msg-lead-score">
              <div class="msg-score-bar">
                <div class="msg-score-fill" :style="{ width: (activeConversation.contact?.lead_score || 0) + '%' }"></div>
              </div>
              <span class="msg-score-value">{{ activeConversation.contact?.lead_score || 0 }}/100</span>
            </div>
          </div>

          <div class="msg-contact-section" v-if="activeConversation.contact?.tags?.length">
            <h4>Tags</h4>
            <div class="msg-tags">
              <span v-for="tag in activeConversation.contact.tags" :key="tag" class="msg-tag">{{ tag }}</span>
            </div>
          </div>

          <div class="msg-contact-section" v-if="activeConversation.contact?.ai_summary">
            <h4>AI Summary</h4>
            <p class="msg-ai-summary">{{ activeConversation.contact.ai_summary }}</p>
          </div>

          <div class="msg-contact-section">
            <h4>Details</h4>
            <div class="msg-detail-row">
              <span>Channel</span>
              <span>{{ activeConversation.channel?.channel_type_display }}</span>
            </div>
            <div class="msg-detail-row">
              <span>Status</span>
              <span class="msg-status-pill" :class="activeConversation.status">{{ activeConversation.status }}</span>
            </div>
            <div class="msg-detail-row">
              <span>AI Agent</span>
              <span>{{ activeConversation.ai_enabled ? 'Active' : 'Disabled' }}</span>
            </div>
          </div>
        </div>

        <!-- ── Tab: Agent ── -->
        <div v-if="activePanel === 'agent'" class="msg-panel-content">
          <!-- Tone Selector -->
          <div class="msg-agent-section">
            <h4>Active Tone</h4>
            <div class="msg-tone-grid">
              <button v-for="t in availableTones" :key="t.key"
                :class="['msg-tone-btn', { active: activeTone === t.key }]"
                @click="setTone(t.key)">
                <span class="msg-tone-icon">{{ toneIcons[t.key] }}</span>
                {{ t.label }}
              </button>
            </div>
          </div>

          <!-- Training Docs -->
          <div class="msg-agent-section">
            <div class="msg-section-header">
              <h4>Training Documents</h4>
              <button class="msg-link-btn" @click="showDocEditor = true; editingDoc = null; docForm = { title: '', doc_type: 'custom', content: '' }">
                + New
              </button>
            </div>

            <div v-if="trainingDocs.length === 0" class="msg-empty-docs">
              <p>No training docs yet. Add docs or use a template to train your agent.</p>
            </div>

            <div v-for="doc in trainingDocs" :key="doc.id" class="msg-doc-card">
              <div class="msg-doc-header">
                <div class="msg-doc-info">
                  <span class="msg-doc-type-badge" :class="doc.doc_type">{{ doc.doc_type_display }}</span>
                  <span class="msg-doc-title">{{ doc.title }}</span>
                </div>
                <div class="msg-doc-actions">
                  <label class="msg-toggle-switch">
                    <input type="checkbox" :checked="doc.is_active" @change="toggleDocActive(doc)">
                    <span class="msg-toggle-slider"></span>
                  </label>
                </div>
              </div>
              <div class="msg-doc-footer">
                <button class="msg-link-btn" @click="openDocEditor(doc)">Edit</button>
                <button class="msg-link-btn danger" @click="deleteDoc(doc)">Delete</button>
              </div>
            </div>
          </div>

          <!-- Templates -->
          <div class="msg-agent-section">
            <h4>Starter Templates</h4>
            <div v-for="tpl in templates" :key="tpl.slug" class="msg-template-card">
              <div class="msg-template-info">
                <div class="msg-template-title">{{ tpl.title }}</div>
                <div class="msg-template-desc">{{ tpl.description }}</div>
              </div>
              <button class="msg-btn-sm" @click="applyTemplate(tpl.slug)" :disabled="applyingTemplate === tpl.slug">
                {{ applyingTemplate === tpl.slug ? '...' : 'Use' }}
              </button>
            </div>
          </div>
        </div>

        <!-- ── Tab: Audit ── -->
        <div v-if="activePanel === 'audit'" class="msg-panel-content">
          <div v-if="!auditMessage" class="msg-audit-empty">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            <p>Click any <strong>⚡ AI</strong> message to inspect its audit trail.</p>
          </div>

          <div v-else class="msg-audit-detail">
            <h4>AI Reply Audit</h4>

            <div class="msg-audit-preview">
              "{{ auditMessage.content.substring(0, 120) }}{{ auditMessage.content.length > 120 ? '...' : '' }}"
            </div>

            <div class="msg-audit-field">
              <span class="msg-audit-label">Tone Used</span>
              <span class="msg-audit-value tone-badge" :class="auditMessage.ai_audit?.tone">
                {{ toneIcons[auditMessage.ai_audit?.tone] }} {{ auditMessage.ai_audit?.tone }}
              </span>
            </div>

            <div class="msg-audit-field">
              <span class="msg-audit-label">Model</span>
              <span class="msg-audit-value mono">{{ auditMessage.ai_audit?.model }}</span>
            </div>

            <div class="msg-audit-field">
              <span class="msg-audit-label">Input Tokens</span>
              <span class="msg-audit-value">{{ (auditMessage.ai_audit?.input_tokens || 0).toLocaleString() }}</span>
            </div>

            <div class="msg-audit-field">
              <span class="msg-audit-label">Output Tokens</span>
              <span class="msg-audit-value">{{ (auditMessage.ai_audit?.output_tokens || 0).toLocaleString() }}</span>
            </div>

            <div class="msg-audit-field">
              <span class="msg-audit-label">Est. Cost</span>
              <span class="msg-audit-value cost">${{ auditMessage.ai_audit?.estimated_cost_usd?.toFixed(4) || '0.0000' }}</span>
            </div>

            <div class="msg-audit-docs" v-if="auditMessage.ai_audit?.training_docs?.length">
              <span class="msg-audit-label">Active Docs</span>
              <div class="msg-audit-doc-list">
                <span v-for="docTitle in auditMessage.ai_audit.training_docs" :key="docTitle" class="msg-audit-doc-tag">
                  📄 {{ docTitle }}
                </span>
              </div>
            </div>

            <div class="msg-audit-field" v-if="!auditMessage.ai_audit?.training_docs?.length">
              <span class="msg-audit-label">Active Docs</span>
              <span class="msg-audit-value" style="color: #94a3b8;">None (used legacy config)</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Doc Editor Modal ── -->
    <div v-if="showDocEditor" class="msg-modal-overlay" @click.self="showDocEditor = false">
      <div class="msg-modal">
        <div class="msg-modal-header">
          <h3>{{ editingDoc ? 'Edit Training Doc' : 'New Training Doc' }}</h3>
          <button class="msg-modal-close" @click="showDocEditor = false">✕</button>
        </div>
        <div class="msg-modal-body">
          <div class="form-group">
            <label class="form-label">Title</label>
            <input v-model="docForm.title" class="form-input" placeholder="e.g. Product Catalog" />
          </div>
          <div class="form-group" style="margin-top: 12px">
            <label class="form-label">Type</label>
            <select v-model="docForm.doc_type" class="form-input">
              <option value="persona">Persona & Tone</option>
              <option value="product">Product Knowledge</option>
              <option value="rules">Rules & Objections</option>
              <option value="script">Sales Script</option>
              <option value="faq">FAQ</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          <div class="form-group" style="margin-top: 12px">
            <label class="form-label">Content (Markdown)</label>
            <textarea v-model="docForm.content" class="form-input msg-doc-textarea" rows="14"
              placeholder="# My Training Doc&#10;&#10;Write markdown here..."></textarea>
          </div>
        </div>
        <div class="msg-modal-footer">
          <button class="msg-btn msg-btn-outline" @click="showDocEditor = false">Cancel</button>
          <button class="msg-btn msg-btn-primary" @click="saveDoc" :disabled="savingDoc">
            {{ savingDoc ? 'Saving...' : 'Save Document' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import messagingApi from '@/api/messaging'

const route = useRoute()
const websiteId = computed(() => route.params.websiteId)

// ── Conversation state ──
const conversations = ref([])
const activeConversation = ref(null)
const searchQuery = ref('')
const activeFilter = ref('all')
const messageText = ref('')
const seeding = ref(false)
const aiGenerating = ref(false)
const messagesContainer = ref(null)

// ── Right panel state ──
const activePanel = ref('contact')
const panelTabs = [
  { key: 'contact', label: 'Contact' },
  { key: 'agent', label: 'Agent' },
  { key: 'audit', label: 'Audit' },
]

// ── Agent state ──
const trainingDocs = ref([])
const templates = ref([])
const activeTone = ref('professional')
const availableTones = ref([])
const applyingTemplate = ref(null)

const toneIcons = {
  professional: '💼', friendly: '😊', casual: '🤙',
  assertive: '🎯', bargaining: '🤝', empathetic: '💚',
}

// ── Doc editor state ──
const showDocEditor = ref(false)
const editingDoc = ref(null)
const docForm = ref({ title: '', doc_type: 'custom', content: '' })
const savingDoc = ref(false)

// ── Audit state ──
const auditMessage = ref(null)

const statusFilters = computed(() => [
  { key: 'all', label: 'All', count: conversations.value.length },
  { key: 'open', label: 'Open', count: conversations.value.filter(c => c.status === 'open').length },
  { key: 'snoozed', label: 'Snoozed', count: conversations.value.filter(c => c.status === 'snoozed').length },
  { key: 'closed', label: 'Closed', count: conversations.value.filter(c => c.status === 'closed').length },
])

const filteredConversations = computed(() => {
  let list = conversations.value
  if (activeFilter.value !== 'all') list = list.filter(c => c.status === activeFilter.value)
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(c => (c.contact_name || '').toLowerCase().includes(q) || (c.last_message_preview || '').toLowerCase().includes(q))
  }
  return list
})

// ── Helpers ──
function getInitials(name) {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase()
}

function formatTime(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return 'now'
  if (diff < 3600000) return Math.floor(diff / 60000) + 'm'
  if (diff < 86400000) return Math.floor(diff / 3600000) + 'h'
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function unwrap(res) {
  // Handle the envelope: { success, data } or { data: { results } }
  const d = res?.data?.data ?? res?.data ?? res
  return d
}

// ── Conversation APIs ──
async function loadConversations() {
  try {
    const res = await messagingApi.listConversations(websiteId.value)
    const d = unwrap(res)
    conversations.value = d.results || d || []
  } catch (e) { console.error('Failed to load conversations', e) }
}

async function selectConversation(conv) {
  try {
    const res = await messagingApi.getConversation(websiteId.value, conv.id)
    activeConversation.value = unwrap(res)
    conv.unread_count = 0
    auditMessage.value = null
    await nextTick()
    scrollToBottom()
  } catch (e) { console.error('Failed to load conversation', e) }
}

async function sendMessage() {
  if (!messageText.value.trim() || !activeConversation.value) return
  try {
    const res = await messagingApi.sendMessage(websiteId.value, activeConversation.value.id, { content: messageText.value })
    const msg = unwrap(res)
    activeConversation.value.messages.push(msg)
    messageText.value = ''
    updateSidebarConversation(activeConversation.value.id, msg.content, msg.created_at)
    scrollToBottom()
  } catch (e) { console.error('Failed to send message', e) }
}

async function generateAIReply() {
  if (!activeConversation.value) return
  aiGenerating.value = true
  try {
    const res = await messagingApi.generateAIReply(websiteId.value, activeConversation.value.id)
    const msg = unwrap(res)
    activeConversation.value.messages.push(msg)
    updateSidebarConversation(activeConversation.value.id, msg.content, msg.created_at)
    scrollToBottom()
  } catch (e) { console.error('AI reply failed', e) }
  finally { aiGenerating.value = false }
}

async function toggleAI() {
  if (!activeConversation.value) return
  const newVal = !activeConversation.value.ai_enabled
  activeConversation.value.ai_enabled = newVal
  try {
    await messagingApi.updateConversation(websiteId.value, activeConversation.value.id, { ai_enabled: newVal })
  } catch (e) {
    console.error('Failed to toggle AI', e)
    activeConversation.value.ai_enabled = !newVal
  }
}

async function seedDemo() {
  seeding.value = true
  try {
    await messagingApi.seedDemo(websiteId.value)
    await loadConversations()
    if (conversations.value.length && !activeConversation.value) {
      await selectConversation(conversations.value[0])
    }
  } catch (e) { console.error('Seed failed', e) }
  finally { seeding.value = false }
}

function updateSidebarConversation(convId, preview, timestamp) {
  const conv = conversations.value.find(c => c.id === convId)
  if (conv) {
    conv.last_message_preview = (preview || '').slice(0, 200)
    conv.last_message_at = timestamp || new Date().toISOString()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// ── Agent APIs ──
async function loadAgentData() {
  if (!websiteId.value) return
  try {
    const [docsRes, toneRes, tplRes] = await Promise.all([
      messagingApi.listTrainingDocs(websiteId.value),
      messagingApi.getTone(websiteId.value),
      messagingApi.listTemplates(websiteId.value),
    ])
    const docs = unwrap(docsRes)
    trainingDocs.value = docs.results || docs || []
    const tone = unwrap(toneRes)
    activeTone.value = tone.tone || 'professional'
    availableTones.value = tone.available_tones || [
      { key: 'professional', label: 'Professional' },
      { key: 'friendly', label: 'Friendly' },
      { key: 'casual', label: 'Casual' },
      { key: 'assertive', label: 'Assertive' },
      { key: 'bargaining', label: 'Bargaining' },
      { key: 'empathetic', label: 'Empathetic' },
    ]
    templates.value = unwrap(tplRes) || []
  } catch (e) { console.error('Failed to load agent data', e) }
}

async function setTone(tone) {
  const prev = activeTone.value
  activeTone.value = tone
  try {
    await messagingApi.setTone(websiteId.value, tone)
  } catch (e) {
    console.error('Failed to set tone', e)
    activeTone.value = prev
  }
}

async function toggleDocActive(doc) {
  const newVal = !doc.is_active
  doc.is_active = newVal
  try {
    await messagingApi.updateTrainingDoc(websiteId.value, doc.id, { ...doc, is_active: newVal })
  } catch (e) {
    console.error('Failed to toggle doc', e)
    doc.is_active = !newVal
  }
}

function openDocEditor(doc) {
  editingDoc.value = doc
  docForm.value = { title: doc.title, doc_type: doc.doc_type, content: doc.content }
  showDocEditor.value = true
}

async function saveDoc() {
  if (!docForm.value.title || !docForm.value.content) return
  savingDoc.value = true
  try {
    if (editingDoc.value) {
      const res = await messagingApi.updateTrainingDoc(websiteId.value, editingDoc.value.id, docForm.value)
      const updated = unwrap(res)
      const idx = trainingDocs.value.findIndex(d => d.id === editingDoc.value.id)
      if (idx >= 0) trainingDocs.value[idx] = updated
    } else {
      const res = await messagingApi.createTrainingDoc(websiteId.value, docForm.value)
      trainingDocs.value.push(unwrap(res))
    }
    showDocEditor.value = false
  } catch (e) { console.error('Failed to save doc', e) }
  finally { savingDoc.value = false }
}

async function deleteDoc(doc) {
  if (!confirm(`Delete "${doc.title}"?`)) return
  try {
    await messagingApi.deleteTrainingDoc(websiteId.value, doc.id)
    trainingDocs.value = trainingDocs.value.filter(d => d.id !== doc.id)
  } catch (e) { console.error('Failed to delete doc', e) }
}

async function applyTemplate(slug) {
  applyingTemplate.value = slug
  try {
    const res = await messagingApi.applyTemplate(websiteId.value, slug)
    const doc = unwrap(res)
    const idx = trainingDocs.value.findIndex(d => d.title === doc.title)
    if (idx >= 0) trainingDocs.value[idx] = doc
    else trainingDocs.value.push(doc)
  } catch (e) { console.error('Failed to apply template', e) }
  finally { applyingTemplate.value = null }
}

// ── Audit ──
function selectAuditMessage(msg) {
  auditMessage.value = msg
  activePanel.value = 'audit'
}

// ── Watchers ──
watch(websiteId, () => {
  if (websiteId.value) {
    loadConversations()
    loadAgentData()
  }
}, { immediate: true })
</script>

<style scoped>
.msg-page { padding: 0; height: calc(100vh - 64px); display: flex; flex-direction: column; background: #f8fafc; }

/* ── Header ── */
.msg-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; border-bottom: 1px solid #e2e8f0; background: white; }
.msg-header h1 { font-size: 22px; font-weight: 700; margin: 0; color: #0f172a; }
.msg-header-count { font-size: 13px; color: #94a3b8; margin-left: 12px; }
.msg-header-left { display: flex; align-items: center; }
.msg-header-actions { display: flex; gap: 8px; }

/* ── Buttons ── */
.msg-btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; border: none; transition: all 0.15s; }
.msg-btn-primary { background: #6366f1; color: white; }
.msg-btn-primary:hover { background: #4f46e5; }
.msg-btn-outline { background: white; color: #475569; border: 1px solid #e2e8f0; }
.msg-btn-outline:hover { background: #f1f5f9; }
.msg-btn-sm { padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; border: 1px solid #e2e8f0; background: white; color: #6366f1; transition: all 0.15s; }
.msg-btn-sm:hover { background: #eef2ff; }
.msg-btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── 3-Panel Layout ── */
.msg-layout { display: grid; grid-template-columns: 320px 1fr 320px; flex: 1; overflow: hidden; }

/* ── Left Sidebar ── */
.msg-sidebar { border-right: 1px solid #e2e8f0; background: white; display: flex; flex-direction: column; overflow-y: auto; }
.msg-search { display: flex; align-items: center; gap: 8px; padding: 12px 16px; border-bottom: 1px solid #f1f5f9; }
.msg-search svg { color: #94a3b8; flex-shrink: 0; }
.msg-search input { border: none; outline: none; font-size: 14px; width: 100%; background: transparent; color: #1e293b; }

.msg-filters { display: flex; gap: 4px; padding: 8px 12px; border-bottom: 1px solid #f1f5f9; }
.msg-filter-btn { background: none; border: none; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 500; color: #64748b; cursor: pointer; display: flex; align-items: center; gap: 4px; }
.msg-filter-btn.active { background: #6366f1; color: white; }
.msg-filter-btn:hover:not(.active) { background: #f1f5f9; }
.msg-filter-count { font-size: 10px; background: rgba(0,0,0,0.08); padding: 1px 5px; border-radius: 10px; }
.msg-filter-btn.active .msg-filter-count { background: rgba(255,255,255,0.2); }

/* ── Conversation List Items ── */
.msg-conv-list { flex: 1; overflow-y: auto; }
.msg-conv-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; cursor: pointer; border-bottom: 1px solid #f8fafc; transition: background 0.1s; position: relative; }
.msg-conv-item:hover { background: #f8fafc; }
.msg-conv-item.active { background: #eef2ff; border-left: 3px solid #6366f1; }

.msg-conv-avatar { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #6366f1, #8b5cf6); display: flex; align-items: center; justify-content: center; color: white; font-size: 13px; font-weight: 700; flex-shrink: 0; position: relative; }
.msg-channel-dot { position: absolute; bottom: -1px; right: -1px; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; }
.msg-channel-dot.webchat { background: #10b981; }
.msg-channel-dot.instagram { background: #e1306c; }
.msg-channel-dot.whatsapp { background: #25d366; }
.msg-channel-dot.messenger { background: #0084ff; }

.msg-conv-info { flex: 1; min-width: 0; }
.msg-conv-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px; }
.msg-conv-name { font-size: 14px; font-weight: 600; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.msg-conv-time { font-size: 11px; color: #94a3b8; flex-shrink: 0; }
.msg-conv-preview { font-size: 13px; color: #64748b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.msg-unread-badge { background: #6366f1; color: white; font-size: 10px; font-weight: 700; width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; position: absolute; right: 16px; top: 50%; transform: translateY(-50%); }

/* ── Empty State ── */
.msg-empty-state { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; padding: 32px; }
.msg-empty-state p { color: #94a3b8; font-size: 14px; margin: 0; }

/* ── Chat Panel ── */
.msg-chat { display: flex; flex-direction: column; background: #f8fafc; overflow: hidden; }
.msg-no-chat { align-items: center; justify-content: center; gap: 8px; }
.msg-no-chat h3 { color: #64748b; font-weight: 600; margin: 0; }
.msg-no-chat p { color: #94a3b8; font-size: 14px; margin: 0; }

.msg-chat-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; background: white; border-bottom: 1px solid #e2e8f0; }
.msg-chat-header-left { display: flex; align-items: center; gap: 12px; }
.msg-chat-avatar { width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, #6366f1, #8b5cf6); display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: 700; }
.msg-chat-name { font-size: 15px; font-weight: 600; color: #1e293b; }
.msg-chat-channel { font-size: 12px; color: #94a3b8; display: flex; align-items: center; gap: 6px; }
.msg-channel-icon.webchat { color: #10b981; }
.msg-channel-icon.instagram { color: #e1306c; }
.msg-channel-icon.whatsapp { color: #25d366; }
.msg-channel-icon.messenger { color: #0084ff; }
.msg-ai-badge { font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: #dcfce7; color: #16a34a; }
.msg-ai-badge.off { background: #fef2f2; color: #dc2626; }

.msg-chat-header-right { display: flex; gap: 8px; }
.msg-icon-btn { display: inline-flex; align-items: center; gap: 4px; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; border: 1px solid #e2e8f0; background: white; color: #475569; transition: all 0.15s; }
.msg-icon-btn:hover { background: #f1f5f9; }
.msg-icon-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Messages ── */
.msg-messages { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 8px; }
.msg-bubble-row { display: flex; }
.msg-bubble-row.inbound { justify-content: flex-start; }
.msg-bubble-row.outbound { justify-content: flex-end; }

.msg-bubble { max-width: 70%; padding: 10px 14px; border-radius: 16px; font-size: 14px; line-height: 1.5; }
.msg-bubble.inbound { background: white; color: #1e293b; border: 1px solid #e2e8f0; border-bottom-left-radius: 4px; }
.msg-bubble.outbound { background: #6366f1; color: white; border-bottom-right-radius: 4px; }
.msg-bubble.outbound.ai { background: linear-gradient(135deg, #6366f1, #8b5cf6); cursor: pointer; }
.msg-bubble.outbound.ai:hover { box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.3); }

.msg-bubble-meta { display: flex; gap: 6px; align-items: center; margin-top: 4px; font-size: 10px; opacity: 0.7; }
.msg-bubble-ai { background: rgba(255,255,255,0.2); padding: 1px 4px; border-radius: 3px; font-weight: 700; }
.msg-bubble.inbound .msg-bubble-ai { background: #eef2ff; color: #6366f1; }
.msg-bubble-audit-hint { cursor: pointer; font-size: 11px; }

/* ── Input Bar ── */
.msg-input-bar { display: flex; gap: 8px; padding: 12px 20px; background: white; border-top: 1px solid #e2e8f0; }
.msg-input { flex: 1; padding: 10px 16px; border: 1px solid #e2e8f0; border-radius: 24px; font-size: 14px; outline: none; transition: border 0.15s; }
.msg-input:focus { border-color: #6366f1; }
.msg-send-btn { width: 40px; height: 40px; border-radius: 50%; background: #6366f1; color: white; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.15s; }
.msg-send-btn:hover { background: #4f46e5; }
.msg-send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* ── Right Panel ── */
.msg-right-panel { border-left: 1px solid #e2e8f0; background: white; overflow-y: auto; display: flex; flex-direction: column; }

.msg-panel-tabs { display: flex; border-bottom: 1px solid #e2e8f0; background: #fafbfc; }
.msg-panel-tab { flex: 1; padding: 10px 0; text-align: center; font-size: 12px; font-weight: 600; color: #64748b; cursor: pointer; border: none; background: none; border-bottom: 2px solid transparent; transition: all 0.15s; }
.msg-panel-tab.active { color: #6366f1; border-bottom-color: #6366f1; }
.msg-panel-tab:hover:not(.active) { color: #334155; background: #f1f5f9; }

.msg-panel-content { padding: 20px; flex: 1; }

/* ── Contact Tab (existing styles) ── */
.msg-contact-header { text-align: center; padding-bottom: 16px; border-bottom: 1px solid #f1f5f9; margin-bottom: 16px; }
.msg-contact-big-avatar { width: 56px; height: 56px; border-radius: 50%; background: linear-gradient(135deg, #6366f1, #8b5cf6); display: flex; align-items: center; justify-content: center; color: white; font-size: 18px; font-weight: 700; margin: 0 auto 8px; }
.msg-contact-header h3 { font-size: 16px; font-weight: 700; margin: 0 0 2px; color: #1e293b; }
.msg-contact-header p { font-size: 13px; color: #64748b; margin: 0; }

.msg-contact-section { margin-bottom: 16px; }
.msg-contact-section h4 { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; margin: 0 0 8px; }

.msg-lead-score { display: flex; align-items: center; gap: 8px; }
.msg-score-bar { flex: 1; height: 6px; background: #f1f5f9; border-radius: 3px; overflow: hidden; }
.msg-score-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #f97316, #16a34a); transition: width 0.3s; }
.msg-score-value { font-size: 13px; font-weight: 700; color: #1e293b; }

.msg-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.msg-tag { font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 100px; background: #eef2ff; color: #6366f1; }

.msg-ai-summary { font-size: 13px; color: #475569; line-height: 1.5; margin: 0; background: #f8fafc; padding: 10px; border-radius: 8px; border-left: 3px solid #8b5cf6; }

.msg-detail-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #f8fafc; font-size: 13px; }
.msg-detail-row span:first-child { color: #94a3b8; }
.msg-detail-row span:last-child { color: #1e293b; font-weight: 500; }

.msg-status-pill { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 100px; text-transform: capitalize; }
.msg-status-pill.open { background: #dcfce7; color: #16a34a; }
.msg-status-pill.snoozed { background: #fef3c7; color: #d97706; }
.msg-status-pill.closed { background: #f1f5f9; color: #64748b; }

/* ── Agent Tab ── */
.msg-agent-section { margin-bottom: 24px; }
.msg-agent-section h4 { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; margin: 0 0 10px; }

.msg-section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.msg-section-header h4 { margin: 0; }

.msg-link-btn { background: none; border: none; font-size: 12px; font-weight: 600; color: #6366f1; cursor: pointer; padding: 2px 4px; }
.msg-link-btn:hover { text-decoration: underline; }
.msg-link-btn.danger { color: #ef4444; }

/* Tone grid */
.msg-tone-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.msg-tone-btn { display: flex; align-items: center; gap: 6px; padding: 8px 10px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer; border: 1px solid #e2e8f0; background: white; color: #475569; transition: all 0.15s; }
.msg-tone-btn:hover { background: #f8fafc; border-color: #cbd5e1; }
.msg-tone-btn.active { background: #eef2ff; border-color: #6366f1; color: #4338ca; box-shadow: 0 0 0 1px #6366f1; }
.msg-tone-icon { font-size: 14px; }

/* Training doc cards */
.msg-doc-card { padding: 10px 12px; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 8px; transition: border-color 0.15s; }
.msg-doc-card:hover { border-color: #cbd5e1; }
.msg-doc-header { display: flex; justify-content: space-between; align-items: center; }
.msg-doc-info { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
.msg-doc-title { font-size: 13px; font-weight: 600; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.msg-doc-type-badge { font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.03em; white-space: nowrap; }
.msg-doc-type-badge.persona { background: #dbeafe; color: #2563eb; }
.msg-doc-type-badge.product { background: #dcfce7; color: #16a34a; }
.msg-doc-type-badge.rules { background: #fef3c7; color: #d97706; }
.msg-doc-type-badge.script { background: #f3e8ff; color: #7c3aed; }
.msg-doc-type-badge.faq { background: #fce7f3; color: #db2777; }
.msg-doc-type-badge.custom { background: #f1f5f9; color: #475569; }

.msg-doc-footer { display: flex; gap: 8px; margin-top: 6px; }
.msg-doc-actions { flex-shrink: 0; }

/* Toggle switch */
.msg-toggle-switch { position: relative; display: inline-block; width: 32px; height: 18px; }
.msg-toggle-switch input { opacity: 0; width: 0; height: 0; }
.msg-toggle-slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #cbd5e1; transition: 0.2s; border-radius: 18px; }
.msg-toggle-slider::before { content: ""; position: absolute; height: 14px; width: 14px; left: 2px; bottom: 2px; background-color: white; transition: 0.2s; border-radius: 50%; }
.msg-toggle-switch input:checked + .msg-toggle-slider { background-color: #6366f1; }
.msg-toggle-switch input:checked + .msg-toggle-slider::before { transform: translateX(14px); }

/* Template cards */
.msg-template-card { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; border: 1px solid #f1f5f9; border-radius: 8px; margin-bottom: 6px; }
.msg-template-info { flex: 1; min-width: 0; }
.msg-template-title { font-size: 13px; font-weight: 600; color: #1e293b; }
.msg-template-desc { font-size: 11px; color: #94a3b8; margin-top: 2px; }

.msg-empty-docs { text-align: center; padding: 20px 12px; }
.msg-empty-docs p { font-size: 13px; color: #94a3b8; margin: 0; }

/* ── Audit Tab ── */
.msg-audit-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; padding: 40px 16px; text-align: center; }
.msg-audit-empty p { font-size: 13px; color: #94a3b8; margin: 0; line-height: 1.5; }

.msg-audit-detail h4 { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; margin: 0 0 12px; }

.msg-audit-preview { font-size: 13px; color: #475569; line-height: 1.5; padding: 10px 12px; background: #f8fafc; border-radius: 8px; border-left: 3px solid #8b5cf6; margin-bottom: 16px; font-style: italic; }

.msg-audit-field { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f8fafc; }
.msg-audit-label { font-size: 12px; color: #94a3b8; font-weight: 500; }
.msg-audit-value { font-size: 13px; color: #1e293b; font-weight: 600; }
.msg-audit-value.mono { font-family: 'SF Mono', 'Cascadia Mono', monospace; font-size: 11px; }
.msg-audit-value.cost { color: #6366f1; }

.tone-badge { padding: 3px 8px; border-radius: 6px; font-size: 12px; text-transform: capitalize; }
.tone-badge.professional { background: #dbeafe; color: #2563eb; }
.tone-badge.friendly { background: #fef3c7; color: #d97706; }
.tone-badge.casual { background: #dcfce7; color: #16a34a; }
.tone-badge.assertive { background: #fce7f3; color: #db2777; }
.tone-badge.bargaining { background: #f3e8ff; color: #7c3aed; }
.tone-badge.empathetic { background: #d1fae5; color: #059669; }

.msg-audit-docs { padding: 8px 0; }
.msg-audit-doc-list { display: flex; flex-direction: column; gap: 4px; margin-top: 6px; }
.msg-audit-doc-tag { font-size: 12px; color: #475569; padding: 4px 8px; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0; }

/* ── Doc Editor Modal ── */
.msg-modal-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.5); z-index: 1000; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(4px); }
.msg-modal { background: white; border-radius: 16px; width: 90%; max-width: 640px; max-height: 85vh; display: flex; flex-direction: column; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25); }
.msg-modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #e2e8f0; }
.msg-modal-header h3 { font-size: 16px; font-weight: 700; margin: 0; color: #0f172a; }
.msg-modal-close { background: none; border: none; font-size: 18px; color: #94a3b8; cursor: pointer; padding: 4px; }
.msg-modal-close:hover { color: #475569; }
.msg-modal-body { padding: 20px; overflow-y: auto; flex: 1; }
.msg-modal-footer { display: flex; justify-content: flex-end; gap: 8px; padding: 16px 20px; border-top: 1px solid #e2e8f0; }

.msg-doc-textarea { font-family: 'SF Mono', 'Cascadia Mono', 'Consolas', monospace; font-size: 13px; line-height: 1.6; resize: vertical; min-height: 280px; }

/* ── Responsive ── */
@media (max-width: 1200px) {
  .msg-layout { grid-template-columns: 280px 1fr 280px; }
}
@media (max-width: 1024px) {
  .msg-layout { grid-template-columns: 280px 1fr; }
  .msg-right-panel { display: none; }
}
@media (max-width: 768px) {
  .msg-layout { grid-template-columns: 1fr; }
  .msg-sidebar { max-height: 40vh; }
}
</style>
