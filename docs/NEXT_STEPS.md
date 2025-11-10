# Next Steps After Security Hardening

## ✅ What Just Happened

We've completed comprehensive security hardening for mcp-devdiag:

**Automated Security:**
- ✅ Sigstore provenance attestations enabled
- ✅ TestPyPI workflow for RC testing
- ✅ Dependabot configured (weekly updates)
- ✅ CodeQL security scanning active
- ✅ OpenSSF Scorecard monitoring

**Files Added/Modified:**
```
.github/workflows/release.yml           (MODIFIED: added attestations)
.github/workflows/release-testpypi.yml  (NEW)
.github/workflows/codeql.yml            (NEW)
.github/workflows/scorecard.yml         (NEW)
.github/dependabot.yml                  (NEW)
docs/SECURITY_OPS_CHECKLIST.md          (NEW: complete guide)
```

**Commit:** `1f75eb1` - Pushed to GitHub

---

## 🔴 Required Manual Actions (15 minutes)

### 1. Revoke Old PyPI Token (5 min)

Since Trusted Publishing is now active, the old API token is obsolete and should be removed:

**Steps:**
1. Go to: https://pypi.org/manage/account/token/
2. Find the token you created before Trusted Publishing (probably named "mcp-devdiag" or similar)
3. Click **"Remove"** to revoke it
4. Confirm deletion

**Why:** Old tokens are a security risk. With Trusted Publishing, they're unnecessary.

---

### 2. Clear PowerShell History (5 min, optional but recommended)

If your shell history contains the old token:

```powershell
# Check if token is in history
Get-Content (Get-PSReadlineOption).HistorySavePath | Select-String "pypi-"

# If found, clear the history file
Remove-Item (Get-PSReadlineOption).HistorySavePath

# Restart PowerShell
exit
```

**Why:** Prevents accidental exposure of the revoked token.

---

### 3. Enable 2FA on PyPI (5 min, if not already)

PyPI requires 2FA for package maintainers:

1. Go to: https://pypi.org/manage/account/#account-totp
2. Follow the setup wizard (use Google Authenticator, Authy, etc.)
3. Save recovery codes in a secure location

**Why:** Required by PyPI for maintainers of popular packages.

---

## 🟡 Optional Enhancements (30 minutes)

### 1. Configure TestPyPI Trusted Publishing (10 min)

To test releases on TestPyPI before production:

1. Create account: https://test.pypi.org/account/register/
2. Create project manually (first time): https://test.pypi.org/manage/project/mcp-devdiag/
3. Configure Trusted Publishing: https://test.pypi.org/manage/project/mcp-devdiag/settings/publishing/
   - **Owner:** leok974
   - **Repository:** mcp-devdiag
   - **Workflow:** release-testpypi.yml
   - **Environment:** (leave blank)

**Usage:**
```bash
git tag -a v0.3.0-rc1 -m "Release candidate"
git push origin v0.3.0-rc1
# Publishes to TestPyPI automatically
```

---

### 2. Enable GitHub Branch Protection (10 min)

Improves OpenSSF Scorecard score:

1. Go to: https://github.com/leok974/mcp-devdiag/settings/branches
2. Click **"Add branch protection rule"**
3. Branch name pattern: `main`
4. Enable:
   - ✅ Require a pull request before merging
   - ✅ Require status checks to pass before merging
   - ✅ Require linear history

**Why:** Prevents accidental force pushes and enforces code review.

---

### 3. Add Security Badges to README (10 min)

Optional badges to showcase security features:

```markdown
[![CodeQL](https://github.com/leok974/mcp-devdiag/workflows/CodeQL/badge.svg)](https://github.com/leok974/mcp-devdiag/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/leok974/mcp-devdiag/badge)](https://securityscorecards.dev/viewer/?uri=github.com/leok974/mcp-devdiag)
[![Dependabot Status](https://img.shields.io/badge/Dependabot-enabled-success.svg)](https://github.com/leok974/mcp-devdiag/network/updates)
```

Add these to `README.md` below the existing badges.

---

## 🟢 Monitor Security Features

### Automated Workflows (No Action Needed)

These will run automatically:

**CodeQL Scanning:**
- Trigger: Push to main, PRs, Mondays 6 AM UTC
- View: https://github.com/leok974/mcp-devdiag/security/code-scanning
- Expected: First scan completes after this push

**OpenSSF Scorecard:**
- Trigger: Push to main, Mondays 3 AM UTC
- View: https://securityscorecards.dev/viewer/?uri=github.com/leok974/mcp-devdiag
- Expected: First score available after this push

**Dependabot:**
- Trigger: Weekly checks
- View: https://github.com/leok974/mcp-devdiag/security/dependabot
- Expected: First PR within 1 week (if updates available)

---

### First Dependabot PR

When Dependabot creates its first PR:

1. Review the changes (usually safe for patch/minor versions)
2. Check that tests pass
3. Merge if all looks good
4. This sets the pattern for future auto-updates

---

## 📊 Verify Setup

### Check Workflows Are Running

```bash
# View recent workflow runs
gh run list --limit 5

# Should show CodeQL and Scorecard starting/running
```

### Check Security Tab

Visit: https://github.com/leok974/mcp-devdiag/security

You should see:
- **Code scanning**: CodeQL results
- **Dependabot alerts**: Enabled
- **Secret scanning**: Enabled (GitHub feature)

---

## 🚀 Next Release With Attestations

When you're ready for v0.3.0:

```bash
# Update version
vim pyproject.toml  # Bump to 0.3.0
vim CHANGELOG.md    # Add release notes

# Commit and tag
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): prepare v0.3.0"
git tag -a v0.3.0 -m "Release v0.3.0"
git push origin main v0.3.0

# Workflow publishes to PyPI with attestations automatically!
```

### Verify Attestations (After Release)

```bash
# Download and verify attestation
pip download mcp-devdiag==0.3.0
pip install sigstore

python -m sigstore verify identity mcp_devdiag-0.3.0-py3-none-any.whl \
  --cert-identity https://github.com/leok974/mcp-devdiag/.github/workflows/release.yml@refs/tags/v0.3.0 \
  --cert-oidc-issuer https://token.actions.githubusercontent.com

# Should output: Verification succeeded!
```

---

## 📚 Documentation Reference

- **Complete Security Guide:** `docs/SECURITY_OPS_CHECKLIST.md`
- **Trusted Publishing Setup:** `docs/PYPI_TRUSTED_PUBLISHING.md`
- **Production Checklist:** `docs/PYPI_PRODUCTION_READY.md`
- **Quick Reference:** `docs/QUICK_REFERENCE.md`
- **Marketing Templates:** `docs/MARKETING.md`

---

## ✅ Current Status Summary

**Package:** mcp-devdiag 0.2.1 (live on PyPI)

**Security Posture:**
- ✅ Trusted Publishing (OIDC, no API tokens)
- ✅ Sigstore provenance enabled
- ✅ Automated security scanning (CodeQL)
- ✅ Supply-chain monitoring (Scorecard)
- ✅ Dependency updates (Dependabot)
- ✅ Clean credential hygiene

**Next Milestone:** v0.3.0 with full attestation verification

---

## 🎯 Success Metrics

After setup is complete, you should see:

**Within 24 Hours:**
- CodeQL scan results in Security tab
- OpenSSF Scorecard score published
- No security alerts or vulnerabilities

**Within 1 Week:**
- First Dependabot PR (if updates available)
- Scorecard score improves (with branch protection)

**Next Release (v0.3.0):**
- Attestations visible on PyPI
- Verified with sigstore
- Supply-chain transparency

---

**mcp-devdiag is now production-ready with enterprise-grade security! 🎉**

For questions or issues, see: https://github.com/leok974/mcp-devdiag/issues
