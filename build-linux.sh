#!/bin/bash
# Build Explorium CLI Linux binaries (amd64 + arm64) using Docker
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION=$(grep 'version = ' pyproject.toml | head -1 | cut -d'"' -f2)

echo "=== Explorium CLI Linux Build (v${VERSION}) ==="
echo ""

# Clean previous linux builds
rm -f dist/explorium-linux-*

build_linux() {
    local PLATFORM="$1"   # linux/amd64 or linux/arm64
    local SUFFIX="$2"     # amd64 or arm64

    echo "--- Building for linux/${SUFFIX} ---"

    docker run --rm --platform "${PLATFORM}" \
        -v "${SCRIPT_DIR}:/src" \
        -w /src \
        python:3.11-slim \
        bash -c "
            set -e
            apt-get update -qq && apt-get install -y -qq binutils > /dev/null 2>&1
            pip install --quiet pyinstaller
            pip install --quiet -e .
            pyinstaller --onefile \
                --name explorium-linux-${SUFFIX} \
                --exclude-module setuptools \
                --exclude-module pkg_resources \
                --exclude-module tkinter \
                --exclude-module matplotlib \
                --exclude-module numpy \
                --exclude-module pandas \
                --exclude-module scipy \
                --exclude-module PIL \
                --distpath /src/dist \
                --workpath /tmp/build \
                --specpath /tmp \
                explorium_cli/main.py
            echo 'Build complete'
        "

    if [[ -f "dist/explorium-linux-${SUFFIX}" ]]; then
        chmod +x "dist/explorium-linux-${SUFFIX}"
        SIZE=$(du -h "dist/explorium-linux-${SUFFIX}" | cut -f1)
        echo "  ✓ dist/explorium-linux-${SUFFIX} (${SIZE})"
    else
        echo "  ✗ Build failed for linux/${SUFFIX}"
        return 1
    fi
}

# Build both architectures
build_linux "linux/amd64" "amd64"
echo ""
build_linux "linux/arm64" "arm64"

echo ""
echo "=== Build Complete ==="
echo ""
ls -lh dist/explorium-linux-*
echo ""
echo "To test locally (arm64):"
echo "  docker run --rm --platform linux/arm64 -v ${SCRIPT_DIR}/dist:/dist python:3.11-slim /dist/explorium-linux-arm64 --version"
