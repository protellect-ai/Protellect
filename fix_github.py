#!/usr/bin/env python3
"""
Protellect — GitHub Fix Script
Run this ONCE from inside the Protellect folder to push the correct app.py to GitHub.

Usage:
  python3 fix_github.py YOUR_GITHUB_TOKEN

Get a token at: https://github.com/settings/tokens
  → New token (classic) → check "repo" scope → Generate
"""
import sys, base64, json, urllib.request, urllib.error, os

REPO = "protellect-ai/Protellect"

def push(token, filepath="app.py"):
    # Read file
    if not os.path.exists(filepath):
        print(f"❌  {filepath} not found. Run this from inside the Protellect folder.")
        return

    with open(filepath, "rb") as f:
        raw = f.read()

    # Verify it's Python not TOML
    if raw[:7] == b"[theme]":
        print("❌  app.py starts with [theme] — you have the wrong file! Get the correct app.py from Claude.")
        return
    if raw[:3] != b'"""':
        print(f"⚠  app.py starts with: {repr(raw[:30])} — double-check this is the right file.")
        input("Press Enter to continue anyway, or Ctrl+C to cancel: ")

    encoded = base64.b64encode(raw).decode()
    print(f"✓  Read app.py  ({len(raw):,} bytes)")

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "Protellect-Fix-Script/1.0",
    }

    # Get current file SHA (required for update)
    url = f"https://api.github.com/repos/{REPO}/contents/{filepath}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            current = json.loads(resp.read())
            sha = current.get("sha", "")
            current_size = current.get("size", 0)
            print(f"✓  Found existing app.py on GitHub  ({current_size:,} bytes, SHA: {sha[:12]}...)")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            sha = ""
            print("⚠  app.py not found on GitHub — will create it fresh.")
        elif e.code == 401:
            print("❌  Token rejected. Make sure your token has 'repo' scope.")
            return
        else:
            print(f"❌  GitHub API error: {e.code} {e.reason}")
            return

    # Push the correct file
    payload = {
        "message": "fix: replace broken app.py with correct Protellect v5 Python file",
        "content": encoded,
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha

    req2 = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req2) as resp:
            result = json.loads(resp.read())
            commit_url = result.get("commit", {}).get("html_url", "")
            print(f"✅  DONE! app.py pushed to GitHub successfully.")
            print(f"    Commit: {commit_url}")
            print(f"\n    Streamlit Cloud will redeploy automatically in ~30 seconds.")
            print(f"    Visit: https://protellect-ai.streamlit.app  (or your app URL)")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌  Push failed: {e.code} — {body[:200]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        token = input("Paste your GitHub token here: ").strip()
    else:
        token = sys.argv[1].strip()

    if not token or not token.startswith(("ghp_", "github_pat_", "gho_")):
        print(f"⚠  Token looks unusual: {token[:10]}... — proceeding anyway.")

    push(token)
