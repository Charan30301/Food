#!/usr/bin/env python3
"""Generate VAPID keys for Web Push.

Print the public key and a base64-encoded PEM private key suitable for
VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY_B64 environment variables.
"""
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

private_key = ec.generate_private_key(ec.SECP256R1())
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
public = private_key.public_key().public_numbers()
public_bytes = b"\x04" + public.x.to_bytes(32, "big") + public.y.to_bytes(32, "big")

def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

print("VAPID_PUBLIC_KEY=" + b64url(public_bytes))
print("VAPID_PRIVATE_KEY_B64=" + base64.b64encode(private_pem).decode("ascii"))
print("VAPID_CLAIM_EMAIL=mailto:your-email@example.com")
