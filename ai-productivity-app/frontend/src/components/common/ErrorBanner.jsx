export default function ErrorBanner({ children }) {
  if (!children) return null;
  return (
    <div
      role="alert"
      className="mb-4 p-4 rounded-md bg-error-50 text-error-600 border border-error-100 dark:bg-error-900/30 dark:text-error-400"
      data-testid="error-banner"
    >
      {children}
    </div>
  );
}
