import json

import streamlit as st

from utils import (extract_json, friendly_error, generate, get_api_key,
                   paste_or_upload)

BOOLEAN_PROMPT = """You are an expert technical sourcer. Build boolean search strings for finding candidates for the role below.

ROLE / JOB DESCRIPTION:
{jd}

EXTRA GUIDANCE FROM THE RECRUITER: {guidance}

Think carefully about:
- Job title variations and synonyms candidates actually use on their profiles (e.g. "DevSecOps" vs "Security Engineer, CI/CD")
- Skill and tool synonyms, certifications, and adjacent terms
- Terms that should be EXCLUDED to cut noise (recruiters, sales, students where appropriate)

Return a JSON object in EXACTLY this format. No preamble, no markdown fences:

{{
  "role_summary": "One sentence on the target candidate",
  "title_variations": ["title 1", "title 2", "..."],
  "core_skills": ["skill 1", "skill 2", "..."],
  "strings": {{
    "linkedin_broad": "Boolean string for LinkedIn Recruiter keyword search. Wider net - titles OR'd with core skills. LinkedIn supports AND, OR, NOT, quotes, parentheses.",
    "linkedin_precise": "Tighter LinkedIn Recruiter string - must-have skills AND'd, exclusions with NOT.",
    "seek": "String for SEEK Talent Search. SEEK supports AND, OR, NOT, quotes, parentheses - keep it shorter than the LinkedIn strings.",
    "google_xray": "Google X-ray string for LinkedIn profiles, e.g. site:linkedin.com/in (\\"...\\" OR \\"...\\") ... - include a location term."
  }},
  "tips": [
    "2-4 short tips specific to sourcing this role type - where these candidates hang out, terms to try if results are thin, etc."
  ]
}}

Rules:
- Quote multi-word phrases
- Balance parentheses carefully - these must paste in and just work
- Assume the Australian market unless the JD says otherwise
- Do not use em dashes anywhere"""


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("🔎 Boolean Search Builder")
st.markdown("Paste a JD, get ready-to-paste search strings for LinkedIn Recruiter, "
            "SEEK Talent Search, and Google X-ray.")

api_key = get_api_key()

st.divider()

jd = paste_or_upload(
    "Job description or role summary",
    key="bool_jd",
    height=280,
    placeholder="Paste the full JD, or just describe the role: e.g. Senior DevSecOps engineer, AWS + Kubernetes + Terraform, needs CI/CD security experience, Sydney, no clearance required...",
    upload_hint="Drop the JD as a PDF, Word, or text file",
)

guidance = st.text_input(
    "Anything to emphasise or exclude? (optional)",
    placeholder="e.g. must have financial services background; exclude contractors; open to Melbourne-based"
)

run = st.button("Build Search Strings", type="primary", use_container_width=True)

if run:
    if not api_key:
        st.error("Add your Anthropic API key in the sidebar first.")
        st.stop()
    if not jd.strip():
        st.error("Add a JD or role summary first - drop a file or paste it.")
        st.stop()

    with st.spinner("Building search strings..."):
        try:
            raw = generate(api_key, BOOLEAN_PROMPT.format(
                jd=jd[:10000], guidance=guidance or "None"), max_tokens=2048)
            data = extract_json(raw)
        except json.JSONDecodeError:
            st.error("Claude returned output that couldn't be parsed. Try again.")
            st.stop()
        except Exception as e:
            st.error(friendly_error(e))
            st.stop()

    st.session_state.boolean_result = data

# ── Results (persist across reruns) ──────────────────────────────────────────

data = st.session_state.get("boolean_result")
if data:
    st.divider()
    if data.get("role_summary"):
        st.info(data["role_summary"])

    strings = data.get("strings", {})
    labels = [
        ("linkedin_broad", "LinkedIn Recruiter — broad"),
        ("linkedin_precise", "LinkedIn Recruiter — precise"),
        ("seek", "SEEK Talent Search"),
        ("google_xray", "Google X-ray"),
    ]
    for key, label in labels:
        if strings.get(key):
            st.markdown(f"**{label}**")
            st.code(strings[key], language=None, wrap_lines=True)

    c1, c2 = st.columns(2)
    with c1:
        if data.get("title_variations"):
            st.markdown("**Title variations**")
            for t in data["title_variations"]:
                st.markdown(f"- {t}")
    with c2:
        if data.get("core_skills"):
            st.markdown("**Core skills & synonyms**")
            for s in data["core_skills"]:
                st.markdown(f"- {s}")

    if data.get("tips"):
        with st.expander("💡 Sourcing tips for this role", expanded=True):
            for tip in data["tips"]:
                st.markdown(f"- {tip}")
