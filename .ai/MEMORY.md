## Active Task

Simplify ContextKit to minimal memory system: 2 files, 3 commands.

## Current Context

v0.5.0 — reduced from 10 files / 16 commands to 2 files / 3 commands.
The AI writes MEMORY.md directly after each task. Archive handles overflow.

## Key Decisions

- Single MEMORY.md replaces 10 separate files — context budget is finite
- No CLI update commands — AI writes memory directly, zero friction
- Archive only preserves history, never truncates active file

## Code Patterns

- Compact markdown: max 1 blank line between sections
- Templates have zero placeholder text

## Gotchas & Lessons

- Template pollution (`[Component Name]`) wastes context budget — never use placeholders
- CLI commands require discipline the AI doesn't have — direct file editing is reliable
- 10 files at session start = 500+ lines read before any work begins

## Next Steps

1. Deploy v0.5.0
2. Use on real projects, iterate based on what actually gets written
