import api from './client'

export default {
    /**
     * Suggest real competitor brands for a business based on its name + industry
     * + url + description. Backed by Claude Haiku via DiscoveryService.suggest.
     * Used during onboarding before any website exists in the DB.
     */
    suggest: (data) => api.post('/competitors/suggest/', data),

    list:    (wid) => api.get(`/competitors/${wid}/`),
    add:     (wid, data) => api.post(`/competitors/${wid}/`, data),
    discover:(wid) => api.get(`/competitors/${wid}/discover/`),
}
