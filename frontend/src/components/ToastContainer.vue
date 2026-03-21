<template>
  <Teleport to="body">
    <div class="toast-container" v-if="toasts.length">
      <transition-group name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast-item"
          :class="[`toast-${toast.type}`, { 'toast-leaving': toast.leaving }]"
          @click="remove(toast.id)"
          role="alert"
        >
          <span class="toast-icon">{{ toast.icon }}</span>
          <span class="toast-message">{{ toast.message }}</span>
          <button class="toast-close" @click.stop="remove(toast.id)" aria-label="Close">×</button>
        </div>
      </transition-group>
    </div>
  </Teleport>
</template>

<script setup>
import { useToast } from '@/composables/useToast'
const { toasts, remove } = useToast()
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 10000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 420px;
  pointer-events: none;
}

.toast-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.4;
  cursor: pointer;
  pointer-events: auto;
  animation: toast-in 0.35s ease;
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: opacity 0.3s, transform 0.3s;
}

.toast-leaving {
  opacity: 0;
  transform: translateX(100%);
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.toast-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  flex-shrink: 0;
}

.toast-message { flex: 1; }

.toast-close {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  opacity: 0.5;
  padding: 0 2px;
  line-height: 1;
  transition: opacity 0.15s;
  flex-shrink: 0;
}
.toast-close:hover { opacity: 1; }

/* ── Type styles ── */
.toast-success {
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.25);
  color: #15803d;
}
.toast-success .toast-icon { background: #22c55e; color: #fff; }
.toast-success .toast-close { color: #15803d; }

.toast-error {
  background: rgba(239, 68, 68, 0.10);
  border: 1px solid rgba(239, 68, 68, 0.20);
  color: #b91c1c;
}
.toast-error .toast-icon { background: #ef4444; color: #fff; }
.toast-error .toast-close { color: #b91c1c; }

.toast-warning {
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.25);
  color: #92400e;
}
.toast-warning .toast-icon { background: #f59e0b; color: #fff; }
.toast-warning .toast-close { color: #92400e; }

.toast-info {
  background: rgba(59, 130, 246, 0.10);
  border: 1px solid rgba(59, 130, 246, 0.20);
  color: #1d4ed8;
}
.toast-info .toast-icon { background: #3b82f6; color: #fff; }
.toast-info .toast-close { color: #1d4ed8; }

/* Dark theme support */
[data-theme="dark"] .toast-success { color: #86efac; }
[data-theme="dark"] .toast-error { color: #fca5a5; }
[data-theme="dark"] .toast-warning { color: #fcd34d; }
[data-theme="dark"] .toast-info { color: #93c5fd; }
[data-theme="dark"] .toast-close { color: inherit; }

@media (max-width: 480px) {
  .toast-container {
    top: auto;
    bottom: 20px;
    right: 12px;
    left: 12px;
    max-width: 100%;
  }
}
</style>
