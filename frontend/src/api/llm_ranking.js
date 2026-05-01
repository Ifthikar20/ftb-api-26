import api from './client'

export default {
    listAudits: (wid, params) => api.get(`/llm-ranking/${wid}/audits/`, { params }),
    previewPrompts: (wid, params) => api.get(`/llm-ranking/${wid}/preview-prompts/`, { params }),
    scanUrl: (wid, url) => api.post(`/llm-ranking/${wid}/scan-url/`, { url }),
    runAudit: (wid, data) => api.post(`/llm-ranking/${wid}/audits/`, data),
    preflight: (wid, data) => api.post(`/llm-ranking/${wid}/audits/preflight/`, data),
    getAudit: (wid, aid) => api.get(`/llm-ranking/${wid}/audits/${aid}/`),
    deleteAudit: (wid, aid) => api.delete(`/llm-ranking/${wid}/audits/${aid}/`),
    executeAudit: (wid, aid) => api.post(`/llm-ranking/${wid}/audits/${aid}/run/`),
    auditLogs: (wid, aid, params) => api.get(`/llm-ranking/${wid}/audits/${aid}/logs/`, { params }),
    breakdown: (wid, aid) => api.get(`/llm-ranking/${wid}/audits/${aid}/breakdown/`),
    recommendations: (wid, aid) => api.get(`/llm-ranking/${wid}/audits/${aid}/recommendations/`),
    // Prompt-level results with optional filters
    promptResults: (wid, aid, params) => api.get(`/llm-ranking/${wid}/audits/${aid}/prompts/`, { params }),
    // Per-provider detailed report
    providerDetail: (wid, aid, provider) => api.get(`/llm-ranking/${wid}/audits/${aid}/providers/${provider}/`),
    // Usage metering
    usage: (wid, params) => api.get(`/llm-ranking/${wid}/usage/`, { params }),
    // Per-provider configuration / health (only implemented providers returned)
    providerHealth: (wid) => api.get(`/llm-ranking/${wid}/provider-health/`),
    history: (wid, params) => api.get(`/llm-ranking/${wid}/history/`, { params }),
    // Schedule endpoints
    getSchedule: (wid) => api.get(`/llm-ranking/${wid}/schedule/`),
    saveSchedule: (wid, data) => api.post(`/llm-ranking/${wid}/schedule/`, data),
    deleteSchedule: (wid) => api.delete(`/llm-ranking/${wid}/schedule/`),
}
