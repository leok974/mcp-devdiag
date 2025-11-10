"""S3 export functionality for redacted diagnostic bundles."""

from typing import Any
import json
import time
import logging

logger = logging.getLogger(__name__)

# Safe keys allowed in exported bundles (no sensitive data)
SAFE_KEYS = {"problems", "remediation", "evidence", "score", "ok", "fixes", "severity", "preset", "probes_run"}

# Observability metrics (in-memory counters)
_EXPORTS_TOTAL = {"ok": 0, "error": 0}
_LAST_EXPORT_TIMESTAMP = 0


def _redact(obj: Any) -> Any:
    """
    Recursively redact object to only include safe keys.
    
    Args:
        obj: Object to redact (dict, list, or primitive)
    
    Returns:
        Redacted copy with only SAFE_KEYS preserved at top level
    """
    if isinstance(obj, dict):
        return {
            k: _redact(v)
            for k, v in obj.items()
            if k in SAFE_KEYS
        }
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    return obj


async def export_snapshot(payload: dict, tenant: str, export_config: dict) -> dict:
    """
    Export redacted diagnostic bundle to S3.
    
    Args:
        payload: Diagnostic bundle to export
        tenant: Tenant identifier
        export_config: Export configuration with s3_bucket and optional region
    
    Returns:
        Dict with export status and S3 location
    
    Raises:
        ValueError: If S3 export not configured or payload too large
        RuntimeError: If boto3 not available or S3 upload fails
    """
    global _LAST_EXPORT_TIMESTAMP
    
    if not export_config or not export_config.get("s3_bucket"):
        raise ValueError("S3 export not configured - set export.s3_bucket in devdiag.yaml")
    
    try:
        import boto3
    except ImportError:
        _EXPORTS_TOTAL["error"] += 1
        logger.error("S3 export failed: boto3 not installed")
        raise RuntimeError("boto3 not installed. Install with: pip install boto3")
    
    # Redact payload to remove sensitive data
    bundle = _redact(payload)
    bundle_json = json.dumps(bundle, indent=2)
    bundle_size = len(bundle_json.encode("utf-8"))
    
    # Enforce size cap (default 256 KB)
    max_bytes = export_config.get("max_bytes", 262144)
    if bundle_size > max_bytes:
        _EXPORTS_TOTAL["error"] += 1
        logger.warning(f"S3 export rejected: payload size {bundle_size} exceeds limit {max_bytes}")
        raise ValueError(f"Payload size {bundle_size} bytes exceeds limit {max_bytes} bytes")
    
    # Generate S3 key with timestamp
    key_prefix = export_config.get("key_prefix", "")
    timestamp = int(time.time())
    key = f"{key_prefix}{tenant}/snapshots/{timestamp}.json"
    
    # Create S3 client
    region = export_config.get("region")
    s3_kwargs = {"region_name": region} if region else {}
    s3 = boto3.client("s3", **s3_kwargs)
    
    # Upload with server-side encryption
    try:
        s3.put_object(
            Bucket=export_config["s3_bucket"],
            Key=key,
            Body=bundle_json.encode("utf-8"),
            ContentType="application/json",
            ServerSideEncryption="AES256",
        )
        
        # Update observability metrics
        _EXPORTS_TOTAL["ok"] += 1
        _LAST_EXPORT_TIMESTAMP = timestamp
        logger.info(f"S3 export succeeded: s3://{export_config['s3_bucket']}/{key}")
        
    except Exception as e:
        _EXPORTS_TOTAL["error"] += 1
        logger.error(f"S3 upload failed: {e}", exc_info=True)
        raise RuntimeError(f"S3 upload failed: {e}")
    
    return {
        "ok": True,
        "bucket": export_config["s3_bucket"],
        "key": key,
        "timestamp": timestamp,
        "size_bytes": bundle_size,
    }


def get_export_metrics() -> dict:
    """
    Get export observability metrics.
    
    Returns:
        Dict with devdiag_exports_total and devdiag_last_export_unixtime
    """
    return {
        "devdiag_exports_total": _EXPORTS_TOTAL.copy(),
        "devdiag_last_export_unixtime": _LAST_EXPORT_TIMESTAMP,
    }
