"""DevDiag configuration loader and utilities."""

from pathlib import Path
from dataclasses import dataclass
import yaml
import fnmatch


@dataclass
class LearnPrivacyConfig:
    """Privacy settings for learning mode."""

    hash_targets: bool
    keep_evidence_keys: list[str]


@dataclass
class LearnConfig:
    """Configuration for closed-loop learning."""

    enabled: bool
    store: str
    privacy: LearnPrivacyConfig
    retention_days: int
    min_support: int
    alpha: float
    beta: float


class DevDiagConfig:
    """DevDiag configuration with defaults and validation."""

    def __init__(self, d: dict):
        self.mode = d.get("mode", "dev")
        self.tenant = d.get("tenant", "default")
        self.allow_probes = d.get("allow_probes", [])
        self.sampling = d.get("sampling", {})
        self.retention = d.get("retention", {})
        self.rbac = d.get("rbac", {"provider": "noop", "roles": []})
        self.redaction = d.get("redaction", {})
        self.shipping = d.get("shipping", {})

        # Security settings
        sec = d.get("security", {})
        self.jwks_url = sec.get("jwks_url")
        self.audience = sec.get("audience", "mcp-devdiag")
        self.ssrf_block_cidrs = sec.get(
            "ssrf_block_cidrs",
            ["127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16"],
        )

        # Rate limits
        lim = d.get("limits", {})
        self.per_tenant_rpm = lim.get("per_tenant_rpm", 30)
        self.burst = lim.get("burst", 5)
        self.export_max_bytes = lim.get("export_max_bytes", 262144)  # 256 KB

        # Diagnostic settings
        diag = d.get("diag", {})
        self.browser_enabled = diag.get("browser_enabled", False)
        self.suppress = diag.get("suppress", [])
        self.presets = diag.get("presets", ["chat", "embed", "app", "full"])

        # Export settings
        exp = d.get("export", {})
        self.s3_bucket = exp.get("s3_bucket")
        self.s3_region = exp.get("region", "us-east-1")
        self.s3_key_prefix = exp.get("key_prefix", "")

        # Learning settings
        learn = d.get("learn", {})
        privacy = learn.get("privacy", {})
        self.learn = LearnConfig(
            enabled=learn.get("enabled", False),
            store=learn.get("store", "sqlite:///devdiag.db"),
            privacy=LearnPrivacyConfig(
                hash_targets=privacy.get("hash_targets", True),
                keep_evidence_keys=privacy.get(
                    "keep_evidence_keys", ["csp", "xfo", "framework", "server", "routes"]
                ),
            ),
            retention_days=learn.get("retention_days", 180),
            min_support=learn.get("min_support", 2),
            alpha=learn.get("alpha", 0.6),
            beta=learn.get("beta", 0.7),
        )

    def method_url_allowed(self, method: str, url: str) -> bool:
        """Check if a method+URL combination is allow-listed for probes."""
        target = f"{method.upper()} {url}"
        return any(fnmatch.fnmatch(target, pattern) for pattern in self.allow_probes)


def load_config(path: str | Path = "devdiag.yaml") -> DevDiagConfig:
    """Load DevDiag configuration from YAML file."""
    p = Path(path)
    if not p.exists():
        return DevDiagConfig({})
    return DevDiagConfig(yaml.safe_load(p.read_text()))
