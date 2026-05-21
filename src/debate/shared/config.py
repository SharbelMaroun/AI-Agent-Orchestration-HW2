"""Config loader: parses config/*.json + .env. See docs/PLAN.md §7.

Implementation pending Phase 3.2.
"""


class SetupConfig:
    """Mirrors config/setup.json. Phase 3.2."""


class RateLimitConfig:
    """Mirrors config/rate_limits.json. Phase 3.2."""


class LoggingConfig:
    """Mirrors config/logging_config.json. Phase 3.2."""


def load_setup(path: str = "config/setup.json") -> SetupConfig:
    """Load and validate setup.json. Phase 3.2."""
    raise NotImplementedError


def load_rate_limits(path: str = "config/rate_limits.json") -> RateLimitConfig:
    """Load and validate rate_limits.json. Phase 3.2."""
    raise NotImplementedError


def load_logging(path: str = "config/logging_config.json") -> LoggingConfig:
    """Load and validate logging_config.json. Phase 3.2."""
    raise NotImplementedError
