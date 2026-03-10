import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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
        meta: { guest: true }
    },
    {
        path: '/welcome',
        redirect: '/'
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
    protect('/competitors/:websiteId', 'competitors', () => import('@/pages/CompetitorsPage.vue'), true),
    protect('/audits/:websiteId', 'audits', () => import('@/pages/AuditsPage.vue'), true),
    protect('/heatmap/:websiteId', 'heatmap', () => import('@/pages/HeatmapPage.vue'), true),
    protect('/keywords/:websiteId', 'keywords', () => import('@/pages/KeywordsPage.vue'), true),
    protect('/strategy/:websiteId', 'strategy', () => import('@/pages/StrategyPage.vue'), true),
    protect('/agents/:websiteId', 'agents', () => import('@/pages/AgentsPage.vue'), true),
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

router.beforeEach((to, from, next) => {
    const auth = useAuthStore()

    if (to.meta.requiresAuth && !auth.isAuthenticated) {
        return next({ name: 'login', query: { redirect: to.fullPath } })
    }

    // If guest visits a guest-only page but is already logged in, go to dashboard
    if (to.meta.guest && auth.isAuthenticated) {
        return next({ name: 'dashboard' })
    }

    next()
})

export default router
