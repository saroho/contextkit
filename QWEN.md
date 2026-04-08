# Project Instructions

## AI Memory Management

### Automatic Updates (After Every Change)
When you make meaningful code changes, architectural decisions, or finish a task:
1. Use update commands to record the change:

**Planning:**
- `contextkit add-requirement REQ-001 "Title" --user-story "As a [user], I want [goal]" --priority High --acceptance "Criterion 1|Criterion 2"`
- `contextkit requirement-done REQ-001 --notes "Implementation notes"`

**Design:**
- `contextkit update-design frontend "Component details, state, events"`
- `contextkit update-design backend "API components, services"`
- `contextkit update-design api "POST /api/... Request/Response schema"`
- `contextkit update-design ui-patterns "Layout, accessibility, responsive"`

**Development:**
- `contextkit add-decision "Title" --context "Why" --decision "What" --consequences "Trade-offs"`
- `contextkit add-pattern "Category" "Title" "Description"`
- `contextkit add-lesson "Title" --symptom "What" --root-cause "Why" --fix "How" --prevention "Prevent"`
- `contextkit update-context --change "Description" --next-steps "Step 1|Step 2"`
- `contextkit task-done "Task description"`

**Testing:**
- `contextkit update-testing --unit 75 --integration 60 --gaps "Known gaps" --benchmarks "Metric: value"`

**Release:**
- `contextkit add-release v0.1.0 --added "Feature 1|Feature 2" --fixed "Bug fix" --deployment "Environment: Status"`

2. Run `contextkit maintain` to rotate large files and archive old content
3. Run `contextkit summarize` periodically to compress all .ai/ files into CONTEXT.md
4. User sees confirmation of what was updated

### Session Start
Read ALL `.ai/*.md` files at session start to understand:
- Current work state (CONTEXT.md)
- Requirements and acceptance (REQUIREMENTS.md)
- System architecture and UI/UX design (DESIGN.md)
- Why decisions were made (DECISIONS.md)
- Code conventions to follow (PATTERNS.md)
- Past mistakes to avoid (LESSONS.md)
- Test coverage and gaps (TESTING.md)
- Task progress and history (TASKS.md)
- Recent releases and deployments (RELEASE.md)

Full history is preserved in `.ai/archive/` for deep context when needed.
