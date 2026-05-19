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
    {
        path: '/dpa',
        name: 'dpa',
        component: () => import('@/pages/info/DpaPage.vue'),
        meta: { public: true }
    },
    {
        path: '/cookies',
        name: 'cookies',
        component: () => import('@/pages/info/CookiesPage.vue'),
        meta: { public: true }
    },
    {
        path: '/ai-policy',
        name: 'ai-policy',
        component: () => import('@/pages/info/AiPolicyPage.vue'),
        meta: { public: true }
    },

    /* ── Marketing / company (public) ── */
    {
        path: '/about',
        name: 'about',
        component: () => import('@/pages/info/AboutPage.vue'),
        meta: { public: true }
    },
    {
        path: '/contact',
        name: 'contact',
        component: () => import('@/pages/info/ContactPage.vue'),
        meta: { public: true }
    },
    {
        path: '/blog',
        name: 'blog',
        component: () => import('@/pages/info/BlogPage.vue'),
        meta: { public: true }
    },
    {
        path: '/changelog',
        name: 'changelog',
        component: () => import('@/pages/info/ChangelogPage.vue'),
        meta: { public: true }
    },
    {
        path: '/status',
        name: 'status',
        component: () => import('@/pages/info/StatusPage.vue'),
        meta: { public: true }
    },
    {
        path: '/docs',
        name: 'docs',
        component: () => import('@/pages/info/DocsPage.vue'),
        meta: { public: true }
    },
    {
        path: '/api',
        name: 'api-reference',
        component: () => import('@/pages/info/ApiReferencePage.vue'),
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
        // Public sign-up is closed — the only path to a real account
        // is admin-driven (scripts/create_test_user.py). Keep the route
        // alive so cached marketing links don't 404, but bounce to
        // /login.
        path: '/register',
        name: 'register',
        redirect: { name: 'login' },
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
    // Legacy /app-onboarding redirects to the dashboard. The
    // onboarding flow is now a modal overlay rendered by
    // DashboardPage when the session marks the user as needing
    // onboarding.
    { path: '/app-onboarding', redirect: { name: 'dashboard' } },
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
// Dashboard is intentionally included — the onboarding modal renders
// on top of the dashboard for first-run users, so the route gate must
// allow them through.
const GATE_EXEMPT = new Set([
    'login', 'register', 'forgot-password', 'verify-email',
    'landing', 'terms', 'privacy',
    'dashboard', 'paywall', 'not-found',
])

router.beforeEach(async (to, from, next) => {
    const auth = useAuthStore()

    // On first load, restore the session. Two paths:
    //   1. accessToken hydrated from localStorage — assume it's good
    //      and fetch /auth/me to confirm. If it 401s the interceptor
    //      will trigger a refresh-cookie attempt automatically.
    //   2. No token in storage — try refresh cookie directly.
    // sessionRestored only flips to true once we have a definitive
    // answer (success, or confirmed 401/403). Transient failures
    // leave it false so the next nav retries.
    if (!sessionRestored && !auth.isAuthenticated) {
        const hadSession = localStorage.getItem('fb-session')
        if (hadSession) {
            try {
                await auth.refreshToken()
                if (auth.accessToken) {
                    await auth.fetchSession()
                    sessionRestored = true
                } else if (!localStorage.getItem('fb-session')) {
                    sessionRestored = true
                }
            } catch {
                // belt + braces; refreshToken handles its own errors
            }
        } else {
            sessionRestored = true
        }
    } else if (!sessionRestored && auth.isAuthenticated) {
        // Access token came from localStorage — verify it works.
        // The interceptor handles 401 by attempting a refresh; if
        // that also fails it clears auth and bounces to login.
        sessionRestored = true
        auth.fetchSession().catch(() => {})
    }

    if (to.meta.requiresAuth && !auth.isAuthenticated) {
        return next({ name: 'login', query: { redirect: to.fullPath } })
    }

    // Public pages (like landing) are accessible to everyone
    if (to.meta.public) {
        return next()
    }

    // If guest visits a guest-only page (login/register) but is already
    // logged in, send them to the right next step.
    if (to.meta.guest && auth.isAuthenticated) {
        if (!auth.session) {
            try { await auth.fetchSession() } catch (_) {}
        }
        const route = auth.session?.next_route
        if (route === 'onboarding') return next({ name: 'dashboard' })
        if (route === 'paywall') return next({ name: 'paywall' })
        return next({ name: 'dashboard' })
    }

    // Funnel gate: onboarding first (modal on /dashboard), then paywall
    // (its own route), then the app. The user has to walk through each
    // gate in order — they cannot reach /llm-ranking/* until they have
    // a website AND a paid subscription.
    if (auth.isAuthenticated) {
        if (!auth.session) {
            try { await auth.fetchSession() } catch (_) {}
        }
        const route = auth.session?.next_route
        if (route === 'onboarding' && !GATE_EXEMPT.has(to.name)) {
            return next({ name: 'dashboard' })
        }
        if (route === 'paywall' && to.name !== 'paywall') {
            return next({ name: 'paywall' })
        }
    }

    // Guard: project-specific pages require an active project
    const projectPages = ['analytics', 'llm-ranking', 'website-detail', 'source-influence', 'prompt-library', 'brand-vault', 'content-studio', 'content-studio-draft']
    if (projectPages.includes(to.name) && auth.isAuthenticated) {
        const app = useAppStore()
        if (!app.activeWebsite) {
            return next({ name: 'websites' })
        }
    }

    next()
})

export default router
