import api from './client'

const gamificationApi = {
  status: () => api.get('/gamification/status/'),
  progress: () => api.get('/gamification/progress/'),
  cards: () => api.get('/gamification/cards/'),
}

export default gamificationApi
