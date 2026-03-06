import api from './client'

export default {
    generate: (wid) => api.post(`/strategy/${wid}/generate/`),
    current: (wid) => api.get(`/strategy/${wid}/current/`),
    history: (wid) => api.get(`/strategy/${wid}/history/`),
    actions: (wid) => api.get(`/strategy/${wid}/actions/`),
    updateAction: (wid, aid, data) => api.put(`/strategy/${wid}/actions/${aid}/`, data),
    calendar: (wid, params) => api.get(`/strategy/${wid}/calendar/`, { params }),
    addCalendarEntry: (wid, data) => api.post(`/strategy/${wid}/calendar/`, data),
    generateCalendar: (wid) => api.post(`/strategy/${wid}/calendar/generate/`),
    chat: (wid, data) => api.post(`/strategy/${wid}/chat/`, data),
    chatHistory: (wid) => api.get(`/strategy/${wid}/chat/history/`),
    niche: (wid) => api.get(`/strategy/${wid}/niche/`),
    predictions: (wid) => api.get(`/strategy/${wid}/predictions/`),
    brief: (wid) => api.get(`/strategy/${wid}/brief/`),
    playbooks: () => api.get('/strategy/playbooks/'),
}
