"""Custom httpx transport that logs retry attempts."""

import httpx
import structlog

logger = structlog.get_logger(__name__)


class RetryLoggingTransport(httpx.AsyncHTTPTransport):
    """HTTPx transport wrapper that logs retry attempts.

    This transport wraps the standard AsyncHTTPTransport and intercepts
    responses to detect and log 429 rate limit errors before they trigger
    retries in the Anthropic SDK.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.retry_count = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Handle request and log retries."""
        response = await super().handle_async_request(request)

        # Log 429 responses (which will trigger retries in the SDK)
        if response.status_code == 429:
            self.retry_count += 1
            retry_after = response.headers.get("retry-after", "unknown")
            logger.warning(
                "Rate limit hit (429) - SDK will retry",
                retry_count=self.retry_count,
                retry_after=retry_after,
                request_url=str(request.url),
                status_code=response.status_code,
            )

        # Log other retryable errors (408, 409, 5xx)
        elif response.status_code in (408, 409) or response.status_code >= 500:
            self.retry_count += 1
            logger.warning(
                f"Retryable error ({response.status_code}) - SDK will retry",
                retry_count=self.retry_count,
                request_url=str(request.url),
                status_code=response.status_code,
            )

        return response
