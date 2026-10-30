"""Checks the Cloudinary settings in .env. Never prints the API key or secret."""
import os, sys
from dotenv import load_dotenv
import cloudinary, cloudinary.api

load_dotenv(".env", override=True)
name = (os.getenv("CLOUDINARY_CLOUD_NAME") or "").strip()
key = (os.getenv("CLOUDINARY_API_KEY") or "").strip()
secret = (os.getenv("CLOUDINARY_API_SECRET") or "").strip()
print("cloud name:", repr(name) if name else "(EMPTY)")
print("api key set:", bool(key), "| digits only:", key.isdigit(), "| length:", len(key))
print("api secret set:", bool(secret), "| length:", len(secret))
for k in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"):
    raw = os.getenv(k) or ""
    if raw != raw.strip() or raw.startswith(("'", '"')):
        print(f"  warning: {k} has spaces or quotes around it")
if not (name and key and secret):
    sys.exit("\nNOT CONNECTED: one or more values are empty in .env (check the lines start at the very left, no spaces before them).")
cloudinary.config(cloud_name=name, api_key=key, api_secret=secret, secure=True)
try:
    print("\nping:", cloudinary.api.ping())
    u = cloudinary.api.usage()
    print("CONNECTED. plan:", u.get("plan"), "| storage used (bytes):", (u.get("storage") or {}).get("usage"))
    raw = cloudinary.api.resources(resource_type="raw", max_results=5)
    print("raw files (scans/attachments) found:", len(raw.get("resources", [])),
          [r.get("public_id") for r in raw.get("resources", [])][:5])
except Exception as e:
    print("\nNOT CONNECTED:", type(e).__name__, str(e)[:300])
