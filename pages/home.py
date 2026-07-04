from pathlib import Path

import streamlit as st

# ── Logo ──────────────────────────────────────────────────────────────────────

_logo_path = Path(__file__).parent.parent / "assets" / "logo.svg"
_logo_svg = _logo_path.read_text(encoding="utf-8")
st.markdown(_logo_svg, unsafe_allow_html=True)
st.markdown("<div style='margin-top: 4px; color: #6B7280; font-size: 15px;'>"
            "Your AI co-pilot for the full recruitment lifecycle — from brief to placement."
            "</div>", unsafe_allow_html=True)

st.divider()

# ── Getting started ──────────────────────────────────────────────────────────

if not st.session_state.get("api_key"):
    st.warning("**Add your Anthropic API key in the sidebar to get started.** "
               "It's stored in session only — never saved to disk. "
               "Get one at console.anthropic.com.")
else:
    st.success("You're set up. Your name, company, and niche live under "
               "**Your details** in the sidebar — every tool uses them automatically.")

# ── Tools split into BD and Delivery tabs ────────────────────────────────────

bd_tab, delivery_tab = st.tabs(["Business Development", "Delivery"])

with bd_tab:
    st.markdown("Tools to help you win new clients and grow your desk.")
    st.markdown("""
| Tool | What it does |
|------|-------------|
| 🤝 **BD Outreach** | Write targeted messages to potential clients that get replies |
| 🔍 **BD Research & Call Prep** | Full call brief before any BD conversation — grounded in live web search |
| 🗺️ **Market Map Builder** | Identify target companies by role type and location, verified with live search |
""")

with delivery_tab:
    st.markdown("Tools to help you fill roles faster and make better placements.")
    st.markdown("""
| Tool | What it does |
|------|-------------|
| 📋 **CV Screener** | Rank candidates against a JD with a scored, exportable shortlist |
| 🔎 **Boolean Search Builder** | Turn a JD into ready-to-paste LinkedIn, SEEK, and X-ray search strings |
| ✉️ **Candidate Outreach** | Personalised InMail and email messages for candidates |
| 📝 **Candidate Profile Writer** | Turn a raw CV into a polished client-ready profile |
| 📄 **JD Optimizer** | Turn a vague hiring manager brief into a compelling job description |
| 🎤 **Interview Prep Pack** | Candidate-specific prep guide with live company research |
""")

st.divider()
st.caption("Select a tool from the sidebar. Tools that research companies use live web "
           "search — each search costs a fraction of a cent on top of normal token usage.")
