<template>
  <div class="msg-page">
    <!-- ═══ Header ═══ -->
    <div class="msg-header">
      <div class="msg-header-left">
        <h1>Messaging</h1>
        <span class="msg-header-count">{{ conversations.length }} conversations</span>
      </div>
      <div class="msg-header-actions">
        <button class="msg-btn msg-btn-outline" @click="seedDemo" :disabled="seeding">
          <span v-if="seeding">Creating...</span>
          <span v-else>+ Demo Data</span>
        </button>
        <button class="msg-btn msg-btn-primary">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          New Chat
        </button>
      </div>
    </div>

    <!-- ═══ 3-Panel Layout ═══ -->
    <div class="msg-layout">
      <!-- ── Left: Conversation List ── -->
      <div class="msg-sidebar">
        <div class="msg-search">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
          <input v-model="searchQuery" placeholder="Search conversations..." />
        </div>

        <div class="msg-filters">
          <button v-for="f in statusFilters" :key="f.key"
            :class="['msg-filter-btn', { active: activeFilter === f.key }]"
            @click="activeFilter = f.key">
            {{ f.label }}
            <span v-if="f.count" class="msg-filter-count">{{ f.count }}</span>
          </button>
        </div>

        <div class="msg-conv-list" v-if="filteredConversations.length">
          <div v-for="conv in filteredConversations" :key="conv.id"
            :class="['msg-conv-item', { active: activeConversation?.id === conv.id }]"
            @click="selectConversation(conv)">
            <div class="msg-conv-avatar">
              <span>{{ getInitials(conv.contact_name) }}</span>
              <span class="msg-channel-dot" :class="conv.channel_type"></span>
            </div>
            <div class="msg-conv-info">
              <div class="msg-conv-row">
                <span class="msg-conv-name">{{ conv.contact_name || 'Unknown' }}</span>
                <span class="msg-conv-time">{{ formatTime(conv.last_message_at) }}</span>
              </div>
              <div class="msg-conv-preview">{{ conv.last_message_preview }}</div>
            </div>
            <span v-if="conv.unread_count" class="msg-unread-badge">{{ conv.unread_count }}</span>
          </div>
        </div>

        <div v-else class="msg-empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <p>No conversations yet</p>
          <button class="msg-btn msg-btn-outline" @click="seedDemo">Load Demo Data</button>
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
            <div :class="['msg-bubble', msg.direction, msg.sent_by]">
              <div class="msg-bubble-content">{{ msg.content }}</div>
              <div class="msg-bubble-meta">
                <span v-if="msg.sent_by === 'ai'" class="msg-bubble-ai">⚡ AI</span>
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

      <!-- ── Right: Contact Info ── -->
      <div class="msg-contact-panel" v-if="activeConversation">
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
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()
const websiteId = computed(() => route.params.websiteId)

const conversations = ref([])
const activeConversation = ref(null)
const searchQuery = ref('')
const activeFilter = ref('all')
const messageText = ref('')
const seeding = ref(false)
const aiGenerating = ref(false)
const messagesContainer = ref(null)

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

async function apiFetch(path, options = {}) {
  const token = auth.token || localStorage.getItem('access_token')
  const res = await fetch(`/api/v1/messaging/${websiteId.value}${path}`, {
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

async function loadConversations() {
  try {
    const data = await apiFetch('/conversations/')
    conversations.value = data.results || data
  } catch (e) { console.error('Failed to load conversations', e) }
}

async function selectConversation(conv) {
  try {
    const data = await apiFetch(`/conversations/${conv.id}/`)
    activeConversation.value = data
    conv.unread_count = 0
    await nextTick()
    scrollToBottom()
  } catch (e) { console.error('Failed to load conversation', e) }
}

async function sendMessage() {
  if (!messageText.value.trim() || !activeConversation.value) return
  try {
    const msg = await apiFetch(`/conversations/${activeConversation.value.id}/send/`, {
      method: 'POST',
      body: JSON.stringify({ content: messageText.value }),
    })
    activeConversation.value.messages.push(msg)
    messageText.value = ''
    scrollToBottom()
  } catch (e) { console.error('Failed to send message', e) }
}

async function generateAIReply() {
  if (!activeConversation.value) return
  aiGenerating.value = true
  try {
    const msg = await apiFetch(`/conversations/${activeConversation.value.id}/ai-reply/`, {
      method: 'POST',
      body: JSON.stringify({}),
    })
    activeConversation.value.messages.push(msg)
    scrollToBottom()
  } catch (e) { console.error('AI reply failed', e) }
  finally { aiGenerating.value = false }
}

function toggleAI() {
  if (activeConversation.value) {
    activeConversation.value.ai_enabled = !activeConversation.value.ai_enabled
  }
}

async function seedDemo() {
  seeding.value = true
  try {
    await apiFetch('/seed-demo/', { method: 'POST', body: JSON.stringify({}) })
    await loadConversations()
  } catch (e) { console.error('Seed failed', e) }
  finally { seeding.value = false }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

watch(websiteId, () => { if (websiteId.value) loadConversations() }, { immediate: true })
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

/* ── 3-Panel Layout ── */
.msg-layout { display: grid; grid-template-columns: 320px 1fr 300px; flex: 1; overflow: hidden; }

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
.msg-bubble.outbound.ai { background: linear-gradient(135deg, #6366f1, #8b5cf6); }

.msg-bubble-meta { display: flex; gap: 6px; align-items: center; margin-top: 4px; font-size: 10px; opacity: 0.7; }
.msg-bubble-ai { background: rgba(255,255,255,0.2); padding: 1px 4px; border-radius: 3px; font-weight: 700; }
.msg-bubble.inbound .msg-bubble-ai { background: #eef2ff; color: #6366f1; }

/* ── Input Bar ── */
.msg-input-bar { display: flex; gap: 8px; padding: 12px 20px; background: white; border-top: 1px solid #e2e8f0; }
.msg-input { flex: 1; padding: 10px 16px; border: 1px solid #e2e8f0; border-radius: 24px; font-size: 14px; outline: none; transition: border 0.15s; }
.msg-input:focus { border-color: #6366f1; }
.msg-send-btn { width: 40px; height: 40px; border-radius: 50%; background: #6366f1; color: white; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.15s; }
.msg-send-btn:hover { background: #4f46e5; }
.msg-send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* ── Right Panel: Contact Info ── */
.msg-contact-panel { border-left: 1px solid #e2e8f0; background: white; overflow-y: auto; padding: 20px; }
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

/* ── Responsive ── */
@media (max-width: 1024px) {
  .msg-layout { grid-template-columns: 280px 1fr; }
  .msg-contact-panel { display: none; }
}
@media (max-width: 768px) {
  .msg-layout { grid-template-columns: 1fr; }
  .msg-sidebar { max-height: 40vh; }
}
</style>
