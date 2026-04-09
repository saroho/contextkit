"""ContextKit — minimal project memory for AI coding agents."""

__version__ = "0.5.0"


def cli() -> None:
    """Entry point: contextkit."""
    from .cli import cli as _cli

    _cli()
