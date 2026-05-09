import api from './client'

export default {
  facts: (websiteId, params = {}) =>
    api.get(`/brand-vault/websites/${websiteId}/facts/`, { params }),
  factDetail: (id) => api.get(`/brand-vault/facts/${id}/`),
  approve: (id) => api.post(`/brand-vault/facts/${id}/approve/`),
  reject: (id) => api.post(`/brand-vault/facts/${id}/reject/`),
  edit: (id, payload) => api.post(`/brand-vault/facts/${id}/edit/`, payload),
  triggerExtract: (websiteId) =>
    api.post(`/brand-vault/websites/${websiteId}/extract/`),
  stats: (websiteId) => api.get(`/brand-vault/websites/${websiteId}/stats/`),
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
  toneSamples: (websiteId, params = {}) =>
    api.get(`/brand-vault/websites/${websiteId}/tone-samples/`, { params }),
}
