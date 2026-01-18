#!/bin/bash
# Build script for Explorium CLI macOS binary

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Explorium CLI Build Script ==="
echo ""

# Get architecture
ARCH=$(uname -m)
echo "Building for architecture: $ARCH"
echo ""

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info

# Ensure dependencies are installed
echo "Installing dependencies..."
pip install -e . -q
pip install pyinstaller -q

# Build the binary
echo ""
echo "Building binary with PyInstaller..."
pyinstaller --onefile \
    --name explorium \
    --exclude-module setuptools \
    --exclude-module pkg_resources \
    --exclude-module tkinter \
    --exclude-module matplotlib \
    --exclude-module numpy \
    --exclude-module pandas \
    --exclude-module scipy \
    --exclude-module PIL \
    explorium_cli/main.py

# Check if build succeeded
if [[ -f "dist/explorium" ]]; then
    echo ""
    echo "=== Build Successful ==="
    echo ""

    # Get binary info
    BINARY_PATH="dist/explorium"
    BINARY_SIZE=$(du -h "$BINARY_PATH" | cut -f1)

    echo "Binary location: $BINARY_PATH"
    echo "Binary size: $BINARY_SIZE"
    echo "Architecture: $(file "$BINARY_PATH" | grep -o 'arm64\|x86_64')"
    echo ""

    # Test the binary
    echo "Testing binary..."
    if "$BINARY_PATH" --help > /dev/null 2>&1; then
        echo "✓ Binary runs successfully"
    else
        echo "✗ Binary test failed"
        exit 1
    fi

    # Create versioned copy
    VERSION=$(grep 'version = ' pyproject.toml | head -1 | cut -d'"' -f2)
    VERSIONED_NAME="explorium-${VERSION}-macos-${ARCH}"
    cp "$BINARY_PATH" "dist/${VERSIONED_NAME}"
    echo "✓ Created versioned binary: dist/${VERSIONED_NAME}"

    echo ""
    echo "=== Installation ==="
    echo ""
    echo "To install system-wide, run:"
    echo "  sudo cp dist/explorium /usr/local/bin/"
    echo ""
    echo "Or add to your PATH:"
    echo "  export PATH=\"\$PATH:$SCRIPT_DIR/dist\""
    echo ""
else
    echo ""
    echo "=== Build Failed ==="
    exit 1
fi
