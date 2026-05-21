"""Smoke tests — verify the package imports and version is correct."""

import debate


def test_package_imports() -> None:
    """The `debate` package must be importable."""
    assert debate is not None


def test_version_is_set() -> None:
    """Canonical version string is non-empty and starts at 1.00."""
    assert debate.__version__
    assert debate.__version__ == "1.00"
