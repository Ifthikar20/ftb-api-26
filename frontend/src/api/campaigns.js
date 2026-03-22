import api from './client'

export default {
    list: (wid, params) => api.get(`/leads/${wid}/campaigns/`, { params }),
    create: (wid, data) => api.post(`/leads/${wid}/campaigns/`, data),
    get: (wid, cid) => api.get(`/leads/${wid}/campaigns/${cid}/`),
    update: (wid, cid, data) => api.put(`/leads/${wid}/campaigns/${cid}/`, data),
    delete: (wid, cid) => api.delete(`/leads/${wid}/campaigns/${cid}/`),
    send: (wid, cid) => api.post(`/leads/${wid}/campaigns/${cid}/send/`),
    stats: (wid, cid) => api.get(`/leads/${wid}/campaigns/${cid}/stats/`),
    recipients: (wid, cid) => api.get(`/leads/${wid}/campaigns/${cid}/recipients/`),
}
