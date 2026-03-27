<template>
  <AuthLayout title="Create your account" subtitle="Start your free 7-day trial — no credit card required.">
    <form @submit.prevent="handleRegister" class="auth-form">
      <div v-if="error" class="form-alert form-alert-danger">{{ error }}</div>

      <!-- ── Trial Banner ── -->
      <div class="trial-banner">
        <div class="trial-icon">🚀</div>
        <div class="trial-text">
          <strong>7 days free</strong> — full access to all features.
          <span class="trial-sub">No commitment. Cancel anytime.</span>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Full Name</label>
        <input v-model="fullName" class="form-input" placeholder="Jane Doe" required />
      </div>

      <div class="form-group">
        <label class="form-label">Email</label>
        <input v-model="email" type="email" class="form-input" placeholder="you@company.com" required />
      </div>

      <div class="form-group">
        <label class="form-label">Password</label>
        <input v-model="password" type="password" class="form-input" placeholder="Min 12 characters" required />
      </div>

      <button type="submit" class="btn btn-primary w-full btn-lg" :disabled="loading">
        {{ loading ? 'Creating...' : 'Start Free Trial' }}
      </button>

      <p class="auth-terms">
        By signing up you agree to our <a href="/terms" target="_blank">Terms</a> and <a href="/privacy" target="_blank">Privacy Policy</a>.
      </p>

      <p class="auth-switch">
        Already have an account? <router-link to="/login">Sign in</router-link>
      </p>
    </form>
  </AuthLayout>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AuthLayout from '@/layouts/AuthLayout.vue'

const router = useRouter()
const authStore = useAuthStore()

const fullName = ref('')
const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleRegister() {
  loading.value = true
  error.value = ''
  try {
    await authStore.register({
      full_name: fullName.value,
      email: email.value,
      password: password.value,
      segment: 'individual',  // Everyone starts as individual
    })
    router.push({ path: '/verify-email', query: { email: email.value } })
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message || 'Registration failed.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-form { display: flex; flex-direction: column; gap: 18px; }

.form-alert { padding: 12px 16px; border-radius: var(--radius-md); font-size: var(--font-sm); font-weight: 500; }
.form-alert-danger { background: var(--color-danger-bg); color: var(--color-danger); border: 1px solid rgba(231, 76, 60, 0.2); }

.auth-switch { text-align: center; font-size: var(--font-sm); color: var(--text-secondary); margin: 0; }
.auth-switch a { color: var(--text-primary); font-weight: 600; }

.auth-terms {
  text-align: center;
  font-size: 0.72rem;
  color: var(--text-muted);
  margin: -6px 0 0;
  line-height: 1.5;
}
.auth-terms a {
  color: var(--text-secondary);
  text-decoration: underline;
  text-underline-offset: 2px;
}

/* ── Trial Banner ── */
.trial-banner {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.08), rgba(99, 102, 241, 0.06));
  border: 1px solid rgba(139, 92, 246, 0.15);
}

.trial-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.trial-text {
  font-size: var(--font-sm);
  color: var(--text-primary);
  font-weight: 600;
  line-height: 1.5;
}

.trial-sub {
  display: block;
  font-weight: 400;
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 1px;
}
</style>
