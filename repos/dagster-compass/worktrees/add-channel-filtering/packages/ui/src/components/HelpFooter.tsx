export function HelpFooter({showTermsLink = true}: {showTermsLink?: boolean}) {
  return (
    <div className="text-center mt-8">
      <p className="text-sm text-gray-600">
        Need help? Visit our{' '}
        <a
          href="http://docs.compass.dagster.io/admins"
          target="_blank"
          rel="noopener noreferrer"
          className="blue-brand hover:text-blue-brand-dark hover:underline"
        >
          Docs
        </a>{' '}
        or{' '}
        <a
          href="mailto:compass-support@dagsterlabs.com"
          className="blue-brand hover:text-blue-brand-dark  hover:underline"
        >
          contact support.
        </a>
      </p>
      {showTermsLink && (
        <p className="flex gap-2 mt-2 text-xs text-gray-600 justify-center">
          <a
            href="https://compass.dagster.io/terms"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-brand hover:text-blue-brand-dark hover:underline"
          >
            Terms of Service
          </a>{' '}
          |{' '}
          <a
            href="https://dagster.io/privacy"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-brand hover:text-blue-brand-dark hover:underline"
          >
            Privacy Policy
          </a>
        </p>
      )}
    </div>
  );
}
