/* LoginPage
 *
 * Purpose
 * -------
 * Presents a login form with validation (react-hook-form) and uses AuthContext
 * to authenticate the user. Redirects to dashboard (/) on success.
 */

import React, { useState } from 'react';
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
      <div className="flex flex-col items-center justify-center min-h-screen">
        <div className="w-full max-w-sm bg-white shadow p-6 rounded">
          <h1 className="text-2xl mb-4 text-center">Register</h1>
          <Register onLoginSwitch={() => setShowRegister(false)} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="w-full max-w-sm bg-white shadow p-6 rounded"
      >
        <h1 className="text-2xl mb-4 text-center">Login</h1>

        <label className="block mb-2">
          <span className="text-gray-700">Username or Email</span>
          <input
            className="mt-1 block w-full border rounded p-2"
            autoComplete="username"
            {...register('username_or_email', { required: 'Username or email required' })}
            disabled={isSubmitting || loading}
          />
          {errors.username_or_email && (
            <span className="text-red-600 text-sm">
              {errors.username_or_email.message}
            </span>
          )}
        </label>

        <label className="block mb-4">
          <span className="text-gray-700">Password</span>
          <input
            type="password"
            className="mt-1 block w-full border rounded p-2"
            autoComplete="current-password"
            {...register('password', { required: 'Password required' })}
            disabled={isSubmitting || loading}
          />
          {errors.password && (
            <span className="text-red-600 text-sm">
              {errors.password.message}
            </span>
          )}
        </label>

        {submitError && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-3">
            <p className="text-red-700 text-sm">{submitError}</p>
          </div>
        )}

        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded disabled:opacity-50"
          disabled={isSubmitting || loading}
        >
          {isSubmitting || loading ? 'Logging in...' : 'Login'}
        </button>

        <p className="text-center mt-4 text-sm text-gray-600">
          <a href="/forgot" className="text-blue-600 hover:underline">
            Forgot your password?
          </a>
        </p>

        <p className="text-center mt-2 text-sm text-gray-600">
          Don't have an account?{' '}
          <button
            type="button"
            onClick={() => setShowRegister(true)}
            className="text-blue-600 hover:underline"
          >
            Register here
          </button>
        </p>
      </form>
    </div>
  );
}
