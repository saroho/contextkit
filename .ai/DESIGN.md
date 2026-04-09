## Architecture

Single-file Python package: `contextkit/` with `cli.py` (commands), `files.py` (I/O, templates).
Entry points: `contextkit:cli` via pyproject.toml scripts, `python -m contextkit` via `__main__.py`.
