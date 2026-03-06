import api from './client'

export default {
    list: (wid) => api.get(`/competitors/${wid}/`),
    add: (wid, data) => api.post(`/competitors/${wid}/`, data),
    discover: (wid) => api.get(`/competitors/${wid}/discover/`),
    get: (wid, cid) => api.get(`/competitors/${wid}/${cid}/`),
    remove: (wid, cid) => api.delete(`/competitors/${wid}/${cid}/`),
    compare: (wid) => api.get(`/competitors/${wid}/compare/`),
    keywords: (wid) => api.get(`/competitors/${wid}/keywords/`),
    keywordGaps: (wid) => api.get(`/competitors/${wid}/keywords/gaps/`),
    content: (wid) => api.get(`/competitors/${wid}/content/`),
    contentGaps: (wid) => api.get(`/competitors/${wid}/content/gaps/`),
    changes: (wid) => api.get(`/competitors/${wid}/changes/`),
    threats: (wid) => api.get(`/competitors/${wid}/threats/`),
}
