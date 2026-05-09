import api from './client'

// REST client for the demand-side prompt library. The backend mounts
// these routes at /api/v1/prompt-library/ — see config/urls.py.
export default {
    getIndustries: () => api.get('/prompt-library/industries/'),

    getPrompts: (params) => api.get('/prompt-library/prompts/', { params }),

    previewSample: (payload) =>
        api.post('/prompt-library/prompts/preview-sample/', payload),

    useLibrarySample: (auditId, payload) =>
        api.post(`/prompt-library/audits/${auditId}/use-library-sample/`, payload),

    getAuditSample: (auditId) =>
        api.get(`/prompt-library/audits/${auditId}/sample/`),
}
