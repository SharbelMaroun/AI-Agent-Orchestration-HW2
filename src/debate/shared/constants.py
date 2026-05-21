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


class MessageType(str, Enum):
    """Envelope type for all inter-process JSON messages."""

    OPENING_BRIEF = "OPENING_BRIEF"
    READY = "READY"
    YOUR_TURN = "YOUR_TURN"
    PING = "PING"
    VERDICT = "VERDICT"
    HEARTBEAT = "HEARTBEAT"
    COLLUSION_WARNING = "COLLUSION_WARNING"
