# Explorium CLI — Development Instructions

## Project Overview

Python CLI wrapping the Explorium B2B data API. Built with Click, distributed as a PyInstaller binary. Version is in `explorium_cli/__init__.py` and `pyproject.toml`.

## Golden Rule: Keep Everything In Sync

Any change to the CLI interface (new command, renamed flag, changed behavior) **must** update all of these:

1. **The code** — `explorium_cli/commands/*.py`
2. **The help text** — Click option `help=` strings in the command decorators
3. **The skill files** — both copies must match:
   - `skills/SKILL.md` (standalone skill)
   - `plugin/skills/explorium-cli/SKILL.md` (plugin skill)
4. **The commands reference** — both copies must match:
   - `commands-reference.md` (root)
   - `plugin/skills/explorium-cli/commands-reference.md` (plugin)
5. **The CLI documentation** — `CLI_DOCUMENTATION.md`
6. **The README** — `README.md` (if the change affects user-facing examples)
7. **The architecture doc** — `Project-Architecture.md` (if the change affects modules, dependencies, structure, or design patterns)

If you change a flag name, add a command, or alter output format — grep all seven locations and update them. Do not commit code changes without updating the docs.

## Obsidian Markdown Style

All documentation files in this repo use **Obsidian Flavored Markdown**. When creating or editing any `.md` file, follow these conventions:

- **Frontmatter** — every doc must have YAML frontmatter with `title`, `date`, `tags`, and relevant metadata
- **Wikilinks** — use `[[Note Name]]` or `[[Note Name|Display Text]]` to link between docs, not standard markdown links
- **Callouts** — use `> [!type]` callouts (`note`, `tip`, `warning`, `danger`, `bug`, `info`, `todo`) instead of plain blockquotes
- **Highlights** — use `==text==` to highlight key terms or critical values
- **Tags** — use frontmatter `tags:` lists, not inline `#tags`
- **Mermaid diagrams** — use fenced `mermaid` blocks for architecture and flow diagrams

This applies to all files: PRDs, tickets, architecture docs, and any new documentation.

## Version Bumping

When releasing a new version, update **both** files:

```bash
# explorium_cli/__init__.py
__version__ = "X.Y.Z"

# pyproject.toml
version = "X.Y.Z"
```

Also update the skill version in `skills/SKILL.md` frontmatter:

```yaml
version: X.Y.Z
```

Then create a versioned skill file:

```bash
zip -j vibe-prospecting-multistep-workflow-X.Y.Z.skill skills/SKILL.md
```

## Testing

Run tests before committing any code change:

```bash
pytest tests/ -v
```

There are 22 test files. Key ones to watch:
- `test_search_filters.py` — 49 tests for filter options; update if you add/change filters
- `test_filter_validation.py` — enum validation; update if you change `constants.py`
- `test_cli_integration.py` — end-to-end CLI tests
- `test_documentation_examples.py` — validates doc examples actually work

## Building Binaries

**Before pushing to remote**, build the distribution binary for the current platform:

### macOS (Apple Silicon)

```bash
./build.sh
```

Produces `dist/explorium` and `dist/explorium-{version}-macos-{arch}`.

### Linux

```bash
./build-linux.sh
```

Produces `dist/explorium-linux-{arch}`.

### Build verification

After building, verify the binary works:

```bash
dist/explorium --version
dist/explorium --help
```

## Commit & Push Checklist

**Run this checklist before EVERY commit**, not just before push:

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Help text updated for any changed/added flags
- [ ] Both skill files updated (`skills/SKILL.md` and `plugin/skills/explorium-cli/SKILL.md`)
- [ ] Both commands-reference files updated (`commands-reference.md` and `plugin/skills/explorium-cli/commands-reference.md`)
- [ ] `CLI_DOCUMENTATION.md` updated if user-facing behavior changed
- [ ] `Project-Architecture.md` updated if modules, deps, or structure changed
- [ ] Version bumped in `__init__.py`, `pyproject.toml`, and `skills/SKILL.md` (if releasing)
- [ ] Versioned skill file created (`vibe-prospecting-multistep-workflow-X.Y.Z.skill`)
- [ ] Binary built (`./build.sh` or `./build-linux.sh`)
- [ ] Binary tested (`dist/explorium --version`)

## Project Structure

```
explorium_cli/           # Source code
  main.py                # Click entry point
  commands/              # Command groups (businesses, prospects, research, config, webhooks)
  api/                   # HTTP client + endpoint wrappers
  batching.py            # CSV parsing, batch splitting (50/batch)
  pagination.py          # Auto-pagination (--total flag)
  parallel_search.py     # Fan-out search per business ID
  concurrency.py         # ThreadPoolExecutor wrapper
  match_utils.py         # Name/domain/linkedin → ID resolution
  formatters.py          # JSON/CSV/table output
  constants.py           # Valid enum values (departments, job levels)
  validation.py          # Client-side filter validation
  ai_client.py           # Anthropic SDK wrapper
  research.py            # AI research orchestration
tests/                   # 22 pytest test files
tickets/                 # PRDs and bug tickets
skills/                  # Claude Code skill (SKILL.md)
plugin/                  # Claude Code plugin (skill + commands-reference)
build.sh                 # macOS build script
build-linux.sh           # Linux build script
install.sh               # curl-pipe installer
```

## Configuration

- Config file: `~/.explorium/config.yaml`
- API key env var: `EXPLORIUM_API_KEY`
- Anthropic key env var: `ANTHROPIC_API_KEY` (for research commands)

## Key Conventions

- **Output goes to stdout**, warnings/progress go to stderr
- All `-f`/`--file` flags accept `-` for stdin piping
- CSV column names are case-insensitive with alias support (see `batching.py`)
- Batch size is 50 for all bulk operations
- Default concurrency is 5 threads (configurable via `--threads`)
- Filter validation is **soft** — unknown values warn but pass through to the API
- Match confidence threshold defaults to 0.8

## Files That Must Stay Identical

These file pairs must always have matching content:

| Primary | Copy |
|---------|------|
| `skills/SKILL.md` | `plugin/skills/explorium-cli/SKILL.md` |
| `commands-reference.md` | `plugin/skills/explorium-cli/commands-reference.md` |

When updating one, copy to the other. The `setup-cowork.sh` script syncs the standalone skill to `~/.claude/skills/` at session startup.
