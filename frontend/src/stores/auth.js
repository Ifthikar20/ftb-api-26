import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
    // Access token stored ONLY in memory (never localStorage) — spec requirement
    const accessToken = ref(null)
    const user = ref(null)
    const loading = ref(false)

    const isAuthenticated = computed(() => !!accessToken.value)
    const userInitials = computed(() => {
        if (!user.value?.full_name) return '?'
        return user.value.full_name
            .split(' ')
            .map(n => n[0])
            .join('')
            .toUpperCase()
            .slice(0, 2)
    })

    async function login(email, password) {
        loading.value = true
        try {
            const { data } = await api.post('/auth/login/', { email, password })
            const result = data.data || data
            accessToken.value = result.access
            user.value = result.user
            return result
        } finally {
            loading.value = false
        }
    }

    async function register(payload) {
        loading.value = true
        try {
            const { data } = await api.post('/auth/register/', payload)
            return data.data || data
        } finally {
            loading.value = false
        }
    }

    async function logout() {
        try {
            await api.post('/auth/logout/')
        } catch { /* ignore */ }
        clearAuth()
    }

    async function fetchMe() {
        try {
            const { data } = await api.get('/auth/me/', { _silentError: true })
            user.value = data.data || data
            return user.value
        } catch {
            clearAuth()
        }
    }

    async function refreshToken() {
        try {
            const { data } = await api.post('/auth/refresh/', {}, { _silentError: true })
            const result = data.data || data
            accessToken.value = result.access
            return result.access
        } catch {
            clearAuth()
        }
    }

    function clearAuth() {
        accessToken.value = null
        user.value = null
    }

    return {
        accessToken,
        user,
        loading,
        isAuthenticated,
        userInitials,
        login,
        register,
        logout,
        fetchMe,
        refreshToken,
        clearAuth,
    }
})
