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

    // Prompt Library v2: redesigned card grid surface.
    createWebsitePrompt: (websiteId, payload) =>
        api.post(`/prompt-library/websites/${websiteId}/prompts/`, payload),

    preview: (promptId, websiteId) =>
        api.get(`/prompt-library/prompts/${promptId}/preview/`, {
            params: websiteId ? { website: websiteId } : {},
        }),

    effectiveness: (promptId) =>
        api.get(`/prompt-library/prompts/${promptId}/effectiveness/`),

    autoTemplate: (rawText) =>
        api.post('/prompt-library/prompts/auto-template/', { raw_text: rawText }),

    searchSources: (query) =>
        api.post('/prompt-library/prompts/search-sources/', { query }),

    smokeTest: (promptId, payload) =>
        api.post(`/prompt-library/prompts/${promptId}/smoke-test/`, payload),

    synthesize: (payload) =>
        api.post('/prompt-library/prompts/synthesize/', payload),

    generateFromContext: (payload) =>
        api.post('/prompt-library/prompts/generate-from-context/', payload),

    savePromptToWebsite: (websiteId, payload) =>
        api.post(`/prompt-library/websites/${websiteId}/prompts/`, payload),

    getVariables: (websiteId) =>
        api.get(`/prompt-library/websites/${websiteId}/variables/`),

    updateVariables: (websiteId, variables) =>
        api.put(`/prompt-library/websites/${websiteId}/variables/`, { variables }),

    enable: (promptId) =>
        api.post(`/prompt-library/prompts/${promptId}/enable/`),

    disable: (promptId) =>
        api.post(`/prompt-library/prompts/${promptId}/disable/`),
}
