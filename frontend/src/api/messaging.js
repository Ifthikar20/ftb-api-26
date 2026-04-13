import api from './client'

const base = (wid) => `/messaging/${wid}`

export default {
    // Conversations
    listConversations: (wid, params) => api.get(`${base(wid)}/conversations/`, { params }),
    getConversation: (wid, cid) => api.get(`${base(wid)}/conversations/${cid}/`),
    updateConversation: (wid, cid, data) => api.patch(`${base(wid)}/conversations/${cid}/`, data),

    // Messages
    sendMessage: (wid, cid, data) => api.post(`${base(wid)}/conversations/${cid}/send/`, data),
    generateAIReply: (wid, cid) => api.post(`${base(wid)}/conversations/${cid}/ai-reply/`, {}),

    // Training Docs (.md knowledge base)
    listTrainingDocs: (wid) => api.get(`${base(wid)}/training-docs/`),
    createTrainingDoc: (wid, data) => api.post(`${base(wid)}/training-docs/`, data),
    getTrainingDoc: (wid, docId) => api.get(`${base(wid)}/training-docs/${docId}/`),
    updateTrainingDoc: (wid, docId, data) => api.put(`${base(wid)}/training-docs/${docId}/`, data),
    deleteTrainingDoc: (wid, docId) => api.delete(`${base(wid)}/training-docs/${docId}/`),

    // Starter Templates
    listTemplates: (wid) => api.get(`${base(wid)}/training-docs/templates/`),
    applyTemplate: (wid, slug) => api.post(`${base(wid)}/training-docs/from-template/`, { slug }),

    // Agent Tone
    getTone: (wid) => api.get(`${base(wid)}/agent-tone/`),
    setTone: (wid, tone) => api.patch(`${base(wid)}/agent-tone/`, { tone }),

    // Seed demo data
    seedDemo: (wid) => api.post(`${base(wid)}/seed-demo/`, {}),
}
