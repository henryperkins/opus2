import { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';

function Register({ onLoginSwitch }) {
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    inviteCode: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    try {
      // Import and use auth API directly for registration
      const { authAPI } = await import('../../api/auth');
      await authAPI.register({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        invite_code: formData.inviteCode
      });
      // Backend returns a token and sets the auth cookie, so we can immediately
      // call the global login helper to populate user state and redirect.
      // This provides a smoother UX – account available right after sign-up.
      await login(formData.username || formData.email, formData.password);

      setSuccess(true);
      // Delay a moment so the success message is visible before redirect.
      setTimeout(() => {
        onLoginSwitch?.();
      }, 500);
    } catch (err) {
      console.error('Registration error:', err);
      console.error('Response data:', err.response?.data);
      console.error('Response status:', err.response?.status);
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  if (success) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-md p-4">
        <h3 className="text-lg font-medium text-green-800">Registration Successful!</h3>
        <p className="text-green-700 mt-1">You can now log in with your credentials.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="username" className="block text-sm font-medium text-gray-700">Username</label>
        <input
          type="text"
          id="username"
          name="username"
          value={formData.username}
          onChange={handleChange}
          autoComplete="username"
          required
          disabled={loading}
          className="mt-1 block w-full border rounded-md p-2 disabled:opacity-50"
        />
      </div>

      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700">Email</label>
        <input
          type="email"
          id="email"
          name="email"
          value={formData.email}
          onChange={handleChange}
          autoComplete="email"
          required
          disabled={loading}
          className="mt-1 block w-full border rounded-md p-2 disabled:opacity-50"
        />
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700">Password</label>
        <input
          type="password"
          id="password"
          name="password"
          value={formData.password}
          onChange={handleChange}
          autoComplete="new-password"
          required
          disabled={loading}
          minLength={8}
          className="mt-1 block w-full border rounded-md p-2 disabled:opacity-50"
        />
      </div>

      <div>
        <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">Confirm Password</label>
        <input
          type="password"
          id="confirmPassword"
          name="confirmPassword"
          value={formData.confirmPassword}
          onChange={handleChange}
          autoComplete="new-password"
          required
          disabled={loading}
          minLength={8}
          className="mt-1 block w-full border rounded-md p-2 disabled:opacity-50"
        />
      </div>

      <div>
        <label htmlFor="inviteCode" className="block text-sm font-medium text-gray-700">Invite Code</label>
        <input
          type="text"
          id="inviteCode"
          name="inviteCode"
          value={formData.inviteCode}
          onChange={handleChange}
          required
          disabled={loading}
          placeholder="Required for registration"
          className="mt-1 block w-full border rounded-md p-2 disabled:opacity-50"
        />
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      <button type="submit" disabled={loading} className="w-full bg-blue-600 text-white py-2 rounded-md disabled:opacity-50">
        {loading ? 'Creating Account...' : 'Register'}
      </button>

      <p className="text-center text-sm text-gray-600">
        Already have an account?{' '}
        <button type="button" onClick={onLoginSwitch} className="text-blue-600 hover:underline">
          Login here
        </button>
      </p>
    </form>
  );
}

export default Register;