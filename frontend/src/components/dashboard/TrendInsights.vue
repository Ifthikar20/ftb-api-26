<template>
  <div class="card trend-insights-card">
    <div class="card-header">
      <h3 class="card-title">🔮 Trend Insights</h3>
      <span class="badge badge-info">AI-Powered</span>
    </div>
    <p class="trend-desc">FetchBot analyzes trending topics and keywords to find growth opportunities for your business.</p>

    <div class="trend-items">
      <div v-for="trend in trends" :key="trend.keyword" class="trend-item">
        <div class="trend-left">
          <span class="trend-spark" :style="{ color: trend.color }">{{ trend.icon }}</span>
          <div>
            <span class="trend-keyword">{{ trend.keyword }}</span>
            <span class="trend-volume">{{ trend.volume }}</span>
          </div>
        </div>
        <span class="trend-tag" :style="{ background: trend.bgColor, color: trend.color }">{{ trend.relevance }}</span>
      </div>
    </div>

    <div class="integrations-cta">
      <h4 class="cta-title">📡 Connect to Supercharge</h4>
      <div class="integration-list">
        <div v-for="intg in suggestedIntegrations" :key="intg.name" class="integration-item">
          <span class="integration-icon" v-html="intg.icon"></span>
          <div class="integration-info">
            <span class="integration-name">{{ intg.name }}</span>
            <span class="integration-desc">{{ intg.desc }}</span>
          </div>
          <button class="btn-sm btn-outline" @click="$emit('connect', intg.type)">Connect</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['connect'])

const trends = [
  {
    keyword: '"AI productivity tools"',
    volume: '↑ 340% this week',
    icon: '🔥',
    relevance: 'High Match',
    color: '#ef4444',
    bgColor: '#fef2f2',
  },
  {
    keyword: '"automation workflows"',
    volume: '↑ 120% this month',
    icon: '📈',
    relevance: 'Medium',
    color: '#f97316',
    bgColor: '#fff7ed',
  },
  {
    keyword: '"growth hacking 2026"',
    volume: '↑ 85% trending',
    icon: '⚡',
    relevance: 'Opportunity',
    color: '#8b5cf6',
    bgColor: '#f5f3ff',
  },
]

const suggestedIntegrations = [
  {
    type: 'slack',
    name: 'Slack',
    desc: 'Get trend alerts and growth reports directly in your channels',
    icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M14.5 2a2.5 2.5 0 0 0 0 5H17V4.5A2.5 2.5 0 0 0 14.5 2z" fill="#E01E5A"/><path d="M2 14.5a2.5 2.5 0 0 0 5 0V12H4.5A2.5 2.5 0 0 0 2 14.5z" fill="#36C5F0"/><path d="M9.5 22a2.5 2.5 0 0 0 0-5H7v2.5A2.5 2.5 0 0 0 9.5 22z" fill="#2EB67D"/><path d="M22 9.5a2.5 2.5 0 0 0-5 0V12h2.5A2.5 2.5 0 0 0 22 9.5z" fill="#ECB22E"/></svg>',
  },
  {
    type: 'discord',
    name: 'Discord',
    desc: 'Share weekly insights with your team in a dedicated bot channel',
    icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="#5865F2"><path d="M20.3 4.1a19.4 19.4 0 0 0-4.8-1.5 14.5 14.5 0 0 0-.6 1.3 18 18 0 0 0-5.4 0c-.2-.5-.4-.9-.6-1.3A19.3 19.3 0 0 0 4 4.1 20 20 0 0 0 .5 17.7a19.5 19.5 0 0 0 6 3 14.6 14.6 0 0 0 1.3-2 12.6 12.6 0 0 1-2-.9l.5-.4c3.8 1.8 8 1.8 11.8 0 .2.1.3.3.5.4-.6.4-1.3.7-2 .9.4.7.8 1.4 1.3 2a19.5 19.5 0 0 0 6-3A20 20 0 0 0 20.3 4.1zM8 14.8c-1.2 0-2.2-1.1-2.2-2.4S6.8 10 8 10s2.2 1.1 2.2 2.4S9.2 14.8 8 14.8zm8 0c-1.2 0-2.2-1.1-2.2-2.4S14.8 10 16 10s2.2 1.1 2.2 2.4S17.2 14.8 16 14.8z"/></svg>',
  },
  {
    type: 'telegram',
    name: 'Telegram',
    desc: 'Receive instant growth milestone notifications anywhere',
    icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="#229ED9"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm4.6 6.8l-1.7 7.9c-.1.5-.5.7-.9.4l-2.5-1.8-1.2 1.2c-.1.2-.3.3-.5.3l.2-2.5 4.5-4c.2-.2 0-.3-.3-.1L8.7 13.5l-2.4-.7c-.5-.2-.5-.5.1-.7l9.5-3.7c.4-.1.8.1.7.7z"/></svg>',
  },
]
</script>

<style scoped>
.trend-insights-card {
  padding: 20px 24px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.card-title {
  font-size: var(--font-base);
  font-weight: 700;
  color: var(--text-primary);
}

.badge-info {
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  color: white;
}

.trend-desc {
  font-size: var(--font-xs);
  color: var(--text-muted);
  margin-bottom: 16px;
  line-height: 1.4;
}

.trend-items {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
}

.trend-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  transition: all var(--transition-fast);
}

.trend-item:hover {
  transform: translateX(2px);
}

.trend-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.trend-spark { font-size: 1.1rem; }

.trend-keyword {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
  display: block;
}

.trend-volume {
  font-size: var(--font-xs);
  color: var(--text-muted);
}

.trend-tag {
  font-size: 0.6rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.integrations-cta {
  border-top: 1px solid var(--border-color);
  padding-top: 16px;
}

.cta-title {
  font-size: var(--font-sm);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.integration-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.integration-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--bg-surface);
}

.integration-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.integration-info {
  flex: 1;
  min-width: 0;
}

.integration-name {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--text-primary);
  display: block;
}

.integration-desc {
  font-size: var(--font-xs);
  color: var(--text-muted);
  line-height: 1.3;
}

.btn-sm {
  font-size: 0.65rem;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-fast);
}

.btn-sm:hover {
  border-color: var(--text-primary);
  color: var(--text-primary);
}
</style>
