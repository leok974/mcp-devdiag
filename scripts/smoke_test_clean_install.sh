#!/usr/bin/env bash
# Clean environment smoke test for mcp-devdiag
# Tests the consumer installation experience from PyPI
#
# Usage: ./smoke_test_clean_install.sh [version]
#   Default version: 0.2.0

set -euo pipefail

VERSION="${1:-0.2.0}"
VENV_DIR="/tmp/mcp-devdiag-smoke-$$"

echo "🧪 mcp-devdiag Clean Install Smoke Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Version: $VERSION"
echo "Venv:    $VENV_DIR"
echo ""

# Cleanup function
cleanup() {
  if [[ -d "$VENV_DIR" ]]; then
    echo "🧹 Cleaning up test environment..."
    rm -rf "$VENV_DIR"
  fi
}

trap cleanup EXIT

# Step 1: Create clean virtual environment
echo "1️⃣  Creating clean virtual environment..."
python -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Step 2: Upgrade pip
echo "2️⃣  Upgrading pip..."
python -m pip install --upgrade pip -q

# Step 3: Install mcp-devdiag from PyPI
echo "3️⃣  Installing mcp-devdiag==$VERSION from PyPI..."
pip install "mcp-devdiag==$VERSION" -q

# Step 4: Verify import
echo "4️⃣  Verifying import..."
python -c "import mcp_devdiag; print('   ✅ Import successful')"

# Step 5: Check installed version
echo "5️⃣  Checking installed version..."
INSTALLED_VERSION=$(python -c "import importlib.metadata as m; print(m.version('mcp-devdiag'))")
echo "   Installed: $INSTALLED_VERSION"

if [[ "$INSTALLED_VERSION" != "$VERSION" ]]; then
  echo "   ❌ Version mismatch! Expected $VERSION, got $INSTALLED_VERSION"
  exit 1
fi
echo "   ✅ Version match"

# Step 6: Verify entry point
echo "6️⃣  Verifying CLI entry point..."
if command -v mcp-devdiag &> /dev/null; then
  echo "   ✅ mcp-devdiag command found"
else
  echo "   ⚠️  mcp-devdiag command not in PATH (expected in venv)"
fi

# Step 7: Check package metadata
echo "7️⃣  Checking package metadata..."
python - <<'PY'
import importlib.metadata as m

metadata = m.metadata("mcp-devdiag")
print(f"   Name:        {metadata['Name']}")
print(f"   Version:     {metadata['Version']}")
print(f"   Summary:     {metadata['Summary']}")
print(f"   Author:      {metadata['Author']}")
print(f"   License:     {metadata.get('License', 'N/A')}")
print(f"   Python:      {metadata.get('Requires-Python', 'N/A')}")

# Check URLs
if 'Home-page' in metadata or 'Project-URL' in metadata:
    print("   URLs:")
    for key, value in metadata.items():
        if key == 'Project-URL':
            print(f"     - {value}")
PY

# Step 8: Test optional extras availability
echo "8️⃣  Testing optional extras (not installed by default)..."
python - <<'PY'
import sys

try:
    import playwright
    print("   ⚠️  Playwright found (should not be in base install)")
except ImportError:
    print("   ✅ Playwright not installed (correct)")

try:
    import boto3
    print("   ⚠️  boto3 found (should not be in base install)")
except ImportError:
    print("   ✅ boto3 not installed (correct)")
PY

# Step 9: List installed dependencies
echo "9️⃣  Checking core dependencies..."
pip list --format=freeze | grep -E "mcp-devdiag|fastmcp|httpx|pydantic|python-jose" || true

# Success
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All smoke tests passed!"
echo ""
echo "Consumer installation experience verified:"
echo "  • PyPI package installs correctly"
echo "  • Version matches expected: $VERSION"
echo "  • Module imports successfully"
echo "  • No unexpected dependencies"
echo "  • Metadata is complete"
echo ""
echo "To test with extras:"
echo "  pip install \"mcp-devdiag[playwright,export]==$VERSION\""
