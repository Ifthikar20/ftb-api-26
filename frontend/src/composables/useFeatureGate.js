/**
 * Feature gating composable — Two-tier model (Individual / Enterprise).
 */
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

const PLAN_FEATURES = {
  individual: {
    integrations: 2, projects: 3, pageviews: 50000, team_members: 1, ai_credits: 100, competitors: 5,
    pipeline: true, trends: true, sso: false, api: false, whitelabel: false,
    agents: false, llm_ranking: false,
    tabs: ['dashboard', 'projects', 'analytics', 'leads', 'heatmaps', 'keywords', 'campaigns', 'integrations', 'billing', 'settings'],
  },
  enterprise: {
    integrations: -1, projects: -1, pageviews: -1, team_members: -1, ai_credits: -1, competitors: -1,
    pipeline: true, trends: true, sso: true, api: true, whitelabel: true,
    agents: true, llm_ranking: true,
    tabs: ['dashboard', 'projects', 'analytics', 'leads', 'heatmaps', 'keywords', 'agents', 'campaigns', 'llm_ranking', 'integrations', 'billing', 'settings'],
  },
}

// Legacy plan mapping
const PLAN_TO_SEGMENT = {
  individual: 'individual', enterprise: 'enterprise',
  free: 'individual', starter: 'individual', growth: 'individual',
  team: 'enterprise', scale: 'enterprise', business: 'enterprise',
}

export function useFeatureGate() {
  const auth = useAuthStore()

  const segment = computed(() => {
    const userPlan = auth.user?.segment || auth.user?.plan || 'individual'
    return PLAN_TO_SEGMENT[userPlan] || 'individual'
  })

  const isEnterprise = computed(() => segment.value === 'enterprise')
  const limits = computed(() => PLAN_FEATURES[segment.value] || PLAN_FEATURES.individual)
  const visibleTabs = computed(() => limits.value.tabs)

  function canAccess(feature) {
    const val = limits.value[feature]
    if (typeof val === 'boolean') return val
    if (typeof val === 'number') return val !== 0
    return false
  }

  function getLimit(feature) {
    return limits.value[feature] ?? 0
  }

  function isWithinLimit(feature, currentUsage) {
    const limit = getLimit(feature)
    if (limit === -1) return true
    return currentUsage < limit
  }

  function isTabVisible(tabId) {
    return visibleTabs.value.includes(tabId)
  }

  return { segment, isEnterprise, limits, visibleTabs, canAccess, getLimit, isWithinLimit, isTabVisible }
}
