# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-11-10

### Added
- Production-safe RBAC with JWKS verification (RS256, `aud=mcp-devdiag`)
- Per-tenant rate limiting (TokenBucket: 30 req/min, burst 5)
- Incident mode with TTL auto-revert for temporary elevated access
- Vendor-neutral diagnostic probes (CSP headers, inline CSP, DOM overlays, handshake, framework detection)
- Standardized ProbeResult TypedDict with severity scoring system
- Probe presets (chat, embed, app, full) for curated diagnostic bundles
- `diag_status_plus` endpoint with score, severity, and fix recommendations
- `diag_quickcheck` endpoint for CI-safe HTTP-only validation
- `get_probe_result_schema` endpoint for client type generation
- Prometheus metrics integration with universal queries
- Grafana dashboard JSON (`dashboards/devdiag.json`)
- Postman collection (`postman/devdiag.postman_collection.json`)
- TypeScript SDK with Zod validation (`docs/examples/devdiag.ts`)
- Python client SDK (`docs/examples/devdiag_client.py`)
- Docker Compose and Kubernetes deployment manifests
- SSRF protection blocking private IP ranges (RFC1918, loopback, link-local)
- Production policy tests enforcing security defaults
- SLO definitions with Prometheus alert rules
- Comprehensive runbooks (SECURITY.md, RUNBOOK.md, RELEASE.md)
- GitHub Actions CI workflow with optional browser test gating
- 60-second smoke test documentation

### Changed
- `get_status` upgraded to include bundle diagnostics and severity scoring (backward compatible)
- Driver abstraction with HttpDriver (prod-safe) and PlaywrightDriver (runtime checks)
- Enhanced `__all__` exports and package metadata

### Security
- Enforced header deny-list (authorization, cookie, set-cookie, x-api-key)
- Production mode forbids request/response body capture
- URL allow-list validation on all probe endpoints
- JWKS-backed JWT verification with 10-minute cache TTL
- Private IP blocking prevents SSRF attacks
- Header redaction in logs and metrics

### Fixed
- Improved error handling for missing dependencies (Playwright degradation)
- Proper TypedDict usage for mypy compatibility

## [Unreleased]

### Added
- Production-safe DevDiag with RBAC, sampling, and policy enforcement
- `devdiag.yaml` configuration with mode-based deployment support (dev/staging/prod)
- Role-based access control (RBAC) with JWT authentication
  - `reader` role: read-only access to metrics, logs, summaries
  - `operator` role: full access including mode switching and sampling adjustments
- Production sampling controls (configurable rates, default 2%)
- Allow-listed HTTP probes with fnmatch pattern matching
- Header redaction for sensitive data (authorization, cookies, API keys)
- Policy enforcement tests for CI/CD pipelines
  - Validates sampling rates ≤5% in production
  - Ensures redaction rules are configured
  - Verifies probe allowlists are present
- Security authorization tests for RBAC validation
- Prometheus metrics integration adapter with fallback
- Frontend telemetry capture module (`devCapture.ts`)
  - Session-level sampling
  - URL scrubbing for query parameters
  - `sendBeacon()` reliability for page unload scenarios
- Environment-specific configuration examples (staging, production)
- Operations runbook with incident response procedures
- Comprehensive README documentation
  - Production mode scope and limitations
  - RBAC operations guide
  - Configuration reference
  - Deployment best practices

### Changed
- README expanded with production deployment guidance
- MCP server tools now support production-safe diagnostics

### Security
- JWT-based authorization (note: lightweight parsing; JWKS validation recommended for production)
- Sensitive header filtering (authorization, cookie, set-cookie, x-api-key)
- Query parameter redaction (token, key, code, session)
- Path parameter masking for user IDs and tokens
- Probe endpoint allowlist enforcement (403 for non-allowed URLs)

## [0.1.0] - 2025-01-10

### Added
- Initial MCP server implementation with FastMCP framework
- Backend log reading (`get_backend_logs`)
- Frontend log reading (`get_frontend_logs`)
- Environment state retrieval (`get_env_state`)
- Network telemetry (`get_network_log`, `get_network_summary`)
- Request diagnostics (`get_request_diagnostics`)
- Comprehensive status endpoint (`get_status`)
- Development tooling (pytest, ruff, mypy)
- GitHub Actions CI/CD pipeline
- VS Code workspace configuration
- MIT License
- Basic README documentation

### Infrastructure
- Python package structure with `pyproject.toml`
- Pre-commit hooks configuration
- Makefile for common development tasks
- `.editorconfig` for consistent code formatting
- `.gitignore` for Python projects

[Unreleased]: https://github.com/leok974/mcp-devdiag/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/leok974/mcp-devdiag/releases/tag/v0.1.0
