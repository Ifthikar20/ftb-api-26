import api from './client'

export default {
    listAudits: (wid, params) => api.get(`/llm-ranking/${wid}/audits/`, { params }),
    runAudit: (wid, data) => api.post(`/llm-ranking/${wid}/audits/`, data),
    getAudit: (wid, aid) => api.get(`/llm-ranking/${wid}/audits/${aid}/`),
    deleteAudit: (wid, aid) => api.delete(`/llm-ranking/${wid}/audits/${aid}/`),
    breakdown: (wid, aid) => api.get(`/llm-ranking/${wid}/audits/${aid}/breakdown/`),
    recommendations: (wid, aid) => api.get(`/llm-ranking/${wid}/audits/${aid}/recommendations/`),
    history: (wid, params) => api.get(`/llm-ranking/${wid}/history/`, { params }),
    providerHealth: () => api.get(`/llm-ranking/provider-health/`),
}
