/* LoginPage
 *
 * Purpose
 * -------
 * Presents a login form with validation (react-hook-form) and uses AuthContext
 * to authenticate the user. Redirects to dashboard (/) on success.
 */

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import Register from '../components/auth/Register';

export default function LoginPage() {
  const { register, handleSubmit, formState } = useForm();
  const { login, user, loading } = useAuth();
  const navigate = useNavigate();
  const { errors, isSubmitting } = formState;
  const [submitError, setSubmitError] = useState('');
  const [showRegister, setShowRegister] = useState(false);

  if (user) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(values) {
    setSubmitError('');

    // Temporarily disable browser password-manager autofill that may interfere
    const formEl = document.querySelector('form');
    formEl?.setAttribute('autocomplete', 'off');
    try {
      await login(values.username_or_email, values.password);
      navigate('/', { replace: true });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error(err);
      const msg = err?.response?.data?.detail || 'Login failed';
      setSubmitError(msg);
    } finally {
      // Re-enable autocomplete
      formEl?.setAttribute('autocomplete', 'on');
    }
  }

  if (showRegister) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col items-center justify-center p-4">
        <div className="w-full max-w-md">
          {/* App Branding */}
          <div className="text-center mb-8">
            <div className="mx-auto w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Create Account</h1>
            <p className="text-gray-600">Join AI Productivity and boost your workflow.</p>
          </div>

          {/* Register Form */}
          <div className="bg-white shadow-xl rounded-2xl p-8">
            <Register onLoginSwitch={() => setShowRegister(false)} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* App Branding */}
        <div className="text-center mb-8">
          <div className="mx-auto w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Productivity</h1>
          <p className="text-gray-600">Welcome back! Please sign in to your account.</p>
        </div>

        {/* Login Form */}
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="bg-white shadow-xl rounded-2xl p-8 space-y-6"
        >
          <div className="space-y-4">
            <div>
              <label htmlFor="username_or_email" className="block text-sm font-medium text-gray-700 mb-2">
                Username or Email
              </label>
              <input
                id="username_or_email"
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 disabled:bg-gray-50 disabled:opacity-50"
                autoComplete="username"
                placeholder="Enter your username or email"
                {...register('username_or_email', { required: 'Username or email required' })}
                disabled={isSubmitting || loading}
              />
              {errors.username_or_email && (
                <p className="text-red-600 text-sm mt-1">
                  {errors.username_or_email.message}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 disabled:bg-gray-50 disabled:opacity-50"
                autoComplete="current-password"
                placeholder="Enter your password"
                {...register('password', { required: 'Password required' })}
                disabled={isSubmitting || loading}
              />
              {errors.password && (
                <p className="text-red-600 text-sm mt-1">
                  {errors.password.message}
                </p>
              )}
            </div>
          </div>

          {submitError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center">
                <svg className="w-5 h-5 text-red-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-red-700 text-sm">{submitError}</p>
              </div>
            </div>
          )}

          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            disabled={isSubmitting || loading}
          >
            {isSubmitting || loading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Signing in...
              </>
            ) : (
              'Sign In'
            )}
          </button>

          <div className="flex items-center justify-center space-x-4 text-sm">
            <a href="/forgot" className="text-blue-600 hover:text-blue-700 hover:underline transition-colors duration-200">
              Forgot password?
            </a>
            <span className="text-gray-300">•</span>
            <button
              type="button"
              onClick={() => setShowRegister(true)}
              className="text-blue-600 hover:text-blue-700 hover:underline transition-colors duration-200"
            >
              Create account
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
