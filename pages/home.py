import streamlit as st
from pathlib import Path

# Persist API key across page navigations
# On Streamlit Cloud the key is pre-loaded from secrets; locally the user enters it below
if "api_key" not in st.session_state:
    try:
        st.session_state.api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        st.session_state.api_key = ""

# ── Logo ──────────────────────────────────────────────────────────────────────

_logo_path = Path(__file__).parent.parent / "assets" / "logo.svg"
_logo_svg  = _logo_path.read_text(encoding="utf-8")
st.markdown(_logo_svg, unsafe_allow_html=True)
st.markdown("<div style='margin-top: 4px; color: #6B7280; font-size: 15px;'>"
            "Your AI co-pilot for the full recruitment lifecycle — from brief to placement."
            "</div>", unsafe_allow_html=True)

st.divider()

# ── API Key ──────────────────────────────────────────────────────────────────

st.markdown("### API Key")
key = st.text_input(
    "Anthropic API Key",
    value=st.session_state.api_key,
    type="password",
    help="Stored in session only — never saved to disk. Get yours at console.anthropic.com"
)
if key:
    st.session_state.api_key = key
    st.success("Key saved for this session")

st.divider()

# ── Tools split into BD and Delivery tabs ────────────────────────────────────

bd_tab, delivery_tab = st.tabs(["Business Development", "Delivery"])

with bd_tab:
    st.markdown("Tools to help you win new clients and grow your desk.")
    st.markdown("""
| Tool | What it does | Status |
|------|-------------|--------|
| 🤝 **BD Outreach** | Write targeted messages to potential clients that get replies | ✅ Ready |
| 🔍 **BD Research & Call Prep** | Full call brief before any BD conversation | ✅ Ready |
| 🗺️ **Market Map Builder** | Identify target companies by tech stack and location | ✅ Ready |
""")

with delivery_tab:
    st.markdown("Tools to help you fill roles faster and make better placements.")
    st.markdown("""
| Tool | What it does | Status |
|------|-------------|--------|
| 📋 **CV Screener** | Rank candidates against a JD with a scored shortlist | ✅ Ready |
| ✉️ **Candidate Outreach** | Personalised InMail and email messages for candidates | ✅ Ready |
| 📝 **Candidate Profile Writer** | Turn a raw CV into a polished client-ready profile | ✅ Ready |
| 📄 **JD Optimizer** | Turn a vague brief into a compelling job description | 🔜 Coming soon |
| 🎤 **Interview Prep Pack** | Candidate-specific prep guide to increase offer rates | ✅ Ready |
""")

st.divider()
st.caption("Select a tool from the sidebar. Set your API key above before using any tool.")
