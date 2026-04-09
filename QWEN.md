# ⚠️ MANDATORY SESSION STARTUP PROCEDURE
# Do this FIRST, before ANY other work. No exceptions.

1. Read THIS file (QWEN.md) — you're doing it now.
2. Read ALL `.ai/*.md` files in this order:
   - Current work state `.ai/CONTEXT.md`
   - Requirements and acceptance`.ai/REQUIREMENTS.md`
   - System architecture and UI/UX design `.ai/DESIGN.md`
   - Why decisions were made `.ai/DECISIONS.md`
   - Code conventions to follow `.ai/PATTERNS.md`
   - Past mistakes to avoid `.ai/LESSONS.md`
   - Test coverage and gaps `.ai/TESTING.md`
   - Task progress and history `.ai/TASKS.md`   
   - Recent releases and deployments`.ai/RELEASE.md`
3. Only after completing step 2, proceed with the user's request.
4. User sees confirmation of what was done

> **Deep history**: Full history is preserved in `.ai/archive/` for deep context when needed.

---

## AI Memory Management

### Automatic Updates (After Every Change)
When you make meaningful code changes, architectural decisions, or finish a task:

**1. Record the change** (pick the matching command by workflow phase):

| Phase | Command |
|-------|---------|
| **Planning** | `contextkit add-requirement REQ-XXX "Title" --user-story "As a..." --priority High --acceptance "c1\|c2"` |
| | `contextkit requirement-done REQ-XXX --notes "Implementation notes"` |
| **Design** | `contextkit update-design frontend "Component details, state, events"` |
| | `contextkit update-design backend "API components, services"` |
| | `contextkit update-design api "POST /api/... Request/Response schema"` |
| | `contextkit update-design ui-patterns "Layout, accessibility, responsive"` |
| **Development** | `contextkit add-decision "Title" --context "Why" --decision "What" --consequences "Trade-offs"` |
| | `contextkit add-pattern "Category" "Title" "Description"` |
| | `contextkit add-lesson "Title" --symptom "What" --root-cause "Why" --fix "How" --prevention "Prevent"` |
| | `contextkit update-context --change "Description" --next-steps "Step 1\|Step 2"` |
| | `contextkit task-done "Task description"` |
| **Testing** | `contextkit update-testing --unit N --integration N --gaps "Known gaps" --benchmarks "Metric: value"` |
| **Release** | `contextkit add-release v0.1.0 --added "F1\|F2" --fixed "Bug" --deployment "Env: Status"` |

**2. End of session**: `contextkit compress` (AI reads each file, writes compressed version, originals auto-archived)

**3. Verify**:
   - Read the tail of the updated `.ai/*.md` file to confirm it looks correct
   - Run `pytest` to ensure nothing broke
   - Run `contextkit status` to check file health

**4. Report back**:
   - Confirm what was changed in memory
   - Report test status
   - Flag any conflicts or stale content

### Periodic Maintenance
- Run `contextkit maintain` to rotate large files and archive old content
