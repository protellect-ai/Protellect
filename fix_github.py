#!/usr/bin/env python3
"""
Protellect — GitHub Fix Script
Pushes the correct app.py directly to GitHub in one command.

Usage:
    python3 fix_github.py YOUR_GITHUB_TOKEN

Get token: https://github.com/settings/tokens
  → New token (classic) → check "repo" scope → Generate
  Token starts with ghp_...
"""
import sys, base64, json, urllib.request, urllib.error, os

REPO  = "protellect-ai/Protellect"
FILE  = "app.py"

def push(token):
    if not os.path.exists(FILE):
        print(f"❌  {FILE} not found. Run this script from inside the Protellect_Final folder.")
        return False

    with open(FILE, "rb") as f:
        raw = f.read()

    # Verify it's Python not TOML
    first_line = raw.splitlines()[0].decode("utf-8", errors="replace") if raw else ""
    if first_line.strip().startswith("[theme]"):
        print("❌  app.py starts with [theme] — wrong file! You have the config.toml.")
        print("    The correct app.py starts with: from __future__ import annotations")
        return False

    print(f"✓  app.py verified ({len(raw):,} bytes)")
    print(f"   First line: {first_line.strip()[:60]}")

    encoded = base64.b64encode(raw).decode()
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "Protellect-Fix/1.0",
    }

    # Get current file SHA
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE}"
    req = urllib.request.Request(url, headers=headers)
    sha = ""
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            sha = data.get("sha", "")
            current_size = data.get("size", 0)
            print(f"✓  Found existing GitHub {FILE} ({current_size:,} bytes, SHA: {sha[:10]}...)")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("ℹ  app.py not found on GitHub — will create it.")
        elif e.code == 401:
            print("❌  Token rejected. Ensure it has 'repo' scope.")
            return False
        else:
            print(f"❌  GitHub error: {e.code} {e.reason}")
            return False

    # Push
    payload = {
        "message": "fix: upload correct Protellect app.py",
        "content": encoded,
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha

    req2 = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers=headers, method="PUT"
    )
    try:
        with urllib.request.urlopen(req2) as resp:
            result = json.loads(resp.read())
            commit_url = result.get("commit", {}).get("html_url", "")
            print(f"\n✅  SUCCESS — app.py pushed to GitHub")
            print(f"    Commit: {commit_url}")
            print(f"\n    Streamlit Cloud redeploys in ~30 seconds.")
            print(f"    Visit your app URL to verify.")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"❌  Push failed ({e.code}): {body}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        token = input("\nPaste your GitHub token (ghp_...): ").strip()
    else:
        token = sys.argv[1].strip()

    if not token:
        print("❌  No token provided.")
        sys.exit(1)

    print(f"\n🔬 Protellect — GitHub Push Script")
    print(f"   Repo: {REPO}")
    print(f"   File: {FILE}\n")

    success = push(token)
    sys.exit(0 if success else 1)
