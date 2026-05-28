"""AI Agent Debate — top-level package.

Exposes the public SDK and the canonical version string.
See docs/PRD.md and docs/PLAN.md.
"""

import logging as _logging
import os as _os
import warnings as _warnings

# Silence Hugging Face Hub's anonymous-rate-limit nudge ("You are sending
# unauthenticated requests to the HF Hub..."). The nudge is emitted via
# warnings.warn from `huggingface_hub`. Warning filters do NOT cross the
# multiprocessing boundary, so suppressing only in `embedder.py` misses
# subprocess workers spawned by `process_orchestrator`. Setting it here
# means every Python interpreter that imports `debate` — parent or child —
# applies the filter before any HF code runs. Env vars are also set since
# they DO cross the boundary and cover the related telemetry/progress paths.
_os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
_os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
_os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
_logging.getLogger("huggingface_hub").setLevel(_logging.ERROR)
_warnings.filterwarnings("ignore", message=".*unauthenticated requests to the HF Hub.*")
_warnings.filterwarnings("ignore", message=".*HF_TOKEN.*")

from debate.shared.version import __version__  # noqa: E402

__all__ = ["__version__"]
