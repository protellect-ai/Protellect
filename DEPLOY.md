# Deploying Protellect

## On Streamlit Cloud (recommended)

1. Push these files to your GitHub repo root:
   - `app.py`
   - `protellect_data.py`
   - `protellect_citations.py`
   - `protellect_icons.py`
   - `requirements.txt`

2. At https://share.streamlit.io connect the repo and set the entry point to `app.py`.

3. In **Manage app → Settings → Secrets**, add:

   ```toml
   ANTHROPIC_API_KEY = "sk-ant-api03-..."   # optional, enables Claude chat
   GEMINI_API_KEY    = "AIza..."            # optional, enables Gemini chat

   [credentials]
   "you@example.com" = "your-strong-password"

   [credential_plans]
   "you@example.com" = "enterprise"          # free | pro | enterprise
   ```

4. The app reboots automatically when secrets are saved.

## Important notes

- **`set_page_config` must stay first.** The three helper modules are imported
  before it, but they make no Streamlit calls at import time, so this is safe.
- **No credentials in code.** All login accounts come from `[credentials]` in
  secrets. If none are set, the app falls back to one free-tier demo account
  plus guest access.
- **API keys are optional.** Without an AI key, the workspace chat uses a
  rule-based offline fallback. All 17 data-source integrations work without any
  key (they query public APIs).
- **File size.** `app.py` is large. If the GitHub web editor refuses to display
  it, push via git on the command line instead:

  ```bash
  git add app.py protellect_data.py protellect_citations.py protellect_icons.py requirements.txt
  git commit -m "Modular split"
  git push
  ```

## Local development

```bash
pip install -r requirements.txt
streamlit run app.py
```
