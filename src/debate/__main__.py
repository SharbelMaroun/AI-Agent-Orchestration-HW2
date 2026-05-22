"""Entry point so `python -m debate` launches the terminal menu.

Mirrors the `debate` script registered in `pyproject.toml` so users have a
working command whether they install the script or invoke the package
directly.
"""

import sys

from debate.main import cli

if __name__ == "__main__":
    sys.exit(cli())
