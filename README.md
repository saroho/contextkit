# ContextKit

Persist project "memory" for AI coding agents in a small set of files under `.ai/`.

## What you get

- **Curated memory files**: `CONTEXT.md`, `DECISIONS.md`, `PATTERNS.md`, `LESSONS.md`, `TASKS.md`
- **Maintenance**: `contextkit maintain` rotates large files and archives completed tasks
- **Works with Qwen Code**: plain CLI + project `QWEN.md` instructions

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

## Use

Create `.ai/` files:

```bash
contextkit init
```

Maintain (rotate large files, archive old tasks):

```bash
contextkit maintain
```

Both in one:

```bash
contextkit all
```

Check status:

```bash
contextkit status
```

## Qwen Code Integration

Add to your project's `QWEN.md`:

```
When you make meaningful code changes, run the `contextkit` skill to update `.ai/` files.
```

Install the project Skill:

```bash
contextkit skill-install --tool qwen --scope project
```

Restart Qwen Code, then invoke:

```
/skills contextkit
```

## Remove

```bash
rm -rf .ai/
```

## License

MIT
