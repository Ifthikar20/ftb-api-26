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
  publishDraft: (id, target_id) =>
    api.post(`/content-studio/drafts/${id}/publish/`, { target_id }),
  exportDraft: (id, format = 'md') =>
    api.get(`/content-studio/drafts/${id}/export/`, {
      params: { format },
      responseType: 'blob',
    }),
  publishTargets: (websiteId) =>
    api.get(`/content-studio/websites/${websiteId}/publish-targets/`),
  createPublishTarget: (websiteId, payload) =>
    api.post(`/content-studio/websites/${websiteId}/publish-targets/`, payload),
  updatePublishTarget: (id, payload) =>
    api.patch(`/content-studio/publish-targets/${id}/`, payload),
  deletePublishTarget: (id) =>
    api.delete(`/content-studio/publish-targets/${id}/`),
  roi: (websiteId, params = {}) =>
    api.get(`/content-studio/websites/${websiteId}/roi/`, { params }),
}
