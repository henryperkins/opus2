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

  // -----------------------------------------------------------------------
  // Password-reset flow
  // -----------------------------------------------------------------------

  /**
   * Request password-reset link/token by email.
   *
   * Backend purposely does **not** reveal whether the email exists – it always
   * returns 202 Accepted.  The UI should therefore show a generic success
   * message regardless of the account state.
   */
  async requestPasswordReset(email) {
    const response = await client.post('/api/auth/reset-request', { email });
    return response.data;
  },

  /**
   * Submit new password together with the one-time JWT token.
   *
   * @param {string} token  Token received by email / URL param
   * @param {string} newPassword  The new password the user chose
   */
  async submitPasswordReset(token, newPassword) {
    const response = await client.post('/api/auth/reset', {
      token,
      new_password: newPassword,
    });
    return response.data;
  },

  async refreshToken() {
    const response = await client.post('/api/auth/refresh');
    return response.data;
  },

  /**
   * Partially update the authenticated user's profile.
   *
   * Backend accepts any subset of { username, email, password } and returns
   * the updated *UserResponse* model.  We simply forward the response data.
   *
   * @param {Object} changes - Partial user fields to update
   * @returns {Promise<import('../types').User>} Updated user object
   */
  async updateProfile(changes) {
    // Clean undefined / empty string values – backend treats missing keys as
    // "no-change" whereas explicit null/empty may fail validation.
    const payload = {};
    ['username', 'email', 'password'].forEach((key) => {
      const value = changes[key];
      if (value !== undefined && value !== null && value !== '') {
        payload[key] = value;
      }
    });

    if (Object.keys(payload).length === 0) {
      throw new Error('No profile changes provided');
    }

    const response = await client.patch('/api/auth/me', payload);
    return response.data;
  },
};

export default authAPI;