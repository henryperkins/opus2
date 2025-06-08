// frontend/src/api/chat.js
import client from './client';

const chatAPI = {
  async createSession(projectId, title = null) {
    const response = await client.post('/api/chat/sessions', {
      project_id: Number(projectId),
      title,
    });
    return response.data;
  },

  async getMessages(sessionId, params = {}) {
    const response = await client.get(`/api/chat/sessions/${sessionId}/messages`, {
      params,
    });
    return response.data;
  },

  async deleteSession(sessionId) {
    await client.delete(`/api/chat/sessions/${sessionId}`);
  },
};

export default chatAPI;
