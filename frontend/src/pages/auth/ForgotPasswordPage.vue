<template>
  <AuthLayout title="Forgot password?" subtitle="Enter your email and we'll send you a reset link.">
    <form @submit.prevent="handleReset" class="auth-form">
      <div v-if="success" class="form-alert form-alert-success">{{ success }}</div>
      <div v-if="error" class="form-alert form-alert-danger">{{ error }}</div>

      <div class="form-group">
        <label class="form-label">Email</label>
        <input v-model="email" type="email" class="form-input" placeholder="you@company.com" required />
      </div>

      <button type="submit" class="btn btn-primary w-full btn-lg" :disabled="loading">
        {{ loading ? 'Sending...' : 'Send Reset Link' }}
      </button>

      <p class="auth-switch">
        <router-link to="/login">← Back to login</router-link>
      </p>
    </form>
  </AuthLayout>
</template>

<script setup>
import { ref } from 'vue'
import AuthLayout from '@/layouts/AuthLayout.vue'
import authApi from '@/api/auth'

const email = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')

async function handleReset() {
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    await authApi.forgotPassword(email.value)
    success.value = 'If an account exists with that email, a reset link has been sent.'
  } catch (e) {
    error.value = e.response?.data?.error?.message || 'Something went wrong.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-form { display: flex; flex-direction: column; gap: 18px; }
.form-alert { padding: 12px 16px; border-radius: var(--radius-md); font-size: var(--font-sm); font-weight: 500; }
.form-alert-danger { background: var(--color-danger-bg); color: var(--color-danger); border: 1px solid rgba(231, 76, 60, 0.2); }
.form-alert-success { background: var(--color-success-bg); color: var(--color-success); border: 1px solid rgba(39, 174, 96, 0.2); }
.auth-switch { text-align: center; font-size: var(--font-sm); }
.auth-switch a { color: var(--text-primary); font-weight: 600; }
</style>
