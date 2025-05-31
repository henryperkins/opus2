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
      setSuccess(true);
      setTimeout(() => {
        onLoginSwitch?.();
      }, 2000);
    } catch (err) {
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
      <div className="success-message">
        <h3>Registration Successful!</h3>
        <p>You can now log in with your credentials.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="register-form">
      <div className="form-group">
        <label htmlFor="username">Username</label>
        <input
          type="text"
          id="username"
          name="username"
          value={formData.username}
          onChange={handleChange}
          autoComplete="username"
          required
          disabled={loading}
        />
      </div>

      <div className="form-group">
        <label htmlFor="email">Email</label>
        <input
          type="email"
          id="email"
          name="email"
          value={formData.email}
          onChange={handleChange}
          autoComplete="email"
          required
          disabled={loading}
        />
      </div>

      <div className="form-group">
        <label htmlFor="password">Password</label>
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
        />
      </div>

      <div className="form-group">
        <label htmlFor="confirmPassword">Confirm Password</label>
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
        />
      </div>

      <div className="form-group">
        <label htmlFor="inviteCode">Invite Code</label>
        <input
          type="text"
          id="inviteCode"
          name="inviteCode"
          value={formData.inviteCode}
          onChange={handleChange}
          required
          disabled={loading}
          placeholder="Required for registration"
        />
      </div>

      {error && <div className="error-message">{error}</div>}

      <button type="submit" disabled={loading} className="register-button">
        {loading ? 'Creating Account...' : 'Register'}
      </button>

      <p className="switch-auth">
        Already have an account?{' '}
        <button type="button" onClick={onLoginSwitch} className="link-button">
          Login here
        </button>
      </p>
    </form>
  );
}

export default Register;