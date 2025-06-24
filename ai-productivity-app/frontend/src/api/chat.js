import client from './client';

const chatAPI = {
  // Create a new chat session
  createSession: (data = {}) => {
    return client.post('/api/chat/sessions', data);
  },

  // Get session details
  getSession: (sessionId) => {
    return client.get(`/api/chat/sessions/${sessionId}`);
  },

  // Get messages from a session
  getMessages: (sessionId, params = {}) => {
    return client.get(`/api/chat/sessions/${sessionId}/messages`, { params });
  },

  // Get session history
  getSessionHistory: (params = {}) => {
    return client.get('/api/chat/sessions', { params });
  },

  // Update a session
  updateSession: (sessionId, data) => {
    return client.patch(`/api/chat/sessions/${sessionId}`, data);
  },

  // Delete a session
  deleteSession: (sessionId) => {
    return client.delete(`/api/chat/sessions/${sessionId}`);
  },

  // -------------------------
  // Message-level operations
  // -------------------------
  // Send a new message to a session
  sendMessage: (sessionId, data) => {
    return client.post(`/api/chat/sessions/${sessionId}/messages`, data);
  },

  // Edit an existing message
  editMessage: (id, content) => {
    return client.patch(`/api/chat/messages/${id}`, { content });
  },

  // Delete a message
  deleteMessage: (id) => {
    return client.delete(`/api/chat/messages/${id}`);
  }
};

// Export as default
export default chatAPI;

// Also export the createSession function as a named export for backward compatibility
export const createSession = chatAPI.createSession;
