import api from './client'

export default {
    // Lead source configuration
    getSources: (wid) => api.get(`/social-leads/${wid}/sources/`),
    createSource: (wid, data) => api.post(`/social-leads/${wid}/sources/`, data),
    updateSource: (wid, sid, data) => api.put(`/social-leads/${wid}/sources/${sid}/`, data),
    deleteSource: (wid, sid) => api.delete(`/social-leads/${wid}/sources/${sid}/`),

    // Social leads list
    getLeads: (wid, params) => api.get(`/social-leads/${wid}/leads/`, { params }),

    // LinkedIn manual sync
    syncLinkedIn: (wid, sid) => api.post(`/social-leads/${wid}/sources/${sid}/sync/linkedin/`),

    // X CSV import
    importX: (wid, rows) => api.post(`/social-leads/${wid}/import/x/`, { rows }),
}
