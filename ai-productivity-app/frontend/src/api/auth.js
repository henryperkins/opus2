import client from './client';

export const authAPI = {
  async login(credentials) {
    try {
      const response = await client.post('/api/auth/login', credentials);

      // Validate expected payload (backend returns access_token)
      if (!response.data || !response.data.access_token) {
        throw new Error('Invalid response from authentication server');
      }

      return response.data;
    } catch (error) {
      if (error.response?.status === 401) {
        throw new Error('Invalid username / email or password');
      }
      throw error;
    }
  },

  async register(userData) {
    const response = await client.post('/api/auth/register', userData);
    return response.data;
  },

  async logout() {
    const response = await client.post('/api/auth/logout');
    return response.data;
  },

  async getCurrentUser() {
    const response = await client.get('/api/auth/me');
    return response.data;
  },

  async resetPassword(email) {
    const response = await client.post('/api/auth/reset-password', { email });
    return response.data;
  },

  async refreshToken() {
    const response = await client.post('/api/auth/refresh');
    return response.data;
  }
};

export default authAPI;