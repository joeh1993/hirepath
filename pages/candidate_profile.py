import streamlit as st

from utils import (friendly_error, generate, get_api_key, markdown_to_docx,
                   paste_or_upload, scrub)

PROFILE_PROMPT = """You are an expert technical recruitment consultant writing a candidate profile to send to a hiring client. Your profiles are known for being sharp, honest, and compelling - they make clients want to meet the candidate.

RAW CV / CANDIDATE INFORMATION:
{cv_text}

{role_section}

{notes_section}

FORMAT: {format_type}
TONE: {tone}

Write a polished candidate profile based on the above. The profile should:
1. Open with a strong one-sentence overview of who this person is (their level, specialism, and standout quality)
2. Cover their career trajectory and most relevant experience concisely
3. Highlight 2-3 real achievements or strengths with specifics where possible
4. {role_fit_instruction}
5. Close with their motivation for moving and availability if known

CRITICAL RULES:
- Never use em dashes or double hyphens
- Never use the words "genuinely" or "leverage"
- Never use "passionate" or "passionate about"
- Never use "strong communication skills"
- Never use "team player"
- Never use "results-driven"
- No cliches or filler phrases
- Write in third person (e.g. "Joel brings..." not "I bring...")
- Be specific - vague profiles get ignored

{format_instructions}

After the profile, add a short section:

KEY STATS:
- Current role: [extract from CV]
- Years experience: [estimate]
- Location: [extract from CV]
- Availability: {availability}
- Salary expectations: {salary}"""

FORMAT_INSTRUCTIONS = {
    "Email submission (paragraphs)": (
        "Write 2-3 flowing paragraphs. No headers or bullet points. Should paste cleanly into an email body.",
        "Comment on their fit for the specific role and why you are putting them forward."
    ),
    "Formal submission (structured)": (
        "Use clear headers: Overview, Career Background, Key Strengths, Role Fit. Under each header write in prose, not bullets.",
        "Include a dedicated 'Role Fit' section explaining why this candidate suits the specific opportunity."
    ),
    "Short brief (5-6 sentences)": (
        "Write 5-6 sentences maximum. Think executive summary - busy clients should get everything they need in 30 seconds.",
        "In one sentence, state clearly why this candidate is worth meeting for this role."
    ),
}

# ── UI ────────────────────────────────────────────────────────────────────────

st.title("📝 Candidate Profile Writer")
st.markdown("Turn a raw CV into a polished, client-ready profile in seconds.")

api_key = get_api_key()

st.divider()

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Candidate CV")
    cv_text = paste_or_upload(
        "Candidate CV",
        key="profile_cv",
        height=250,
        placeholder="Paste the candidate's CV content...",
        upload_hint="Drop the candidate's CV - PDF and DOCX work best",
    )

    st.subheader("Role Details *(optional)*")
    role_details = st.text_area(
        "What role are you submitting them for?",
        height=100,
        placeholder="e.g. Senior Security Engineer at a Sydney fintech, $180-200k, greenfield security program. Leave blank for a general profile."
    )

    st.subheader("Your Notes *(optional)*")
    extra_notes = st.text_area(
        "Anything not on the CV worth mentioning?",
        height=100,
        placeholder="e.g. Actively looking, needs to move quickly. Open to contract or perm. Interviewed well - very articulate. Prefers a smaller company environment."
    )

with col_right:
    st.subheader("Settings")

    format_type = st.selectbox(
        "Profile format",
        list(FORMAT_INSTRUCTIONS),
        help="Email submission pastes straight into a client email. Formal is for document submissions. Short brief for a quick intro."
    )

    tone = st.selectbox(
        "Tone",
        ["Professional", "Warm & Conversational", "Direct & Punchy"]
    )

    st.markdown("**Candidate details** *(shown in Key Stats)*")
    availability = st.text_input(
        "Availability",
        placeholder="e.g. 4 weeks notice, available immediately, 3 months"
    )
    salary = st.text_input(
        "Salary expectations",
        placeholder="e.g. $180-190k base + super, open to discussion"
    )

st.divider()

run = st.button("Write Profile", type="primary", use_container_width=True)

if run:
    if not api_key:
        st.error("Add your Anthropic API key in the sidebar first.")
        st.stop()
    if not cv_text.strip():
        st.error("Add a CV first - drop a file or paste the text.")
        st.stop()

    role_section = (
        f"ROLE THEY ARE BEING SUBMITTED FOR:\n{role_details}"
        if role_details.strip()
        else "NOTE: No specific role provided. Write a general profile that could be sent to multiple clients."
    )
    notes_section = (
        f"ADDITIONAL NOTES FROM RECRUITER:\n{extra_notes}"
        if extra_notes.strip()
        else ""
    )
    format_instr, role_fit_instr = FORMAT_INSTRUCTIONS[format_type]

    prompt = PROFILE_PROMPT.format(
        cv_text=cv_text[:30000],
        role_section=role_section,
        notes_section=notes_section,
        format_type=format_type,
        tone=tone,
        role_fit_instruction=role_fit_instr,
        format_instructions=format_instr,
        availability=availability or "Not specified",
        salary=salary or "Not specified",
    )

    with st.spinner("Writing candidate profile..."):
        try:
            profile = scrub(generate(api_key, prompt, max_tokens=2048))
            profile = profile.replace("passionate", "focused")
        except Exception as e:
            st.error(friendly_error(e))
            st.stop()

    st.session_state.profile_result = {"profile": profile}

# ── Results (persist across reruns) ──────────────────────────────────────────

state = st.session_state.get("profile_result")
if state:
    profile = state["profile"]
    st.subheader("Candidate Profile")

    if "KEY STATS:" in profile:
        body, _, stats = profile.partition("KEY STATS:")
        st.code(body.strip(), language=None, wrap_lines=True)
        st.markdown("**Key Stats**")
        st.markdown(stats.strip())
    else:
        st.code(profile.strip(), language=None, wrap_lines=True)

    docx_bytes = markdown_to_docx(profile, "Candidate Profile")
    st.download_button(
        "⬇️ Download Word (.docx)",
        data=docx_bytes,
        file_name="candidate_profile.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    st.caption("Use the copy icon in the top-right of the text block to copy the profile.")
