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
        <input v-model="password" type="password" class="form-input" placeholder="••••••••" required />
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

      <p class="auth-switch">
        Don't have an account? <router-link to="/register">Create one</router-link>
      </p>
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
const remember = ref(false)
const loading = ref(false)
const error = ref('')

// Auto-login from run_dev.sh token
onMounted(async () => {
  const autoToken = route.query.auto_token
  if (autoToken) {
    authStore.accessToken = autoToken
    try {
      await authStore.fetchMe()
      router.replace('/dashboard')
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
    router.push(route.query.redirect || '/dashboard')
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
  justify-content: space-between;
  align-items: center;
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
</style>
