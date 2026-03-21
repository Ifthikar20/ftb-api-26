<template>
  <AuthLayout title="Verify your email" :subtitle="`Enter the 6-digit code sent to ${email}`">
    <form @submit.prevent="handleVerify" class="auth-form">
      <div v-if="error" class="form-alert form-alert-danger">{{ error }}</div>

      <div class="form-group">
        <label class="form-label">Verification Code</label>
        <input v-model="otp" class="form-input otp-input" placeholder="000000" maxlength="6" required />
      </div>

      <button type="submit" class="btn btn-primary w-full btn-lg" :disabled="loading">
        {{ loading ? 'Verifying...' : 'Verify Email' }}
      </button>

      <p class="auth-switch">
        Didn't receive the code?
        <button type="button" class="resend-btn" @click="handleResend" :disabled="resending">
          {{ resending ? 'Sending...' : 'Resend code' }}
        </button>
      </p>
    </form>
  </AuthLayout>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AuthLayout from '@/layouts/AuthLayout.vue'
import authApi from '@/api/auth'

const router = useRouter()
const route = useRoute()
const email = ref(route.query.email || '')
const otp = ref('')
const loading = ref(false)
const resending = ref(false)
const error = ref('')

async function handleVerify() {
  loading.value = true
  error.value = ''
  try {
    await authApi.verifyEmail(email.value, otp.value)
    router.push('/login')
  } catch (e) {
    error.value = e.response?.data?.error?.message || 'Invalid or expired code.'
  } finally {
    loading.value = false
  }
}

async function handleResend() {
  resending.value = true
  try {
    await authApi.resendVerification(email.value)
  } catch {}
  resending.value = false
}
</script>

<style scoped>
.auth-form { display: flex; flex-direction: column; gap: 18px; }
.form-alert { padding: 12px 16px; border-radius: var(--radius-md); font-size: var(--font-sm); font-weight: 500; }
.form-alert-danger { background: var(--color-danger-bg); color: var(--color-danger); border: 1px solid rgba(231, 76, 60, 0.2); }
.otp-input { text-align: center; font-size: var(--font-2xl); letter-spacing: 0.4em; font-weight: 700; }
.auth-switch { text-align: center; font-size: var(--font-sm); color: var(--text-secondary); }
.resend-btn { background: none; border: none; color: var(--text-primary); font-weight: 600; cursor: pointer; font-family: var(--font-family); font-size: var(--font-sm); }
.resend-btn:hover { opacity: 0.7; }
</style>
