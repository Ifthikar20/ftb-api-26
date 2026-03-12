import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import analyticsApi from '@/api/analytics'

const STALE_MS = 30_000 // 30 seconds before re-fetch
const POLL_MS = 30_000 // auto-refresh every 30 seconds

export const useAnalyticsStore = defineStore('analytics', () => {
    // ── Per-website cache: { [websiteId]: { overview, chart, ... , _ts: { overview: Date } } }
    const cache = ref({})

    // Currently active website
    const activeWebsiteId = ref(null)
    const activePeriod = ref('30d')
    const activeTab = ref('overview')
    const initialLoading = ref(true) // only true until first data arrives
    const refreshing = ref(false)    // true during background refresh

    // ── Helpers ──
    function _key(wid) {
        const k = wid || activeWebsiteId.value
        if (!cache.value[k]) {
            cache.value[k] = {
                stats: [], chartData: [], topPages: [], sources: [], devices: [],
                countries: [], realtimeVisitors: 0, noData: false,
                funnelList: [], funnelResult: null,
                retentionData: {}, engagementData: {}, flowData: {}, entryExitData: {},
                journeys: [], liveEvents: [],
                insightsData: {}, visitorList: [], timelineEvents: [],
                _ts: {},
            }
        }
        return cache.value[k]
    }

    function isStale(section, wid) {
        const ts = _key(wid)._ts[section]
        return !ts || (Date.now() - ts > STALE_MS)
    }

    function hasData(wid) {
        const c = _key(wid)
        return c.stats.length > 0 || c.chartData.length > 0
    }

    // ── Computed getters (read from active website cache) ──
    const data = computed(() => _key())

    // ── Fetch functions ──
    async function fetchOverview(wid, period, { force = false } = {}) {
        wid = wid || activeWebsiteId.value
        period = period || activePeriod.value
        if (!wid) return

        if (!force && !isStale('overview', wid) && hasData(wid)) {
            return // cached and fresh
        }

        const isFirst = !hasData(wid)
        if (isFirst) initialLoading.value = true
        else refreshing.value = true

        try {
            const [overviewRes, chartRes, pagesRes, sourcesRes, devicesRes, countriesRes] = await Promise.allSettled([
                analyticsApi.overview(wid, { period }),
                analyticsApi.chart(wid, { period }),
                analyticsApi.pages(wid, { period }),
                analyticsApi.sources(wid, { period }),
                analyticsApi.devices(wid, { period }),
                analyticsApi.countries(wid, { period }),
            ])

            const c = _key(wid)
            const unwrap = (r) => r.status === 'fulfilled' ? (r.value?.data?.data ?? r.value?.data ?? {}) : {}
            const unwrapArr = (r) => {
                const d = unwrap(r)
                return Array.isArray(d) ? d : []
            }

            const o = unwrap(overviewRes)

            c.stats = [
                { label: 'Unique Visitors', value: (o.total_visitors || 0).toLocaleString(), trend: o.visitor_growth_pct || 0, highlight: true },
                { label: 'Page Views', value: (o.total_pageviews || 0).toLocaleString(), trend: o.pageviews_trend || 0 },
                { label: 'Avg. Session', value: o.avg_session || '0:00', trend: o.session_trend || 0 },
                { label: 'Bounce Rate', value: (o.bounce_rate || '0') + '%', trend: o.bounce_trend || 0 },
            ]

            c.chartData = unwrapArr(chartRes)

            const pd = unwrapArr(pagesRes)
            c.topPages = pd.map(p => ({ url: p.url || p.page, views: p.views || p.count || 0 }))

            const sd = unwrapArr(sourcesRes)
            const sourceColors = ['#c9a050', '#1a1a2e', '#27ae60', '#2980b9', '#e74c3c']
            c.sources = sd.map((s, i) => ({
                name: s.source || s.name || 'direct',
                pct: s.percentage || s.pct || 0,
                sessions: s.sessions || s.count || 0,
                color: sourceColors[i % sourceColors.length],
            }))

            c.devices = unwrapArr(devicesRes)
            c.countries = unwrapArr(countriesRes)
            c.realtimeVisitors = o.realtime || 0
            c.noData = !c.chartData.length && !c.topPages.length && !c.sources.length

            c._ts.overview = Date.now()
        } catch {
            // Keep cached data on error
        } finally {
            initialLoading.value = false
            refreshing.value = false
        }
    }

    async function fetchFunnels(wid) {
        wid = wid || activeWebsiteId.value
        if (!wid || !isStale('funnels', wid)) return
        try {
            const res = await analyticsApi.funnels(wid)
            _key(wid).funnelList = res.data?.data || res.data || []
            _key(wid)._ts.funnels = Date.now()
        } catch { /* keep cached */ }
    }

    async function runFunnel(wid, fid, period) {
        wid = wid || activeWebsiteId.value
        try {
            const res = await analyticsApi.calculateFunnel(wid, fid, { period: period || activePeriod.value })
            _key(wid).funnelResult = res.data?.data || res.data || null
        } catch { /* keep cached */ }
    }

    async function createFunnel(wid, payload) {
        wid = wid || activeWebsiteId.value
        await analyticsApi.createFunnel(wid, payload)
        _key(wid)._ts.funnels = 0 // force re-fetch
        await fetchFunnels(wid)
    }

    async function fetchRetention(wid) {
        wid = wid || activeWebsiteId.value
        if (!wid || !isStale('retention', wid)) return
        try {
            const [retRes, engRes] = await Promise.all([
                analyticsApi.retention(wid, { weeks: 8 }),
                analyticsApi.engagement(wid, { period: activePeriod.value }),
            ])
            _key(wid).retentionData = retRes.data?.data || retRes.data || {}
            _key(wid).engagementData = engRes.data?.data || engRes.data || {}
            _key(wid)._ts.retention = Date.now()
        } catch { /* keep cached */ }
    }

    async function fetchFlows(wid, period) {
        wid = wid || activeWebsiteId.value
        if (!wid || !isStale('flows', wid)) return
        try {
            const [flowRes, eeRes, journeyRes] = await Promise.all([
                analyticsApi.flows(wid, { period: period || activePeriod.value }),
                analyticsApi.entryExit(wid, { period: period || activePeriod.value }),
                analyticsApi.journeys(wid, { period: period || activePeriod.value }),
            ])
            _key(wid).flowData = flowRes.data?.data || flowRes.data || {}
            _key(wid).entryExitData = eeRes.data?.data || eeRes.data || {}
            _key(wid).journeys = journeyRes.data?.data || journeyRes.data || []
            _key(wid)._ts.flows = Date.now()
        } catch { /* keep cached */ }
    }

    async function fetchLiveEvents(wid) {
        wid = wid || activeWebsiteId.value
        if (!wid) return
        try {
            const res = await analyticsApi.liveEvents(wid)
            _key(wid).liveEvents = res.data?.data || res.data || []
        } catch { /* keep cached */ }
    }

    async function fetchInsights(wid) {
        wid = wid || activeWebsiteId.value
        if (!wid || !isStale('insights', wid)) return
        try {
            const res = await analyticsApi.insights(wid)
            _key(wid).insightsData = res.data?.data || res.data || {}
            _key(wid)._ts.insights = Date.now()
        } catch { /* keep cached */ }
    }

    async function fetchVisitors(wid) {
        wid = wid || activeWebsiteId.value
        if (!wid || !isStale('visitors', wid)) return
        try {
            const res = await analyticsApi.visitors(wid)
            _key(wid).visitorList = res.data?.data || res.data || []
            _key(wid)._ts.visitors = Date.now()
        } catch { /* keep cached */ }
    }

    async function loadTimeline(wid, vid) {
        wid = wid || activeWebsiteId.value
        try {
            const res = await analyticsApi.visitorTimeline(wid, vid)
            _key(wid).timelineEvents = res.data?.data || res.data || []
        } catch { /* keep cached */ }
    }

    // ── Tab switching: show cached, refresh in background ──
    async function switchTab(tabId) {
        activeTab.value = tabId
        loadTabBackground()
    }

    async function loadTabBackground() {
        const tab = activeTab.value
        const wid = activeWebsiteId.value
        if (!wid) return
        try {
            if (tab === 'overview') await fetchOverview(wid, activePeriod.value)
            else if (tab === 'funnels') await fetchFunnels(wid)
            else if (tab === 'retention') await fetchRetention(wid)
            else if (tab === 'flows') await fetchFlows(wid)
            else if (tab === 'insights') await fetchInsights(wid)
            else if (tab === 'events') await fetchVisitors(wid)
        } catch { /* silent */ }
    }

    function init(wid, period) {
        activeWebsiteId.value = wid
        activePeriod.value = period || '30d'
    }

    function changePeriod(period) {
        activePeriod.value = period
        // Invalidate overview cache so it re-fetches with new period
        const c = _key()
        if (c._ts) {
            c._ts.overview = 0
            c._ts.flows = 0
        }
        loadTabBackground()
    }

    // ── Force refresh: invalidate all caches and re-fetch ──
    function forceRefresh() {
        const wid = activeWebsiteId.value
        if (!wid) return
        const c = _key(wid)
        // Clear ALL timestamps so every fetch runs fresh
        Object.keys(c._ts).forEach(k => { c._ts[k] = 0 })
        loadTabBackground()
    }

    // ── Auto-polling: keep data fresh while page is active ──
    let _pollTimer = null

    function startPolling() {
        stopPolling()
        _pollTimer = setInterval(() => {
            const wid = activeWebsiteId.value
            if (!wid) return
            // Invalidate current tab's cache and re-fetch
            const c = _key(wid)
            const tab = activeTab.value
            const section = tab === 'events' ? 'visitors' : tab
            if (c._ts[section]) c._ts[section] = 0
            if (tab === 'overview' && c._ts.overview) c._ts.overview = 0
            loadTabBackground()
        }, POLL_MS)
    }

    function stopPolling() {
        if (_pollTimer) {
            clearInterval(_pollTimer)
            _pollTimer = null
        }
    }

    // ── Manual sessionStorage persistence ──
    function saveToSession() {
        try {
            const payload = { cache: cache.value, activeWebsiteId: activeWebsiteId.value, activePeriod: activePeriod.value, activeTab: activeTab.value }
            sessionStorage.setItem('fb-analytics', JSON.stringify(payload))
        } catch { /* quota exceeded, ignore */ }
    }

    function restoreFromSession() {
        try {
            const raw = sessionStorage.getItem('fb-analytics')
            if (!raw) return
            const saved = JSON.parse(raw)
            if (saved.cache) cache.value = saved.cache
            if (saved.activeWebsiteId) activeWebsiteId.value = saved.activeWebsiteId
            if (saved.activePeriod) activePeriod.value = saved.activePeriod
            if (saved.activeTab) activeTab.value = saved.activeTab
            // If we restored data, skip the initial loading spinner
            if (hasData(activeWebsiteId.value)) initialLoading.value = false
        } catch { /* corrupt data, ignore */ }
    }

    // Restore on store creation
    restoreFromSession()

    return {
        cache, activeWebsiteId, activePeriod, activeTab,
        initialLoading, refreshing, data,
        init, switchTab, changePeriod, loadTabBackground,
        fetchOverview, fetchFunnels, runFunnel, createFunnel,
        fetchRetention, fetchFlows, fetchInsights, fetchVisitors,
        fetchLiveEvents, loadTimeline, saveToSession, forceRefresh, startPolling, stopPolling,
    }
})
