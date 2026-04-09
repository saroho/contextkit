# Context Kit

## Problem

AI coding agents forget everything between sessions.

## Solution

One file. Optionally two.

```
.ai/MEMORY.md      ← always
.ai/DESIGN.md      ← only if architecture is non-trivial
.ai/archive/       ← historical snapshots
```

## Setup

Create `.ai/MEMORY.md`:

```markdown
## Active Task

## Current Context

## Key Decisions

## Code Patterns

## Gotchas & Lessons

## Next Steps
```

Create `.ai/DESIGN.md` only if needed:

```markdown
## Architecture
```

## How It Works

1. **Session start** — Read `.ai/MEMORY.md` (and `.ai/DESIGN.md` if it exists)
2. **During work** — Update after meaningful changes
3. **Session end** — Keep under ~150 lines

### When It Grows Too Large

1. Copy full `.ai/MEMORY.md` → `.ai/archive/MEMORY_YYYY-MM-DD.md`
2. Compress `.ai/MEMORY.md` down to ~80 lines
3. Keep: active task, key decisions, current gotchas
4. Drop: completed tasks, obsolete context

## For Your Project

### Works with Claude Code, Gemini CLI, and Cursor

This convention is **just markdown files in your repo**, so you can use it with any AI coding tool that can read project instructions and edit files.

Add the following snippet to your tool’s project instruction file:

- **Claude Code CLI**: `CLAUDE.md` (repo root)
- **Qwen**: `QWEN.md` (repo root)
- **Cursor**: `.cursor/rules/ai-memory.md` (recommended) or your existing Cursor rules/instructions file
- **Gemini CLI**: your Gemini CLI project instruction file (use whatever file your setup already loads for repo-level guidance; if you don’t have one yet, create a repo-root instruction file and point Gemini CLI at it)

```markdown
## Memory

Read `.ai/MEMORY.md` at session start.
Read `.ai/DESIGN.md` if it exists.
Update after meaningful changes.
Keep under ~150 lines.

### When MEMORY.md approaches 150 lines:
1. Copy full content to `.ai/archive/MEMORY_YYYY-MM-DD.md`
2. Compress `.ai/MEMORY.md` to ~80 lines
3. Keep: active task, key decisions, current gotchas
4. Drop: completed tasks, obsolete context
```

## No Tool Required

The AI reads and writes markdown files natively.
No CLI, no package, no friction. Just files and a convention.
