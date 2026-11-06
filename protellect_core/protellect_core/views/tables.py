"""Short tables are sized to their rows. A dataframe with its own scrollbar captures the mouse wheel, so a short table that scrolls inside itself makes the page feel stuck."""
from __future__ import annotations

import streamlit as st

_ROW, _HEAD, _MAX_ROWS, _CAP = 35, 38, 14, 350
_installed = False


def install() -> None:
    global _installed
    if _installed or getattr(st.dataframe, "_protellect", False):
        return
    orig = st.dataframe

    def dataframe(data=None, *a, **k):
        if "height" not in k:
            try:
                n = len(data)
            except TypeError:
                n = None
            if n is not None:
                k["height"] = _HEAD + _ROW * max(n, 1) if n <= _MAX_ROWS else _CAP
        return orig(data, *a, **k)

    dataframe._protellect = True
    st.dataframe = dataframe
    _installed = True
