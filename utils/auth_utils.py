"""
Simple API key utility
- generate_api_key(): create a random, URL-safe API key (default 256-bit entropy)
- hash_api_key(key): return a string that can be stored safely (PBKDF2-HMAC-SHA256)
- verify_api_key(key, stored): return True if the key matches the stored hash
"""

import secrets
import hashlib
import hmac
import base64
from typing import Optional

# Internal helper functions for base64 encoding
def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

# Internal helper functions for base64 decoding
def _b64_decode(s: str) -> bytes:
    padding = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)

# Generate a new random API key
def generate_api_key(n_bytes: int = 32) -> str:
    return secrets.token_urlsafe(n_bytes)

# Hash an API key for storage using PBKDF2-HMAC-SHA256
def hash_api_key(api_key: str, *, iterations: int = 200_000, salt: Optional[bytes] = None, dk_len: int = 32) -> str:
    # Hash an API key for storage using PBKDF2-HMAC-SHA256.
    # Returns a single string in this format: pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>
    if salt is None:
        salt = secrets.token_bytes(16)  # 128-bit salt
    dk = hashlib.pbkdf2_hmac("sha256", api_key.encode("utf-8"), salt, iterations, dklen=dk_len)
    return f"pbkdf2_sha256${iterations}${_b64_encode(salt)}${_b64_encode(dk)}"


def verify_api_key(api_key: str, stored: str) -> bool:
    # Verify an API key against a stored hash string. Returns True if the key matches the stored hash, False otherwise.
    try:
        algo, iter_str, salt_b64, hash_b64 = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iter_str)
        salt = _b64_decode(salt_b64)
        expected = _b64_decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", api_key.encode("utf-8"), salt, iterations, dklen=len(expected))
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False

def compare_api_key(api_key1: str, api_key2: str) -> bool:
    # Compare two unhashed API keys using hmac.compare_digest for timing-attack resistance.
    return hmac.compare_digest(api_key1, api_key2)


if __name__ == "__main__":
    # Example usage
    key = generate_api_key()
    stored = hash_api_key(key)
    print("Test API key generation and verification")
    print("API key: ", key)
    print("Stored hash:", stored)
    print("Verify OK:", verify_api_key(key, stored))
