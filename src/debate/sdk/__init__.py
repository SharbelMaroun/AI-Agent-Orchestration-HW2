"""Public SDK — sole entry point for all business logic.

CLI / GUI / future API delegate to DebateSDK. See CLAUDE.md §4 SDK rule.
"""

# NOTE: do NOT re-export DebateSDK here. `debate.sdk.wiring` is imported by the
# process worker (debate.services.process_worker), so importing this package
# must stay lightweight — eagerly importing debate.sdk.sdk (which pulls in the
# process orchestrator) creates a circular import. Import the facade directly:
# `from debate.sdk.sdk import DebateSDK`.
from debate.shared.version import __version__

__all__ = ["__version__"]
