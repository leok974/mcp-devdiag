# Quick Reference: Next Steps After v0.2.0 Release

## ⚡ Immediate Actions (15 minutes)

### 1. Enable PyPI 2FA (Required for Maintainers)
```
URL: https://pypi.org/manage/account/#account-totp
Action: Enable Two-Factor Authentication
Save: Recovery codes (print or save securely)
```

### 2. Configure Trusted Publishing (Replaces API Tokens)
```
URL: https://pypi.org/manage/project/mcp-devdiag/settings/publishing/

Fill in:
  PyPI Project Name:    mcp-devdiag
  Owner:                leok974
  Repository name:      mcp-devdiag
  Workflow name:        release.yml
  Environment name:     (leave blank)

Click: "Add"
```

### 3. Test Trusted Publishing
```bash
# Create test tag
git tag -a v0.2.1-rc1 -m "Test trusted publishing"
git push origin v0.2.1-rc1

# Watch: https://github.com/leok974/mcp-devdiag/actions
# Verify: Package appears on PyPI

# Clean up test (if needed)
git tag -d v0.2.1-rc1
git push origin :refs/tags/v0.2.1-rc1
```

### 4. Remove Old API Token
```bash
# Windows:
notepad C:\Users\pierr\.pypirc
# Delete or comment out the token line

# Revoke on PyPI:
URL: https://pypi.org/manage/account/token/
Action: Find token → Remove
```

---

## 🚀 Marketing & Announcement (30 minutes)

### 1. Social Media Posts

**Copy templates from:** `docs/MARKETING.md`

**Platforms to hit:**
- [ ] Twitter/X (short post or thread)
- [ ] LinkedIn (professional announcement)
- [ ] Discord/Slack communities
- [ ] Reddit (r/Python, r/programming, r/devops)
- [ ] Hacker News (Show HN)

**Key links to include:**
- PyPI: https://pypi.org/project/mcp-devdiag/
- GitHub: https://github.com/leok974/mcp-devdiag
- Release: https://github.com/leok974/mcp-devdiag/releases/tag/v0.2.0

### 2. Update Project Description

**GitHub repo description:**
```
Production-safe MCP diagnostics with RBAC, probes, metrics & security guardrails
```

**GitHub repo topics:**
```
mcp, diagnostics, observability, security, rbac, ai-agents, copilot, prometheus
```

---

## 🧪 Validation (10 minutes)

### Run Clean Install Test
```bash
# Linux/Mac:
./scripts/smoke_test_clean_install.sh 0.2.0

# Windows (WSL or Git Bash):
bash scripts/smoke_test_clean_install.sh 0.2.0
```

**Expected:** All tests pass ✅

### Verify PyPI Page
```
URL: https://pypi.org/project/mcp-devdiag/

Check:
- [ ] Version shows 0.2.0
- [ ] README renders correctly
- [ ] Project links show in sidebar (Homepage, Docs, Changelog, Issues)
- [ ] Badges render correctly
- [ ] Python versions: 3.10-3.13
```

---

## 📝 Documentation Checklist

All created and ready:

- [x] `.github/workflows/release.yml` - Automated releases
- [x] `docs/PYPI_TRUSTED_PUBLISHING.md` - Setup guide
- [x] `docs/MARKETING.md` - Announcement templates
- [x] `docs/PYPI_PRODUCTION_READY.md` - Complete checklist
- [x] `scripts/smoke_test_clean_install.sh` - Validation script
- [x] README badges and quickstart
- [x] `pyproject.toml` project URLs

---

## 🎯 Optional Enhancements

### Add Sigstore Attestations (5 minutes)

**Edit:** `.github/workflows/release.yml`

**Change:**
```yaml
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

**To:**
```yaml
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          attestations: true  # Enable Sigstore provenance
```

**Commit:**
```bash
git add .github/workflows/release.yml
git commit -m "feat: enable Sigstore attestations for supply-chain security"
git push origin main
```

**Benefit:** Cryptographic proof of package provenance

---

## 📊 Monitoring

### Track Metrics

**PyPI Stats:**
```
URL: https://pypistats.org/packages/mcp-devdiag
Metrics: Downloads per day/week/month
```

**GitHub Activity:**
```
Stars: https://github.com/leok974/mcp-devdiag/stargazers
Issues: https://github.com/leok974/mcp-devdiag/issues
PRs: https://github.com/leok974/mcp-devdiag/pulls
```

**Set up alerts:**
- GitHub notifications for issues/PRs
- Weekly PyPI download report (if desired)

---

## 🔄 Future Release Process (Automated!)

With Trusted Publishing configured:

```bash
# 1. Make changes, update version
vim pyproject.toml  # Bump version
vim CHANGELOG.md    # Add release notes

# 2. Commit
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): v0.3.0"

# 3. Tag and push
git tag -a v0.3.0 -m "Release v0.3.0"
git push origin main --tags

# 4. GitHub Actions automatically:
#    - Builds package
#    - Publishes to PyPI
#    - No manual intervention!

# 5. Create GitHub Release (if desired)
gh release create v0.3.0 \
  --title "v0.3.0 - [Title]" \
  --notes-file .github/RELEASE_NOTES_v0.3.0.md

# 6. Announce using templates in docs/MARKETING.md
```

**No more manual `twine upload`! 🎉**

---

## 🆘 Troubleshooting

### Trusted Publishing Not Working?

**Check:**
1. PyPI publisher configured correctly (exact match: owner, repo, workflow)
2. Workflow has `permissions.id-token: write`
3. Using `pypa/gh-action-pypi-publish@release/v1`
4. Tag format matches `v*` pattern

**Debug:**
- View workflow logs: https://github.com/leok974/mcp-devdiag/actions
- Check PyPI publishing logs in workflow output

### Package Not Rendering on PyPI?

**Fix:**
1. Ensure `readme = "README.md"` in `pyproject.toml`
2. Run `twine check dist/*` locally
3. Check for Markdown syntax errors
4. Ensure links are absolute (not relative)

---

## 📚 Documentation Links

- **Setup Guide:** `docs/PYPI_TRUSTED_PUBLISHING.md`
- **Marketing Templates:** `docs/MARKETING.md`
- **Production Checklist:** `docs/PYPI_PRODUCTION_READY.md`
- **Add-ons Guide:** `docs/ADDONS.md`
- **README:** Well-documented with badges and quickstart

---

## ✅ Success Criteria

- [x] Package published to PyPI ✅
- [x] GitHub Release created ✅
- [x] Documentation complete ✅
- [ ] 2FA enabled (your action)
- [ ] Trusted Publishing configured (your action)
- [ ] Announcement posted (your action)
- [ ] Smoke test passed (your action)

**You're 3 actions away from complete production readiness! 🚀**

1. Enable 2FA (5 min)
2. Configure Trusted Publishing (5 min)
3. Post announcement (5-30 min depending on platforms)

**Total time: 15-40 minutes**
