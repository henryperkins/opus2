import { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';

function Login() {
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    username_or_email: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await login(formData.username_or_email, formData.password);
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
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

  return (
    <form onSubmit={handleSubmit} className="login-form">
      <div className="form-group">
        <label htmlFor="username_or_email">Username or Email</label>
        <input
          type="text"
          id="username_or_email"
          name="username_or_email"
          value={formData.username_or_email}
          onChange={handleChange}
          required
          disabled={loading}
          placeholder="Enter your username or email"
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
          required
          disabled={loading}
          minLength={8}
        />
      </div>

      {error && <div className="error-message">{error}</div>}

      <button type="submit" disabled={loading} className="login-button">
        {loading ? 'Logging in...' : 'Login'}
      </button>
    </form>
  );
}

export default Login;