#!/usr/bin/env python3
"""Add the Hypotheses tab to the Protellect app.py. Standard library only.

    python protellect_hypothesis/patch_app.py app.py            apply (writes app.py.bak first)
    python protellect_hypothesis/patch_app.py app.py --check    show what would change, write nothing
    python protellect_hypothesis/patch_app.py app.py --undo     restore app.py from app.py.bak

It makes three small edits, each wrapped in `# >>> protellect_hypothesis integration` markers:
  1. ALL_TAB_NAMES gets "Hypotheses".
  2. Just before `def _tab_visible`, "Hypotheses" is forced into the visible tabs (right after "Triage"), so users who
     already finished onboarding or who have a research goal set still see it.
  3. After the last `tabN = _tab_by_name.get(...)` line, a new tab variable and a `with tab:` block that calls the
     engine. That block is wrapped in try/except, so if the engine ever fails the rest of the app is unaffected.
Before writing, it checks every anchor exists and that the patched file still compiles. Safe to run twice.
"""
from __future__ import annotations

import re
import shutil
import sys
from typing import List, Tuple

BEGIN = "# >>> protellect_hypothesis integration"
END = "# <<< protellect_hypothesis integration"

VISIBLE_BLOCK = f'''{BEGIN}: always offer the Hypotheses tab (after Triage when present)
if "Hypotheses" not in _visible_tab_names:
    _vt = list(_visible_tab_names)
    _vt.insert(_vt.index("Triage") + 1 if "Triage" in _vt else len(_vt), "Hypotheses")
    _visible_tab_names = _vt
{END}

'''


def _tab_block(var: str) -> str:
    return f'''{BEGIN}
{var} = _tab_by_name.get("Hypotheses", _SinkTab())
with {var}:
    try:
        from protellect_hypothesis.app_integration import render_hypothesis_workspace
        render_hypothesis_workspace()
    except Exception as _hyp_err:  # never let the new tab break the rest of the app
        st.warning(f"The Hypotheses tab is unavailable: {{type(_hyp_err).__name__}}: {{_hyp_err}}")
{END}
'''


def patch(src: str) -> Tuple[str, List[Tuple[str, str]]]:
    """Return (new_source, report). Report items are (step, 'applied' | 'already present' | 'MISSING ANCHOR')."""
    if BEGIN in src:
        return src, [("all steps", "already present")]
    report: List[Tuple[str, str]] = []
    lines = src.split("\n")

    # 1. ALL_TAB_NAMES
    m = re.search(r'^(ALL_TAB_NAMES\s*=\s*\[)(.*?)(\])', src, re.M)
    if m and '"Hypotheses"' not in m.group(2):
        inner = m.group(2).rstrip()
        new_inner = inner + ("," if inner else "") + '"Hypotheses"'
        src = src[:m.start()] + m.group(1) + new_inner + m.group(3) + src[m.end():]
        report.append(("add to ALL_TAB_NAMES", "applied"))
        lines = src.split("\n")
    else:
        report.append(("add to ALL_TAB_NAMES", "already present" if m else "MISSING ANCHOR (non-critical)"))

    # 2. force the tab into the visible set
    idx = next((i for i, l in enumerate(lines) if l.startswith("def _tab_visible(")), None)
    if idx is None or "_visible_tab_names" not in src:
        report.append(("force tab visible", "MISSING ANCHOR"))
    else:
        lines[idx:idx] = VISIBLE_BLOCK.split("\n")[:-1]
        report.append(("force tab visible", "applied"))

    # 3. tab variable + block after the last `tabN = _tab_by_name.get(`
    last = None
    for i, l in enumerate(lines):
        mm = re.match(r'^tab(\d+)\s*=\s*_tab_by_name\.get\(', l)
        if mm:
            last = (i, int(mm.group(1)))
    if last is None or "_SinkTab" not in src:
        report.append(("add tab block", "MISSING ANCHOR"))
    else:
        i, n = last
        lines[i + 1:i + 1] = [""] + _tab_block(f"tab{n + 1}").split("\n")[:-1]
        report.append(("add tab block", "applied"))
    return "\n".join(lines), report


def _compiles(text: str) -> bool:
    try:
        compile(text, "app.py", "exec")
        return True
    except SyntaxError:
        return False


def main(argv: List[str]) -> int:
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    path, flags = argv[0], set(argv[1:])
    bak = path + ".bak"
    if "--undo" in flags:
        try:
            shutil.copyfile(bak, path)
        except FileNotFoundError:
            print(f"No backup found at {bak}; nothing to restore.")
            return 2
        print(f"Restored {path} from {bak}.")
        return 0
    try:
        src = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        print(f"File not found: {path}. Run this from your repo root, for example:\n  python protellect_hypothesis/patch_app.py app.py")
        return 2
    new, report = patch(src)
    for step, status in report:
        print(f"  {step}: {status}")
    critical_missing = [s for s, st in report if st.startswith("MISSING ANCHOR") and "non-critical" not in st]
    if critical_missing:
        print("\nNothing was changed: this app.py does not have the expected structure for: " + ", ".join(critical_missing) +
              ".\nSend the file to whoever maintains the integration and they will adapt the patch.")
        return 1
    if new == src:
        print("\nNo changes needed.")
        return 0
    if _compiles(src) and not _compiles(new):
        print("\nNothing was changed: the patched file would not compile. Please report this.")
        return 1
    if "--check" in flags:
        print("\nDry run: nothing written. Run again without --check to apply.")
        return 0
    shutil.copyfile(path, bak)
    open(path, "w", encoding="utf-8").write(new)
    print(f"\nPatched {path}. Backup saved as {bak}. Undo with: python protellect_hypothesis/patch_app.py {path} --undo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
