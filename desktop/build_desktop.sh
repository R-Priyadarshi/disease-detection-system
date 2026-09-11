#!/usr/bin/env bash
# ==============================================================================
# ALVEON PACS — Cross-Platform Desktop Client Build Script
# Builds native binaries (Linux AppImage/deb, Windows portable/installer, macOS dmg)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "================================================================="
echo "  ALVEON PACS v5.1 — Native Desktop Workstation Builder"
echo "================================================================="
echo "Working directory: $SCRIPT_DIR"

cd "$SCRIPT_DIR"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is required to build the ALVEON desktop workstation."
    echo "Please install Node.js (v18+ recommended): https://nodejs.org/"
    exit 1
fi

echo "Node.js version: $(node -v)"
echo "NPM version: $(npm -v)"

# Install dependencies if node_modules does not exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Electron dependencies..."
    npm install
fi

# Detect platform or accept CLI argument
TARGET="${1:-current}"

case "$TARGET" in
    linux)
        echo "🐧 Building Linux AppImage and DEB package..."
        npm run build:linux
        ;;
    win|windows)
        echo "🪟 Building Windows NSIS installer and portable executable..."
        npm run build:win
        ;;
    mac|darwin)
        echo "🍎 Building macOS DMG disk image..."
        npm run build:mac
        ;;
    all)
        echo "🌐 Packaging all targets..."
        npm run dist
        ;;
    current|*)
        echo "🖥️ Building for current operating system ($(uname -s))..."
        npm run dist
        ;;
esac

echo ""
echo "✅ Build completed successfully!"
echo "Artifacts are available in: $SCRIPT_DIR/dist"
ls -lh "$SCRIPT_DIR/dist" 2>/dev/null || true
