import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate, useParams } from 'react-router-dom';

export default function ResetPasswordPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState('');
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm();

  async function onSubmit({ password }) {
    setServerError('');
    try {
      const { authAPI } = await import('../api/auth');
      await authAPI.submitPasswordReset(token, password);
      setSuccess(true);
      // Optionally redirect to login after short delay
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      console.error(err);
      setServerError(err.response?.data?.detail || err.message || 'Error resetting password');
    }
  }

  // Password confirmation validation
  const password = watch('password');

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 p-4">
      <div className="w-full max-w-md bg-white rounded shadow p-6 space-y-4">
        <h1 className="text-2xl font-semibold text-center">Reset your password</h1>

        {success ? (
          <p className="text-green-700 text-center">
            Password updated! Redirecting to login…
          </p>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1" htmlFor="password">
                New password
              </label>
              <input
                id="password"
                type="password"
                className="w-full border rounded px-3 py-2"
                {...register('password', {
                  required: 'Password is required',
                  minLength: {
                    value: 8,
                    message: 'Must be at least 8 characters',
                  },
                })}
              />
              {errors.password && (
                <p className="text-red-600 text-sm mt-1">{errors.password.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-1" htmlFor="confirm">
                Confirm password
              </label>
              <input
                id="confirm"
                type="password"
                className="w-full border rounded px-3 py-2"
                {...register('confirm', {
                  required: 'Please confirm',
                  validate: (val) => val === password || 'Passwords do not match',
                })}
              />
              {errors.confirm && (
                <p className="text-red-600 text-sm mt-1">{errors.confirm.message}</p>
              )}
            </div>

            {serverError && <p className="text-red-600 text-sm">{serverError}</p>}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded"
            >
              {isSubmitting ? 'Saving…' : 'Reset password'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
