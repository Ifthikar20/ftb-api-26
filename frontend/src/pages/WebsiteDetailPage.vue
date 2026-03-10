<template>
  <div class="detail-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ website?.name || 'Website' }}</h1>
        <p class="page-subtitle text-muted">{{ website?.url }}</p>
      </div>
      <div class="flex gap-8">
        <button class="btn btn-secondary" @click="$router.push(`/audits/${id}`)">Run Audit</button>
        <button class="btn btn-primary" @click="$router.push(`/analytics/${id}`)">View Analytics</button>
      </div>
    </div>

    <!-- Pixel Installation -->
    <div class="card" style="margin-bottom:24px">
      <div class="card-header">
        <h3 class="card-title">Pixel Installation</h3>
        <span class="badge" :class="website?.pixel_verified ? 'badge-success' : 'badge-warning'">
          {{ website?.pixel_verified ? 'Verified' : 'Not Verified' }}
        </span>
      </div>
      <p class="text-secondary text-sm" style="margin-bottom:16px">
        Add this script to your website's <code>&lt;head&gt;</code> tag to start tracking visitors.
      </p>
      <div class="code-block">
        <code>&lt;script src="https://fetchbot.ai/pixel/growthpilot.min.js" data-key="{{ website?.pixel_key || 'your-pixel-key' }}"&gt;&lt;/script&gt;</code>
      </div>
      <button class="btn btn-secondary btn-sm" style="margin-top:12px" @click="copyPixel">
        {{ copied ? 'Copied!' : 'Copy Snippet' }}
      </button>
    </div>

    <div class="content-grid">
      <!-- Quick Navigation -->
      <div class="card">
        <h3 class="card-title" style="margin-bottom:16px">Quick Navigation</h3>
        <div class="nav-tiles">
          <div class="nav-tile" @click="$router.push(`/analytics/${id}`)">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 21V9l6-6 6 6 6-6v18"/></svg>
            <span class="font-semibold">Analytics</span>
          </div>
          <div class="nav-tile" @click="$router.push(`/leads/${id}`)">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-7 8-7s8 3 8 7"/></svg>
            <span class="font-semibold">Leads</span>
          </div>
          <div class="nav-tile" @click="$router.push(`/competitors/${id}`)">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="6" width="7" height="14" rx="1.5"/><rect x="14" y="3" width="7" height="17" rx="1.5"/></svg>
            <span class="font-semibold">Competitors</span>
          </div>
          <div class="nav-tile" @click="$router.push(`/strategy/${id}`)">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2l3 6h6l-5 4 2 6-6-3-6 3 2-6-5-4h6z" stroke-linejoin="round"/></svg>
            <span class="font-semibold">Strategy</span>
          </div>
        </div>
      </div>

      <!-- Website Info -->
      <div class="card">
        <h3 class="card-title" style="margin-bottom:16px">Website Info</h3>
        <div class="info-list">
          <div class="info-row">
            <span class="text-muted">URL</span>
            <span>{{ website?.url || '--' }}</span>
          </div>
          <div class="info-row">
            <span class="text-muted">Industry</span>
            <span>{{ website?.industry || 'Not set' }}</span>
          </div>
          <div class="info-row">
            <span class="text-muted">Crawl Status</span>
            <span class="badge badge-primary">{{ website?.crawl_status || 'pending' }}</span>
          </div>
          <div class="info-row">
            <span class="text-muted">Created</span>
            <span>{{ website?.created_at ? new Date(website.created_at).toLocaleDateString() : '--' }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import websitesApi from '@/api/websites'

const props = defineProps({ id: String })
const website = ref(null)
const copied = ref(false)

onMounted(async () => {
  try {
    const { data } = await websitesApi.get(props.id)
    website.value = data?.data || data
  } catch { /* handle */ }
})

function copyPixel() {
  const snippet = `<script src="https://fetchbot.ai/pixel/growthpilot.min.js" data-key="${website.value?.pixel_key || ''}">\<\/script>`
  navigator.clipboard.writeText(snippet)
  copied.value = true
  setTimeout(() => copied.value = false, 2000)
}
</script>

<style scoped>
.code-block {
  background: var(--bg-root);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: var(--font-sm);
  color: var(--color-success);
  overflow-x: auto;
}

.nav-tiles {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.nav-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  font-size: var(--font-sm);
  color: var(--text-secondary);
}

.nav-tile:hover {
  border-color: var(--brand-accent);
  background: var(--brand-accent-glow);
  color: var(--text-primary);
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-sm);
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}

.info-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
</style>
