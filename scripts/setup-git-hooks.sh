#!/bin/bash
# Git Hooks Setup Script
# Run this after cloning the repository to install git hooks

set -e

echo "→ Setting up git hooks for mcp-devdiag..."

# Check if gitleaks is installed
if ! command -v gitleaks &> /dev/null; then
    echo "⚠️  gitleaks not found. Installing..."
    
    # Detect OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install gitleaks
        else
            echo "❌ Homebrew not found. Please install gitleaks manually:"
            echo "   https://github.com/gitleaks/gitleaks#installing"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux - download binary
        echo "Downloading gitleaks binary..."
        GITLEAKS_VERSION="8.29.0"
        curl -sSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" -o /tmp/gitleaks.tar.gz
        tar -xzf /tmp/gitleaks.tar.gz -C /tmp
        sudo mv /tmp/gitleaks /usr/local/bin/
        sudo chmod +x /usr/local/bin/gitleaks
        rm /tmp/gitleaks.tar.gz
    else
        echo "❌ Unsupported OS: $OSTYPE"
        echo "   Please install gitleaks manually:"
        echo "   https://github.com/gitleaks/gitleaks#installing"
        exit 1
    fi
    
    echo "✅ gitleaks installed"
else
    echo "✅ gitleaks already installed ($(gitleaks version))"
fi

# Verify pre-commit hook exists
HOOK_PATH=".git/hooks/pre-commit"
if [ -f "$HOOK_PATH" ]; then
    echo "✅ pre-commit hook already installed"
    chmod +x "$HOOK_PATH"
else
    echo "⚠️  pre-commit hook not found at $HOOK_PATH"
    echo "   Expected location: .git/hooks/pre-commit"
fi

# Test gitleaks
echo ""
echo "Testing gitleaks..."
if gitleaks detect --no-git --redact --verbose; then
    echo ""
    echo "✅ All git hooks configured successfully!"
    echo ""
    echo "Pre-commit hook will:"
    echo "  • Scan staged files for secrets before each commit"
    echo "  • Block commits containing API keys, tokens, passwords"
    echo "  • Can be bypassed with: git commit --no-verify (NOT RECOMMENDED)"
else
    echo ""
    echo "⚠️  gitleaks found potential secrets. Review and fix before committing."
    exit 1
fi

echo ""
echo "Done! You're ready to contribute securely."
