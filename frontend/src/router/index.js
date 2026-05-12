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

    /* ── Public Integrations Showcase ── hidden for now; redirect to landing ── */
    { path: '/integrations',          redirect: '/' },
    { path: '/integration/:slug',     redirect: '/' },

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
    protect('/llm-ranking/:websiteId', 'llm-ranking', () => import('@/pages/LLMRankingPage.vue'), true),
    protect('/llm-ranking/:websiteId/prompts', 'prompt-library', () => import('@/pages/PromptLibraryPage.vue'), true),
    // /saved-prompts is preserved as a redirect to the Prompt Library 'Saved' tab
    {
        path: '/llm-ranking/:websiteId/saved-prompts',
        redirect: to => ({ path: `/llm-ranking/${to.params.websiteId}/prompts`, query: { tab: 'saved' } }),
    },
    protect('/llm-ranking/:websiteId/source-influence', 'source-influence', () => import('@/pages/SourceInfluencePage.vue'), true),
    protect('/llm-ranking/:websiteId/brand-vault', 'brand-vault', () => import('@/pages/BrandVaultPage.vue'), true),
    protect('/llm-ranking/:websiteId/content', 'content-studio', () => import('@/pages/ContentStudioPage.vue'), true),
    protect('/llm-ranking/:websiteId/content/drafts/:draftId', 'content-studio-draft', () => import('@/pages/DraftEditorPage.vue'), true),
    protect('/llm-ranking/:websiteId/content/publish-targets', 'content-studio-targets', () => import('@/pages/PublishTargetsPage.vue'), true),
    protect('/llm-ranking/:websiteId/content/roi', 'content-studio-roi', () => import('@/pages/ROIPage.vue'), true),
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

if (import.meta.env.DEV) {
    routes.unshift({
        path: '/design-system',
        name: 'design-system',
        component: () => import('@/pages/_DesignSystem.vue'),
    })
}

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
    'landing', 'terms', 'privacy',
    'onboarding', 'app-onboarding', 'paywall', 'not-found',
])

router.beforeEach(async (to, from, next) => {
    const auth = useAuthStore()

    // On first load, try to restore session from the refresh-token
    // cookie. We only flip `sessionRestored` to true once we either
    // succeed OR the server actively rejects the cookie (401/403).
    // A transient failure (network blip, 5xx) leaves the flag false
    // so the very next navigation tries again — otherwise the user
    // would be stuck on /login until a full reload.
    if (!sessionRestored && !auth.isAuthenticated) {
        const hadSession = localStorage.getItem('fb-session')
        if (hadSession) {
            try {
                await auth.refreshToken()
                if (auth.accessToken) {
                    await auth.fetchSession()
                    sessionRestored = true
                } else if (!localStorage.getItem('fb-session')) {
                    // refreshToken cleared fb-session — that means the
                    // server returned 401/403. No valid session.
                    sessionRestored = true
                }
                // else: transient failure; retry on next navigation.
            } catch {
                // Belt and braces — refreshToken catches its own errors,
                // but if anything else escapes we still don't lock the
                // user out permanently.
            }
        } else {
            sessionRestored = true
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
    const projectPages = ['analytics', 'llm-ranking', 'website-detail', 'source-influence', 'prompt-library', 'brand-vault', 'content-studio', 'content-studio-draft', 'content-studio-targets', 'content-studio-roi']
    if (projectPages.includes(to.name) && auth.isAuthenticated) {
        const app = useAppStore()
        if (!app.activeWebsite) {
            return next({ name: 'websites' })
        }
    }

    next()
})

export default router
