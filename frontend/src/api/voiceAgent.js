import api from './client'

export default {
    // Agent config
    getConfig: (wid) => api.get(`/voice-agent/${wid}/config/`),
    updateConfig: (wid, data) => api.put(`/voice-agent/${wid}/config/`, data),
    activate: (wid, action) => api.post(`/voice-agent/${wid}/activate/`, { action }),
    createWebCall: (wid) => api.post(`/voice-agent/${wid}/web-call/`),

    // Call logs
    getCalls: (wid, params) => api.get(`/voice-agent/${wid}/calls/`, { params }),
    getCall: (wid, callId) => api.get(`/voice-agent/${wid}/calls/${callId}/`),
    getCallStats: (wid) => api.get(`/voice-agent/${wid}/calls/stats/`),

    // Calendar
    getEvents: (wid, params) => api.get(`/voice-agent/${wid}/calendar/`, { params }),
    createEvent: (wid, data) => api.post(`/voice-agent/${wid}/calendar/`, data),
    getEvent: (wid, eid) => api.get(`/voice-agent/${wid}/calendar/${eid}/`),
    updateEvent: (wid, eid, data) => api.put(`/voice-agent/${wid}/calendar/${eid}/`, data),
    cancelEvent: (wid, eid) => api.delete(`/voice-agent/${wid}/calendar/${eid}/`),
    getAvailability: (wid, date) => api.get(`/voice-agent/${wid}/calendar/availability/`, { params: { date } }),

    // Callback reminders
    getReminders: (wid) => api.get(`/voice-agent/${wid}/reminders/`),
    createReminder: (wid, data) => api.post(`/voice-agent/${wid}/reminders/`, data),
    updateReminder: (wid, rid, data) => api.put(`/voice-agent/${wid}/reminders/${rid}/`, data),

    // Todos (AI-extracted action items from calls)
    getTodos: (wid, params) => api.get(`/voice-agent/${wid}/todos/`, { params }),
    getTodoStats: (wid) => api.get(`/voice-agent/${wid}/todos/stats/`),
    updateTodo: (wid, tid, data) => api.put(`/voice-agent/${wid}/todos/${tid}/`, data),

    // Call extraction (AI analysis)
    getExtraction: (wid, callId) => api.get(`/voice-agent/${wid}/calls/${callId}/extraction/`),

    // Phone numbers
    getPhoneNumbers: (wid) => api.get(`/voice-agent/${wid}/phone-numbers/`),
    addPhoneNumber: (wid, data) => api.post(`/voice-agent/${wid}/phone-numbers/`, data),
    updatePhoneNumber: (wid, nid, data) => api.put(`/voice-agent/${wid}/phone-numbers/${nid}/`, data),
    deletePhoneNumber: (wid, nid) => api.delete(`/voice-agent/${wid}/phone-numbers/${nid}/`),
    startPhoneVerification: (wid, data) => api.post(`/voice-agent/${wid}/phone-numbers/verify/start/`, data),
    confirmPhoneVerification: (wid, data) => api.post(`/voice-agent/${wid}/phone-numbers/verify/confirm/`, data),

    // Usage / billing
    getUsage: (wid, params) => api.get(`/voice-agent/${wid}/usage/`, { params }),

    // Lead detection (transcript-based)
    getPossibleLeads: (wid, params) => api.get(`/voice-agent/${wid}/lead-detection/`, { params }),
    promotePossibleLead: (wid, callId) => api.post(`/voice-agent/${wid}/lead-detection/${callId}/`, { action: 'promote' }),
    dismissPossibleLead: (wid, callId) => api.post(`/voice-agent/${wid}/lead-detection/${callId}/`, { action: 'dismiss' }),

    // Agent context documents (knowledge base)
    getContextDocs: (wid) => api.get(`/voice-agent/${wid}/context-docs/`),
    createContextDoc: (wid, data) => api.post(`/voice-agent/${wid}/context-docs/`, data),
    uploadContextDoc: (wid, file, title) => {
        const fd = new FormData()
        fd.append('file', file)
        if (title) fd.append('title', title)
        return api.post(`/voice-agent/${wid}/context-docs/upload/`, fd, {
            headers: { 'Content-Type': 'multipart/form-data' },
        })
    },
    updateContextDoc: (wid, did, data) => api.put(`/voice-agent/${wid}/context-docs/${did}/`, data),
    deleteContextDoc: (wid, did) => api.delete(`/voice-agent/${wid}/context-docs/${did}/`),

    // Onboarding: starter templates + setup checklist
    listTemplates: (segment) => api.get('/voice-agent/onboarding/templates/', { params: segment ? { segment } : {} }),
    previewTemplate: (wid, slug) => api.get(`/voice-agent/${wid}/onboarding/templates/${slug}/preview/`),
    applyTemplate: (wid, slug) => api.post(`/voice-agent/${wid}/onboarding/templates/${slug}/apply/`),
    getSetupStatus: (wid) => api.get(`/voice-agent/${wid}/onboarding/setup-status/`),

    // Outbound campaigns
    listCampaigns: (wid, params) => api.get(`/voice-agent/${wid}/campaigns/`, { params }),
    createCampaign: (wid, data) => api.post(`/voice-agent/${wid}/campaigns/`, data),
    getCampaign: (wid, cid) => api.get(`/voice-agent/${wid}/campaigns/${cid}/`),
    updateCampaign: (wid, cid, data) => api.put(`/voice-agent/${wid}/campaigns/${cid}/`, data),
    deleteCampaign: (wid, cid) => api.delete(`/voice-agent/${wid}/campaigns/${cid}/`),
    startCampaign: (wid, cid) => api.post(`/voice-agent/${wid}/campaigns/${cid}/start/`),
    pauseCampaign: (wid, cid) => api.post(`/voice-agent/${wid}/campaigns/${cid}/pause/`),

    // Campaign targets
    listTargets: (wid, cid, params) => api.get(`/voice-agent/${wid}/campaigns/${cid}/targets/`, { params }),
    addTarget: (wid, cid, data) => api.post(`/voice-agent/${wid}/campaigns/${cid}/targets/`, data),
    uploadTargets: (wid, cid, file) => {
        const fd = new FormData()
        fd.append('file', file)
        return api.post(`/voice-agent/${wid}/campaigns/${cid}/targets/upload/`, fd, {
            headers: { 'Content-Type': 'multipart/form-data' },
        })
    },

    // Ad-hoc single outbound call
    callNow: (wid, data) => api.post(`/voice-agent/${wid}/call-now/`, data),
}
