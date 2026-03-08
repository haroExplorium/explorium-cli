#!/usr/bin/env bash
# Cowork session setup: pull latest, install CLI, sync skill
# Called by the Cowork skill at session startup
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Pull latest
echo "Pulling latest CLI..." >&2
git pull --ff-only origin main 2>&1 | tail -1 >&2

# 2. Install CLI
echo "Installing CLI..." >&2
pip install -e . --break-system-packages -q 2>&1 | grep -v "notice" >&2 || true

# 3. Health check
VERSION=$(explorium --version 2>/dev/null || echo "FAILED")
echo "CLI version: $VERSION" >&2

# 4. Sync skill to Claude Code
SKILL_DIR="$HOME/.claude/skills/explorium-cli"
mkdir -p "$SKILL_DIR"
cp "$SCRIPT_DIR/skills/SKILL.md" "$SKILL_DIR/SKILL.md"
echo "Skill synced to $SKILL_DIR" >&2

# 5. Configure API key if provided and not already set
if [[ -n "${EXPLORIUM_API_KEY:-}" ]]; then
    if ! explorium config show 2>/dev/null | grep -q "NOT SET"; then
        echo "API key already configured" >&2
    else
        explorium config init -k "$EXPLORIUM_API_KEY" 2>&1 >&2
        echo "API key configured" >&2
    fi
fi

echo "Setup complete" >&2
