"""One place that embeds an HTML page in the app.

Streamlit has deprecated st.components.v1.html in favour of st.iframe. Use the old call where it still works (every older
Streamlit) and fall back to st.iframe where it has been removed, so the 3D viewer, the signalling player and the cascade
animation keep working across versions.
"""
from __future__ import annotations

import streamlit as st


def html_frame(markup: str, height: int = 300) -> None:
    try:
        import streamlit.components.v1 as components
        components.html(markup, height=height, scrolling=False)
        return
    except (AttributeError, ImportError, NotImplementedError):
        pass
    except Exception:
        # an unexpected failure in the old call: try the new one rather than lose the panel
        pass
    iframe = getattr(st, "iframe", None)
    if iframe is None:
        st.warning("This Streamlit version cannot embed the interactive panel. Upgrade Streamlit.")
        return
    iframe(markup, height=max(int(height), 1))
