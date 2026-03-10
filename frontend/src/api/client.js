import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import router from '@/router'

const api = axios.create({
    baseURL: '/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true,
})

/* ── Request Interceptor ── */
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
    failedQueue.forEach(({ resolve, reject }) => {
        if (error) reject(error)
        else resolve(token)
    })
    failedQueue = []
}

api.interceptors.request.use((config) => {
    const auth = useAuthStore()
    if (auth.accessToken) {
        config.headers.Authorization = `Bearer ${auth.accessToken}`
    }

    // Add request tracing
    config.headers['X-Request-ID'] = crypto.randomUUID
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`

    return config
})

/* ── Response Interceptor ── */

// User-friendly fallback messages — never show raw errors
const FRIENDLY_MESSAGES = {
    400: 'Something didn\'t look right. Please check your input.',
    401: 'Your session has expired. Please log in again.',
    403: 'You don\'t have permission to do that.',
    404: 'We couldn\'t find what you\'re looking for.',
    409: 'This action conflicts with something already in progress.',
    429: 'You\'re making requests too quickly. Please wait a moment.',
    500: 'Something went wrong on our end. Please try again.',
    502: 'Our servers are temporarily unavailable. Please try again shortly.',
    503: 'This feature is temporarily unavailable. Please try again shortly.',
}

api.interceptors.response.use(
    (response) => {
        // Unwrap envelope: { success: true, data: ... }
        if (response.data && response.data.success !== undefined) {
            return response.data.data !== undefined ? response.data : response
        }
        return response
    },
    async (error) => {
        const originalRequest = error.config

        // 401 — try to refresh (silently, no toast)
        if (error.response?.status === 401 && !originalRequest._retry) {
            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject })
                }).then((token) => {
                    originalRequest.headers.Authorization = `Bearer ${token}`
                    return api(originalRequest)
                })
            }

            originalRequest._retry = true
            isRefreshing = true

            try {
                const { data } = await axios.post('/api/v1/auth/refresh/', {}, { withCredentials: true })
                const newToken = data.data?.access || data.access
                const auth = useAuthStore()
                auth.accessToken = newToken

                processQueue(null, newToken)
                originalRequest.headers.Authorization = `Bearer ${newToken}`
                return api(originalRequest)
            } catch (refreshError) {
                processQueue(refreshError, null)
                const auth = useAuthStore()
                auth.clearAuth()
                router.push({ name: 'login' })
                return Promise.reject(refreshError)
            } finally {
                isRefreshing = false
            }
        }

        // ── Extract user-friendly message ──
        const status = error.response?.status || 0
        const serverMessage = error.response?.data?.error?.message

        // Use the server's friendly message if it exists, otherwise use our fallback
        const displayMessage = serverMessage || FRIENDLY_MESSAGES[status] || FRIENDLY_MESSAGES[500]

        // Attach for page-level catch blocks to use
        error.displayMessage = displayMessage

        // ── Show toast automatically for most errors ──
        // Skip toasts for: 401 (handled above), cancelled requests, and network errors
        const skipToast = (
            status === 401 ||
            axios.isCancel(error) ||
            originalRequest?._silentError  // opt-in: api.get('/...', { _silentError: true })
        )

        if (!skipToast) {
            try {
                const toast = useToast()
                if (status === 429) {
                    toast.warning(displayMessage)
                } else if (status >= 500) {
                    toast.error(displayMessage)
                } else if (status === 403) {
                    toast.warning(displayMessage)
                } else {
                    toast.error(displayMessage)
                }
            } catch {
                // Toast composable may not be available outside Vue context
            }
        }

        return Promise.reject(error)
    }
)

export default api
