# Git Hooks Setup Script
# Run this after cloning the repository to install git hooks

Write-Host "→ Setting up git hooks for mcp-devdiag..." -ForegroundColor Cyan

# Check if gitleaks is installed
if (-not (Get-Command gitleaks -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️  gitleaks not found. Installing via winget..." -ForegroundColor Yellow
    winget install gitleaks --source winget --silent
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install gitleaks. Please install manually:" -ForegroundColor Red
        Write-Host "   winget install gitleaks" -ForegroundColor Gray
        exit 1
    }
    
    Write-Host "✅ gitleaks installed" -ForegroundColor Green
} else {
    Write-Host "✅ gitleaks already installed" -ForegroundColor Green
}

# Verify pre-commit hook exists
$hookPath = ".git\hooks\pre-commit"
if (Test-Path $hookPath) {
    Write-Host "✅ pre-commit hook already installed" -ForegroundColor Green
} else {
    Write-Host "⚠️  pre-commit hook not found at $hookPath" -ForegroundColor Yellow
    Write-Host "   Expected location: .git/hooks/pre-commit" -ForegroundColor Gray
}

# Test gitleaks
Write-Host ""
Write-Host "Testing gitleaks..." -ForegroundColor Cyan
gitleaks detect --no-git --redact --verbose

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ All git hooks configured successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Pre-commit hook will:" -ForegroundColor Cyan
    Write-Host "  • Scan staged files for secrets before each commit" -ForegroundColor Gray
    Write-Host "  • Block commits containing API keys, tokens, passwords" -ForegroundColor Gray
    Write-Host "  • Can be bypassed with: git commit --no-verify (NOT RECOMMENDED)" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "⚠️  gitleaks found potential secrets. Review and fix before committing." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done! You're ready to contribute securely." -ForegroundColor Green
