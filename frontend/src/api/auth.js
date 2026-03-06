import api from './client'

export default {
    login: (data) => api.post('/auth/login/', data),
    register: (data) => api.post('/auth/register/', data),
    logout: () => api.post('/auth/logout/'),
    refresh: () => api.post('/auth/refresh/'),
    verifyEmail: (data) => api.post('/auth/verify-email/', data),
    resendVerification: (data) => api.post('/auth/resend-verification/', data),
    forgotPassword: (data) => api.post('/auth/forgot-password/', data),
    resetPassword: (data) => api.post('/auth/reset-password/', data),
    changePassword: (data) => api.post('/auth/change-password/', data),
    googleAuth: (data) => api.post('/auth/google/', data),
    getMe: () => api.get('/auth/me/'),
    updateMe: (data) => api.put('/auth/me/', data),
    deleteMe: () => api.delete('/auth/me/'),
    exportData: () => api.get('/auth/me/export/'),
}
