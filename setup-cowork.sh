#!/usr/bin/env bash
# Cowork session setup: pull latest, install CLI, sync skill
# Called by the Cowork skill at session startup
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PERSISTENT_DIR="${PERSISTENT_DIR:-$HOME}"
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

# 5. Locate API key file
KEY_FILE="$HOME/.explorium/api_key"

# Also check inside the user's workspace folder (Cowork/)
if [ ! -f "$KEY_FILE" ] || [ ! -s "$KEY_FILE" ]; then
    for d in "$PERSISTENT_DIR"/*/ "$PERSISTENT_DIR"/*/*/; do
        ALT="$d.explorium/api_key"
        [ -f "$ALT" ] && [ -s "$ALT" ] && KEY_FILE="$ALT" && break
    done
fi

# 6. Configure API key
if [ -f "$KEY_FILE" ] && [ -s "$KEY_FILE" ]; then
    API_KEY=$(cat "$KEY_FILE")
    explorium config init -k "$API_KEY" 2>&1 >&2
    echo "API key configured from $KEY_FILE" >&2
elif [[ -n "${EXPLORIUM_API_KEY:-}" ]]; then
    explorium config init -k "$EXPLORIUM_API_KEY" 2>&1 >&2
    echo "API key configured from env" >&2
else
    echo "Warning: No API key found. Run: explorium config init -k <KEY>" >&2
fi

# 7. Locate Anthropic API key (needed for research command)
ANTHROPIC_KEY_FILE="$HOME/.anthropic/api_key"

if [ ! -f "$ANTHROPIC_KEY_FILE" ] || [ ! -s "$ANTHROPIC_KEY_FILE" ]; then
    for d in "$PERSISTENT_DIR"/*/ "$PERSISTENT_DIR"/*/*/; do
        ALT="$d.anthropic/api_key"
        [ -f "$ALT" ] && [ -s "$ALT" ] && ANTHROPIC_KEY_FILE="$ALT" && break
    done
fi

if [ -f "$ANTHROPIC_KEY_FILE" ] && [ -s "$ANTHROPIC_KEY_FILE" ]; then
    export ANTHROPIC_API_KEY=$(cat "$ANTHROPIC_KEY_FILE")
    echo "Anthropic API key configured from $ANTHROPIC_KEY_FILE" >&2
elif [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "Warning: No Anthropic API key found. Research command won't work." >&2
fi

echo "Setup complete" >&2
