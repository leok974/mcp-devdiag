"""S3 export functionality for redacted diagnostic bundles."""

from typing import Any, Dict
import json
import time

# Safe keys allowed in exported bundles (no sensitive data)
SAFE_KEYS = {"problems", "remediation", "evidence", "score", "ok", "fixes", "severity", "preset", "probes_run"}


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
        ValueError: If S3 export not configured
        RuntimeError: If boto3 not available or S3 upload fails
    """
    if not export_config or not export_config.get("s3_bucket"):
        raise ValueError("S3 export not configured - set export.s3_bucket in devdiag.yaml")
    
    try:
        import boto3
    except ImportError:
        raise RuntimeError("boto3 not installed. Install with: pip install boto3")
    
    # Redact payload to remove sensitive data
    bundle = _redact(payload)
    
    # Generate S3 key with timestamp
    key = f"{tenant}/snapshots/{int(time.time())}.json"
    
    # Create S3 client
    region = export_config.get("region")
    s3_kwargs = {"region_name": region} if region else {}
    s3 = boto3.client("s3", **s3_kwargs)
    
    # Upload with server-side encryption
    try:
        s3.put_object(
            Bucket=export_config["s3_bucket"],
            Key=key,
            Body=json.dumps(bundle, indent=2).encode("utf-8"),
            ContentType="application/json",
            ServerSideEncryption="AES256",
        )
    except Exception as e:
        raise RuntimeError(f"S3 upload failed: {e}")
    
    return {
        "ok": True,
        "bucket": export_config["s3_bucket"],
        "key": key,
        "timestamp": int(time.time()),
    }
