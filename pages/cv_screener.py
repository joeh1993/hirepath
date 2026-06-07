import streamlit as st
import anthropic
import json
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


SCREEN_PROMPT = """You are an expert technical recruitment consultant with 10+ years of experience placing engineers and tech professionals. Evaluate each candidate against the job description provided.

JOB DESCRIPTION:
{jd}

CANDIDATES:
{candidates}

Assess each candidate and return a JSON array. One object per candidate, in this exact format:
[
  {{
    "name": "Full name extracted from CV, or filename if not found",
    "score": <integer 1-10, where 10 is a perfect match>,
    "tier": "Strong Yes | Yes | Maybe | No",
    "strengths": ["specific strength 1", "specific strength 2", "specific strength 3"],
    "gaps": ["specific gap 1", "specific gap 2"],
    "years_experience": <integer, estimated total relevant experience>,
    "current_role": "their current or most recent job title",
    "recommendation": "One punchy sentence on whether to progress them and why."
  }}
]

Scoring guide:
- 9-10: Exceptional match, tick every box, would excite any client
- 7-8: Strong match, minor gaps that are trainable
- 5-6: Partial match, worth a conversation
- 3-4: Significant gaps but some relevant experience
- 1-2: Poor fit

Be direct and specific â€” vague feedback is useless. Focus on technical skills, experience level, and role fit.
Return ONLY the JSON array. No preamble, no explanation, no markdown code fences."""


def screen_candidates(jd: str, candidates: list[tuple[str, str]], api_key: str) -> list[dict]:
    client = anthropic.Anthropic(api_key=api_key)

    candidate_sections = ""
    for i, (name, text) in enumerate(candidates):
        # Truncate very long CVs to keep prompt manageable
        truncated = text[:4000] if len(text) > 4000 else text
        candidate_sections += f"\n\n--- CANDIDATE {i + 1}: {name} ---\n{truncated}"

    prompt = SCREEN_PROMPT.format(jd=jd[:3000], candidates=candidate_sections)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    # Strip markdown fences if model adds them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


# â”€â”€ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

st.title("CV Screener")
st.markdown("Paste a job description, upload candidate CVs, and get a ranked shortlist in seconds.")

# Pull API key from session state (set on home page)
api_key = st.session_state.get("api_key", "")
if not api_key:
    api_key = st.text_input("Anthropic API Key", type="password",
                             help="Or set it on the Home page to persist across tools")
    if api_key:
        st.session_state.api_key = api_key

st.divider()

col_jd, col_cv = st.columns([1, 1])

with col_jd:
    st.subheader("Job Description")
    jd = st.text_area(
        "Paste the full JD here",
        height=350,
        placeholder="Include: role title, required skills, years of experience, responsibilities..."
    )

with col_cv:
    st.subheader("Candidate CVs")
    uploaded_files = st.file_uploader(
        "Upload one or more CVs",
        accept_multiple_files=True,
        type=["pdf", "docx", "txt"],
        help="PDF and DOCX are best. Upload as many as you like."
    )
    if uploaded_files:
        st.caption(f"{len(uploaded_files)} file(s) ready to screen")

st.divider()

run = st.button("Screen Candidates", type="primary", use_container_width=True)

if run:
    if not api_key:
        st.error("Add your Anthropic API key above or on the Home page.")
        st.stop()
    if not jd.strip():
        st.error("Paste the job description before screening.")
        st.stop()
    if not uploaded_files:
        st.error("Upload at least one CV.")
        st.stop()

    # Extract text
    candidates = []
    progress = st.progress(0, text="Reading CVs...")
    for i, f in enumerate(uploaded_files):
        text = extract_text(f)
        candidates.append((f.name, text))
        progress.progress((i + 1) / len(uploaded_files), text=f"Read: {f.name}")

    progress.progress(100, text="Sending to Claude...")

    try:
        results = screen_candidates(jd, candidates, api_key)
    except json.JSONDecodeError as e:
        st.error(f"Claude returned unexpected output. Try again. ({e})")
        st.stop()
    except anthropic.AuthenticationError:
        st.error("Invalid API key. Check it and try again.")
        st.stop()

    progress.empty()

    results.sort(key=lambda x: x.get("score", 0), reverse=True)

    tier_icon = {"Strong Yes": "ðŸŸ¢", "Yes": "ðŸŸ¡", "Maybe": "ðŸŸ ", "No": "ðŸ”´"}

    st.subheader(f"Results â€” {len(results)} candidate(s) screened")

    # Summary table
    table_data = []
    for r in results:
        icon = tier_icon.get(r.get("tier", ""), "âšª")
        table_data.append({
            "": icon,
            "Name": r.get("name", "Unknown"),
            "Score": f"{r.get('score', '?')}/10",
            "Tier": r.get("tier", "â€”"),
            "Current Role": r.get("current_role", "â€”"),
            "Exp (yrs)": r.get("years_experience", "â€”"),
        })

    st.dataframe(table_data, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Detailed Assessments")

    for r in results:
        icon = tier_icon.get(r.get("tier", ""), "âšª")
        score = r.get("score", "?")
        name = r.get("name", "Unknown")
        tier = r.get("tier", "â€”")

        with st.expander(f"{icon} {name} â€” {score}/10 | {tier}"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Strengths**")
                for s in r.get("strengths", []):
                    st.markdown(f"âœ“ {s}")
            with c2:
                st.markdown("**Gaps**")
                gaps = r.get("gaps", [])
                if gaps:
                    for g in gaps:
                        st.markdown(f"âœ— {g}")
                else:
                    st.markdown("None identified")

            st.markdown(f"**Recommendation:** {r.get('recommendation', 'â€”')}")

