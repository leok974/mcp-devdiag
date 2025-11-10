"""DevDiag configuration loader and utilities."""

from pathlib import Path
import yaml
import fnmatch


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
