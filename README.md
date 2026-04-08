# ContextKit

Persist project “memory” for AI coding agents in a small set of files under `.ai/`.

### What you get

- **Curated memory files**: `CONTEXT.md`, `DECISIONS.md`, `PATTERNS.md`, `LESSONS.md`, `TASKS.md`
- **Maintenance**: `contextkit maintain` rotates large files, archives completed tasks, and **compacts** empty/low-signal sections to keep files LLM-friendly
- **Works with tools**: plain CLI, Qwen project Skill, or MCP tool server (Claude Code / MCP-capable CLIs)

## Install

Recommended:

```bash
pipx install .
```

If `contextkit` is not found on Windows:

```powershell
python -m pipx ensurepath
```

Fallback (works everywhere):

```bash
python -m pip install .
python -m contextkit --help
```

## Use (in any project root)

Create/update `.ai/`:

```bash
contextkit all
```

Maintain `.ai/`:

```bash
contextkit maintain
```

## Qwen Code CLI (project Skill)

Install the Skill into `.qwen/skills/contextkit/SKILL.md`:

```bash
contextkit skill-install --tool qwen --scope project
```

Restart Qwen Code if it’s already running, then invoke explicitly:

```text
/skills contextkit
```

Recommended workflow inside Qwen Code:

- Read `.ai/CONTEXT.md` first
- After meaningful changes, update `.ai/*` and run:

```text
!contextkit maintain
```

## Claude Code CLI (tool via MCP)

Install with MCP extras:

```bash
pipx install ".[mcp]"
```

Add MCP server (project scope):

```bash
claude mcp add --transport stdio --scope project contextkit -- python -m contextkit mcp-serve
```

Verify it’s connected:

```bash
claude mcp list
```

Inside Claude Code you can ask it to run the ContextKit tools (for example “run contextkit_maintain”).

## Remove (from a project)

Preview:

```bash
contextkit remove --what all
```

Delete:

```bash
contextkit remove --what all --yes
```

## License

MIT

