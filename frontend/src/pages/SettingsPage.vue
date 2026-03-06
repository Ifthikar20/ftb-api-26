<template>
  <div class="settings-page fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">Settings</h1>
        <p class="page-subtitle">Manage your account and preferences.</p>
      </div>
    </div>

    <div class="content-grid" style="grid-template-columns: 1fr">
      <!-- Profile -->
      <div class="card" style="margin-bottom:20px">
        <div class="card-header"><h3 class="card-title">Profile</h3></div>
        <form @submit.prevent="saveProfile" class="settings-form">
          <div class="form-group">
            <label class="form-label">Full Name</label>
            <input v-model="profile.full_name" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Email</label>
            <input v-model="profile.email" class="form-input" disabled />
          </div>
          <div class="form-group">
            <label class="form-label">Company</label>
            <input v-model="profile.company_name" class="form-input" />
          </div>
          <button type="submit" class="btn btn-primary btn-sm" :disabled="saving">{{ saving ? 'Saving...' : 'Save Changes' }}</button>
        </form>
      </div>

      <!-- Notification Preferences -->
      <div class="card" style="margin-bottom:20px">
        <div class="card-header"><h3 class="card-title">Notification Preferences</h3></div>
        <div class="settings-form">
          <label class="toggle-row">
            <span>Hot lead email alerts</span>
            <input type="checkbox" v-model="notifPrefs.hot_lead_email" @change="saveNotifPrefs" />
          </label>
          <label class="toggle-row">
            <span>Weekly report</span>
            <input type="checkbox" v-model="notifPrefs.weekly_report" @change="saveNotifPrefs" />
          </label>
          <label class="toggle-row">
            <span>Competitor change alerts</span>
            <input type="checkbox" v-model="notifPrefs.competitor_changes" @change="saveNotifPrefs" />
          </label>
          <label class="toggle-row">
            <span>Audit complete alerts</span>
            <input type="checkbox" v-model="notifPrefs.audit_complete" @change="saveNotifPrefs" />
          </label>
        </div>
      </div>

      <!-- Theme -->
      <div class="card">
        <div class="card-header"><h3 class="card-title">Appearance</h3></div>
        <div class="settings-form">
          <label class="toggle-row">
            <span>Dark Mode</span>
            <input type="checkbox" :checked="appStore.theme === 'dark'" @change="appStore.toggleTheme()" />
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import notificationsApi from '@/api/notifications'

const authStore = useAuthStore()
const appStore = useAppStore()
const saving = ref(false)

const profile = ref({
  full_name: '',
  email: '',
  company_name: '',
})

const notifPrefs = ref({
  hot_lead_email: true,
  weekly_report: true,
  competitor_changes: true,
  audit_complete: true,
})

onMounted(async () => {
  if (authStore.user) {
    profile.value = {
      full_name: authStore.user.full_name || '',
      email: authStore.user.email || '',
      company_name: authStore.user.company_name || '',
    }
  }
  try {
    const { data } = await notificationsApi.getPreferences()
    const d = data?.data || data
    if (d) notifPrefs.value = { ...notifPrefs.value, ...d }
  } catch {}
})

async function saveProfile() {
  saving.value = true
  try {
    // Would call auth API to update profile
    // For now, update local state
    if (authStore.user) {
      authStore.user.full_name = profile.value.full_name
      authStore.user.company_name = profile.value.company_name
    }
  } finally {
    saving.value = false
  }
}

async function saveNotifPrefs() {
  try {
    await notificationsApi.updatePreferences(notifPrefs.value)
  } catch {}
}
</script>

<style scoped>
.settings-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 480px;
}

.toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: var(--font-sm);
  color: var(--text-primary);
  cursor: pointer;
}

.toggle-row:last-child { border-bottom: none; }

.toggle-row input[type="checkbox"] {
  accent-color: var(--text-primary);
  width: 18px;
  height: 18px;
}
</style>
