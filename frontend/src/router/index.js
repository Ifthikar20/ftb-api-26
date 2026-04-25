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

    /* ── Public Integrations Showcase ── */
    {
        path: '/integrations',
        name: 'public-integrations',
        component: () => import('@/pages/public/PublicIntegrationsPage.vue'),
        meta: { public: true }
    },
    {
        path: '/integration/:slug',
        name: 'integration-detail',
        component: () => import('@/pages/public/IntegrationDetailPage.vue'),
        meta: { public: true },
        props: true
    },

    /* ── Auth (public) ── */
    {
        path: '/login',
        name: 'login',
        component: () => import('@/pages/auth/LoginPage.vue'),
        meta: { layout: 'auth', guest: true }
    },
    // Sign-up disabled during beta — route redirects to login.
    {
        path: '/register',
        name: 'register',
        redirect: { name: 'login', query: { signupClosed: '1' } },
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

    protect('/heatmap/:websiteId', 'heatmap', () => import('@/pages/HeatmapPage.vue'), true),
    protect('/keywords/:websiteId', 'keywords', () => import('@/pages/KeywordsPage.vue'), true),
    protect('/campaigns/:websiteId', 'campaigns', () => import('@/pages/CampaignsPage.vue'), true),
    protect('/messaging/:websiteId', 'messaging', () => import('@/pages/MessagingPage.vue'), true),
    protect('/llm-ranking/:websiteId', 'llm-ranking', () => import('@/pages/LLMRankingPage.vue'), true),
    protect('/onboarding/:websiteId', 'onboarding', () => import('@/pages/OnboardingPage.vue'), true),
    protect('/app-onboarding', 'app-onboarding', () => import('@/pages/AppOnboardingPage.vue')),
    {
        path: '/paywall',
        name: 'paywall',
        component: () => import('@/pages/PaywallPage.vue'),
        meta: { requiresAuth: true, layout: 'auth' }
    },
    protect('/app/integrations', 'integrations', () => import('@/pages/IntegrationsPage.vue')),
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

// Routes exempt from the onboarding/paywall gate (user is mid-flow fixing their state)
const GATE_EXEMPT = new Set([
    'login', 'register', 'forgot-password', 'verify-email',
    'landing', 'terms', 'privacy', 'public-integrations', 'integration-detail',
    'onboarding', 'app-onboarding', 'paywall', 'not-found',
])

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
                    await auth.fetchSession()
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

    // Onboarding + paywall gate: authenticated users with incomplete setup
    // must finish onboarding and subscribe before reaching the app.
    if (auth.isAuthenticated && !GATE_EXEMPT.has(to.name)) {
        // Refresh session on transition into a protected route if we don't have one
        if (!auth.session) {
            await auth.fetchSession()
        }
        const route = auth.session?.next_route
        if (route === 'onboarding') {
            const wid = auth.session?.onboarding?.first_incomplete_website_id
            return next(wid ? { name: 'onboarding', params: { websiteId: wid } } : { name: 'app-onboarding' })
        }
        if (route === 'paywall') {
            return next({ name: 'paywall' })
        }
    }

    // Guard: project-specific pages require an active project
    const projectPages = ['analytics', 'leads', 'heatmap', 'keywords', 'campaigns', 'messaging', 'llm-ranking', 'website-detail']
    if (projectPages.includes(to.name) && auth.isAuthenticated) {
        const app = useAppStore()
        if (!app.activeWebsite) {
            return next({ name: 'websites' })
        }
    }

    next()
})

export default router
