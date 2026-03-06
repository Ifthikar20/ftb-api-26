import api from './client'

export default {
    run: (wid) => api.post(`/audits/${wid}/run/`),
    status: (wid) => api.get(`/audits/${wid}/status/`),
    latest: (wid) => api.get(`/audits/${wid}/latest/`),
    history: (wid) => api.get(`/audits/${wid}/history/`),
    get: (wid, aid) => api.get(`/audits/${wid}/${aid}/`),
    issues: (wid, aid, params) => api.get(`/audits/${wid}/${aid}/issues/`, { params }),
    updateIssue: (wid, aid, iid, data) => api.put(`/audits/${wid}/${aid}/issues/${iid}/`, data),
    compare: (wid, params) => api.get(`/audits/${wid}/compare/`, { params }),
    getSchedule: (wid) => api.get(`/audits/${wid}/schedule/`),
    updateSchedule: (wid, data) => api.put(`/audits/${wid}/schedule/`, data),
}
