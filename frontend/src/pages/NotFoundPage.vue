<template>
  <div class="not-found fade-in">
    <div class="empty-state">
      <div class="empty-state-icon"><svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="var(--text-muted)" stroke-width="1.5"><circle cx="20" cy="20" r="14"/><path d="M30 30l12 12"/></svg></div>
      <h1 class="empty-state-title">Page Not Found</h1>
      <p class="empty-state-desc">The page you're looking for doesn't exist or has been moved.</p>
      <button class="btn btn-primary" @click="$router.push('/dashboard')">Go to Dashboard</button>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
}
</style>
