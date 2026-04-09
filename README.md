# ContextKit

**Full SDLC memory system for AI coding agents.**

Persist project context across AI sessions using a hybrid approach:
- **LLM compression** — Per-file summarization keeps active files small and dense
- **Python archiving** — Deterministic rotation with full history preservation

Covers: Requirements → Design → Development → Testing → Release

## Install

```bash
pipx install .
```

If `contextkit` is not found on Windows:

```powershell
python -m pipx ensurepath
```

Fallback:

```bash
python -m pip install .
python -m contextkit --help
```

## Quick Start

### 1. Initialize Memory System

```bash
contextkit init
```

### 2. Plan: Requirements

```bash
contextkit add-requirement REQ-001 "User Authentication" \
  --user-story "As a user, I want to log in so that I can access my data" \
  --priority High \
  --acceptance "Login form validates credentials|Session persists across refresh|Logout clears session"

contextkit requirement-done REQ-001 --notes "Implemented with JWT"
```

### 3. Design: Architecture & UI/UX

```bash
contextkit update-design backend "REST API with FastAPI. Components: auth, users, tasks."
contextkit update-design frontend "React components: LoginForm, Dashboard. State: React context."
contextkit update-design ui-patterns "Data tables: sortable, filterable, paginated."
contextkit update-design api "POST /api/auth/login {email, password} -> 200 {token}"
```

### 4. Record Decisions, Patterns, Lessons

```bash
contextkit add-decision "Use SQLite" \
  --context "Simple deployment" \
  --decision "SQLite with WAL mode" \
  --consequences "Easier deployment, limited concurrency"

contextkit add-pattern "Error Handling" "Retry with backoff" "Use tenacity for retries"

contextkit add-lesson "WAL mode locks" \
  --symptom "Database locked errors" \
  --root-cause "Missing WAL config" \
  --fix "Added ?_journal_mode=WAL" \
  --prevention "Always configure WAL mode"
```

### 5. Track Tasks & Testing

```bash
contextkit task-done "Implement JWT authentication"

contextkit update-testing \
  --unit 75 --integration 60 --e2e 0 \
  --gaps "E2E not set up|Need UI component tests" \
  --benchmarks "API response: 200ms (target: 500ms)"
```

### 6. Release

```bash
contextkit add-release v0.1.0 \
  --added "User authentication|Task management" \
  --changed "Refactored auth module" \
  --fixed "Login form validation bug" \
  --deployment "Production: Deployed|Staging: Verified"
```

### 7. Compress Context (End of Session)

Compress all accumulating `.ai/` files into concise versions:

```bash
contextkit compress
```

This displays each file with targeted compression instructions. The AI reads the output, writes compressed versions, and originals are auto-archived.

**No API keys needed** — uses your existing AI session.

### 8. Maintain & Archive

```bash
# Rotate large files, archive old content
contextkit maintain

# Preview without making changes
contextkit maintain --dry-run --explain
```

## Workflow

### Typical AI Session

1. **Session start** → AI reads all `.ai/*.md` files (especially CONTEXT.md)
2. **During work** → AI uses update commands after meaningful changes
3. **Session end** → Run `contextkit compress` to compress all files with AI help
4. **Periodically** → Run `contextkit maintain` to archive large files

### Qwen Code Integration

Add to your project's `QWEN.md`:

```markdown
## AI Memory Management

### Automatic Updates (After Every Change)
When you make meaningful code changes, architectural decisions, or finish a task:
1. Use update commands to record the change:
   - `contextkit add-requirement` / `requirement-done`
   - `contextkit update-design` / `add-decision` / `add-pattern`
   - `contextkit add-lesson` / `update-context` / `task-done`
   - `contextkit update-testing` / `add-release`
2. Run `contextkit compress` at end of session to compress all files with AI
3. Run `contextkit maintain` periodically to archive large files

### Session Start
Read ALL `.ai/*.md` files at session start to understand current project state.
Full history is preserved in `.ai/archive/` for deep context when needed.
```

## Command Reference

### Init & Status

| Command | Description |
|---------|-------------|
| `contextkit init` | Create `.ai/` files and archive structure |
| `contextkit status` | Show file sizes and missing files |

### Planning (Requirements)

| Command | Description | Example |
|---------|-------------|---------|
| `add-requirement` | Add feature requirement | `contextkit add-requirement REQ-001 "Auth" --user-story "..." --priority High --acceptance "c1\|c2"` |
| `requirement-done` | Mark requirement done | `contextkit requirement-done REQ-001 --notes "Implemented with JWT"` |

### Design

| Command | Description | Example |
|---------|-------------|---------|
| `update-design` | Update design section | `contextkit update-design frontend "React components: ..."` |

Design sections: `architecture`, `backend`, `frontend`, `ui-patterns`, `data-models`, `api`, `state`, `dependencies`

### Development

| Command | Description | Example |
|---------|-------------|---------|
| `add-decision` | Record architecture decision | `contextkit add-decision "Use X" --context "Why" --decision "What" --consequences "Trade-offs"` |
| `add-pattern` | Record code pattern | `contextkit add-pattern "Category" "Title" "Description"` |
| `add-lesson` | Document lesson learned | `contextkit add-lesson "Bug" --symptom "What" --root-cause "Why" --fix "How" --prevention "Prevent"` |
| `update-context` | Update current context | `contextkit update-context --change "Description" --next-steps "Step 1\|Step 2"` |
| `task-done` | Mark task completed | `contextkit task-done "Task description"` |

### Testing

| Command | Description | Example |
|---------|-------------|---------|
| `update-testing` | Update test status | `contextkit update-testing --unit 75 --integration 60 --gaps "E2E not set up" --benchmarks "API: 200ms"` |

### Release

| Command | Description | Example |
|---------|-------------|---------|
| `add-release` | Add release notes | `contextkit add-release v0.1.0 --added "Feature 1\|Feature 2" --fixed "Bug fix"` |

### Compression (LLM-driven)

| Command | Description |
|---------|-------------|
| `compress` | Display all accumulating files for AI to compress into concise versions |
| `compress --write FILE --content "..."` | Write compressed content for a specific file (auto-archives original) |

### Maintenance

| Command | Description |
|---------|-------------|
| `maintain` | Rotate large files, archive old tasks |
| `all` | Run init + maintain |

**Maintain options:**
- `--line-threshold N` — Rotate files with >N lines (default: 100)
- `--keep-last N` — Keep last N lines when rotating (default: 60)
- `--task-days N` — Archive tasks older than N days (default: 30)
- `--dry-run` — Preview without making changes
- `--explain` — Show what would be done and why

## Architecture

```
.ai/
├── CONTEXT.md          ← LLM-compressed current state (READ AT SESSION START)
├── REQUIREMENTS.md     ← Features, user stories, acceptance criteria
├── DESIGN.md           ← System architecture, frontend/backend, UI/UX, APIs
├── DECISIONS.md        ← Architecture decisions (ADRs)
├── PATTERNS.md         ← Code conventions and anti-patterns
├── LESSONS.md          ← Lessons learned from bugs
├── TESTING.md          ← Test coverage, gaps, benchmarks
├── TASKS.md            ← Active and completed tasks
├── RELEASE.md          ← Release history, deployment notes
│
└── archive/            ← Full history (Python-based, lossless)
    ├── context/
    ├── requirements/
    ├── design/
    ├── decisions/
    ├── patterns/
    ├── lessons/
    ├── testing/
    ├── tasks/
    └── releases/
```

**Hybrid approach:**
- **LLM** for intelligent compression (summarization)
- **Python** for deterministic operations (rotation, archival)

## Code Structure

```
contextkit/
├── __init__.py     # Package entry point
├── cli.py          # Argument parsing, command dispatch
├── commands.py     # SDLC command implementations
├── compress.py     # LLM-driven per-file compression protocol
├── maintain.py     # Archive rotation logic
└── files.py        # File I/O, templates, markdown helpers
tests/
├── test_cli.py     # CLI command tests
└── test_files.py   # File utility tests
```

## Remove

```bash
rm -rf .ai/
```

## License

MIT
