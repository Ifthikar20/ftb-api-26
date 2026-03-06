import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
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

        // 401 — try to refresh
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

        // Extract human-readable error
        const message =
            error.response?.data?.error?.message ||
            error.response?.data?.message ||
            error.message ||
            'Something went wrong'

        error.displayMessage = message
        return Promise.reject(error)
    }
)

export default api
