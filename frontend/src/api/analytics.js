import api from './client'

export default {
    overview: (wid, params) => api.get(`/analytics/${wid}/overview/`, { params }),
    visitors: (wid, params) => api.get(`/analytics/${wid}/visitors/`, { params }),
    visitor: (wid, vid) => api.get(`/analytics/${wid}/visitors/${vid}/`),
    sources: (wid, params) => api.get(`/analytics/${wid}/sources/`, { params }),
    pages: (wid, params) => api.get(`/analytics/${wid}/pages/`, { params }),
    funnel: (wid) => api.get(`/analytics/${wid}/funnel/`),
    geo: (wid, params) => api.get(`/analytics/${wid}/geo/`, { params }),
    devices: (wid, params) => api.get(`/analytics/${wid}/devices/`, { params }),
    trends: (wid, params) => api.get(`/analytics/${wid}/trends/`, { params }),
    realtime: (wid) => api.get(`/analytics/${wid}/realtime/`),
}
