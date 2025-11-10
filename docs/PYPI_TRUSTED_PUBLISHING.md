# PyPI Trusted Publishing Setup Guide

This guide walks you through enabling PyPI Trusted Publishing for mcp-devdiag to eliminate long-lived API tokens.

## Why Trusted Publishing?

**Benefits:**
- ✅ No long-lived API tokens to rotate
- ✅ Automatic authentication via GitHub Actions OIDC
- ✅ More secure (scoped to specific repo + workflow)
- ✅ Easier to maintain (no secrets management)

**How it works:**
GitHub Actions generates a short-lived OIDC token that PyPI verifies against your registered publisher configuration.

---

## Step 1: Configure PyPI Trusted Publisher

1. **Go to PyPI project settings:**
   - Navigate to: https://pypi.org/manage/project/mcp-devdiag/settings/publishing/

2. **Add a new publisher:**
   - Click "Add a new publisher"
   - Fill in the form:
     ```
     PyPI Project Name:    mcp-devdiag
     Owner:                leok974
     Repository name:      mcp-devdiag
     Workflow name:        release.yml
     Environment name:     (leave blank)
     ```

3. **Save the configuration**

---

## Step 2: Verify GitHub Actions Workflow

The workflow is already created at `.github/workflows/release.yml`:

```yaml
name: Release to PyPI

on:
  push:
    tags:
      - 'v*'

permissions:
  id-token: write  # Required for PyPI Trusted Publishing
  contents: read

jobs:
  pypi-publish:
    name: Publish to PyPI
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install build dependencies
        run: python -m pip install --upgrade build
      
      - name: Build distributions
        run: python -m build
      
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        # No secrets needed with Trusted Publishing!
```

**Key points:**
- Triggers on tag push (`v*`)
- `permissions.id-token: write` enables OIDC token generation
- No `with.password` or secrets required

---

## Step 3: Remove Old API Token

After Trusted Publishing is working:

1. **Delete the API token from `.pypirc`:**
   ```bash
   # Remove or comment out the token in C:\Users\pierr\.pypirc
   # Or on Linux/Mac: ~/.pypirc
   ```

2. **Revoke the token on PyPI:**
   - Go to: https://pypi.org/manage/account/token/
   - Find your mcp-devdiag token
   - Click "Remove"

3. **Remove from GitHub Secrets** (if stored):
   - Go to: https://github.com/leok974/mcp-devdiag/settings/secrets/actions
   - Delete any `PYPI_API_TOKEN` secret

---

## Step 4: Test the Workflow

1. **Create a test tag:**
   ```bash
   git tag -a v0.2.1-test -m "Test trusted publishing"
   git push origin v0.2.1-test
   ```

2. **Watch the workflow:**
   - Go to: https://github.com/leok974/mcp-devdiag/actions
   - Click on the "Release to PyPI" workflow run
   - Verify it completes successfully

3. **Check PyPI:**
   - Visit: https://pypi.org/project/mcp-devdiag/
   - Confirm the new version is published

4. **Clean up test tag** (if needed):
   ```bash
   git tag -d v0.2.1-test
   git push origin :refs/tags/v0.2.1-test
   ```

---

## Step 5: Enable 2FA on PyPI (Required for Maintainers)

1. **Go to PyPI account security:**
   - Navigate to: https://pypi.org/manage/account/#account-totp

2. **Enable Two-Factor Authentication:**
   - Choose your preferred method (TOTP app recommended)
   - Scan QR code with authenticator app (Authy, Google Authenticator, etc.)
   - Save recovery codes securely

3. **Verify 2FA is enabled:**
   - You'll see "Two factor authentication is enabled" badge

**Note:** 2FA is required for all PyPI maintainers as of September 2023.

---

## Step 6: (Optional) Add Sigstore Provenance

For supply-chain security, enable provenance attestations:

**Update `.github/workflows/release.yml`:**

```yaml
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          attestations: true  # Generate Sigstore attestations
```

**What this does:**
- Generates cryptographic provenance for your package
- Links package to specific GitHub commit and workflow
- Helps consumers verify package authenticity
- No additional configuration needed!

---

## Troubleshooting

### "Trusted publishing exchange failure"

**Cause:** PyPI publisher configuration doesn't match workflow.

**Fix:**
1. Verify repository name, workflow name, and owner match exactly
2. Ensure `permissions.id-token: write` is set
3. Check you're using `pypa/gh-action-pypi-publish@release/v1` (not older versions)

### "Invalid or expired token"

**Cause:** OIDC token generation failed.

**Fix:**
1. Check GitHub Actions permissions are enabled for the repository
2. Verify workflow has `id-token: write` permission
3. Ensure you're running on a supported runner (ubuntu-latest, etc.)

### "Project not found"

**Cause:** PyPI project doesn't exist or publisher not configured.

**Fix:**
1. Ensure the project exists on PyPI (publish manually first if needed)
2. Configure Trusted Publisher on PyPI before first automated publish

---

## Security Checklist

Before going live with Trusted Publishing:

- [ ] Trusted Publisher configured on PyPI
- [ ] Workflow file committed to repository
- [ ] Test tag pushed successfully
- [ ] Old API token removed from `.pypirc`
- [ ] Old API token revoked on PyPI
- [ ] 2FA enabled on PyPI account
- [ ] Recovery codes saved securely
- [ ] GitHub Actions permissions reviewed
- [ ] (Optional) Sigstore attestations enabled

---

## Additional Resources

- **PyPI Trusted Publishing Docs:** https://docs.pypi.org/trusted-publishers/
- **GitHub OIDC Docs:** https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect
- **Sigstore Attestations:** https://github.com/pypa/gh-action-pypi-publish#attestations

---

## Release Process (After Setup)

With Trusted Publishing enabled, releasing is simple:

```bash
# 1. Update version in pyproject.toml
# 2. Update CHANGELOG.md
# 3. Commit changes
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): v0.3.0"

# 4. Create and push tag
git tag -a v0.3.0 -m "Release v0.3.0"
git push origin main --tags

# 5. GitHub Actions automatically publishes to PyPI!
# No manual twine upload needed
```

That's it! The workflow handles building, validating, and publishing automatically.
