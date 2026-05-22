import api from './client'

export default {
  // Facts ----------------------------------------------------------------
  facts: (websiteId, params = {}) =>
    api.get(`/brand-vault/websites/${websiteId}/facts/`, { params }),
  factDetail: (id) => api.get(`/brand-vault/facts/${id}/`),
  factUsage: (id) => api.get(`/brand-vault/facts/${id}/usage/`),
  approve: (id) => api.post(`/brand-vault/facts/${id}/approve/`),
  reject: (id) => api.post(`/brand-vault/facts/${id}/reject/`),
  edit: (id, payload) => api.post(`/brand-vault/facts/${id}/edit/`, payload),
  bulkAction: (websiteId, ids, action) =>
    api.post(`/brand-vault/websites/${websiteId}/facts/bulk/`, { ids, action }),

  // Extraction -----------------------------------------------------------
  triggerExtract: (websiteId) =>
    api.post(`/brand-vault/websites/${websiteId}/extract/`),
  extractStatus: (websiteId) =>
    api.get(`/brand-vault/websites/${websiteId}/extract/status/`),

  // Dashboard --------------------------------------------------------------
  stats: (websiteId) => api.get(`/brand-vault/websites/${websiteId}/stats/`),
  contradictions: (websiteId) =>
    api.get(`/brand-vault/websites/${websiteId}/contradictions/`),
  coverage: (websiteId) =>
    api.get(`/brand-vault/websites/${websiteId}/coverage/`),
  revisions: (websiteId, params = {}) =>
    api.get(`/brand-vault/websites/${websiteId}/revisions/`, { params }),
  backlinks: (websiteId) =>
    api.get(`/brand-vault/websites/${websiteId}/backlinks/`),
  keywords: (websiteId) =>
    api.get(`/brand-vault/websites/${websiteId}/keywords/`),

  // Imports ---------------------------------------------------------------
  importJson: (websiteId, facts) =>
    api.post(`/brand-vault/websites/${websiteId}/facts/import/`, { facts }),
  importCsv: (websiteId, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post(
      `/brand-vault/websites/${websiteId}/facts/import-csv/`,
      fd,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
  },

  // Tone of Voice ---------------------------------------------------------
  toneSamples: (websiteId, params = {}) =>
    api.get(`/brand-vault/websites/${websiteId}/tone-samples/`, { params }),
  addToneSample: (websiteId, text) =>
    api.post(`/brand-vault/websites/${websiteId}/tone-samples/create/`, { text }),
  deleteToneSample: (id) =>
    api.delete(`/brand-vault/tone-samples/${id}/`),
}
