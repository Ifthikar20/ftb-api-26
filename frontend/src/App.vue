<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

onMounted(async () => {
  // Try to restore session from refresh token cookie on page load
  if (!auth.isAuthenticated) {
    try {
      await auth.refreshToken()
      if (auth.accessToken) {
        await auth.fetchMe()
      }
    } catch {
      // No valid refresh cookie — user stays logged out
    }
  }
})
</script>

<template>
  <router-view />
</template>
