/**
 * Handle 401 authentication errors with user-friendly messages.
 *
 * This utility provides consistent error handling for authentication failures
 * across the React application, distinguishing between expired sessions and
 * permission issues.
 */

export class AuthError extends Error {
  constructor(
    message: string,
    public isExpired: boolean = true,
  ) {
    super(message);
    this.name = 'AuthError';
  }
}

/**
 * Check if a fetch response is a 401 authentication error and throw an
 * appropriate AuthError with user-friendly message.
 *
 * @param response - The fetch Response object
 * @throws {AuthError} If response status is 401
 */
export async function handleAuthError(response: Response): Promise<void> {
  if (response.status !== 401) {
    return;
  }

  // Try to get error details from response text
  let errorText = '';
  try {
    errorText = await response.text();
  } catch {
    // Ignore - we'll use default message
  }

  // Check if the error message indicates session expiry vs permission issues.
  // Backend returns specific HTML messages:
  // - "<h1>Session Expired</h1>..." for expired JWT tokens (jwt.ExpiredSignatureError)
  // - "<h1>Access Denied</h1><p>You don't have permission..." for missing permissions/claims
  // - "You are not authorized to view..." for specific resource authorization failures
  const isSessionExpired = errorText.includes('<h1>Session Expired</h1>');
  const isPermissionError =
    errorText.includes("<h1>Access Denied</h1><p>You don't have permission") ||
    errorText.includes('You are not authorized to');

  let message: string;
  if (isSessionExpired) {
    // JWT token has expired (exp claim in the past)
    message = `Your session has expired. Please return to Slack and run !admin in your governance channel.`;
  } else if (isPermissionError) {
    // Permission denied - user lacks required permissions or never authenticated
    message = `You don't have permission to access this view.`;
  } else {
    // Fallback: treat unknown 401 errors as permission issues
    message = `You don't have permission to access this view.`;
  }

  throw new AuthError(message, isSessionExpired);
}

/**
 * Wrapper for fetch that automatically handles 401 errors.
 *
 * @param url - The URL to fetch
 * @param options - Optional fetch options
 * @returns The fetch Response if successful
 * @throws {AuthError} If response status is 401
 * @throws {Error} For other HTTP errors
 */
export async function fetchWithAuth(url: string, options?: RequestInit): Promise<Response> {
  const response = await fetch(url, options);

  await handleAuthError(response);

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response;
}
