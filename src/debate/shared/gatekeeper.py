"""ApiGatekeeper — single chokepoint for all external API calls.

See docs/PRD_gatekeeper.md. Implementation pending Phase 4.1.
"""


class BudgetExceededError(Exception):
    """Raised when cumulative cost exceeds the configured budget."""


class QueueFullError(Exception):
    """Raised when the gatekeeper's overflow queue is at capacity."""


class ApiCallFailedError(Exception):
    """Raised when an API call exhausts retries."""


class ApiGatekeeper:
    """Centralized API call manager. Phase 4.1."""
