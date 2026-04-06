import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'

/* ── Helper: wrap a protected route in AppLayout ── */
const protect = (path, name, component, props = false) => ({
    path,
    component: () => import('@/layouts/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [{ path: '', name, component, props }]
})

const routes = [
    /* ── Public Landing Page ── */
    {
        path: '/',
        name: 'landing',
        component: () => import('@/pages/LandingPage.vue'),
        meta: { public: true }
    },
    {
        path: '/welcome',
        redirect: '/'
    },

    /* ── Legal (public) ── */
    {
        path: '/terms',
        name: 'terms',
        component: () => import('@/pages/legal/TermsPage.vue'),
        meta: { public: true }
    },
    {
        path: '/privacy',
        name: 'privacy',
        component: () => import('@/pages/legal/PrivacyPage.vue'),
        meta: { public: true }
    },

    /* ── Auth (public) ── */
    {
        path: '/login',
        name: 'login',
        component: () => import('@/pages/auth/LoginPage.vue'),
        meta: { layout: 'auth', guest: true }
    },
    {
        path: '/register',
        name: 'register',
        component: () => import('@/pages/auth/RegisterPage.vue'),
        meta: { layout: 'auth', guest: true }
    },
    {
        path: '/forgot-password',
        name: 'forgot-password',
        component: () => import('@/pages/auth/ForgotPasswordPage.vue'),
        meta: { layout: 'auth', guest: true }
    },
    {
        path: '/verify-email',
        name: 'verify-email',
        component: () => import('@/pages/auth/VerifyEmailPage.vue'),
        meta: { layout: 'auth', guest: true }
    },

    /* ── App (protected — each uses AppLayout) ── */
    protect('/dashboard', 'dashboard', () => import('@/pages/DashboardPage.vue')),
    protect('/websites', 'websites', () => import('@/pages/WebsitesListPage.vue')),
    protect('/websites/:id', 'website-detail', () => import('@/pages/WebsiteDetailPage.vue'), true),
    protect('/analytics/:websiteId', 'analytics', () => import('@/pages/AnalyticsPage.vue'), true),
    protect('/leads/:websiteId', 'leads', () => import('@/pages/LeadsPage.vue'), true),

    protect('/audits/:websiteId', 'audits', () => import('@/pages/AuditsPage.vue'), true),
    protect('/heatmap/:websiteId', 'heatmap', () => import('@/pages/HeatmapPage.vue'), true),
    protect('/keywords/:websiteId', 'keywords', () => import('@/pages/KeywordsPage.vue'), true),
    protect('/strategy/:websiteId', 'strategy', () => import('@/pages/StrategyPage.vue'), true),
    protect('/agents/:websiteId', 'agents', () => import('@/pages/AgentsPage.vue'), true),
    protect('/campaigns/:websiteId', 'campaigns', () => import('@/pages/CampaignsPage.vue'), true),
    protect('/voice-agent/:websiteId', 'voice-agent', () => import('@/pages/VoiceAgentPage.vue'), true),
    protect('/llm-ranking/:websiteId', 'llm-ranking', () => import('@/pages/LLMRankingPage.vue'), true),
    protect('/rewards', 'rewards', () => import('@/pages/RewardsPage.vue')),
    protect('/integrations', 'integrations', () => import('@/pages/IntegrationsPage.vue')),
    protect('/billing', 'billing', () => import('@/pages/BillingPage.vue')),
    protect('/settings', 'settings', () => import('@/pages/SettingsPage.vue')),

    /* ── 404 ── */
    {
        path: '/:pathMatch(.*)*',
        name: 'not-found',
        component: () => import('@/pages/NotFoundPage.vue')
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes,
    scrollBehavior() {
        return { top: 0 }
    }
})

let sessionRestored = false

router.beforeEach(async (to, from, next) => {
    const auth = useAuthStore()

    // On first load, try to restore session from refresh token cookie
    if (!sessionRestored && !auth.isAuthenticated) {
        sessionRestored = true
        const hadSession = localStorage.getItem('fb-session')
        if (hadSession) {
            try {
                await auth.refreshToken()
                if (auth.accessToken) {
                    await auth.fetchMe()
                }
            } catch {
                // No valid session — continue as guest
            }
        }
    }

    if (to.meta.requiresAuth && !auth.isAuthenticated) {
        return next({ name: 'login', query: { redirect: to.fullPath } })
    }

    // Public pages (like landing) are accessible to everyone
    if (to.meta.public) {
        return next()
    }

    // If guest visits a guest-only page (login/register) but is already logged in, go to dashboard
    if (to.meta.guest && auth.isAuthenticated) {
        return next({ name: 'dashboard' })
    }

    // Guard: project-specific pages require an active project
    const projectPages = ['analytics', 'leads', 'audits', 'heatmap', 'keywords', 'strategy', 'agents', 'campaigns', 'llm-ranking', 'voice-agent', 'website-detail']
    if (projectPages.includes(to.name) && auth.isAuthenticated) {
        const app = useAppStore()
        if (!app.activeWebsite) {
            return next({ name: 'websites' })
        }
    }

    next()
})

export default router
