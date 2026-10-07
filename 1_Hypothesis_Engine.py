"""Streamlit multipage entry: appears as a page next to your main app, with no edits to app.py."""
import streamlit as st

from protellect_hypothesis.streamlit_tab import render_hypothesis_tab

st.set_page_config(page_title="Protellect Hypothesis Engine", layout="wide")
render_hypothesis_tab()
