import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
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

    /* ── App (protected) ── */
    {
        path: '/',
        component: () => import('@/layouts/AppLayout.vue'),
        meta: { requiresAuth: true },
        children: [
            { path: '', redirect: '/dashboard' },
            {
                path: 'dashboard',
                name: 'dashboard',
                component: () => import('@/pages/DashboardPage.vue')
            },
            {
                path: 'websites',
                name: 'websites',
                component: () => import('@/pages/WebsitesListPage.vue')
            },
            {
                path: 'websites/:id',
                name: 'website-detail',
                component: () => import('@/pages/WebsiteDetailPage.vue'),
                props: true
            },
            {
                path: 'analytics/:websiteId',
                name: 'analytics',
                component: () => import('@/pages/AnalyticsPage.vue'),
                props: true
            },
            {
                path: 'leads/:websiteId',
                name: 'leads',
                component: () => import('@/pages/LeadsPage.vue'),
                props: true
            },
            {
                path: 'competitors/:websiteId',
                name: 'competitors',
                component: () => import('@/pages/CompetitorsPage.vue'),
                props: true
            },
            {
                path: 'audits/:websiteId',
                name: 'audits',
                component: () => import('@/pages/AuditsPage.vue'),
                props: true
            },
            {
                path: 'heatmap/:websiteId',
                name: 'heatmap',
                component: () => import('@/pages/HeatmapPage.vue'),
                props: true
            },
            {
                path: 'keywords/:websiteId',
                name: 'keywords',
                component: () => import('@/pages/KeywordsPage.vue'),
                props: true
            },
            {
                path: 'strategy/:websiteId',
                name: 'strategy',
                component: () => import('@/pages/StrategyPage.vue'),
                props: true
            },
            {
                path: 'billing',
                name: 'billing',
                component: () => import('@/pages/BillingPage.vue')
            },
            {
                path: 'settings',
                name: 'settings',
                component: () => import('@/pages/SettingsPage.vue')
            },
        ]
    },

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

    if (to.meta.guest && auth.isAuthenticated) {
        return next({ name: 'dashboard' })
    }

    next()
})

export default router
