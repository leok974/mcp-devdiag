#!/usr/bin/env python3
"""
Generate JWT service tokens for DevDiag HTTP tenants.

Usage:
    python generate_devdiag_tokens.py

Requirements:
    pip install PyJWT cryptography

Outputs tenant-specific JWTs with:
    - aud: mcp-devdiag
    - sub: svc:<tenant>
    - exp: 7 days from now
"""

import jwt
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
ISSUER = "https://auth.leoklemet.com"
AUDIENCE = "mcp-devdiag"
TENANTS = ["applylens", "ledgermind", "portfolio"]
EXPIRY_DAYS = 7

# Private key path (adjust as needed)
PRIVATE_KEY_PATH = "private-key.pem"

def load_private_key():
    """Load RSA private key from file."""
    key_path = Path(PRIVATE_KEY_PATH)
    if not key_path.exists():
        print(f"❌ Error: Private key not found at {PRIVATE_KEY_PATH}")
        print(f"   Please generate an RSA key pair:")
        print(f"   openssl genrsa -out private-key.pem 2048")
        print(f"   openssl rsa -in private-key.pem -pubout -out public-key.pem")
        sys.exit(1)
    
    return key_path.read_text()

def generate_token(tenant: str, private_key: str, days: int = EXPIRY_DAYS) -> str:
    """
    Generate a JWT service token for a tenant.
    
    Args:
        tenant: Tenant identifier (e.g., "applylens")
        private_key: RSA private key PEM string
        days: Token expiry in days
    
    Returns:
        Encoded JWT string
    """
    now = datetime.utcnow()
    payload = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": f"svc:{tenant}",
        "iat": now,
        "exp": now + timedelta(days=days),
        "nbf": now,
    }
    
    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token

def decode_token_info(token: str) -> dict:
    """Decode token without verification to show claims."""
    return jwt.decode(token, options={"verify_signature": False})

def main():
    print("=" * 70)
    print("DevDiag Service Token Generator")
    print("=" * 70)
    print()
    
    # Load private key
    try:
        private_key = load_private_key()
    except Exception as e:
        print(f"❌ Error loading private key: {e}")
        sys.exit(1)
    
    print(f"🔑 Loaded private key from: {PRIVATE_KEY_PATH}")
    print(f"🏢 Issuer: {ISSUER}")
    print(f"🎯 Audience: {AUDIENCE}")
    print(f"⏰ Expiry: {EXPIRY_DAYS} days")
    print(f"👥 Tenants: {', '.join(TENANTS)}")
    print()
    print("=" * 70)
    print()
    
    # Generate tokens for each tenant
    tokens = {}
    for tenant in TENANTS:
        try:
            token = generate_token(tenant, private_key)
            tokens[tenant] = token
            
            # Decode to show claims
            claims = decode_token_info(token)
            
            print(f"✅ {tenant.upper()}")
            print(f"   Subject:    {claims['sub']}")
            print(f"   Issued:     {datetime.fromtimestamp(claims['iat']).isoformat()}")
            print(f"   Expires:    {datetime.fromtimestamp(claims['exp']).isoformat()}")
            print(f"   Token:      {token[:50]}...")
            print()
            
        except Exception as e:
            print(f"❌ Error generating token for {tenant}: {e}")
            continue
    
    if not tokens:
        print("❌ No tokens generated successfully.")
        sys.exit(1)
    
    print("=" * 70)
    print()
    print("📋 GITHUB SECRETS (copy to each repository)")
    print("=" * 70)
    print()
    
    # Output for GitHub Secrets
    for tenant in TENANTS:
        if tenant in tokens:
            repo_name = {
                "applylens": "applylens",
                "ledgermind": "ledger-mind",
                "portfolio": "portfolio",
            }.get(tenant, tenant)
            
            print(f"Repository: {repo_name}")
            print(f"Secret Name: DEVDIAG_JWT")
            print(f"Secret Value:")
            print(f"{tokens[tenant]}")
            print()
    
    print("=" * 70)
    print()
    print("📝 ENVIRONMENT VARIABLES (for local development)")
    print("=" * 70)
    print()
    
    for tenant in TENANTS:
        if tenant in tokens:
            print(f"# {tenant.capitalize()} (.env.local)")
            print(f"DEVDIAG_JWT={tokens[tenant]}")
            print()
    
    print("=" * 70)
    print()
    print("🧪 VERIFICATION COMMANDS")
    print("=" * 70)
    print()
    
    for tenant in TENANTS:
        if tenant in tokens:
            test_url = {
                "applylens": "https://applylens.app",
                "ledgermind": "https://app.ledger-mind.org",
                "portfolio": "https://www.leoklemet.com",
            }.get(tenant, "https://example.com")
            
            print(f"# Test {tenant}")
            print(f"curl -X POST https://devdiag.leoklemet.com/diag/run \\")
            print(f"  -H 'Authorization: Bearer {tokens[tenant]}' \\")
            print(f"  -H 'Content-Type: application/json' \\")
            print(f"  -d '{{\"url\":\"{test_url}\",\"preset\":\"app\",\"tenant\":\"{tenant}\"}}'")
            print()
    
    print("=" * 70)
    print()
    print("✅ Token generation complete!")
    print()
    print("⚠️  Security reminders:")
    print("   1. Store tokens securely (GitHub Secrets, not in code)")
    print("   2. Set up weekly rotation (see JWT_SETUP.md)")
    print("   3. Never commit tokens to git")
    print("   4. Delete this output after storing tokens")
    print()

if __name__ == "__main__":
    main()
