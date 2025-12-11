"""Re-export FakeStripeClient from the shared test utils location.

DEPRECATED: This file is maintained for backward compatibility.
Import directly from tests.utils.stripe_client instead.
"""

# Re-export the consolidated FakeStripeClient
from csbot.stripe.stripe_protocol import StripeClientProtocol
from tests.utils.stripe_client import FakeStripeClient

# Ensure the test client follows the protocol (for backward compatibility)
assert isinstance(FakeStripeClient("test_key"), StripeClientProtocol)
