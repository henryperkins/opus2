import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import authAPI from '../api/auth';

export default function ForgotPasswordPage() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isSubmitSuccessful },
  } = useForm();
  const [serverError, setServerError] = useState('');

  async function onSubmit({ email }) {
    setServerError('');
    try {
      await authAPI.requestPasswordReset(email);
    } catch (err) {
      console.error(err);
      setServerError(err.message || 'An unexpected error occurred');
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 p-4">
      <div className="w-full max-w-md bg-white rounded shadow p-6 space-y-4">
        <h1 className="text-2xl font-semibold text-center">Forgot your password?</h1>

        {isSubmitSuccessful ? (
          <p className="text-green-700 text-center">
            If the email exists, a reset link has been sent. Please check your inbox.
          </p>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1" htmlFor="email">
                Email address
              </label>
              <input
                id="email"
                type="email"
                className="w-full border rounded px-3 py-2"
                placeholder="you@example.com"
                {...register('email', {
                  required: 'Email is required',
                  pattern: {
                    value: /\S+@\S+\.\S+/,
                    message: 'Invalid email address',
                  },
                })}
              />
              {errors.email && (
                <p className="text-red-600 text-sm mt-1">{errors.email.message}</p>
              )}
            </div>

            {serverError && <p className="text-red-600 text-sm">{serverError}</p>}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded"
            >
              {isSubmitting ? 'Sending…' : 'Send reset link'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
