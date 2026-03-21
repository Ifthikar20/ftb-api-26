import api from './client'

export default {
    get: () => api.get('/websites/dashboard/'),
}
