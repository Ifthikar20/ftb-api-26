import api from './client'

export default {
  briefs: (websiteId, params = {}) =>
    api.get(`/content-studio/websites/${websiteId}/briefs/`, { params }),
  briefDetail: (id) => api.get(`/content-studio/briefs/${id}/`),
  draftBrief: (id) => api.post(`/content-studio/briefs/${id}/draft/`),
  skipBrief: (id) => api.post(`/content-studio/briefs/${id}/skip/`),
  draftDetail: (id) => api.get(`/content-studio/drafts/${id}/`),
  regenerateDraft: (id) => api.post(`/content-studio/drafts/${id}/regenerate/`),
  updateDraft: (id, payload) => api.patch(`/content-studio/drafts/${id}/`, payload),
  approveDraft: (id) => api.post(`/content-studio/drafts/${id}/approve/`),
}
