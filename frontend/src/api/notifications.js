import api from './client'

export default {
    list: (params) => api.get('/notifications/', { params }),
    unread: () => api.get('/notifications/unread/'),
    markRead: (id) => api.put(`/notifications/${id}/read/`),
    markAllRead: () => api.post('/notifications/read-all/'),
    dismiss: (id) => api.delete(`/notifications/${id}/`),
    getPreferences: () => api.get('/notifications/preferences/'),
    updatePreferences: (data) => api.put('/notifications/preferences/', data),
}
