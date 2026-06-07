import streamlit as st
import anthropic
import io



def extract_text_from_pdf(file_bytes: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text(uploaded_file) -> str:
    data = uploaded_file.read()
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(data)
    if name.endswith(".docx"):
        return extract_text_from_docx(data)
    return data.decode("utf-8", errors="ignore")


PROFILE_PROMPT = """You are an expert technical recruitment consultant writing a candidate profile to send to a hiring client. Your profiles are known for being sharp, honest, and compelling â€” they make clients want to meet the candidate.

RAW CV / CANDIDATE INFORMATION:
{cv_text}

{role_section}

{notes_section}

FORMAT: {format_type}
TONE: {tone}

Write a polished candidate profile based on the above. The profile should:
1. Open with a strong one-sentence overview of who this person is (their level, specialism, and standout quality)
2. Cover their career trajectory and most relevant experience concisely
3. Highlight 2-3 genuine achievements or strengths with specifics where possible
4. {role_fit_instruction}
5. Close with their motivation for moving and availability if known

CRITICAL RULES:
- Never use em dashes (â€” or --)
- Never use the word "genuinely"
- Never use the word "leverage"
- Never use "passionate" or "passionate about"
- Never use "strong communication skills"
- Never use "team player"
- Never use "results-driven"
- No clichÃ©s or filler phrases
- Write in third person (e.g. "Joel brings..." not "I bring...")
- Be specific â€” vague profiles get ignored

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
        "Write 5-6 sentences maximum. Think executive summary â€” busy clients should get everything they need in 30 seconds.",
        "In one sentence, state clearly why this candidate is worth meeting for this role."
    ),
}


def generate_profile(cv_text, role_details, extra_notes, format_type, tone,
                     availability, salary, api_key):
    client = anthropic.Anthropic(api_key=api_key)

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
        cv_text=cv_text[:5000],
        role_section=role_section,
        notes_section=notes_section,
        format_type=format_type,
        tone=tone,
        role_fit_instruction=role_fit_instr,
        format_instructions=format_instr,
        availability=availability or "Not specified",
        salary=salary or "Not specified",
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )

    output = message.content[0].text
    # Hard strip banned words/phrases
    output = output.replace("â€”", "-").replace("--", "-")
    output = output.replace("genuinely", "clearly")
    output = output.replace("passionate", "focused")
    output = output.replace("leverage", "use")
    return output


# â”€â”€ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

st.title("Candidate Profile Writer")
st.markdown("Turn a raw CV into a polished, client-ready profile in seconds.")

api_key = st.session_state.get("api_key", "")
if not api_key:
    api_key = st.text_input("Anthropic API Key", type="password",
                             help="Or set it on the Home page")
    if api_key:
        st.session_state.api_key = api_key

st.divider()

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Candidate CV")
    upload_tab, paste_tab = st.tabs(["Upload file", "Paste text"])

    cv_text = ""
    with upload_tab:
        uploaded_file = st.file_uploader(
            "Upload CV (PDF, DOCX, or TXT)",
            type=["pdf", "docx", "txt"]
        )
        if uploaded_file:
            cv_text = extract_text(uploaded_file)
            st.caption(f"Extracted {len(cv_text)} characters from {uploaded_file.name}")

    with paste_tab:
        pasted = st.text_area("Paste CV text here", height=250)
        if pasted:
            cv_text = pasted

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
        placeholder="e.g. Actively looking, needs to move quickly. Open to contract or perm. Interviewed well â€” very articulate. Prefers a smaller company environment."
    )

with col_right:
    st.subheader("Settings")

    format_type = st.selectbox(
        "Profile format",
        [
            "Email submission (paragraphs)",
            "Formal submission (structured)",
            "Short brief (5-6 sentences)",
        ],
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
        st.error("Add your Anthropic API key above or on the Home page.")
        st.stop()
    if not cv_text.strip():
        st.error("Upload or paste a CV first.")
        st.stop()

    with st.spinner("Writing candidate profile..."):
        profile = generate_profile(
            cv_text, role_details, extra_notes,
            format_type, tone, availability, salary, api_key
        )

    st.subheader("Candidate Profile")

    # Split profile body from key stats
    if "KEY STATS:" in profile:
        body, _, stats = profile.partition("KEY STATS:")
        st.text_area("Profile", value=body.strip(), height=350,
                     label_visibility="collapsed")
        st.divider()
        st.markdown("**Key Stats**")
        st.markdown("KEY STATS:" + stats)
    else:
        st.text_area("Profile", value=profile.strip(), height=400,
                     label_visibility="collapsed")

    st.caption("Click inside the text box and select all (Ctrl+A) to copy.")

