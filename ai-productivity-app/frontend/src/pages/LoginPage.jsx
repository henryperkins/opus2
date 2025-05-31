/* LoginPage
 *
 * Purpose
 * -------
 * Presents a login form with validation (react-hook-form) and uses AuthContext
 * to authenticate the user. Redirects to dashboard (/) on success.
 */

import React from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function LoginPage() {
  const { register, handleSubmit, formState } = useForm();
  const { login, user, loading } = useAuth();
  const navigate = useNavigate();
  const { errors, isSubmitting } = formState;

  if (user) {
    return <Navigate to="/" replace />;
  }

  async function onSubmit(values) {
    try {
      await login(values.username, values.password);
      navigate('/');
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error(err);
      // TODO: display toast
    }
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
            {...register('username', { required: 'Username or email required' })}
            disabled={isSubmitting || loading}
          />
          {errors.username && (
            <span className="text-red-600 text-sm">
              {errors.username.message}
            </span>
          )}
        </label>

        <label className="block mb-4">
          <span className="text-gray-700">Password</span>
          <input
            type="password"
            className="mt-1 block w-full border rounded p-2"
            {...register('password', { required: 'Password required' })}
            disabled={isSubmitting || loading}
          />
          {errors.password && (
            <span className="text-red-600 text-sm">
              {errors.password.message}
            </span>
          )}
        </label>

        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded disabled:opacity-50"
          disabled={isSubmitting || loading}
        >
          {isSubmitting || loading ? 'Logging in...' : 'Login'}
        </button>
      </form>
    </div>
  );
}
