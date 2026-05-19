<template>
  <AuthLayout title="Welcome back" subtitle="Sign in to your FetchBot account.">
    <form @submit.prevent="handleLogin" class="auth-form">
      <div v-if="error" class="form-alert form-alert-danger">{{ error }}</div>

      <div class="form-group">
        <label class="form-label">Email</label>
        <input v-model="email" type="email" class="form-input" placeholder="you@company.com" required />
      </div>

      <div class="form-group">
        <label class="form-label">Password</label>
        <div class="pw-field">
          <input
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            class="form-input pw-input"
            placeholder="••••••••"
            required
            autocomplete="current-password"
          />
          <button
            type="button"
            class="pw-toggle"
            :aria-label="showPassword ? 'Hide password' : 'Show password'"
            :aria-pressed="showPassword"
            @click="showPassword = !showPassword"
          >
            <svg v-if="showPassword" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>
      </div>

      <div class="form-row">
        <label class="checkbox-label">
          <input type="checkbox" v-model="remember" />
          <span>Remember me</span>
        </label>
        <router-link to="/forgot-password" class="form-link">Forgot password?</router-link>
      </div>

      <button type="submit" class="btn btn-primary w-full btn-lg" :disabled="loading">
        {{ loading ? 'Signing in...' : 'Sign In' }}
      </button>

      <div class="divider"><span>or</span></div>

      <button type="button" class="btn btn-secondary w-full" @click="handleGoogleLogin">
        Continue with Google
      </button>

      <p class="auth-switch" style="margin-top: -8px">
        <router-link to="/" style="font-weight: 500;">← Back to Home</router-link>
      </p>
    </form>
  </AuthLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AuthLayout from '@/layouts/AuthLayout.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const remember = ref(false)
const loading = ref(false)
const error = ref('')

// Auto-login from run_dev.sh token
onMounted(async () => {
  const autoToken = route.query.auto_token
  if (autoToken) {
    authStore.accessToken = autoToken
    try {
      const session = await authStore.fetchSession()
      const next = session?.next_route
      if (next === 'onboarding') {
        router.replace('/dashboard')
      } else if (next === 'paywall') {
        router.replace('/paywall')
      } else {
        router.replace('/dashboard')
      }
    } catch {
      authStore.accessToken = null
    }
  }
})

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    await authStore.login(email.value, password.value)
    const session = await authStore.fetchSession()
    const next = session?.next_route
    if (route.query.redirect) {
      router.push(route.query.redirect)
    } else if (next === 'onboarding') {
      router.push('/dashboard')
    } else if (next === 'paywall') {
      router.push('/paywall')
    } else {
      router.push('/dashboard')
    }
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message || 'Login failed.'
  } finally {
    loading.value = false
  }
}

function handleGoogleLogin() {
  // OAuth redirect placeholder
}
</script>

<style scoped>
.beta-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #1e293b;
  background: linear-gradient(135deg, #fef9c3, #fde68a);
  border: 1px solid #fcd34d;
  border-radius: 10px;
  padding: 10px 14px;
  margin-bottom: 16px;
  line-height: 1.4;
}
.beta-badge {
  display: inline-block;
  background: #1e293b;
  color: #fde68a;
  font-weight: 800;
  font-size: 10px;
  letter-spacing: 0.08em;
  padding: 3px 8px;
  border-radius: 999px;
  flex-shrink: 0;
}
.form-alert-info {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e3a8a;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  margin-bottom: 12px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-alert {
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: var(--font-sm);
  font-weight: 500;
}

.form-alert-danger {
  background: var(--color-danger-bg);
  color: var(--color-danger);
  border: 1px solid rgba(231, 76, 60, 0.2);
}

.form-row {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  font-size: var(--font-sm);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
  cursor: pointer;
}

.checkbox-label input {
  accent-color: var(--text-primary);
}

.form-link {
  color: var(--text-secondary);
  font-weight: 500;
  font-size: var(--font-sm);
}

.form-link:hover {
  color: var(--text-primary);
}

.divider {
  display: flex;
  align-items: center;
  gap: 16px;
  color: var(--text-muted);
  font-size: var(--font-xs);
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-color);
}

.auth-switch {
  text-align: center;
  font-size: var(--font-sm);
  color: var(--text-secondary);
}

.auth-switch a {
  color: var(--text-primary);
  font-weight: 600;
}

.pw-field { position: relative; }
.pw-input { padding-right: 44px; }
.pw-toggle {
  position: absolute;
  top: 50%;
  right: 8px;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm, 6px);
  transition: color 0.15s ease, background 0.15s ease;
}
.pw-toggle:hover { color: var(--text-primary); background: rgba(0, 0, 0, 0.04); }
.pw-toggle:focus-visible { outline: 2px solid var(--brand-accent, #ff6b35); outline-offset: 1px; }
</style>
