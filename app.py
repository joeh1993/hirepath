import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="HirePath",
    page_icon="🛤️",
    layout="wide"
)

# ── Sidebar logo (shown on every page) ───────────────────────────────────────

_LOGO_COMPACT = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 190 46" width="170">
  <rect x="0" y="3" width="40" height="40" rx="9" fill="#1A56DB"/>
  <line x1="9" y1="35" x2="31" y2="12" stroke="white" stroke-width="2" stroke-linecap="round" opacity="0.55"/>
  <circle cx="9"  cy="35" r="4"   fill="white" opacity="0.85"/>
  <circle cx="20" cy="23.5" r="3.5" fill="white"/>
  <circle cx="31" cy="12" r="5"   fill="#93C5FD"/>
  <circle cx="31" cy="12" r="2.5" fill="white"/>
  <text x="50" y="30"
        font-family="'Segoe UI','Inter',Arial,sans-serif"
        font-size="23" font-weight="800" fill="#1E3A5F">Hire</text>
  <text x="104" y="30"
        font-family="'Segoe UI','Inter',Arial,sans-serif"
        font-size="23" font-weight="800" fill="#1A56DB">Path</text>
</svg>
"""

st.sidebar.markdown(_LOGO_COMPACT, unsafe_allow_html=True)
st.sidebar.markdown("<hr style='margin: 6px 0 10px 0; border-color: #E5E7EB;'>",
                    unsafe_allow_html=True)

# ── Pages ────────────────────────────────────────────────────────────────────

home        = st.Page("pages/home.py",               title="Home",                    icon="🏠", default=True)

bd_outreach = st.Page("pages/bd_outreach.py",        title="BD Outreach",             icon="🤝")
bd_research = st.Page("pages/bd_research.py",        title="BD Research & Call Prep", icon="🔍")
market_map  = st.Page("pages/market_map.py",         title="Market Map Builder",      icon="🗺️")

cv_screener     = st.Page("pages/cv_screener.py",       title="CV Screener",             icon="📋")
cand_outreach   = st.Page("pages/candidate_outreach.py",title="Candidate Outreach",      icon="✉️")
cand_profile    = st.Page("pages/candidate_profile.py", title="Candidate Profile Writer",icon="📝")
jd_optimizer    = st.Page("pages/jd_optimizer.py",      title="JD Optimizer",            icon="📄")
interview_prep  = st.Page("pages/interview_prep.py",    title="Interview Prep Pack",     icon="🎤")

# ── Navigation ───────────────────────────────────────────────────────────────

pg = st.navigation({
    "":                     [home],
    "Business Development": [bd_outreach, bd_research, market_map],
    "Delivery":             [cv_screener, cand_outreach, cand_profile, jd_optimizer, interview_prep],
})

pg.run()
