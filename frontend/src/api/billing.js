import api from './client'

export default {
    getCurrent: (config) => api.get('/billing/', config),
    getPlans: () => api.get('/billing/plans/'),
    checkout: (data) => api.post('/billing/checkout/', data),
    devSubscribe: (data) => api.post('/billing/dev-subscribe/', data),
    cancel: () => api.post('/billing/cancel/'),
    resume: () => api.post('/billing/resume/'),
    portal: () => api.post('/billing/portal/'),
    invoices: () => api.get('/billing/invoices/'),
    usage: () => api.get('/billing/usage/'),
}
