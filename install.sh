#!/usr/bin/env bash
set -euo pipefail

# Explorium CLI + Claude Code Skill Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/haroExplorium/explorium-cli/main/install.sh | bash

REPO="haroExplorium/explorium-cli"
BIN_DIR="$HOME/.local/bin"
SKILL_DIR="$HOME/.claude/skills/explorium-cli"
BINARY_NAME="explorium"
ASSET_NAME="explorium-darwin-arm64"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { printf "${BLUE}==>${NC} %s\n" "$1"; }
ok()    { printf "${GREEN}==>${NC} %s\n" "$1"; }
warn()  { printf "${YELLOW}==>${NC} %s\n" "$1"; }
error() { printf "${RED}Error:${NC} %s\n" "$1" >&2; exit 1; }

# -------------------------------------------------------------------
# 1. Check platform (macOS ARM only)
# -------------------------------------------------------------------
OS="$(uname -s)"
ARCH="$(uname -m)"

if [[ "$OS" != "Darwin" ]]; then
    error "This installer only supports macOS. Detected: $OS"
fi

if [[ "$ARCH" != "arm64" ]]; then
    error "This installer only supports Apple Silicon (arm64). Detected: $ARCH"
fi

info "Detected macOS ARM64 — proceeding with installation"

# -------------------------------------------------------------------
# 2. Check dependencies
# -------------------------------------------------------------------
if ! command -v curl &>/dev/null; then
    error "curl is required but not found. Please install it and retry."
fi

# -------------------------------------------------------------------
# 3. Create directories
# -------------------------------------------------------------------
info "Creating directories..."
mkdir -p "$BIN_DIR"
mkdir -p "$SKILL_DIR"

# -------------------------------------------------------------------
# 4. Download CLI binary from GitHub releases (latest)
# -------------------------------------------------------------------
info "Downloading Explorium CLI binary..."

RELEASE_URL="https://github.com/${REPO}/releases/latest/download/${ASSET_NAME}"

if ! curl -fSL --progress-bar "$RELEASE_URL" -o "${BIN_DIR}/${BINARY_NAME}"; then
    error "Failed to download CLI binary from ${RELEASE_URL}
    Make sure the release exists at: https://github.com/${REPO}/releases/latest"
fi

chmod +x "${BIN_DIR}/${BINARY_NAME}"
ok "CLI binary installed to ${BIN_DIR}/${BINARY_NAME}"

# -------------------------------------------------------------------
# 5. Download SKILL.md from repo
# -------------------------------------------------------------------
info "Downloading Claude Code skill..."

SKILL_URL="https://raw.githubusercontent.com/${REPO}/main/skills/SKILL.md"

if ! curl -fsSL "$SKILL_URL" -o "${SKILL_DIR}/SKILL.md"; then
    warn "Failed to download SKILL.md from ${SKILL_URL}"
    warn "Skill installation skipped — CLI will still work without it."
else
    ok "Skill installed to ${SKILL_DIR}/SKILL.md"
fi

# -------------------------------------------------------------------
# 6. Add ~/.local/bin to PATH if needed
# -------------------------------------------------------------------
SHELL_NAME="$(basename "$SHELL")"
PROFILE=""

case "$SHELL_NAME" in
    zsh)  PROFILE="$HOME/.zshrc" ;;
    bash) PROFILE="$HOME/.bashrc" ;;
    *)    PROFILE="$HOME/.profile" ;;
esac

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    info "Adding ${BIN_DIR} to PATH in ${PROFILE}..."
    {
        echo ""
        echo "# Explorium CLI"
        echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
    } >> "$PROFILE"
    ok "PATH updated in ${PROFILE}"
    NEED_SOURCE=true
else
    ok "${BIN_DIR} is already in PATH"
    NEED_SOURCE=false
fi

# -------------------------------------------------------------------
# 7. Verify installation
# -------------------------------------------------------------------
info "Verifying installation..."

export PATH="$BIN_DIR:$PATH"

if "${BIN_DIR}/${BINARY_NAME}" --help &>/dev/null; then
    ok "Explorium CLI is working"
else
    warn "Binary downloaded but verification failed. You may need to restart your terminal."
fi

# -------------------------------------------------------------------
# 8. Print next steps
# -------------------------------------------------------------------
echo ""
printf "${GREEN}Installation complete!${NC}\n"
echo ""
echo "Next steps:"
echo ""
echo "  1. Configure your API key:"
echo "     explorium config init --api-key <YOUR_API_KEY>"
echo ""
if [[ "$NEED_SOURCE" == true ]]; then
    echo "  2. Restart your terminal or run:"
    echo "     source ${PROFILE}"
    echo ""
fi
echo "Documentation: https://github.com/${REPO}#readme"
echo ""
