import api from './client'

// REST client for the demand-side prompt library. The backend mounts
// these routes at /api/v1/prompt-library/ — see config/urls.py.
export default {
    getIndustries: () => api.get('/prompt-library/industries/'),

    getIndustryTrends: (slug) => api.get(`/prompt-library/industries/${slug}/trends/`),

    getPrompts: (params) => api.get('/prompt-library/prompts/', { params }),

    previewSample: (payload) =>
        api.post('/prompt-library/prompts/preview-sample/', payload),

    useLibrarySample: (auditId, payload) =>
        api.post(`/prompt-library/audits/${auditId}/use-library-sample/`, payload),

    getAuditSample: (auditId) =>
        api.get(`/prompt-library/audits/${auditId}/sample/`),

    listBrandPrompts: (websiteId) =>
        api.get(`/prompt-library/websites/${websiteId}/brand-prompts/`),

    addBrandPrompt: (websiteId, promptId, notes = '') =>
        api.post(`/prompt-library/websites/${websiteId}/brand-prompts/`, {
            prompt_id: promptId,
            notes,
        }),

    removeBrandPrompt: (brandPromptId) =>
        api.delete(`/prompt-library/brand-prompts/${brandPromptId}/`),
}
