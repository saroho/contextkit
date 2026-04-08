# AI Memory System

A platform-agnostic memory layer for AI-assisted development.  
Works with Qwen Code, Claude Code, Cursor, OpenAI Codex, and any assistant that can read project files.

---

## Goal

AI sessions reset. Your project context should not.

This system keeps:
- Current task state
- Architecture decisions
- Code conventions
- Lessons from bugs/incidents
- Lightweight task history

---

## Architecture (Simple)

Think in 2 layers:

1. Core layer (required, no skill needed)
   - `.ai/CONTEXT.md`
   - `.ai/DECISIONS.md`
   - `.ai/PATTERNS.md`
   - `.ai/LESSONS.md`
   - `.ai/TASKS.md`

2. Automation layer (optional)
   - Skill-based maintenance (for rotation/archiving/dedup)
   - `.ai/INDEX.md` and `.ai/CONFIG.md` if you want stricter operations

If you do nothing else, just keep the 5 core files updated.

---

## Quick Install

### One-Tool Mode (Recommended)

No skill required. Run from project root:

```bash
python ai_memory_tool.py all
```

What it does:
- Creates missing `.ai/` core files
- Preserves existing `.ai/` files (no overwrite by default)
- Creates missing archive subfolders
- Rotates oversized memory files
- Archives completed tasks older than 30 days

Useful commands:

```bash
python ai_memory_tool.py status
python ai_memory_tool.py init
python ai_memory_tool.py maintain
python ai_memory_tool.py all --line-threshold 120 --keep-last 80 --task-days 45
```

### Option A: New Project (No Existing `.ai`)

1. Copy the `templates/*.md` files into a new `.ai/` folder.
2. Rename files as needed to:
   - `README.md`
   - `CONTEXT.md`
   - `DECISIONS.md`
   - `PATTERNS.md`
   - `LESSONS.md`
   - `TASKS.md`
3. Create archive folders:
   - `.ai/archive/context`
   - `.ai/archive/decisions`
   - `.ai/archive/patterns`
   - `.ai/archive/lessons`
   - `.ai/archive/tasks`

### Option B: Existing `.ai` Folder (Recommended Merge-Safe Path)

Use this if your team already has `.ai/` but no skill:

1. Backup current `.ai/` (copy it somewhere safe).
2. Keep your existing files as source of truth.
3. Add only missing files from this system:
   - `CONTEXT.md`, `DECISIONS.md`, `PATTERNS.md`, `LESSONS.md`, `TASKS.md`
4. For files that already exist, merge section-by-section instead of overwriting.
5. Add missing archive subfolders under `.ai/archive/`.
6. Commit after merge so your team has a clean baseline.

This path avoids breaking existing workflows and does not require any skill tooling.

---

## Daily Workflow

| Event | Update |
| :--- | :--- |
| Start work | `CONTEXT.md` |
| Make architecture choice | `DECISIONS.md` |
| Define coding convention | `PATTERNS.md` |
| Fix incident/bug | `LESSONS.md` |
| Finish task | `TASKS.md` |

Keep entries short. High signal wins.

---

## Manual Maintenance (No Skill)

Run weekly or bi-weekly:

1. Move old entries from working files into matching archive files.
2. Keep active files small (target under 100 lines where possible).
3. Remove duplicate lessons and stale completed tasks.
4. Commit `.ai/` changes with normal project commits.

Suggested commit message:

```text
chore(memory): rotate .ai files and archive old entries
```

You can do the same with the tool:

```bash
python ai_memory_tool.py maintain
```

---

## Optional Skill Automation

If you later want automation, add a maintenance skill.  
The system works without it, but automation helps as the project grows.

---

## Agent Integration

Add this to your project instructions (`AGENTS.md`, `.cursorrules`, etc):

```markdown
Read `.ai/CONTEXT.md` at session start.
Review `.ai/DECISIONS.md` before architectural changes.
Follow `.ai/PATTERNS.md` for code style.
Check `.ai/LESSONS.md` for related past issues.
Update `.ai/TASKS.md` when work is completed.
```

---

## Minimal Directory Layout

```plain
.ai/
├── README.md
├── CONTEXT.md
├── DECISIONS.md
├── PATTERNS.md
├── LESSONS.md
├── TASKS.md
└── archive/
    ├── context/
    ├── decisions/
    ├── patterns/
    ├── lessons/
    └── tasks/
```

---

## Troubleshooting

| Problem | Fix |
| :--- | :--- |
| AI ignores `.ai/` | Add explicit instruction in `AGENTS.md` / tool rules |
| `.ai` grows too fast | Archive weekly and keep active files short |
| Team merge conflicts | Keep one section per entry and merge by section |
| Existing `.ai` format differs | Map old sections into the 5 core files gradually |

---

## License

MIT
