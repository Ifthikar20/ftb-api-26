import api from './client'

export default {
    list: (wid, params) => api.get(`/leads/${wid}/`, { params }),
    hot: (wid) => api.get(`/leads/${wid}/hot/`),
    get: (wid, lid) => api.get(`/leads/${wid}/${lid}/`),
    update: (wid, lid, data) => api.put(`/leads/${wid}/${lid}/`, data),
    addNote: (wid, lid, data) => api.post(`/leads/${wid}/${lid}/note/`, data),
    timeline: (wid, lid) => api.get(`/leads/${wid}/${lid}/timeline/`),
    export: (wid) => api.post(`/leads/${wid}/export/`),
    exportXlsx: (wid) => api.post(`/leads/${wid}/export/xlsx/`, {}, { responseType: 'blob' }),
    getScoring: (wid) => api.get(`/leads/${wid}/scoring/`),
    updateScoring: (wid, data) => api.put(`/leads/${wid}/scoring/`, data),
    segments: (wid) => api.get(`/leads/${wid}/segments/`),
    createSegment: (wid, data) => api.post(`/leads/${wid}/segments/`, data),
    aiSearch: (wid, data) => api.post(`/leads/${wid}/ai-search/`, data),
    sendEmail: (wid, lid, data) => api.post(`/leads/${wid}/${lid}/email/`, data),
    getEmails: (wid, lid) => api.get(`/leads/${wid}/${lid}/email/`),
}
