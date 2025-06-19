import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const chatAPI = {
  // Create a new chat session
  createSession: (data = {}) => {
    return axios.post(`${API_BASE_URL}/chat/sessions`, data);
  },

  // Get session details
  getSession: (sessionId) => {
    return axios.get(`${API_BASE_URL}/chat/sessions/${sessionId}`);
  },

  // Send a message in a session
  sendMessage: (sessionId, data) => {
    return axios.post(`${API_BASE_URL}/chat/sessions/${sessionId}/messages`, data);
  },

  // Get messages from a session
  getMessages: (sessionId, params = {}) => {
    return axios.get(`${API_BASE_URL}/chat/sessions/${sessionId}/messages`, { params });
  },

  // Update a message
  updateMessage: (sessionId, messageId, data) => {
    return axios.put(`${API_BASE_URL}/chat/sessions/${sessionId}/messages/${messageId}`, data);
  },

  // Delete a message
  deleteMessage: (sessionId, messageId) => {
    return axios.delete(`${API_BASE_URL}/chat/sessions/${sessionId}/messages/${messageId}`);
  },

  // Get session history
  getSessionHistory: (params = {}) => {
    return axios.get(`${API_BASE_URL}/chat/sessions`, { params });
  },

  // Delete a session
  deleteSession: (sessionId) => {
    return axios.delete(`${API_BASE_URL}/chat/sessions/${sessionId}`);
  }
};

// Export as default
export default chatAPI;

// Also export the createSession function as a named export for backward compatibility
export const createSession = chatAPI.createSession;
