<template>
  <div class="greeting-banner">
    <img src="/images/forest-pixel.png" alt="" class="banner-bg" />
    <div class="banner-overlay"></div>
    <div class="banner-content">
      <div>
        <h1 class="greeting-title">Good {{ timeOfDay }}, {{ firstName }}</h1>
        <p class="greeting-sub">Here's what's happening with your marketing today.</p>
      </div>
      <router-link to="/websites" class="btn btn-primary">+ Add Project</router-link>
    </div>
  </div>
</template>

<script setup>
defineProps({
  timeOfDay: { type: String, required: true },
  firstName: { type: String, required: true },
})
</script>

<style scoped>
.greeting-banner {
  border-radius: var(--radius-lg);
  margin-bottom: 24px;
  position: relative;
  overflow: hidden;
  min-height: 140px;
  display: flex;
  align-items: flex-end;
  box-shadow: var(--shadow-card);
  animation: cardEntrance 400ms cubic-bezier(0.23, 1, 0.32, 1) forwards;
}

.banner-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 30%;
}

.banner-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to top,
    rgba(0, 0, 0, 0.7) 0%,
    rgba(0, 0, 0, 0.3) 50%,
    rgba(0, 0, 0, 0.1) 100%
  );
}

.banner-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  width: 100%;
  padding: 28px 32px;
  gap: 16px;
}

.greeting-title {
  font-family: var(--font-family);
  font-size: 1.5rem;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.02em;
  line-height: 1.3;
  text-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.greeting-sub {
  font-size: var(--font-sm);
  color: rgba(255, 255, 255, 0.8);
  margin-top: 4px;
  text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}

@media (max-width: 640px) {
  .greeting-banner { min-height: 120px; }
  .banner-content { flex-direction: column; align-items: flex-start; padding: 20px; }
}
</style>
