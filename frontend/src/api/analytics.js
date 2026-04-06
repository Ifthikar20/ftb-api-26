import api from './client'

export default {
    // Core
    overview: (wid, params) => api.get(`/analytics/${wid}/overview/`, { params }),
    pages: (wid, params) => api.get(`/analytics/${wid}/pages/`, { params }),
    sources: (wid, params) => api.get(`/analytics/${wid}/sources/`, { params }),
    realtime: (wid) => api.get(`/analytics/${wid}/realtime/`),
    heatmap: (wid, params) => api.get(`/analytics/${wid}/heatmap/`, { params }),

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
    insights: (wid) => api.get(`/analytics/${wid}/insights/`),

    // Live
    liveEvents: (wid) => api.get(`/analytics/${wid}/live/`),

    // Keywords
    keywords: (wid) => api.get(`/analytics/${wid}/keywords/`),
    addKeyword: (wid, data) => api.post(`/analytics/${wid}/keywords/`, data),
    keywordHistory: (wid, kid) => api.get(`/analytics/${wid}/keywords/${kid}/history/`),
    keywordTrending: (wid, params) => api.get(`/analytics/${wid}/keywords/trending/`, { params }),
    keywordScores: (wid) => api.get(`/analytics/${wid}/keywords/scores/`),
    keywordSuggestions: (wid) => api.get(`/analytics/${wid}/keywords/suggestions/`),
    keywordInterest: (wid, data) => api.post(`/analytics/${wid}/keywords/interest/`, data),
    keywordScan: (wid) => api.get(`/analytics/${wid}/keywords/scan/`),
    keywordScanTrigger: (wid) => api.post(`/analytics/${wid}/keywords/scan/`),
    seoEmbed: (wid) => api.get(`/analytics/${wid}/seo-embed/`),

    // Scan schedule config
    getScanConfig: (wid) => api.get(`/analytics/${wid}/keywords/scan-config/`),
    updateScanConfig: (wid, data) => api.put(`/analytics/${wid}/keywords/scan-config/`, data),

    // Platform content (social posts for keyword comparison)
    getPlatformContent: (wid, params) => api.get(`/analytics/${wid}/keywords/platform-content/`, { params }),
    addPlatformContent: (wid, data) => api.post(`/analytics/${wid}/keywords/platform-content/`, data),
    deletePlatformContent: (wid, pid) => api.delete(`/analytics/${wid}/keywords/platform-content/${pid}/`),

    // Keyword gap comparison
    keywordComparison: (wid) => api.get(`/analytics/${wid}/keywords/comparison/`),
}
