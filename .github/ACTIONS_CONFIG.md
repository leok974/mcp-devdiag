# GitHub Actions Configuration

## Repository Variables

Configure these variables in GitHub repository settings:

### CI/CD Variables

**DEVDIAG_BROWSER_TESTS** (optional)
- **Type**: Repository variable
- **Value**: `1` to enable Playwright browser tests, omit or `0` to disable
- **Usage**: Gates browser tests in CI to avoid fork failures
- **Path**: Settings → Secrets and variables → Actions → Variables → New repository variable

**APP_ORIGIN** (for quickcheck workflow)
- **Type**: Repository variable
- **Value**: Your application URL (e.g., `https://app.example.com`)
- **Usage**: Target URL for DevDiag quickcheck probe

### Secrets

**DEVDIAG_URL**
- **Type**: Repository secret
- **Value**: DevDiag server URL (e.g., `https://diag.example.com`)

**DEVDIAG_READER_JWT**
- **Type**: Repository secret
- **Value**: JWT token with reader role for DevDiag API

## Workflows

### ci.yml

Main CI workflow with linting, type checking, and tests:
- **Triggers**: Push to any branch, pull requests
- **Browser tests**: Gated by `DEVDIAG_BROWSER_TESTS` variable
- **Steps**: Install, lint, typecheck, tests, optional Playwright tests

### devdiag-quickcheck.yml

DevDiag probe integration for config changes:
- **Triggers**: PRs changing nginx/headers/HTML, manual dispatch
- **Purpose**: Validate CSP and embedding configuration
- **Secrets**: Requires `DEVDIAG_URL`, `DEVDIAG_READER_JWT`
- **Variables**: Requires `APP_ORIGIN`

## Setup Example

```bash
# Enable browser tests (repository owner only)
gh variable set DEVDIAG_BROWSER_TESTS --body "1"

# Set app origin
gh variable set APP_ORIGIN --body "https://app.example.com"

# Set DevDiag secrets
gh secret set DEVDIAG_URL --body "https://diag.example.com"
gh secret set DEVDIAG_READER_JWT --body "<your-jwt-token>"
```
