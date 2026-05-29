"""Project-wide constants. No hardcoded values from CLAUDE.md §8 live here —
this file is for genuinely immutable categorical values only.
"""

from enum import Enum
from pathlib import Path

DEFAULT_CONFIG_DIR: Path = Path("config")
DEFAULT_RESULTS_DIR: Path = Path("results")
DEFAULT_DATA_DIR: Path = Path("data")

SIDE_DOGS: str = "dogs"
SIDE_CATS: str = "cats"

DEFAULT_MAX_TOKENS: int = 1024
# Fallback per-ping word cap for direct Orchestrator construction only; the real
# debate flow sources this from setup.max_words_per_ping (see sync_runner).
DEFAULT_MAX_WORDS_PER_PING: int = 250


class MessageType(str, Enum):
    """Envelope type for all inter-process JSON messages."""

    OPENING_BRIEF = "OPENING_BRIEF"
    READY = "READY"
    YOUR_TURN = "YOUR_TURN"
    PING = "PING"
    VERDICT = "VERDICT"
    HEARTBEAT = "HEARTBEAT"
    COLLUSION_WARNING = "COLLUSION_WARNING"
