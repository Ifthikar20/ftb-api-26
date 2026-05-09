import api from './client'

export default {
    // Core
    overview: (wid, params) => api.get(`/analytics/${wid}/overview/`, { params }),
    pages: (wid, params) => api.get(`/analytics/${wid}/pages/`, { params }),
    sources: (wid, params) => api.get(`/analytics/${wid}/sources/`, { params }),
    realtime: (wid) => api.get(`/analytics/${wid}/realtime/`),

    // Advanced analytics
    chart: (wid, params) => api.get(`/analytics/${wid}/chart/`, { params }),
    devices: (wid, params) => api.get(`/analytics/${wid}/devices/`, { params }),
    countries: (wid, params) => api.get(`/analytics/${wid}/countries/`, { params }),

    // Funnels
    funnels: (wid) => api.get(`/analytics/${wid}/funnels/`),
    createFunnel: (wid, data) => api.post(`/analytics/${wid}/funnels/`, data),
    calculateFunnel: (wid, fid, params) => api.get(`/analytics/${wid}/funnels/${fid}/calculate/`, { params }),

    // Retention
    retention: (wid, params) => api.get(`/analytics/${wid}/retention/`, { params }),
    retentionCurve: (wid, params) => api.get(`/analytics/${wid}/retention/curve/`, { params }),
    engagement: (wid, params) => api.get(`/analytics/${wid}/retention/engagement/`, { params }),

    // Flows
    flows: (wid, params) => api.get(`/analytics/${wid}/flows/`, { params }),
    entryExit: (wid, params) => api.get(`/analytics/${wid}/entry-exit/`, { params }),
    journeys: (wid, params) => api.get(`/analytics/${wid}/journeys/`, { params }),

    // Visitors
    visitors: (wid, params) => api.get(`/analytics/${wid}/visitors/`, { params }),
    visitorTimeline: (wid, vid) => api.get(`/analytics/${wid}/visitors/${vid}/timeline/`),

    // AI Insights
    insights: (wid, params) => api.get(`/analytics/${wid}/insights/`, { params }),

    // Live
    liveEvents: (wid) => api.get(`/analytics/${wid}/live/`),

    // Dynamic SEO
    seoEmbed: (wid) => api.get(`/analytics/${wid}/seo-embed/`),
}
