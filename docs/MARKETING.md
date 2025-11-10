# Marketing & Announcement Templates for v0.2.0

## LinkedIn Post

🚀 **mcp-devdiag v0.2.0 is now live on PyPI!**

Production-ready MCP server for autonomous development diagnostics with:

✅ RBAC with JWKS (RS256)  
✅ Vendor-neutral diagnostic probes  
✅ Prometheus metrics + Grafana dashboard  
✅ SSRF protection & security guardrails  
✅ Optional add-ons: Playwright, S3 export, suppressions  

**Install in 60 seconds:**
```bash
pip install mcp-devdiag==0.2.0
mcp-devdiag --stdio
```

Perfect for AI agents working with production systems. 31 tests passing, full docs included.

📦 PyPI: https://pypi.org/project/mcp-devdiag/  
📖 GitHub: https://github.com/leok974/mcp-devdiag  

#AI #DevTools #Observability #MCP #OpenSource

---

## Twitter/X Post (Short)

🚀 mcp-devdiag v0.2.0 is live on PyPI!

Production-safe MCP diagnostics with RBAC, probes, metrics & security guardrails.

Install:
```
pip install mcp-devdiag==0.2.0
```

📦 https://pypi.org/project/mcp-devdiag/
📖 https://github.com/leok974/mcp-devdiag

#AI #DevTools #MCP

---

## Twitter/X Thread

1/5 🚀 Just shipped mcp-devdiag v0.2.0 to PyPI!

A production-ready MCP server for autonomous development diagnostics.

Install in 60 seconds:
```
pip install mcp-devdiag==0.2.0
mcp-devdiag --stdio
```

---

2/5 🔒 Security-first design:
• RBAC with JWKS (RS256)
• Per-tenant rate limiting
• SSRF protection (blocks private IPs)
• No request bodies ever captured
• Header redaction built-in

Perfect for AI agents in production.

---

3/5 🔍 Vendor-neutral diagnostic probes:
• CSP headers & inline violations
• CORS configuration
• Framework version detection
• DOM accessibility issues
• Embed handshake validation

Returns scored results with fix recipes.

---

4/5 📊 Operations-ready:
• Prometheus metrics adapter
• Grafana dashboard included
• TypeScript & Python SDKs
• Docker + K8s deployments
• 31 tests passing

Plus optional Playwright driver & S3 export for staging.

---

5/5 📦 Get started:
PyPI: https://pypi.org/project/mcp-devdiag/
GitHub: https://github.com/leok974/mcp-devdiag
Docs: Full README + SECURITY.md + RUNBOOK.md

MIT licensed. PRs welcome!

#AI #DevTools #Observability #MCP #OpenSource

---

## Reddit Post (r/Python, r/programming, r/devops)

**Title:** mcp-devdiag v0.2.0 - Production-safe MCP diagnostics server (now on PyPI)

**Body:**

Hi folks! I just released **mcp-devdiag v0.2.0** to PyPI - a production-ready Model Context Protocol server for autonomous development diagnostics.

## What is it?

An MCP server that provides AI agents with safe, controlled access to production diagnostics:

- **Security-first**: RBAC with JWKS, rate limiting, SSRF protection, no bodies captured
- **Diagnostic probes**: CSP, CORS, frameworks, DOM accessibility (vendor-neutral)
- **Operations**: Prometheus metrics, Grafana dashboard, runbooks included
- **Add-ons**: Playwright driver (staging), S3 export, suppressions

## Quick start

```bash
pip install mcp-devdiag==0.2.0
mcp-devdiag --stdio
```

Configure in VS Code:
```json
{
  "mcpServers": {
    "mcp-devdiag": {
      "command": "mcp-devdiag",
      "args": ["--stdio"]
    }
  }
}
```

## Why?

AI coding assistants need observability, but production access is risky. This provides:

1. Sampling & redaction for safe data collection
2. Allow-lists for controlled URL probing  
3. JWT auth with role-based permissions
4. Audit logging and incident TTLs

All the diagnostics, none of the security nightmares.

## Links

- PyPI: https://pypi.org/project/mcp-devdiag/
- GitHub: https://github.com/leok974/mcp-devdiag
- Docs: Complete README, SECURITY.md, RUNBOOK.md
- Tests: 31 passing, Python 3.10-3.13

MIT licensed. Feedback welcome!

---

## Hacker News Post

**Title:** mcp-devdiag – Production-safe MCP diagnostics with RBAC and probes

**URL:** https://github.com/leok974/mcp-devdiag

**Text (if needed):**

I built mcp-devdiag to give AI coding assistants safe access to production diagnostics without the usual security concerns (leaked credentials, unbounded access, PII exposure).

Key decisions:

1. **JWKS-backed RBAC** instead of API keys (short-lived tokens, standard rotation)
2. **No request/response bodies** ever captured (headers redacted via deny-list)
3. **Allow-list for probes** (explicit URL patterns only)
4. **Vendor-neutral probe design** (works with any framework)

Plus optional Playwright driver for staging (runtime DOM checks) and S3 export for incident snapshots (redacted, size-capped).

Just shipped v0.2.0 to PyPI with 31 tests passing. MIT licensed.

Would love feedback on the security model - trying to balance utility with safety for production use.

---

## Dev.to / Hashnode Blog Post Outline

**Title:** Shipping mcp-devdiag v0.2.0: Production-Safe Diagnostics for AI Coding Assistants

**Outline:**

1. **The Problem**
   - AI agents need observability to fix prod issues
   - Traditional logging is too risky (PII, credentials, unbounded access)
   - Existing solutions lack RBAC or are vendor-locked

2. **Design Principles**
   - Security first: JWKS auth, sampling, redaction
   - Vendor-neutral: Works with any framework
   - Operations-ready: Metrics, dashboards, runbooks

3. **Key Features**
   - RBAC with RS256 JWT
   - Diagnostic probes (CSP, CORS, frameworks, DOM)
   - Prometheus metrics + Grafana
   - Optional add-ons (Playwright, S3 export)

4. **Quick Start**
   - Installation: `pip install mcp-devdiag==0.2.0`
   - Configuration example
   - 60-second smoke test

5. **Under the Hood**
   - Probe architecture (TypedDict, severity scoring)
   - Rate limiting (token bucket per tenant)
   - SSRF protection (CIDR blocks)

6. **Production Deployment**
   - Docker Compose example
   - Kubernetes manifests
   - Security checklist

7. **Lessons Learned**
   - Why JWKS over API keys
   - Balancing utility vs safety
   - The importance of runbooks

8. **What's Next**
   - Community feedback
   - Planned v0.3.0 features
   - Contributing guide

**Call to Action:**
- Try it: https://pypi.org/project/mcp-devdiag/
- Star the repo: https://github.com/leok974/mcp-devdiag
- Report issues or contribute

---

## Discord/Slack Announcement

Hey everyone! 👋

Just shipped **mcp-devdiag v0.2.0** to PyPI! 🎉

It's a production-safe MCP server for autonomous dev diagnostics with RBAC, security guardrails, and vendor-neutral probes.

**Install:**
```bash
pip install mcp-devdiag==0.2.0
```

**Features:**
✅ JWKS auth (RS256)
✅ Diagnostic probes (CSP, CORS, frameworks)
✅ Prometheus metrics + Grafana
✅ Add-ons: Playwright, S3 export

**Links:**
📦 PyPI: https://pypi.org/project/mcp-devdiag/
📖 GitHub: https://github.com/leok974/mcp-devdiag

MIT licensed, 31 tests passing, Python 3.10-3.13.

Would love your feedback! 🙏

---

## Email Newsletter Template

**Subject:** mcp-devdiag v0.2.0 Released - Production-Safe AI Diagnostics

**Body:**

Hi there!

I'm excited to announce the release of **mcp-devdiag v0.2.0**, now available on PyPI!

## What's New in v0.2.0

**Security & RBAC:**
- JWKS-backed authentication (RS256)
- Per-tenant rate limiting
- SSRF protection
- Header redaction

**Diagnostic Probes:**
- Vendor-neutral probe system
- CSP, CORS, framework detection
- DOM accessibility checks
- Severity scoring with fix recipes

**Operations:**
- Prometheus metrics adapter
- Grafana dashboard (included)
- Docker + Kubernetes deployments
- TypeScript & Python SDKs

**Add-Ons (Optional):**
- Playwright driver for runtime DOM checks
- S3 export for incident snapshots
- Suppressions for known non-issues

## Quick Start

```bash
pip install mcp-devdiag==0.2.0
mcp-devdiag --stdio
```

That's it! Full documentation included.

## Links

- **PyPI:** https://pypi.org/project/mcp-devdiag/
- **GitHub:** https://github.com/leok974/mcp-devdiag
- **Docs:** Complete README, SECURITY.md, RUNBOOK.md

## What's Next?

I'd love your feedback! Try it out and let me know what you think. Issues and PRs welcome.

Cheers,
[Your Name]

---

**Choose the appropriate template(s) based on your audience and platform!**
