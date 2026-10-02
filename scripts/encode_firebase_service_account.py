"""Print a base64 value suitable for Render's FIREBASE_SERVICE_ACCOUNT_JSON_B64 variable."""
import base64
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print("Usage: python scripts/encode_firebase_service_account.py firebase-service-account.json")
    raise SystemExit(1)

path = Path(sys.argv[1])
raw = path.read_bytes()
print(base64.b64encode(raw).decode("ascii"))
