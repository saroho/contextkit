# ContextKit

Simple memory system for AI coding workflow.
It works with Qwen Code, Claude Code, Cursor, OpenAI Codex, and other tools.

## Why Use ContextKit

ContextKit is for curated project memory, not raw session logs.

- Keep what matters: decisions, patterns, lessons, tasks
- Find answers fast in clear files like `DECISIONS.md` and `PATTERNS.md`
- Share with team in Git, not locked to one assistant tool
- Keep architecture knowledge for months/years

Mem tools can still help for personal recall (recent files, recent errors), but your `.ai/` files stay the main source of truth for project context.

---

## What Is This

AI assistant forgets after session close.
This project gives you persistent memory files inside `.ai/`.

Main files:
- `CONTEXT.md` for current work
- `DECISIONS.md` for architecture choices
- `PATTERNS.md` for coding conventions
- `LESSONS.md` for bug lessons
- `TASKS.md` for active and done tasks

---

## Full Setup Guide

### Step 1: Get This Repository

You can clone:

```bash
git clone https://github.com/yourusername/ai-memory-system.git
cd ai-memory-system
```

Or you can download ZIP and extract.

---

### Step 2: Put Into Your Project

Go to your real project root, then copy these files:
- `contextkit.py`
- `templates/`

Also copy `.gitignore` rules from this repo if needed.

Example:

```bash
# from this repository folder
cp contextkit.py /path/to/your-project/
cp -r templates /path/to/your-project/
```

If you use Windows and `cp` not available, do same with File Explorer.

---

### Step 3: Run One Command

Inside your project root:

```bash
python contextkit.py all
```

This command will:
- Create missing `.ai/` files
- Keep existing `.ai/` files (no overwrite by default)
- Create `.ai/archive/*` folders
- Rotate too large files
- Archive old completed tasks

No skill is required.

---

## If You Already Have `.ai` Folder

This is safe path:

1. Backup your current `.ai/` folder.
2. Run:
   ```bash
   python contextkit.py init
   ```
3. Tool will only create missing files, not replace existing content.
4. Open your files and merge sections if you want better structure.
5. Commit changes.

---

## Tool Commands

```bash
python contextkit.py status
python contextkit.py init
python contextkit.py maintain
python contextkit.py all
python contextkit.py plan-check --plan-file .ai/maintain-plan.json
python contextkit.py llm-plan-input
python contextkit.py plan-template
python contextkit.py plan-schema
python contextkit.py llm-prompt
```

If you want one skill for everything, use this single entrypoint:

```bash
python contextkit.py skill status
python contextkit.py skill init
python contextkit.py skill maintain
python contextkit.py skill all
```

Custom limits example:

```bash
python contextkit.py all --line-threshold 120 --keep-last 80 --task-days 45
```

Use LLM plan with deterministic execution:

```bash
python contextkit.py maintain --plan-file .ai/maintain-plan.json
```

Safe simulation:

```bash
python contextkit.py maintain --plan-file .ai/maintain-plan.json --dry-run --explain --deterministic
```

Strict validation only:

```bash
python contextkit.py plan-check --plan-file .ai/maintain-plan.json --min-confidence 0.6
```

---

## Daily Usage

At start of work:
- Update `CONTEXT.md`

When architecture decision done:
- Update `DECISIONS.md`

When you set naming/pattern:
- Update `PATTERNS.md`

When bug is fixed:
- Update `LESSONS.md`

When task completed:
- Update `TASKS.md`

Keep text short and clear.

---

## Maintenance Without Skill

Run once per week (or two weeks):

```bash
python contextkit.py maintain
```

Good commit message:

```text
chore(memory): maintain .ai files
```

---

## Add To Agent Instructions

Put this in `AGENTS.md` or tool rule file:

```markdown
Read `.ai/CONTEXT.md` at session start.
Check `.ai/DECISIONS.md` before architecture changes.
Follow `.ai/PATTERNS.md` for conventions.
Look at `.ai/LESSONS.md` for similar past issues.
Update `.ai/TASKS.md` after finishing work.
```

If your platform supports custom skill command, map skill actions:

```text
/contextkit status   -> python contextkit.py skill status
/contextkit init     -> python contextkit.py skill init
/contextkit maintain -> python contextkit.py skill maintain
/contextkit all      -> python contextkit.py skill all
/contextkit llm-plan-input -> python contextkit.py skill llm-plan-input
/contextkit plan-template  -> python contextkit.py skill plan-template
/contextkit plan-schema    -> python contextkit.py skill plan-schema
/contextkit plan-check     -> python contextkit.py skill plan-check --plan-file .ai/maintain-plan.json
/contextkit llm-prompt     -> python contextkit.py skill llm-prompt
```

---

## Hybrid LLM + Python Archive Flow

This project now supports a hybrid mode:
- LLM decides what to rotate/archive
- Python validates and executes plan safely

Step 1: Export project context for LLM:

```bash
python contextkit.py llm-plan-input > .ai/llm-input.json
```

Step 2: Write strict JSON schema:

```bash
python contextkit.py plan-schema
```

Step 3: Get JSON template:

```bash
python contextkit.py plan-template > .ai/maintain-plan.template.json
```

Step 4: Optional, generate a complete planning prompt:

```bash
python contextkit.py llm-prompt > .ai/llm-plan.prompt.txt
```

Step 5: Ask your LLM to produce `.ai/maintain-plan.json` from input + template.

Step 6: Validate plan before execution:

```bash
python contextkit.py plan-check --plan-file .ai/maintain-plan.json --deterministic --min-confidence 0.6
```

Step 7: Execute safely with Python:

```bash
python contextkit.py maintain --plan-file .ai/maintain-plan.json --deterministic --explain
```

Notes:
- Plan file must be valid JSON and version `1`
- Only these files are allowed in `rotate`: `CONTEXT.md`, `DECISIONS.md`, `PATTERNS.md`, `LESSONS.md`, `TASKS.md`
- Each rule can include `confidence` and `reason`
- Python applies safety caps and can reject risky plans
- If plan fails validation, tool falls back to deterministic defaults (unless `--no-fallback`)
- Accepted plans are archived in `.ai/archive/plans/`
- Metrics are tracked in `.ai/archive/metrics.json`

### Safety Controls

```bash
python contextkit.py maintain \
  --plan-file .ai/maintain-plan.json \
  --max-files-rotated 3 \
  --max-lines-removed 500 \
  --max-archive-chars 120000 \
  --min-confidence 0.6
```

### Good Plan Example

```json
{
  "version": 1,
  "rotate": [
    {
      "file": "CONTEXT.md",
      "line_threshold": 130,
      "keep_last": 80,
      "confidence": 0.92,
      "reason": "Context grows quickly and recent lines are most relevant."
    }
  ],
  "tasks": {
    "enabled": true,
    "days": 40,
    "confidence": 0.9,
    "reason": "Old completed tasks are archived after 40 days."
  },
  "limits": {
    "max_files_rotated": 2,
    "max_total_lines_removed": 250,
    "max_archive_chars_added": 60000
  }
}
```

### Bad Plan Example (Rejected)

```json
{
  "version": 1,
  "rotate": [
    {
      "file": ".env",
      "line_threshold": -5,
      "keep_last": -10,
      "confidence": 1.2,
      "reason": ""
    }
  ],
  "tasks": {
    "enabled": "yes",
    "days": -30
  }
}
```

---

## Skill Setup Examples (Qwen, Claude, Others)

Use this section if you want one command like `/contextkit all`.

### Qwen Code CLI

If your Qwen setup supports local skills folder, create a skill file in:
- `~/.qwen/skills/contextkit/SKILL.md`

Example `SKILL.md`:

```markdown
---
name: contextkit
description: Manage .ai memory files in project
---

## Commands
- `/contextkit status` -> `python contextkit.py skill status`
- `/contextkit init` -> `python contextkit.py skill init`
- `/contextkit maintain` -> `python contextkit.py skill maintain`
- `/contextkit all` -> `python contextkit.py skill all`
```

After adding skill, restart Qwen CLI and test:

```text
/contextkit status
```

### Claude CLI

If Claude CLI does not have native skill registry in your environment, use command aliases.
PowerShell example:

```powershell
function contextkit { python contextkit.py skill $args }
```

Then use:

```powershell
contextkit status
contextkit all
```

### Generic CLI (Codex CLI, Cursor terminal, others)

Create one wrapper script in project root:

```bash
python contextkit.py skill all
```

Or create shell aliases:

```bash
alias contextkit='python contextkit.py skill'
contextkit status
contextkit maintain
```

Note:
- Exact skill registration can differ by CLI version.
- If slash-command registration is different in your setup, keep command target same:
  `python contextkit.py skill <action>`

---

## Folder Layout

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

| Problem | Solution |
| :--- | :--- |
| AI does not read `.ai/` | Add explicit instruction in `AGENTS.md` |
| Files become too big | Run `python contextkit.py maintain` |
| Team has merge conflict | Keep one entry per section, merge carefully |
| Existing format is different | Migrate gradually, no need big-bang rewrite |

---

## License

MIT


