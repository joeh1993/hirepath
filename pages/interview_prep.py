import streamlit as st

from utils import (WEB_SEARCH_TOOL, friendly_error, generate_streaming,
                   get_api_key, markdown_to_docx, paste_or_upload, scrub)

PREP_PROMPT = """You are an expert technical recruitment consultant specialising in cyber security roles across the Australian market, particularly Sydney. You are preparing a candidate for an interview and your goal is to maximise their chance of receiving an offer.

Use the information below to build a thorough, personalised interview prep pack.

CANDIDATE CV:
{cv}

ROLE / JOB DESCRIPTION:
{jd}

COMPANY NAME: {company}
INTERVIEW STAGE: {stage}
INTERVIEWER(S): {interviewers}

You have web search available. USE IT before writing:
- Search for {company}'s recent news, funding, acquisitions, incidents, and public statements
- Search for what {company} employees or reviews say about their interview process and culture
- Search for current salary data for this role type in the Australian market
Base the company snapshot and salary coaching on what you actually find. If a search turns up nothing, say so rather than inventing detail.

Produce a prep pack with ALL of the following sections. Use clear markdown headings (## for each section). Be specific - generic advice is useless.

## 1. Company Snapshot
- What the company does, their core business, size, and market position
- RECENT news, funding, acquisitions, or notable achievements (from your searches, with rough dates)
- Culture, values, and what they typically look for in people
- Why cyber security matters specifically to this company

## 2. Role Breakdown
- What this role is actually trying to achieve (not just what the JD says)
- The 3-5 things that will make or break success in the first 90 days
- Any red flags or gaps the candidate should be ready to address

## 3. Likely Technical Questions
List 8-10 technical questions the interviewer is likely to ask, tailored to the role and cyber security niche. For each:
- The question
- Why they are asking it (what they want to hear)
- A strong answer framework the candidate can use

## 4. Likely Behavioural Questions
List 5-6 behavioural questions using STAR format. For each:
- The question
- A suggested talking point pulled directly from the candidate's CV
- What a great answer demonstrates

## 5. Candidate Talking Points
Based on the CV, pull out 4-5 specific achievements or experiences the candidate should weave into the conversation. Frame each as a story the candidate can tell, not a bullet point.

## 6. Questions to Ask the Interviewer
Provide 6-8 sharp, intelligent questions the candidate should ask. Split into:
- Questions about the role and team
- Questions about the company's security posture and challenges
- Questions that subtly demonstrate expertise

## 7. Salary and Negotiation Coaching
- Realistic salary range for this role in the Australian market, based on current data from your searches (cite the source and note it's indicative)
- How and when to raise salary in the conversation
- How to respond if they ask "what are you looking for?" before an offer
- How to negotiate if the first offer is below expectations
- One or two lines to use verbatim

Do not use em dashes anywhere in your response. Do not use the word "genuinely". Be direct, practical, and specific to this candidate and role."""

SECTION_ICONS = {"1": "🏢", "2": "🎯", "3": "💻", "4": "🗣️", "5": "⭐", "6": "❓", "7": "💰"}


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("🎤 Interview Prep Pack")
st.markdown("A candidate-specific prep guide: **live company research**, likely questions, "
            "talking points, and salary coaching.")

api_key = get_api_key()

st.divider()

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Candidate CV")
    cv_content = paste_or_upload(
        "Candidate CV",
        key="prep_cv",
        height=250,
        placeholder="Paste the candidate's CV content...",
        upload_hint="Drop the candidate's CV - PDF and DOCX work best",
    )

    st.subheader("Interview Details")

    company = st.text_input(
        "Company name",
        placeholder="e.g. CrowdStrike, Telstra Security, ANZ Bank"
    )

    stage = st.selectbox(
        "Interview stage",
        options=[
            "First round (recruiter / hiring manager screen)",
            "Technical interview",
            "Panel interview",
            "Final round / executive interview",
            "Culture fit interview",
        ]
    )

    interviewers = st.text_input(
        "Who are they meeting? (optional)",
        placeholder="e.g. Head of Security, Lead SOC Analyst, CTO"
    )

with col_right:
    st.subheader("Role / Job Description")
    jd = paste_or_upload(
        "Job description",
        key="prep_jd",
        height=430,
        placeholder="Paste the full job description. The more detail, the better the prep pack.",
        upload_hint="Drop the JD as a PDF, Word, or text file",
    )

st.divider()

run = st.button("Generate Prep Pack", type="primary", use_container_width=True)

if run:
    if not api_key:
        st.error("Add your Anthropic API key in the sidebar first.")
        st.stop()

    if not cv_content:
        st.error("Provide the candidate's CV: drop a file or paste the text.")
        st.stop()
    if not jd.strip():
        st.error("Add the job description first - drop a file or paste it.")
        st.stop()
    if not company.strip():
        st.error("Enter the company name.")
        st.stop()

    prompt = PREP_PROMPT.format(
        cv=cv_content[:30000],
        jd=jd[:10000],
        company=company.strip(),
        stage=stage,
        interviewers=interviewers if interviewers.strip() else "Not specified",
    )

    st.caption(f"Researching {company.strip()} with live web search and building the pack - "
               "this takes 1-2 minutes. It streams in below as it's written.")
    placeholder = st.empty()
    try:
        result = generate_streaming(api_key, prompt, placeholder,
                                    max_tokens=8192, tools=[WEB_SEARCH_TOOL])
    except Exception as e:
        st.error(friendly_error(e))
        st.stop()

    st.session_state.prep_result = {
        "result": scrub(result), "company": company.strip(), "stage": stage,
    }

# ── Results (persist across reruns) ──────────────────────────────────────────

state = st.session_state.get("prep_result")
if state:
    result = state["result"]
    company = state["company"]
    stage = state["stage"]

    st.success("Prep pack ready!")
    st.divider()

    safe_name = company.replace(" ", "_")
    docx_bytes = markdown_to_docx(result, "Interview Prep Pack", f"{company}   |   {stage}")

    dl_col1, dl_col2, _ = st.columns([1, 1, 2])
    with dl_col1:
        st.download_button(
            label="⬇️ Download Word (.docx)",
            data=docx_bytes,
            file_name=f"{safe_name}_interview_prep.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            type="primary",
        )
    with dl_col2:
        st.download_button(
            label="⬇️ Download plain text",
            data=result,
            file_name=f"{safe_name}_interview_prep.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.divider()

    # Render each ## section as an expander
    sections = []
    current_heading = None
    current_lines: list[str] = []
    for line in result.split("\n"):
        if line.startswith("## "):
            if current_heading is not None:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_heading is not None:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    for heading, content in sections:
        num = heading.split(".")[0].strip() if "." in heading else ""
        icon = SECTION_ICONS.get(num, "📌")
        with st.expander(f"{icon} {heading}", expanded=True):
            st.markdown(content)
