<template>
  <AuthLayout title="Create account" subtitle="Get started with FetchBot for free.">
    <form @submit.prevent="handleRegister" class="auth-form">
      <div v-if="error" class="form-alert form-alert-danger">{{ error }}</div>

      <div class="form-group">
        <label class="form-label">Full Name</label>
        <input v-model="fullName" class="form-input" placeholder="Jane Doe" required />
      </div>

      <div class="form-group">
        <label class="form-label">Email</label>
        <input v-model="email" type="email" class="form-input" placeholder="you@company.com" required />
      </div>

      <div class="form-group">
        <label class="form-label">Company</label>
        <input v-model="company" class="form-input" placeholder="Acme Corp" />
      </div>

      <div class="form-group">
        <label class="form-label">Password</label>
        <input v-model="password" type="password" class="form-input" placeholder="Min 12 characters" required />
      </div>

      <button type="submit" class="btn btn-primary w-full btn-lg" :disabled="loading">
        {{ loading ? 'Creating...' : 'Create Account' }}
      </button>

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
const company = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleRegister() {
  loading.value = true
  error.value = ''
  try {
    await authStore.register({ full_name: fullName.value, email: email.value, company_name: company.value, password: password.value })
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
.auth-switch { text-align: center; font-size: var(--font-sm); color: var(--text-secondary); }
.auth-switch a { color: var(--text-primary); font-weight: 600; }
</style>
