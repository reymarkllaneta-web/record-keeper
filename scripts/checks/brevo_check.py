"""Checks the Brevo settings in .env without sending any email. Never prints the API key."""
import os, sys
import requests
from dotenv import load_dotenv

load_dotenv(".env")
key = os.getenv("BREVO_API_KEY", "").strip()
sender = os.getenv("BREVO_SENDER_EMAIL", "").strip()
print("API key set:", bool(key), "| starts with xkeysib-:", key.startswith("xkeysib-"), "| length:", len(key))
print("Sender email:", sender or "(empty)")
if not key:
    sys.exit("No BREVO_API_KEY in .env")
h = {"api-key": key, "accept": "application/json"}
try:
    r = requests.get("https://api.brevo.com/v3/account", headers=h, timeout=15)
except Exception as e:
    sys.exit(f"Could not reach Brevo: {type(e).__name__}: {e}")
print("\n/account ->", r.status_code)
if r.ok:
    a = r.json()
    print("  account email:", a.get("email"), "| company:", a.get("companyName"))
    for p in a.get("plan", []):
        print("  plan:", p.get("type"), "| credits:", p.get("credits"), p.get("creditsType"))
else:
    print("  ", r.text[:300])
r = requests.get("https://api.brevo.com/v3/senders", headers=h, timeout=15)
print("\n/senders ->", r.status_code)
if r.ok:
    senders = r.json().get("senders", [])
    for s in senders:
        print(f"  {s.get('email')}  active={s.get('active')}")
    match = [s for s in senders if (s.get("email") or "").lower() == sender.lower()]
    print("\nSender in .env is", "VERIFIED/ACTIVE" if match and match[0].get("active") else
          ("listed but NOT active" if match else "NOT in your Brevo senders list"))
else:
    print("  ", r.text[:300])
