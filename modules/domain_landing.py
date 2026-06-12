# modules/domain_landing.py
from __future__ import annotations
import streamlit as st
from modules.config import DOMAIN_STYLES, RESEARCH_DOMAINS
from modules.domain_workspaces import (
    render_oncology_workspace, render_neuroscience_workspace, render_microbiome_workspace,
    render_pharma_workspace, render_molbio_workspace, render_rare_disease_workspace
)

def handle_domain_landing(domain: str, pdata: dict, search_trigger: bool):
    """Show domain-specific landing page when no protein is loaded."""
    if domain and not pdata and not search_trigger:
        domain_handlers = {
            "Oncology": render_oncology_workspace,
            "Neuroscience": render_neuroscience_workspace,
            "Microbiome": render_microbiome_workspace,
            "Pharmaceuticals": render_pharma_workspace,
            "Molecular Biology": render_molbio_workspace,
            "Rare Disease": render_rare_disease_workspace,
        }
        handler = domain_handlers.get(domain)
        if handler:
            handler()
            st.stop()
