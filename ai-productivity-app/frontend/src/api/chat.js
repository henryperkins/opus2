import client from "./client";

// Create a stable API client factory
function createChatAPI() {
  return {
    // Create a new chat session
    createSession: (data = {}) => {
      return client.post("/api/chat/sessions", data);
    },

    // Get session details
    getSession: (sessionId) => {
      return client.get(`/api/chat/sessions/${sessionId}`);
    },

    // Get messages from a session
    getMessages: (sessionId, params = {}) => {
      return client.get(`/api/chat/sessions/${sessionId}/messages`, { params });
    },

    // Get session history (same endpoint) – return normalised array
    getSessionHistory: async (params = {}) => {
      const { data } = await client.get("/api/chat/sessions", { params });
      return Array.isArray(data) ? data : (data?.items ?? data?.sessions ?? []);
    },

    // Get chat sessions (alias for getSessionHistory for backward compatibility)
    // Always resolve to an array for safer call-sites
    getChatSessions: async (params = {}) => {
      const { data } = await client.get("/api/chat/sessions", { params });
      return Array.isArray(data) ? data : (data?.items ?? data?.sessions ?? []);
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
    deleteMessage: async (id) => {
      try {
        return await client.delete(`/api/chat/messages/${id}`);
      } catch (err) {
        if (err.response?.status === 404) return { status: 404 }; // idempotent
        throw err;
      }
    },
  };
}

// Single instance that survives HMR
const chatAPI = createChatAPI();

// Debug: Log available methods during development
if (import.meta.env.DEV) {
  console.log("[Chat API] Available methods:", Object.keys(chatAPI));
}

// Export as default
export default chatAPI;

// Also export the createSession function as a named export for backward compatibility
export const createSession = chatAPI.createSession;

// Export additional methods as named exports for better tree-shaking
export const getChatSessions = chatAPI.getChatSessions;
export const getSessionHistory = chatAPI.getSessionHistory;
export const sendMessage = chatAPI.sendMessage;

// Preserve instance across hot updates
if (import.meta.hot) {
  import.meta.hot.accept();
  import.meta.hot.dispose(() => {
    // Clean up any timers, auth tokens, etc. if needed
    console.log("[HMR] Disposing chat API module");
  });
}
