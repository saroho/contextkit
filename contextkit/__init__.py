"""ContextKit - Full SDLC memory system for AI coding agents."""

__version__ = "0.4.0"


def cli() -> None:
    """Entry point for the contextkit CLI command."""
    from .cli import cli as _cli
    _cli()
