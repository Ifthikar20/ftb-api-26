<template>
  <div class="app-onboarding">
    <div class="onboarding-card">
      <h1 class="title">Welcome to FetchBot</h1>
      <p class="sub">Let's start by adding the website you want to track.</p>

      <form class="form" @submit.prevent="createWebsite">
        <label class="field">
          <span class="label">Website URL</span>
          <input
            v-model="url"
            type="url"
            class="input"
            placeholder="https://acme.com"
            required
            autofocus
          />
        </label>
        <label class="field">
          <span class="label">Business name</span>
          <input
            v-model="name"
            type="text"
            class="input"
            placeholder="Acme Corp"
            required
          />
        </label>

        <p v-if="error" class="error">{{ error }}</p>

        <button type="submit" class="cta" :disabled="loading">
          <span v-if="loading">Creating…</span>
          <span v-else>Continue</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import websitesApi from '@/api/websites'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const url = ref('')
const name = ref('')
const loading = ref(false)
const error = ref('')

async function createWebsite() {
  error.value = ''
  loading.value = true
  try {
    const res = await websitesApi.create({ url: url.value, name: name.value })
    const data = res.data?.data || res.data
    const websiteId = data?.id
    if (!websiteId) {
      error.value = "Couldn't create website. Please try again."
      return
    }
    await authStore.fetchSession()
    router.replace(`/onboarding/${websiteId}`)
  } catch (e) {
    error.value = e.response?.data?.error?.message || e.message || 'Something went wrong.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.app-onboarding {
  min-height: 100vh;
  background: var(--bg-primary, #0b0d12);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.onboarding-card {
  width: 100%;
  max-width: 480px;
  background: var(--bg-surface, #15181f);
  border: 1px solid var(--border-subtle, #2a2f3a);
  border-radius: 14px;
  padding: 40px;
}

.title {
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.sub {
  color: var(--text-muted);
  margin: 0 0 28px;
}

.form { display: flex; flex-direction: column; gap: 16px; }

.field { display: flex; flex-direction: column; gap: 6px; }

.label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-muted);
}

.input {
  padding: 10px 12px;
  background: var(--bg-primary, #0b0d12);
  border: 1px solid var(--border-subtle, #2a2f3a);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 0.95rem;
}

.input:focus {
  outline: none;
  border-color: var(--color-primary, #6366f1);
}

.cta {
  margin-top: 8px;
  padding: 12px 16px;
  background: var(--color-primary, #6366f1);
  color: white;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
}

.cta:disabled { opacity: 0.6; cursor: wait; }

.error { color: var(--color-danger, #ef4444); font-size: 0.9rem; margin: 0; }
</style>
