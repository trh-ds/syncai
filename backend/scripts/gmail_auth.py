"""One-time script to obtain a Gmail refresh token for the ASDR mail bot.

Prerequisites:
1. Go to https://console.cloud.google.com
2. Create a project (or use existing)
3. Enable Gmail API: APIs & Services → Library → Gmail API → Enable
4. Configure OAuth consent screen: External, add your email as test user
5. Create OAuth 2.0 Client ID: Credentials → Create → OAuth client ID → Desktop app
6. Download the JSON, extract client_id and client_secret
7. Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET in backend/.env
8. Run this script: python scripts/gmail_auth.py
9. Copy the printed refresh token to GMAIL_REFRESH_TOKEN in backend/.env

No browser? Set GMAIL_CLIENT_ID + GMAIL_CLIENT_SECRET, run on a machine with a
browser, then copy the token back.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
]

CLIENT_CONFIG = {
    "installed": {
        "client_id": os.environ.get("GMAIL_CLIENT_ID", ""),
        "client_secret": os.environ.get("GMAIL_CLIENT_SECRET", ""),
        "project_id": "",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "redirect_uris": ["http://localhost"],
    }
}


def main():
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("ERROR: Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET environment variables first.")
        print("\nIn PowerShell:")
        print('  $env:GMAIL_CLIENT_ID="..."')
        print('  $env:GMAIL_CLIENT_SECRET="..."')
        print("  python scripts/gmail_auth.py")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n" + "=" * 60)
    print("REFRESH TOKEN (copy this into backend/.env as GMAIL_REFRESH_TOKEN):")
    print("=" * 60)
    print(creds.refresh_token)
    print("=" * 60)

    if creds.id_token:
        id_info = creds.id_token
        print(f"\nAuthenticated as: {id_info.get('email', 'unknown')}")
    print(f"\nAlso set GMAIL_USER_EMAIL=your.email@gmail.com in backend/.env")


if __name__ == "__main__":
    main()
