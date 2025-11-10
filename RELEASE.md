# Release Process

## Version Bump & Tag

### Automated Version Bump

```bash
# Bump patch version and tag
python - <<'PY'
import toml
p = "pyproject.toml"
d = toml.load(p)
v = d["project"]["version"].split(".")
v[-1] = str(int(v[-1]) + 1)
d["project"]["version"] = ".".join(v)
with open(p, "w") as f:
    toml.dump(d, f)
print(f"Bumped to {d['project']['version']}")
PY

# Commit and tag
VERSION=$(python -c "import toml; print(toml.load('pyproject.toml')['project']['version'])")
git add pyproject.toml
git commit -m "chore: release v${VERSION}"
git tag -a "v${VERSION}" -m "DevDiag v${VERSION}"
git push && git push --tags
```

### Manual Version Bump

Edit `pyproject.toml`:

```toml
[project]
version = "0.2.1"  # Increment as needed
```

Then commit and tag:

```bash
VERSION=$(python -c "import toml; print(toml.load('pyproject.toml')['project']['version'])")
git add pyproject.toml
git commit -m "chore: release v${VERSION}"
git tag -a "v${VERSION}" -m "DevDiag v${VERSION}"
git push && git push --tags
```

## CHANGELOG Bullets

**Short, recruiter-friendly format**:

### v0.2.0 (2025-11-10)

**Features**:
- ✨ JWKS-verified RBAC (RS256), per-tenant rate limits, incident TTL auto-revert
- ✨ Vendor-neutral probes (CSP/iframe, inline CSP, overlays, handshake, framework mismatch)
- ✨ Standardized ProbeResult schema + scoring, fixes API, quickcheck GitHub Action
- 📊 Prometheus metrics integration with universal HTTP queries
- 🔒 Production security checklist in SECURITY.md

**Documentation**:
- 📖 README curl recipes for smoke testing
- 📖 Grafana panel examples for monitoring
- 📖 VS Code/Copilot integration guide

**CI/CD**:
- 🚀 GitHub Action for HTTP-only quickcheck
- ✅ Production policy enforcement tests

### v0.1.0 (2025-11-09)

**Initial Release**:
- 🎯 Production-safe autonomous diagnostics
- 🔒 RBAC with reader/operator roles
- 📊 Sampling and adaptive probing
- 🛡️ Header redaction and allowlist enforcement

## Release Checklist

Before tagging a release:

- [ ] All tests passing (`pytest`)
- [ ] Policy tests passing (`pytest tests/test_prod_policy.py`)
- [ ] Linting clean (`ruff check .`)
- [ ] Type checking clean (`mypy mcp_devdiag/`)
- [ ] CHANGELOG.md updated with release notes
- [ ] Version bumped in `pyproject.toml`
- [ ] Documentation up to date (README, SECURITY)
- [ ] GitHub Actions passing on main branch

## Post-Release

1. **Publish to PyPI** (optional):
   ```bash
   python -m build
   python -m twine upload dist/*
   ```

2. **Create GitHub Release**:
   - Go to https://github.com/leok974/mcp-devdiag/releases
   - Draft new release from tag
   - Copy CHANGELOG bullets
   - Attach built wheels if publishing

3. **Update Documentation**:
   - Update version references in docs
   - Announce in team channels
   - Update deployment runbooks

## Semantic Versioning

- **Major** (1.0.0): Breaking changes to API or configuration
- **Minor** (0.2.0): New features, backward compatible
- **Patch** (0.2.1): Bug fixes, security patches
