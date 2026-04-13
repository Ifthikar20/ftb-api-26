import api from './client'

export default {
    list: () => api.get('/notifications/integrations/'),
    connect: (data) => api.post('/notifications/integrations/', data),
    update: (id, data) => api.put(`/notifications/integrations/${id}/`, data),
    disconnect: (id) => api.delete(`/notifications/integrations/${id}/`),
}
