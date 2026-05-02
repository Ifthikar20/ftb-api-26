import api from './client'

export default {
    scan: (url) => api.post('/onboarding/scan/', { url }),
    save: (payload) => api.post('/onboarding/save/', payload),
}
