import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
    // Access token stored ONLY in memory (never localStorage) — spec requirement
    const accessToken = ref(null)
    const user = ref(null)
    const loading = ref(false)
    const session = ref(null)

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
            localStorage.setItem('fb-session', '1')
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
        localStorage.removeItem('fb-session')
    }

    async function fetchMe() {
        try {
            const { data } = await api.get('/auth/me/', { _silentError: true })
            user.value = data.data || data
            return user.value
        } catch (err) {
            // Only clear auth on a real auth failure (401). Network blips,
            // 500s, or transient errors should NOT log the user out — the
            // axios interceptor already handles 401-driven refresh; if that
            // fails it clears auth itself. Anything else, ignore here.
            const status = err?.response?.status
            if (status === 401 || status === 403) {
                clearAuth()
            }
        }
    }

    async function fetchSession() {
        try {
            const { data } = await api.get('/auth/session/', { _silentError: true })
            session.value = data.data || data
            if (session.value?.user) user.value = session.value.user
            return session.value
        } catch {
            session.value = null
            return null
        }
    }

    async function refreshToken() {
        try {
            const { data } = await api.post('/auth/refresh/', {}, { _silentError: true })
            const result = data.data || data
            accessToken.value = result.access
            localStorage.setItem('fb-session', '1')
            return result.access
        } catch (err) {
            // Only clear auth when the server actively says the
            // refresh cookie is no longer valid (401 / 403). Network
            // hiccups, 5xx blips, browser delays — none of those mean
            // the user is signed out, and clearing fb-session here
            // makes every subsequent page load skip the refresh attempt
            // entirely. Stay logged-in until the server says otherwise.
            const status = err?.response?.status
            if (status === 401 || status === 403) {
                clearAuth()
                localStorage.removeItem('fb-session')
            }
            // For anything else, leave fb-session alone so the next
            // navigation can retry the refresh.
            return null
        }
    }

    function clearAuth() {
        accessToken.value = null
        user.value = null
        session.value = null
        localStorage.removeItem('fb-session')
    }

    return {
        accessToken,
        user,
        session,
        loading,
        isAuthenticated,
        userInitials,
        login,
        register,
        logout,
        fetchMe,
        fetchSession,
        refreshToken,
        clearAuth,
    }
})
