<template>
  <div class="auth-layout">
    <div class="auth-left">
      <!-- Watercolor video background -->
      <video class="auth-video-bg" autoplay muted loop playsinline>
        <source src="/videos/watercolor-main.mp4" type="video/mp4" />
      </video>
      <div class="auth-video-overlay"></div>

      <div class="auth-left-content">
        <div class="auth-brand">
          <div class="brand-logo">
            <img src="/images/fb-logo.png" alt="FetchBot" style="width:32px;height:32px;object-fit:contain;filter:brightness(10)" />
          </div>
          <span class="brand-name">FetchBot</span>
        </div>

        <div class="auth-hero">
          <h1 class="auth-headline">Marketing Intelligence, <br/><em>Simplified.</em></h1>
          <p class="auth-tagline">Track visitors, score leads, audit your site, and grow with AI — all in one platform.</p>
          <span class="version-badge">v2.1</span>
        </div>

        <div class="auth-features">
          <div class="feature-item">
            <span class="feature-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M2 14V6l4-4 4 4 4-4v12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg></span>
            <span>Real-time analytics</span>
          </div>
          <div class="feature-item">
            <span class="feature-icon"><svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><circle cx="8" cy="5" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M2 14c0-3 3-5 6-5s6 2 6 5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></span>
            <span>Lead scoring</span>
          </div>
        </div>
      </div>
    </div>

    <div class="auth-right">
      <div class="auth-theme-toggle">
        <button class="theme-toggle" @click="toggleTheme" :title="currentTheme === 'light' ? 'Dark mode' : 'Light mode'">
          <svg v-if="currentTheme === 'light'" width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M15 10A7 7 0 1 1 8 3a5 5 0 0 0 7 7z"/></svg>
          <svg v-else width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="9" cy="9" r="4"/><path d="M9 1v2M9 15v2M1 9h2M15 9h2M3.3 3.3l1.4 1.4M13.3 13.3l1.4 1.4M14.7 3.3l-1.4 1.4M4.7 13.3l-1.4 1.4"/></svg>
        </button>
      </div>

      <div class="auth-form-container">
        <div class="auth-form-header">
          <h2 class="auth-title">{{ title }}</h2>
          <p v-if="subtitle" class="auth-subtitle">{{ subtitle }}</p>
        </div>
        <slot />
      </div>

      <p class="auth-footer">© 2026 FetchBot · Privacy · Terms</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
})

const currentTheme = ref(localStorage.getItem('fb-theme') || 'light')

function toggleTheme() {
  currentTheme.value = currentTheme.value === 'light' ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', currentTheme.value)
  localStorage.setItem('fb-theme', currentTheme.value)
}

onMounted(() => {
  document.documentElement.setAttribute('data-theme', currentTheme.value)
})
</script>

<style scoped>
.auth-layout {
  display: flex;
  min-height: 100vh;
}

/* ── Left Panel — Video Background ── */
.auth-left {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.auth-video-bg {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  object-fit: cover;
  z-index: 0;
}

.auth-video-overlay {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  background: linear-gradient(
    160deg,
    rgba(0, 0, 0, 0.55) 0%,
    rgba(0, 0, 0, 0.35) 40%,
    rgba(0, 0, 0, 0.20) 100%
  );
  z-index: 1;
}

.auth-left-content {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;
  padding: 48px 56px;
}

.auth-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  position: absolute;
  top: 32px;
  left: 48px;
}

.brand-name {
  font-family: var(--font-display);
  font-size: var(--font-xl);
  color: #ffffff;
  text-shadow: 0 1px 8px rgba(0,0,0,0.3);
}

.auth-hero {
  max-width: 480px;
}

.auth-headline {
  font-family: var(--font-display);
  font-size: clamp(2rem, 4vw, 3.5rem);
  font-weight: 400;
  line-height: 1.15;
  color: #ffffff;
  margin-bottom: 20px;
  text-shadow: 0 2px 16px rgba(0,0,0,0.3);
}

.auth-headline em {
  font-style: italic;
  color: #c4dafe;
}

.auth-tagline {
  font-size: var(--font-md);
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.7;
  max-width: 420px;
  text-shadow: 0 1px 6px rgba(0,0,0,0.2);
}

.version-badge {
  display: inline-block;
  margin-top: 12px;
  padding: 4px 12px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: #ffffff;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 999px;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.auth-features {
  display: flex;
  gap: 24px;
  margin-top: 40px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-sm);
  font-weight: 500;
  color: rgba(255, 255, 255, 0.8);
}

.feature-icon {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.9);
}

/* ── Right Panel ── */
.auth-right {
  width: 480px;
  background: var(--bg-card);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 56px;
  border-left: 1px solid var(--border-color);
  position: relative;
}

.auth-theme-toggle {
  position: absolute;
  top: 24px;
  right: 24px;
}

.auth-form-container {
  width: 100%;
  max-width: 360px;
}

.auth-form-header {
  margin-bottom: 32px;
}

.auth-title {
  font-family: var(--font-display);
  font-size: var(--font-2xl);
  font-weight: 400;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.auth-subtitle {
  font-size: var(--font-base);
  color: var(--text-secondary);
}

.auth-footer {
  position: absolute;
  bottom: 24px;
  font-size: var(--font-xs);
  color: var(--text-muted);
}

/* ── Responsive ── */
@media (max-width: 900px) {
  .auth-left {
    display: none;
  }

  .auth-right {
    width: 100%;
    border-left: none;
  }
}
</style>
