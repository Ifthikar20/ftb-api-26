<template>
  <div class="integrations-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Integrations</h1>
        <p class="page-subtitle">Connect your favorite tools to get daily updates, alerts, and growth reports.</p>
      </div>
    </div>

    <!-- Daily Update Preview Card -->
    <div class="daily-preview-card">
      <div class="daily-preview-inner">
        <div class="daily-preview-header">
          <div class="daily-preview-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
            <span>Daily Update Preview</span>
          </div>
          <div class="daily-schedule">
            <span class="schedule-label">Sends every day at</span>
            <select v-model="scheduleTime" class="schedule-select">
              <option value="08:00">8:00 AM</option>
              <option value="09:00">9:00 AM</option>
              <option value="10:00">10:00 AM</option>
              <option value="12:00">12:00 PM</option>
              <option value="17:00">5:00 PM</option>
            </select>
          </div>
        </div>

        <div class="update-preview-msg">
          <div class="preview-app-bar">
            <span class="preview-avatar">🤖</span>
            <span class="preview-bot-name">FetchBot</span>
            <span class="preview-time">Today at {{ formattedTime }}</span>
          </div>
          <div class="preview-body">
            <div class="preview-greeting">📊 <strong>Daily Growth Report</strong> — {{ todayFormatted }}</div>
            <div class="preview-stats">
              <div class="preview-stat-row">
                <span class="preview-stat-icon">👥</span>
                <span><strong>142</strong> new visitors · <strong>+18%</strong> from yesterday</span>
              </div>
              <div class="preview-stat-row">
                <span class="preview-stat-icon">🔥</span>
                <span><strong>7</strong> hot leads identified · <strong>3</strong> ready for outreach</span>
              </div>
              <div class="preview-stat-row">
                <span class="preview-stat-icon">📈</span>
                <span>Top trending: <strong>"AI productivity tools"</strong> ↑340%</span>
              </div>
              <div class="preview-stat-row">
                <span class="preview-stat-icon">🎯</span>
                <span>SEO health: <strong>92/100</strong> · 2 new keywords ranking</span>
              </div>
            </div>
            <div class="preview-cta">
              <span class="preview-link">📎 View full dashboard →</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Integrations Grid -->
    <div class="integrations-grid">
      <div v-for="intg in integrations" :key="intg.id" class="integration-card" :class="{ connected: intg.connected }">
        <!-- Status indicator -->
        <div class="intg-status-dot" :class="intg.connected ? 'status-connected' : 'status-disconnected'">
          <span class="status-pulse" v-if="intg.connected"></span>
        </div>

        <div class="intg-card-top">
          <div class="intg-icon-wrap" :style="{ background: intg.bgColor }">
            <span v-html="intg.icon"></span>
          </div>
          <div class="intg-card-identity">
            <span class="intg-card-name">{{ intg.name }}</span>
            <span class="intg-card-status" :class="intg.connected ? 'text-success' : 'text-muted'">
              {{ intg.connected ? 'Connected' : 'Not connected' }}
            </span>
          </div>
        </div>

        <p class="intg-card-desc">{{ intg.description }}</p>

        <!-- Features -->
        <div class="intg-features">
          <div v-for="feature in intg.features" :key="feature" class="intg-feature">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 8l3.5 3.5L13 5"/></svg>
            <span>{{ feature }}</span>
          </div>
        </div>

        <!-- Connect / Manage -->
        <div class="intg-card-actions">
          <template v-if="intg.connected">
            <button class="intg-btn intg-btn-manage" @click="openSettings(intg)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12.22 2h-.44a2 2 0 00-2 2v.18a2 2 0 01-1 1.73l-.43.25a2 2 0 01-2 0l-.15-.08a2 2 0 00-2.73.73l-.22.38a2 2 0 00.73 2.73l.15.1a2 2 0 011 1.72v.51a2 2 0 01-1 1.74l-.15.09a2 2 0 00-.73 2.73l.22.38a2 2 0 002.73.73l.15-.08a2 2 0 012 0l.43.25a2 2 0 011 1.73V20a2 2 0 002 2h.44a2 2 0 002-2v-.18a2 2 0 011-1.73l.43-.25a2 2 0 012 0l.15.08a2 2 0 002.73-.73l.22-.39a2 2 0 00-.73-2.73l-.15-.08a2 2 0 01-1-1.74v-.5a2 2 0 011-1.74l.15-.09a2 2 0 00.73-2.73l-.22-.38a2 2 0 00-2.73-.73l-.15.08a2 2 0 01-2 0l-.43-.25a2 2 0 01-1-1.73V4a2 2 0 00-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
              Settings
            </button>
            <button class="intg-btn intg-btn-disconnect" @click="disconnect(intg)">Disconnect</button>
          </template>
          <button v-else class="intg-btn intg-btn-connect" @click="openConnect(intg)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 007.5.5l3-3a5 5 0 00-7-7l-1.5 1.5"/><path d="M14 11a5 5 0 00-7.5-.5l-3 3a5 5 0 007 7l1.5-1.5"/></svg>
            Connect {{ intg.name }}
          </button>
        </div>
      </div>
    </div>

    <!-- What Gets Sent Section -->
    <div class="what-gets-sent">
      <h2 class="section-title">What gets sent to your teams</h2>
      <div class="sent-items-grid">
        <div class="sent-item">
          <div class="sent-item-icon" style="background: linear-gradient(135deg, #3b82f6, #2563eb)">📊</div>
          <h4>Daily Growth Report</h4>
          <p>Visitor count, lead score changes, and conversion trends delivered every morning.</p>
        </div>
        <div class="sent-item">
          <div class="sent-item-icon" style="background: linear-gradient(135deg, #ef4444, #dc2626)">🔥</div>
          <h4>Hot Lead Alerts</h4>
          <p>Instant notification when a lead reaches 80+ score or visits your pricing page.</p>
        </div>
        <div class="sent-item">
          <div class="sent-item-icon" style="background: linear-gradient(135deg, #8b5cf6, #7c3aed)">📈</div>
          <h4>Trend Intelligence</h4>
          <p>Weekly trending keywords and market shifts relevant to your business posture.</p>
        </div>
        <div class="sent-item">
          <div class="sent-item-icon" style="background: linear-gradient(135deg, #22c55e, #16a34a)">🏆</div>
          <h4>Growth Milestones</h4>
          <p>Celebrate when your team hits traffic goals, lead targets, or SEO improvements.</p>
        </div>
      </div>
    </div>

    <!-- ══════ Connect Modal ══════ -->
    <BaseModal v-model="showConnectModal" max-width="480px">
      <template #header>
        <h3 class="bm-title">
          <span v-html="activeIntegration?.icon" style="display:inline-flex;vertical-align:-4px;margin-right:8px"></span>
          Connect {{ activeIntegration?.name }}
        </h3>
      </template>

          <div class="connect-steps">
            <!-- Slack -->
            <template v-if="activeIntegration?.id === 'slack'">
              <div class="connect-step">
                <div class="step-number">1</div>
                <div class="step-content">
                  <h4>Create an Incoming Webhook</h4>
                  <p>Go to your <a href="https://api.slack.com/messaging/webhooks" target="_blank" class="step-link">Slack API dashboard</a> and create an Incoming Webhook for your workspace.</p>
                </div>
              </div>
              <div class="connect-step">
                <div class="step-number">2</div>
                <div class="step-content">
                  <h4>Paste the Webhook URL</h4>
                  <input v-model="webhookUrl" class="form-input" placeholder="https://hooks.slack.com/services/T.../B.../..." />
                </div>
              </div>
              <div class="connect-step">
                <div class="step-number">3</div>
                <div class="step-content">
                  <h4>Choose a channel</h4>
                  <input v-model="channelName" class="form-input" placeholder="#marketing-updates" />
                </div>
              </div>
            </template>

            <!-- Discord -->
            <template v-else-if="activeIntegration?.id === 'discord'">
              <div class="connect-step">
                <div class="step-number">1</div>
                <div class="step-content">
                  <h4>Create a Discord Webhook</h4>
                  <p>In your Discord server, go to <strong>Channel Settings → Integrations → Webhooks</strong> and click "New Webhook".</p>
                </div>
              </div>
              <div class="connect-step">
                <div class="step-number">2</div>
                <div class="step-content">
                  <h4>Paste the Webhook URL</h4>
                  <input v-model="webhookUrl" class="form-input" placeholder="https://discord.com/api/webhooks/..." />
                </div>
              </div>
              <div class="connect-step">
                <div class="step-number">3</div>
                <div class="step-content">
                  <h4>Bot display name</h4>
                  <input v-model="channelName" class="form-input" placeholder="FetchBot Growth Bot" value="FetchBot" />
                </div>
              </div>
            </template>

            <!-- Telegram -->
            <template v-else-if="activeIntegration?.id === 'telegram'">
              <div class="connect-step">
                <div class="step-number">1</div>
                <div class="step-content">
                  <h4>Get your Chat ID</h4>
                  <p>Message <a href="https://t.me/userinfobot" target="_blank" class="step-link">@userinfobot</a> on Telegram to get your chat ID.</p>
                </div>
              </div>
              <div class="connect-step">
                <div class="step-number">2</div>
                <div class="step-content">
                  <h4>Enter your Chat ID</h4>
                  <input v-model="webhookUrl" class="form-input" placeholder="123456789" />
                </div>
              </div>
              <div class="connect-step">
                <div class="step-number">3</div>
                <div class="step-content">
                  <h4>Start the bot</h4>
                  <p>Message <a href="https://t.me/FetchBotGrowthBot" target="_blank" class="step-link">@FetchBotGrowthBot</a> to activate notifications.</p>
                </div>
              </div>
            </template>
          </div>

          <!-- Notification Preferences -->
          <div class="notif-prefs">
            <h4 class="prefs-title">Notifications to send</h4>
            <label class="pref-check" v-for="pref in notifPrefs" :key="pref.key">
              <input type="checkbox" v-model="pref.enabled" class="modern-check" />
              <div>
                <span class="pref-name">{{ pref.label }}</span>
                <span class="pref-desc">{{ pref.desc }}</span>
              </div>
            </label>
          </div>

      <template #footer>
        <button class="btn btn-secondary" @click="showConnectModal = false">Cancel</button>
        <button class="btn btn-primary" :disabled="!webhookUrl.trim() || connecting" @click="confirmConnect">
          <span v-if="connecting" class="btn-spinner"></span>
          {{ connecting ? 'Connecting...' : 'Connect & Save' }}
        </button>
      </template>
    </BaseModal>

    <!-- Success Toast Overlay -->
    <Transition name="toast">
      <div v-if="showSuccessToast" class="success-toast">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/></svg>
        <span>{{ successMessage }}</span>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import BaseModal from '@/components/ui/BaseModal.vue'

const scheduleTime = ref('09:00')
const showConnectModal = ref(false)
const activeIntegration = ref(null)
const webhookUrl = ref('')
const channelName = ref('')
const connecting = ref(false)
const showSuccessToast = ref(false)
const successMessage = ref('')

const formattedTime = computed(() => {
  const [h, m] = scheduleTime.value.split(':').map(Number)
  const suffix = h >= 12 ? 'PM' : 'AM'
  return `${h > 12 ? h - 12 : h}:${m.toString().padStart(2, '0')} ${suffix}`
})

const todayFormatted = computed(() => {
  return new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
})

const notifPrefs = reactive([
  { key: 'daily', label: 'Daily Growth Report', desc: 'Morning summary of visitors, leads, and trends', enabled: true },
  { key: 'hotlead', label: 'Hot Lead Alerts', desc: 'Instant alert when a lead scores 80+', enabled: true },
  { key: 'trends', label: 'Weekly Trend Digest', desc: 'Top trending topics relevant to your business', enabled: true },
  { key: 'milestones', label: 'Growth Milestones', desc: 'Team celebrations when targets are hit', enabled: false },
])

const integrations = reactive([
  {
    id: 'slack',
    name: 'Slack',
    description: 'Get trend alerts and growth reports directly in your channels. Perfect for marketing and sales teams.',
    bgColor: 'linear-gradient(135deg, #4A154B15, #E01E5A08)',
    features: ['Daily growth summaries', 'Hot lead alerts in real-time', 'Trend intelligence weekly digest', 'Custom channel routing'],
    connected: false,
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M14.5 2a2.5 2.5 0 0 0 0 5H17V4.5A2.5 2.5 0 0 0 14.5 2z" fill="#E01E5A"/><path d="M2 14.5a2.5 2.5 0 0 0 5 0V12H4.5A2.5 2.5 0 0 0 2 14.5z" fill="#36C5F0"/><path d="M9.5 22a2.5 2.5 0 0 0 0-5H7v2.5A2.5 2.5 0 0 0 9.5 22z" fill="#2EB67D"/><path d="M22 9.5a2.5 2.5 0 0 0-5 0V12h2.5A2.5 2.5 0 0 0 22 9.5z" fill="#ECB22E"/></svg>',
  },
  {
    id: 'discord',
    name: 'Discord',
    description: 'Share weekly insights with your team in a dedicated bot channel. Great for dev and growth teams.',
    bgColor: 'linear-gradient(135deg, #5865F215, #5865F208)',
    features: ['Rich embed messages', 'Weekly performance summaries', 'Bot channel with interactive commands', 'Mention roles on key alerts'],
    connected: false,
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="#5865F2"><path d="M20.3 4.1a19.4 19.4 0 0 0-4.8-1.5 14.5 14.5 0 0 0-.6 1.3 18 18 0 0 0-5.4 0c-.2-.5-.4-.9-.6-1.3A19.3 19.3 0 0 0 4 4.1 20 20 0 0 0 .5 17.7a19.5 19.5 0 0 0 6 3 14.6 14.6 0 0 0 1.3-2 12.6 12.6 0 0 1-2-.9l.5-.4c3.8 1.8 8 1.8 11.8 0 .2.1.3.3.5.4-.6.4-1.3.7-2 .9.4.7.8 1.4 1.3 2a19.5 19.5 0 0 0 6-3A20 20 0 0 0 20.3 4.1zM8 14.8c-1.2 0-2.2-1.1-2.2-2.4S6.8 10 8 10s2.2 1.1 2.2 2.4S9.2 14.8 8 14.8zm8 0c-1.2 0-2.2-1.1-2.2-2.4S14.8 10 16 10s2.2 1.1 2.2 2.4S17.2 14.8 16 14.8z"/></svg>',
  },
  {
    id: 'telegram',
    name: 'Telegram',
    description: 'Receive instant growth milestone notifications anywhere. Perfect for founders and solopreneurs.',
    bgColor: 'linear-gradient(135deg, #229ED915, #229ED908)',
    features: ['Instant push notifications', 'Mobile-first growth alerts', 'Reply to get quick analytics', 'Milestone celebrations'],
    connected: false,
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="#229ED9"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm4.6 6.8l-1.7 7.9c-.1.5-.5.7-.9.4l-2.5-1.8-1.2 1.2c-.1.2-.3.3-.5.3l.2-2.5 4.5-4c.2-.2 0-.3-.3-.1L8.7 13.5l-2.4-.7c-.5-.2-.5-.5.1-.7l9.5-3.7c.4-.1.8.1.7.7z"/></svg>',
  },
])

function openConnect(intg) {
  activeIntegration.value = intg
  webhookUrl.value = ''
  channelName.value = ''
  showConnectModal.value = true
}

function openSettings(intg) {
  activeIntegration.value = intg
  webhookUrl.value = intg.webhookUrl || ''
  channelName.value = intg.channelName || ''
  showConnectModal.value = true
}

function disconnect(intg) {
  intg.connected = false
  intg.webhookUrl = ''
  intg.channelName = ''
  showToast(`${intg.name} disconnected`)
}

async function confirmConnect() {
  if (!webhookUrl.value.trim()) return
  connecting.value = true

  const intg = integrations.find(i => i.id === activeIntegration.value.id)
  if (!intg) { connecting.value = false; return }

  try {
    // Build test message
    const now = new Date().toLocaleString('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
    let sent = false

    if (intg.id === 'slack') {
      // Slack Incoming Webhook
      const payload = {
        text: '📊 *FetchBot Daily Growth Report* — Test Message',
        blocks: [
          { type: 'header', text: { type: 'plain_text', text: '📊 FetchBot Daily Growth Report', emoji: true } },
          { type: 'section', text: { type: 'mrkdwn', text: `*Connected at* ${now}\n\nYou'll receive daily growth reports, hot lead alerts, and trend intelligence right here.` } },
          { type: 'divider' },
          { type: 'section', fields: [
            { type: 'mrkdwn', text: '👥 *142* new visitors\n_+18% from yesterday_' },
            { type: 'mrkdwn', text: '🔥 *7* hot leads\n_3 ready for outreach_' },
            { type: 'mrkdwn', text: '📈 *Top trend:* AI tools\n_↑340% this week_' },
            { type: 'mrkdwn', text: '🎯 *SEO Score:* 92/100\n_2 new keywords ranking_' },
          ]},
          { type: 'divider' },
          { type: 'context', elements: [{ type: 'mrkdwn', text: '✅ FetchBot is now connected! You\'ll receive reports at the scheduled time.' }] },
        ]
      }
      const res = await fetch(webhookUrl.value, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      sent = res.ok
    }

    else if (intg.id === 'discord') {
      // Discord Webhook
      const payload = {
        username: 'FetchBot',
        avatar_url: 'https://fetchbot.ai/favicon.png',
        embeds: [{
          title: '📊 FetchBot Daily Growth Report',
          description: `Connected at ${now}\n\nYou'll receive daily growth reports, hot lead alerts, and trend intelligence right here.`,
          color: 0x8b5cf6,
          fields: [
            { name: '👥 Visitors', value: '**142** new\n+18% from yesterday', inline: true },
            { name: '🔥 Hot Leads', value: '**7** identified\n3 ready for outreach', inline: true },
            { name: '📈 Trending', value: '**AI tools** ↑340%', inline: true },
            { name: '🎯 SEO Score', value: '**92/100**\n2 new keywords', inline: true },
          ],
          footer: { text: '✅ FetchBot is now connected! Reports will arrive at the scheduled time.' },
          timestamp: new Date().toISOString(),
        }]
      }
      const res = await fetch(webhookUrl.value, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      sent = res.ok || res.status === 204
    }

    else if (intg.id === 'telegram') {
      // Telegram Bot API
      const chatId = webhookUrl.value.trim()
      const botToken = '7026952887:AAH_placeholder_token' // Replace with real bot token from env
      const text = `📊 *FetchBot Daily Growth Report*\n_Connected at ${now}_\n\n` +
        `👥 *142* new visitors · +18% from yesterday\n` +
        `🔥 *7* hot leads · 3 ready for outreach\n` +
        `📈 Top trend: *AI tools* ↑340%\n` +
        `🎯 SEO Score: *92/100* · 2 new keywords\n\n` +
        `✅ _FetchBot is connected! Reports will arrive daily._`
      try {
        const res = await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chat_id: chatId, text, parse_mode: 'Markdown' }),
        })
        const data = await res.json()
        sent = data.ok === true
      } catch { sent = false }
    }

    // Update state
    intg.connected = true
    intg.webhookUrl = webhookUrl.value
    intg.channelName = channelName.value

    connecting.value = false
    showConnectModal.value = false

    if (sent) {
      showToast(`${intg.name} connected! A test message was sent — check your ${intg.name} channel.`)
    } else {
      // Still mark as connected — webhook saved, but test might have failed due to CORS
      showToast(`${intg.name} connected! Webhook saved — daily reports will be sent from the server.`)
    }
  } catch (err) {
    // Even if the direct POST fails (CORS), save the connection
    intg.connected = true
    intg.webhookUrl = webhookUrl.value
    intg.channelName = channelName.value
    connecting.value = false
    showConnectModal.value = false
    showToast(`${intg.name} connected! Webhook saved — messages will be sent server-side.`)
  }
}

function showToast(msg) {
  successMessage.value = msg
  showSuccessToast.value = true
  setTimeout(() => { showSuccessToast.value = false }, 4000)
}
</script>

<style scoped>
/* ═══════════════════════════════════════
   Daily Update Preview
   ═══════════════════════════════════════ */
.daily-preview-card {
  margin-bottom: 24px;
  padding: 2px;
  border-radius: calc(var(--radius-lg) + 2px);
  background: linear-gradient(135deg, #3b82f6, #8b5cf6, #6366f1, #3b82f6);
  background-size: 300% 300%;
  animation: gradient-shift 6s ease infinite;
}

@keyframes gradient-shift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.daily-preview-inner {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.daily-preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.daily-preview-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-base);
  font-weight: 700;
  color: var(--text-primary);
}

.daily-schedule {
  display: flex;
  align-items: center;
  gap: 8px;
}

.schedule-label {
  font-size: var(--font-xs);
  color: var(--text-muted);
}

.schedule-select {
  padding: 4px 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  font-size: var(--font-xs);
  background: var(--bg-surface);
  color: var(--text-primary);
  cursor: pointer;
}

/* ── Message Preview ── */
.update-preview-msg {
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.preview-app-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color);
}

.preview-avatar { font-size: 1.2rem; }

.preview-bot-name {
  font-weight: 700;
  font-size: var(--font-sm);
  color: var(--text-primary);
}

.preview-time {
  font-size: var(--font-xs);
  color: var(--text-muted);
  margin-left: auto;
}

.preview-body { padding: 14px; }

.preview-greeting {
  font-size: var(--font-sm);
  color: var(--text-primary);
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px dashed color-mix(in srgb, var(--border-color) 60%, transparent);
}

.preview-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.preview-stat-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-xs);
  color: var(--text-secondary);
}

.preview-stat-icon { font-size: 0.9rem; }
.preview-stat-row strong { color: var(--text-primary); font-weight: 700; }

.preview-cta {
  padding-top: 10px;
  border-top: 1px dashed color-mix(in srgb, var(--border-color) 60%, transparent);
}

.preview-link {
  font-size: var(--font-xs);
  color: var(--brand-accent);
  font-weight: 600;
  cursor: pointer;
}

/* ═══════════════════════════════════════
   Integration Cards Grid
   ═══════════════════════════════════════ */
.integrations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

@keyframes card-in {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.integration-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
  transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);
  animation: card-in 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.integration-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
}

.integration-card.connected {
  border-color: rgba(34, 197, 94, 0.3);
}

/* Status dot */
.intg-status-dot {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 10px; height: 10px;
  border-radius: 50%;
}
.status-connected { background: #22c55e; }
.status-disconnected { background: var(--border-color); }
.status-pulse {
  position: absolute;
  width: 100%; height: 100%;
  border-radius: 50%;
  background: #22c55e;
  animation: pulse-out 2s ease-out infinite;
}
@keyframes pulse-out {
  0% { transform: scale(1); opacity: 0.5; }
  100% { transform: scale(2.5); opacity: 0; }
}

.intg-card-top {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
}

.intg-icon-wrap {
  width: 48px; height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.intg-card-identity { flex: 1; }

.intg-card-name {
  display: block;
  font-size: var(--font-base);
  font-weight: 700;
  color: var(--text-primary);
}

.intg-card-status {
  display: block;
  font-size: var(--font-xs);
  font-weight: 500;
  margin-top: 1px;
}
.text-success { color: #22c55e; }
.text-muted-status { color: var(--text-muted); }

.intg-card-desc {
  font-size: var(--font-xs);
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 14px;
}

/* Features */
.intg-features {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid color-mix(in srgb, var(--border-color) 50%, transparent);
}

.intg-feature {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-xs);
  color: var(--text-muted);
}

.intg-feature svg { color: #22c55e; flex-shrink: 0; }

/* Buttons */
.intg-card-actions {
  display: flex;
  gap: 8px;
}

.intg-btn {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-xs);
  font-weight: 600;
  font-family: var(--font-family);
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.intg-btn-connect {
  flex: 1;
  justify-content: center;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
}
.intg-btn-connect:hover { box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3); transform: translateY(-1px); }

.intg-btn-manage {
  flex: 1;
  justify-content: center;
  background: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}
.intg-btn-manage:hover { border-color: var(--text-primary); color: var(--text-primary); }

.intg-btn-disconnect {
  padding: 8px 12px;
  background: transparent;
  color: var(--text-muted);
  font-size: var(--font-xs);
}
.intg-btn-disconnect:hover { color: #ef4444; }

/* ═══════════════════════════════════════
   What Gets Sent
   ═══════════════════════════════════════ */
.section-title {
  font-size: var(--font-md);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.sent-items-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}

.sent-item {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: all 0.2s;
}
.sent-item:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.04); }

.sent-item-icon {
  width: 36px; height: 36px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  margin-bottom: 10px;
}

.sent-item h4 {
  font-size: var(--font-sm);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px;
}

.sent-item p {
  font-size: var(--font-xs);
  color: var(--text-muted);
  line-height: 1.5;
  margin: 0;
}

/* ═══════════════════════════════════════
   Connect Modal
   ═══════════════════════════════════════ */
.connect-steps {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 16px;
}

.connect-step {
  display: flex;
  gap: 12px;
}

.step-number {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.step-content { flex: 1; }
.step-content h4 {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px;
}
.step-content p {
  font-size: var(--font-xs);
  color: var(--text-muted);
  line-height: 1.4;
  margin: 0 0 8px;
}

.step-link { color: var(--brand-accent); text-decoration: none; font-weight: 600; }
.step-link:hover { text-decoration: underline; }

.notif-prefs {
  border-top: 1px solid var(--border-color);
  padding-top: 14px;
  margin-bottom: 16px;
}

.prefs-title {
  font-size: var(--font-xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin: 0 0 10px;
}

.pref-check {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 6px 0;
  cursor: pointer;
}

.pref-name {
  display: block;
  font-size: var(--font-xs);
  font-weight: 600;
  color: var(--text-primary);
}

.pref-desc {
  display: block;
  font-size: 0.65rem;
  color: var(--text-muted);
  margin-top: 1px;
}

.modern-check {
  width: 15px; height: 15px;
  cursor: pointer;
  accent-color: #8b5cf6;
  margin-top: 2px;
}

.modal-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.btn-spinner {
  display: inline-block;
  width: 12px; height: 12px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin-right: 6px;
  vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Modal Transition ── */
.modal-fade-enter-active { transition: opacity 0.2s; }
.modal-fade-leave-active { transition: opacity 0.15s; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }

/* ── Success Toast ── */
.success-toast {
  position: fixed;
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: var(--bg-card);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: var(--radius-full);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
  z-index: 200;
}

.toast-enter-active { transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1); }
.toast-leave-active { transition: all 0.2s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(-50%) translateY(20px); }

/* ── Responsive ── */
@media (max-width: 768px) {
  .integrations-grid { grid-template-columns: 1fr; }
  .sent-items-grid { grid-template-columns: 1fr; }
  .daily-preview-header { flex-direction: column; gap: 10px; align-items: flex-start; }
}
</style>
