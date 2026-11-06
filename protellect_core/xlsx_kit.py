"""One small Excel builder used by every report in the app.

Why it exists: each report used to hand-roll its own workbook, and the results were patchy (blank sheets, columns
that repeated each other, numbers saved as text, no explanation of what a sheet was). Every workbook built here has:

* a Contents sheet first (what each sheet is, how many rows, and whether it is empty and why);
* a title and a one-line "what this sheet is" on every sheet, and a link back to Contents;
* a filterable header row, frozen panes, wrapped text, real numbers (not text) and clickable links;
* NO blank sheets: an empty table says why it is empty, instead of showing only headers;
* a final "Limits" block, so a reader who only opens the file still sees what the numbers do and do not mean.

Nothing here computes science. It only lays out what the callers give it.
"""
from __future__ import annotations

import datetime as _dt
import io
import math
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

NAVY = "1F3A5F"
GREY = "F2F4F7"
MID = "D0D7E2"
_HDR_FILL = PatternFill("solid", fgColor=NAVY)
_BAND = PatternFill("solid", fgColor=GREY)
_WRAP = Alignment(wrap_text=True, vertical="top")
_THIN = Side(style="thin", color="D9DEE7")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_BAD_SHEET = re.compile(r"[\[\]:*?/\\]")

# colour words used by several reports; callers pass the key, never a hex
FILLS = {
    "good": "D8EFD3", "ok": "E8F3D6", "warn": "FFF0B3", "bad": "F8D2D2", "none": "E4E7EC", "info": "DCE9F7",
}
TIER_FILL = {"Strong": FILLS["good"], "Mixed": FILLS["warn"], "Weak": "F9D9BE", "Contradicted": FILLS["bad"], "Unchecked": FILLS["none"]}


def clean(v: Any) -> Any:
    """Make any value safe for a cell: real numbers stay numbers, NaN becomes empty, control characters are removed."""
    if v is None:
        return None
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(v, (int,)):
        return v
    if isinstance(v, (_dt.datetime, _dt.date)):
        return v
    try:                                   # numpy / pandas scalars
        import numpy as _np
        if isinstance(v, _np.generic):
            return clean(v.item())
    except Exception:                      # noqa: BLE001
        pass
    if isinstance(v, (list, tuple, set)):
        return "; ".join(str(clean(x)) for x in v if clean(x) not in (None, ""))
    if isinstance(v, dict):
        return "; ".join(f"{k}: {clean(x)}" for k, x in v.items())
    s = _ILLEGAL.sub("", str(v))
    return s[:32000]                       # Excel's cell limit is 32,767 characters


def _put(ws, row: int, col: int, v: Any):
    v = clean(v)
    c = ws.cell(row=row, column=col, value=v)
    if isinstance(v, str) and v.startswith("="):          # text that looks like a formula must stay text
        c.data_type = "s"
    return c


def _sheet_name(wb, name: str) -> str:
    base = _BAD_SHEET.sub(" ", name).strip()[:31] or "Sheet"
    n, i = base, 2
    while n in wb.sheetnames:
        suffix = f" {i}"
        n = base[: 31 - len(suffix)] + suffix
        i += 1
    return n


def _est_height(text: str, width_chars: float, line: float = 15.0) -> float:
    lines = 0
    for part in str(text).split("\n"):
        lines += max(1, math.ceil(len(part) / max(width_chars, 1)))
    return min(409.0, max(18.0, lines * line))


class Book:
    def __init__(self, title: str, subtitle: str = "", status: str = ""):
        self.title, self.subtitle, self.status = title, subtitle, status
        self.wb = Workbook()
        self.contents = self.wb.active
        self.contents.title = "Contents"
        self.entries: List[dict] = []
        self.omitted: List[tuple] = []
        self.limits: List[str] = []
        self.made = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ── sheet frame ───────────────────────────────────────────────────────────────────────────
    def _frame(self, name: str, title: str, intro: str, ncols: int, widths: Optional[Sequence[float]]):
        ws = self.wb.create_sheet(_sheet_name(self.wb, name))
        ws.sheet_view.showGridLines = False
        ncols = max(ncols, 2)
        for i in range(1, ncols + 1):
            w = (widths[i - 1] if widths and i - 1 < len(widths) else 18)
            ws.column_dimensions[get_column_letter(i)].width = w
        total_w = sum((widths[i] if widths and i < len(widths) else 18) for i in range(ncols))
        c = _put(ws, 1, 1, title)
        c.font = Font(bold=True, size=14, color=NAVY)
        ws.row_dimensions[1].height = 24
        back = ws.cell(row=1, column=ncols, value="< Contents")
        back.hyperlink = f"#'Contents'!A1"
        back.font = Font(color="0563C1", underline="single", size=10)
        back.alignment = Alignment(horizontal="right")
        if intro:
            _put(ws, 2, 1, intro).alignment = _WRAP
            ws.cell(row=2, column=1).font = Font(italic=True, color="555555", size=10)
            ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
            ws.row_dimensions[2].height = _est_height(intro, total_w * 1.05)
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        return ws

    def _register(self, ws, what: str, n: int, status: str = "", group: str = ""):
        self.entries.append({"sheet": ws.title, "what": what, "n": n, "status": status, "group": group})

    # ── tables ────────────────────────────────────────────────────────────────────────────────
    def table(self, name: str, title: str, intro: str, columns: Sequence[str], rows: Iterable[Sequence[Any]], widths: Optional[Sequence[float]] = None,
              link_cols: Sequence[int] = (), fill_col: Optional[int] = None, fill_map: Optional[Dict[str, str]] = None,
              number_formats: Optional[Dict[int, str]] = None, empty: str = "", what: str = "", group: str = "",
              row_fill: Optional[Callable[[Sequence[Any]], Optional[str]]] = None) -> Any:
        """A filterable table. `empty` is the reason shown when there are no rows (so the sheet is never just headers)."""
        rows = [list(r) for r in rows]
        ws = self._frame(name, title, intro, len(columns), widths)
        hr = 4
        for j, h in enumerate(columns, 1):
            c = _put(ws, hr, j, h)
            c.font, c.fill, c.alignment, c.border = Font(bold=True, color="FFFFFF"), _HDR_FILL, Alignment(wrap_text=True, vertical="center"), _BORDER
        ws.row_dimensions[hr].height = 30
        if not rows:
            msg = empty or "Nothing to show here."
            c = _put(ws, hr + 1, 1, "Empty: " + msg)
            c.alignment = _WRAP
            c.font = Font(italic=True, color="7A4B00")
            ws.merge_cells(start_row=hr + 1, start_column=1, end_row=hr + 1, end_column=len(columns))
            ws.row_dimensions[hr + 1].height = _est_height(msg, sum((widths[i] if widths and i < len(widths) else 18) for i in range(len(columns))))
            self._register(ws, what or title, 0, "empty: " + msg, group)
            ws.freeze_panes = ws.cell(row=hr + 1, column=1)
            return ws
        for i, r in enumerate(rows):
            rr = hr + 1 + i
            rf = row_fill(r) if row_fill else None
            for j, v in enumerate(r, 1):
                c = _put(ws, rr, j, v)
                c.alignment, c.border = _WRAP, _BORDER
                if rf:
                    c.fill = PatternFill("solid", fgColor=rf)
                elif i % 2 == 1:
                    c.fill = _BAND
                if (j - 1) in link_cols and isinstance(c.value, str) and c.value.startswith("http"):
                    c.hyperlink = c.value
                    c.font = Font(color="0563C1", underline="single")
                if number_formats and (j - 1) in number_formats and isinstance(c.value, (int, float)):
                    c.number_format = number_formats[j - 1]
            if fill_col is not None and fill_map:
                key = str(r[fill_col]).lower() if r[fill_col] is not None else ""
                for k, hexv in fill_map.items():
                    if k.lower() in key:
                        ws.cell(row=rr, column=fill_col + 1).fill = PatternFill("solid", fgColor=hexv)
                        ws.cell(row=rr, column=fill_col + 1).font = Font(bold=True)
                        break
        ws.freeze_panes = ws.cell(row=hr + 1, column=1)
        ws.auto_filter.ref = f"A{hr}:{get_column_letter(len(columns))}{hr + len(rows)}"
        self._register(ws, what or title, len(rows), "", group)
        return ws

    def kv(self, name: str, title: str, intro: str, rows: Iterable[Sequence[Any]], columns: Sequence[str] = ("Item", "Value", "Source or note"),
           widths: Sequence[float] = (34, 70, 60), fills: Optional[Dict[int, str]] = None, what: str = "", group: str = "") -> Any:
        """Field / value pairs. `fills` maps a 0-based row index to a fill key from FILLS or a hex colour."""
        rows = [list(r) + [""] * (len(columns) - len(r)) for r in rows]
        ws = self.table(name, title, intro, columns, rows, widths=widths, what=what, group=group, empty="No fields.")
        for i, r in enumerate(rows):
            ws.cell(row=5 + i, column=1).font = Font(bold=True)
            ws.cell(row=5 + i, column=2).alignment = Alignment(wrap_text=True, vertical="top", horizontal="left")
        for idx, key in (fills or {}).items():
            ws.cell(row=5 + idx, column=2).fill = PatternFill("solid", fgColor=FILLS.get(key, TIER_FILL.get(key, key)))
            ws.cell(row=5 + idx, column=2).font = Font(bold=True)
        ws.auto_filter.ref = None
        return ws

    def text(self, name: str, title: str, intro: str, blocks: Iterable[Sequence[str]], columns: Sequence[str] = ("Topic", "Text"),
             widths: Sequence[float] = (30, 130), what: str = "", group: str = "") -> Any:
        blocks = [list(b) for b in blocks]
        ws = self.table(name, title, intro, columns, blocks, widths=widths, what=what, group=group, empty="No text.")
        ws.auto_filter.ref = None
        for i in range(len(blocks)):
            ws.cell(row=5 + i, column=1).font = Font(bold=True)
        return ws

    def omit(self, what: str, why: str) -> None:
        self.omitted.append((what, why))

    def limit(self, text: str) -> None:
        self.limits.append(text)

    # ── finish ────────────────────────────────────────────────────────────────────────────────
    def to_bytes(self) -> bytes:
        ws = self.contents
        ws.sheet_view.showGridLines = False
        for col, w in zip("ABCDE", (30, 78, 9, 52, 4)):
            ws.column_dimensions[col].width = w
        _put(ws, 1, 1, self.title).font = Font(bold=True, size=16, color=NAVY)
        ws.row_dimensions[1].height = 26
        r = 2
        for line in (self.subtitle, f"Generated {self.made}", self.status):
            if line:
                _put(ws, r, 1, line).alignment = _WRAP
                ws.cell(row=r, column=1).font = Font(italic=(r > 2), color="555555", size=10)
                ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
                ws.row_dimensions[r].height = _est_height(line, 150)
                r += 1
        r += 1
        for j, h in enumerate(("Sheet (click to open)", "What is in it", "Rows", "Status"), 1):
            c = _put(ws, r, j, h)
            c.font, c.fill, c.border = Font(bold=True, color="FFFFFF"), _HDR_FILL, _BORDER
        hdr_row = r
        r += 1
        group = None
        for e in self.entries:
            if e["group"] != group and e["group"]:
                group = e["group"]
                g = _put(ws, r, 1, group)
                g.font, g.fill = Font(bold=True, color=NAVY), PatternFill("solid", fgColor=MID)
                for j in range(2, 5):
                    ws.cell(row=r, column=j).fill = PatternFill("solid", fgColor=MID)
                r += 1
            c = _put(ws, r, 1, e["sheet"])
            c.hyperlink = f"#'{e['sheet']}'!A1"
            c.font = Font(color="0563C1", underline="single")
            _put(ws, r, 2, e["what"]).alignment = _WRAP
            _put(ws, r, 3, e["n"])
            st = _put(ws, r, 4, e["status"] or "ok")
            st.alignment = _WRAP
            if e["status"]:
                st.fill = PatternFill("solid", fgColor=FILLS["warn"])
            for j in range(1, 5):
                ws.cell(row=r, column=j).border = _BORDER
                ws.cell(row=r, column=j).alignment = _WRAP
            ws.row_dimensions[r].height = max(_est_height(e["what"], 82), _est_height(e["status"] or "ok", 54))
            r += 1
        ws.freeze_panes = ws.cell(row=hdr_row + 1, column=1)
        for title, items in (("Not in this report, and why", [f"{a}: {b}" for a, b in self.omitted]), ("Read this before using any number", self.limits)):
            if not items:
                continue
            r += 1
            h = _put(ws, r, 1, title)
            h.font = Font(bold=True, color=NAVY, size=12)
            r += 1
            for it in items:
                _put(ws, r, 1, it).alignment = _WRAP
                ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
                ws.row_dimensions[r].height = _est_height(it, 160)
                r += 1
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        self.wb.active = 0
        bio = io.BytesIO()
        self.wb.save(bio)
        return bio.getvalue()
