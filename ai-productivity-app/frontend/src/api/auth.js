import client from './client';

export const authAPI = {
  async login(credentials) {
    const response = await client.post('/api/auth/login', credentials);
    return response.data;
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