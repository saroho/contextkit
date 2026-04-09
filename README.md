# ContextKit

**Minimal project memory for AI coding agents.**

Two files. Three commands. Zero friction.

## The Problem

Every AI coding session starts amnesiac. The agent forgets everything between sessions.

## The Solution

`.ai/MEMORY.md` — a single file the AI reads at session start and updates after each task.

The tool only handles file creation and archival. The AI writes the memory itself.

## Install

```bash
pipx install .
```

## Quick Start

```bash
# Create .ai/ directory with clean MEMORY.md and DESIGN.md
contextkit init

# Check file sizes
contextkit status

# Archive files that have grown (default: 150 lines)
contextkit archive
```

## How It Works

### Session Start
AI reads `.ai/MEMORY.md` (should be <150 lines) to understand:
- What's being worked on
- Key decisions made
- Code patterns to follow
- Gotchas to avoid
- Next steps

### During Session
AI writes directly to `.ai/MEMORY.md` after meaningful changes.
No CLI commands needed. No friction.

### Session End
AI compresses MEMORY.md to keep it under ~150 lines.
Old content can be archived with `contextkit archive`.

### When Files Grow Too Large
```bash
contextkit archive          # Save overflow to .ai/archive/
contextkit archive --dry-run  # Preview what would happen
```

## Files

| File | Purpose |
|------|---------|
| `.ai/MEMORY.md` | Active project memory (read at session start) |
| `.ai/DESIGN.md` | Architecture notes (only if non-trivial) |
| `.ai/archive/` | Full history, never deleted |

## Commands

| Command | Description |
|---------|-------------|
| `contextkit init` | Create `.ai/MEMORY.md` and `.ai/DESIGN.md` |
| `contextkit status` | Show file sizes |
| `contextkit archive` | Archive files exceeding 150 lines |

## For Project Setup

Add to your project's `QWEN.md` or `CLAUDE.md`:

```markdown
## Memory
Read `.ai/MEMORY.md` at session start.
Update it after meaningful changes.
Keep it under ~150 lines.
Run `contextkit archive` if it grows too large.
```

## Code Structure

```
contextkit/
├── __init__.py   # Package + entry point
├── __main__.py   # python -m support
├── cli.py        # init, status, archive
└── files.py      # I/O, templates, compact
tests/
└── test_cli.py   # 14 tests
```

## License

MIT
