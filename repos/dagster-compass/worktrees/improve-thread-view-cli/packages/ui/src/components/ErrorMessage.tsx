interface ErrorMessageProps {
  message: string;
  className?: string;
}

/**
 * Shared error message component with warning icon and support links.
 * Used across dashboard pages for consistent error display.
 */
export function ErrorMessage({message, className = ''}: ErrorMessageProps) {
  return (
    <div className={`flex justify-center pt-32 ${className}`}>
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <i className="ph-bold ph-warning text-red-600 text-xl" />
          <p className="text-red-800">{message}</p>
        </div>
        <p className="text-sm text-red-800">
          Need help? Visit our{' '}
          <a
            href="https://docs.compass.dagster.io/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-red-800 underline hover:text-red-900"
          >
            Docs
          </a>{' '}
          or{' '}
          <a
            href="mailto:compass-support@dagsterlabs.com"
            className="text-red-800 underline hover:text-red-900"
          >
            contact support
          </a>
          .
        </p>
      </div>
    </div>
  );
}
