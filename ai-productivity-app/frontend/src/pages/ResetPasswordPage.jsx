import { useState } from 'react';
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
      window.setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      console.error(err);
      setServerError(err.response?.data?.detail || err.message || 'Error resetting password');
    }
  }

  // Password confirmation validation
  const password = watch('password');

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col items-center justify-center">
      <div className="w-full max-w-md">
        {/* App Branding */}
        <div className="text-center mb-8">
          <div className="mx-auto w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Reset Password</h1>
          <p className="text-gray-600">Create a new password for your account.</p>
        </div>

        {/* Form Container */}
        <div className="bg-white shadow-xl rounded-2xl p-8">
          {success ? (
            <div className="text-center">
              <div className="flex items-center justify-center w-12 h-12 mx-auto mb-4 bg-green-100 rounded-full">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-green-800 mb-2">Password Reset Complete</h3>
              <p className="text-green-700 text-sm mb-4">
                Your password has been updated successfully. Redirecting to login...
              </p>
              <a
                href="/login"
                className="inline-block text-blue-600 hover:text-blue-700 hover:underline transition-colors duration-200"
              >
                Continue to login
              </a>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2" htmlFor="password">
                  New Password
                </label>
                <input
                  id="password"
                  type="password"
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200"
                  placeholder="Enter your new password"
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
                <p className="text-xs text-gray-500 mt-1">Minimum 8 characters</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2" htmlFor="confirm">
                  Confirm Password
                </label>
                <input
                  id="confirm"
                  type="password"
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200"
                  placeholder="Confirm your new password"
                  {...register('confirm', {
                    required: 'Please confirm your password',
                    validate: (val) => val === password || 'Passwords do not match',
                  })}
                />
                {errors.confirm && (
                  <p className="text-red-600 text-sm mt-1">{errors.confirm.message}</p>
                )}
              </div>

              {serverError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-center">
                    <svg className="w-5 h-5 text-red-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-red-700 text-sm">{serverError}</p>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {isSubmitting ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Updating Password...
                  </>
                ) : (
                  'Update Password'
                )}
              </button>

              <div className="text-center">
                <a
                  href="/login"
                  className="text-sm text-blue-600 hover:text-blue-700 hover:underline transition-colors duration-200"
                >
                  Back to login
                </a>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
