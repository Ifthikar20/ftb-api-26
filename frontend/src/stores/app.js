import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

export const useAppStore = defineStore('app', () => {
    const sidebarCollapsed = ref(false)
    const activeWebsite = ref(null)
    const websites = ref([])
    const notifications = ref([])
    const unreadCount = computed(() => notifications.value.filter(n => !n.read).length)

    // Plan state
    const userPlan = ref('starter')
    const projectLimit = ref(-1) // -1 = unlimited (testing mode)

    const canCreateProject = computed(() => {
        if (projectLimit.value === -1) return true
        return websites.value.length < projectLimit.value
    })

    const projectLimitLabel = computed(() => {
        if (projectLimit.value === -1) return `${websites.value.length} projects`
        return `${websites.value.length}/${projectLimit.value} projects`
    })

    function setPlanInfo(plan, limit) {
        userPlan.value = plan
        projectLimit.value = limit
    }

    // Theme: 'light' or 'dark'
    const theme = ref(localStorage.getItem('fb-theme') || 'light')

    function applyTheme(t) {
        document.documentElement.setAttribute('data-theme', t)
        localStorage.setItem('fb-theme', t)
    }

    function toggleTheme() {
        theme.value = theme.value === 'light' ? 'dark' : 'light'
        applyTheme(theme.value)
    }

    // Apply on init
    applyTheme(theme.value)

    function toggleSidebar() {
        sidebarCollapsed.value = !sidebarCollapsed.value
    }

    function setActiveWebsite(website) {
        activeWebsite.value = website
    }

    function setWebsites(list) {
        websites.value = list
        if (!activeWebsite.value && list.length > 0) {
            activeWebsite.value = list[0]
        }
    }

    return {
        sidebarCollapsed,
        activeWebsite,
        websites,
        notifications,
        unreadCount,
        theme,
        userPlan,
        projectLimit,
        canCreateProject,
        projectLimitLabel,
        toggleSidebar,
        toggleTheme,
        setPlanInfo,
        setActiveWebsite,
        setWebsites,
    }
})
