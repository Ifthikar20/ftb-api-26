import api from './client'

export default {
    list: () => api.get('/websites/'),
    create: (data) => api.post('/websites/', data),
    get: (id) => api.get(`/websites/${id}/`),
    update: (id, data) => api.put(`/websites/${id}/`, data),
    delete: (id) => api.delete(`/websites/${id}/`),
    getPixel: (id) => api.get(`/websites/${id}/pixel/`),
    verifyPixel: (id) => api.post(`/websites/${id}/pixel/verify/`),
    getHealth: (id) => api.get(`/websites/${id}/health/`),
    getSettings: (id) => api.get(`/websites/${id}/settings/`),
    updateSettings: (id, data) => api.put(`/websites/${id}/settings/`, data),
    getTeam: (id) => api.get(`/websites/${id}/team/`),
    inviteTeam: (id, data) => api.post(`/websites/${id}/team/invite/`, data),
}
