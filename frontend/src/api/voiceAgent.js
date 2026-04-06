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
}
