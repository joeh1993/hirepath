import streamlit as st

from utils import (extract_text, friendly_error, generate_streaming,
                   get_api_key, markdown_to_docx, recruiter_details, scrub)

JD_PROMPT = """You are an expert technical recruitment consultant who writes job descriptions that attract strong applicants instead of scaring them off. You are turning a hiring manager's rough brief into a compelling, accurate job description.

ROLE TITLE: {role_title}

HIRING MANAGER BRIEF / NOTES:
{brief}

{existing_jd_section}

COMPANY: {company_info}
SALARY / PACKAGE: {salary}
LOCATION & WORK MODEL: {location}
SENIORITY: {seniority}

Write a complete job description in markdown with these sections (## headings):

## About the Opportunity
2-3 sentences that sell the role. Lead with what makes it interesting - the mission, the problem, the team, the tech - not boilerplate about the company being a leader in its space.

## What You'll Do
5-7 bullets. Outcomes and real work, not vague responsibilities. Start each with a verb.

## What You'll Bring
Split into two lists:
**Must have** - 4-6 bullets maximum. Only things that would truly disqualify a candidate if missing. Years-of-experience numbers only if they matter.
**Nice to have** - 2-4 bullets. Everything else goes here or gets cut.

## Why Join
3-5 bullets covering the genuine sell: package, flexibility, growth, tech, team, mission. Use the salary information if provided - ads with salary ranges get significantly more applicants.

## How to Apply
One short, low-friction closing paragraph.

CRITICAL RULES:
- Never use em dashes or double hyphens
- Never use the words "genuinely", "leverage", "rockstar", "ninja", "guru", "wizard"
- No "fast-paced environment", "wear many hats", "work hard play hard", "like a family"
- Avoid laundry lists - a JD with 15 requirements filters out great candidates, especially women, who tend to apply only when they meet every listed requirement
- Use inclusive, plain language. Write at the candidate, not about "the successful applicant"
- Be honest - do not oversell or invent perks not mentioned in the brief
- If the brief is missing something important (e.g. no salary), note it at the very end under "## Notes for the recruiter" with suggestions, so it can be fixed before posting"""


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("📄 JD Optimizer")
st.markdown("Turn a vague hiring manager brief into a compelling, accurate job description.")

api_key = get_api_key()
_, recruiter_company, _ = recruiter_details()

st.divider()

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("The Brief")

    role_title = st.text_input(
        "Role title",
        placeholder="e.g. Senior Security Engineer"
    )

    brief = st.text_area(
        "Hiring manager brief / your notes from the qualification call",
        height=250,
        placeholder="e.g. Needs someone to own cloud security for their AWS estate. Team of 3, reporting to Head of Security. Must know Terraform. They keep losing candidates to fintechs, want to move fast. Budget around $190k..."
    )

    uploaded = st.file_uploader(
        "Existing JD to improve (optional)",
        type=["pdf", "docx", "txt"],
        help="Upload the client's current JD and it will be rewritten rather than started from scratch."
    )
    existing_jd = ""
    if uploaded:
        existing_jd = extract_text(uploaded)
        st.caption(f"Extracted {len(existing_jd)} characters from {uploaded.name}")

with col_right:
    st.subheader("Role Details")

    company_info = st.text_area(
        "About the company (1-2 lines)",
        height=80,
        placeholder="e.g. ASX-listed health tech, ~800 staff, Sydney CBD. Security team of 6."
    )

    salary = st.text_input(
        "Salary / package (strongly recommended)",
        placeholder="e.g. $180-200k + super + bonus"
    )

    location = st.text_input(
        "Location & work model",
        placeholder="e.g. Sydney CBD, hybrid 2 days in office"
    )

    seniority = st.selectbox(
        "Seniority",
        ["Junior", "Mid-level", "Senior", "Lead / Manager", "Executive"]
    , index=2)

st.divider()

run = st.button("Write Job Description", type="primary", use_container_width=True)

if run:
    if not api_key:
        st.error("Add your Anthropic API key in the sidebar first.")
        st.stop()
    if not role_title.strip():
        st.error("Enter the role title.")
        st.stop()
    if not brief.strip() and not existing_jd.strip():
        st.error("Paste the hiring manager brief (or upload an existing JD).")
        st.stop()

    existing_jd_section = (
        f"EXISTING JD TO IMPROVE (keep accurate facts, fix the writing):\n{existing_jd[:15000]}"
        if existing_jd.strip() else
        "No existing JD - write from the brief."
    )

    prompt = JD_PROMPT.format(
        role_title=role_title,
        brief=brief or "See existing JD.",
        existing_jd_section=existing_jd_section,
        company_info=company_info or "Not specified - keep company description generic.",
        salary=salary or "Not provided",
        location=location or "Not specified",
        seniority=seniority,
    )

    st.caption("Writing the JD - it streams in below.")
    placeholder = st.empty()
    try:
        jd_text = generate_streaming(api_key, prompt, placeholder, max_tokens=3000)
    except Exception as e:
        st.error(friendly_error(e))
        st.stop()

    st.session_state.jd_result = {"jd": scrub(jd_text), "role_title": role_title}

# ── Results (persist across reruns) ──────────────────────────────────────────

state = st.session_state.get("jd_result")
if state:
    jd_text = state["jd"]
    role_title = state["role_title"]

    st.divider()
    st.subheader(f"Job Description: {role_title}")

    view_tab, copy_tab = st.tabs(["Preview", "Copy as text"])
    with view_tab:
        st.markdown(jd_text)
    with copy_tab:
        st.code(jd_text, language=None, wrap_lines=True)

    docx_bytes = markdown_to_docx(jd_text, role_title)
    st.download_button(
        "⬇️ Download Word (.docx)",
        data=docx_bytes,
        file_name=f"JD_{role_title.replace(' ', '_')}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="primary",
    )
