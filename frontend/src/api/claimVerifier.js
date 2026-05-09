import api from './client'

export default {
  mismatches: (websiteId, params = {}) =>
    api.get(`/claim-verifier/websites/${websiteId}/mismatches/`, { params }),
  accuracy: (websiteId, params = {}) =>
    api.get(`/claim-verifier/websites/${websiteId}/accuracy/`, { params }),
  auditClaims: (auditId) =>
    api.get(`/claim-verifier/audits/${auditId}/claims/`),
  claimDetail: (id) => api.get(`/claim-verifier/claims/${id}/`),
  dismiss: (mismatchId, payload = {}) =>
    api.post(`/claim-verifier/mismatches/${mismatchId}/dismiss/`, payload),
  dismissalStats: (websiteId, params = {}) =>
    api.get(`/claim-verifier/websites/${websiteId}/dismissal-stats/`, { params }),
}
