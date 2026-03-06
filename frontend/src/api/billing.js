import api from './client'

export default {
    getCurrent: () => api.get('/billing/'),
    getPlans: () => api.get('/billing/plans/'),
    checkout: (data) => api.post('/billing/checkout/', data),
    portal: () => api.post('/billing/portal/'),
    invoices: () => api.get('/billing/invoices/'),
    usage: () => api.get('/billing/usage/'),
}
