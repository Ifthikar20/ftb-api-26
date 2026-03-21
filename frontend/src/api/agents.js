import api from './client'

export default {
    // Agent types
    types: () => api.get('/agents/types/'),

    // Activity feed (cross-website)
    activity: () => api.get('/agents/activity/'),

    // Runs for a website
    runs: (websiteId) => api.get(`/agents/${websiteId}/runs/`),
    runDetail: (websiteId, runId) => api.get(`/agents/${websiteId}/runs/${runId}/`),
    trigger: (websiteId, agentType) => api.post(`/agents/${websiteId}/runs/`, { agent_type: agentType }),
    approve: (websiteId, runId) => api.post(`/agents/${websiteId}/runs/${runId}/approve/`),
    cancel: (websiteId, runId) => api.post(`/agents/${websiteId}/runs/${runId}/cancel/`),
}
