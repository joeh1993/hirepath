import streamlit as st
import anthropic
import io
import re


# ── Helpers ──────────────────────────────────────────────────────────────────

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


BANNED = ["genuinely", "genuinely,", "genuinely."]

def scrub(text: str) -> str:
    for word in BANNED:
        text = text.replace(word, "truly").replace(word.capitalize(), "Truly")
    return text


# ── DOCX export ───────────────────────────────────────────────────────────────

def _add_formatted_runs(paragraph, text: str):
    """Parse **bold** and *italic* inline markers and add styled runs."""
    # Split on bold markers first
    segments = re.split(r'(\*\*.*?\*\*)', text)
    for seg in segments:
        if seg.startswith("**") and seg.endswith("**"):
            run = paragraph.add_run(seg[2:-2])
            run.bold = True
        else:
            # Within non-bold, check for italic
            italic_segs = re.split(r'(\*.*?\*)', seg)
            for iseg in italic_segs:
                if iseg.startswith("*") and iseg.endswith("*") and len(iseg) > 2:
                    run = paragraph.add_run(iseg[1:-1])
                    run.italic = True
                else:
                    # Strip any remaining backtick markers
                    clean = re.sub(r'`(.*?)`', r'\1', iseg)
                    if clean:
                        paragraph.add_run(clean)


def build_docx(result: str, company: str, stage: str) -> bytes:
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    doc = Document()

    # ── Page margins ─────────────────────────────────────────────────────────
    for section in doc.sections:
        section.top_margin    = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2.5)

    # ── Cover block ──────────────────────────────────────────────────────────
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_p.add_run("Interview Prep Pack")
    title_run.bold = True
    title_run.font.size = Pt(22)
    title_run.font.color.rgb = RGBColor(0x1A, 0x56, 0xDB)  # blue

    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = sub_p.add_run(f"{company}   |   {stage}")
    sub_run.font.size = Pt(12)
    sub_run.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)  # grey

    doc.add_paragraph()  # spacer

    # ── Parse sections ────────────────────────────────────────────────────────
    lines = result.split("\n")
    current_heading = None
    current_lines: list[str] = []
    all_sections: list[tuple[str, list[str]]] = []

    for line in lines:
        if line.startswith("## "):
            if current_heading is not None:
                all_sections.append((current_heading, current_lines))
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_heading is not None:
        all_sections.append((current_heading, current_lines))

    # ── Render sections ───────────────────────────────────────────────────────
    for heading, content_lines in all_sections:
        # Section heading
        h = doc.add_heading(heading, level=1)
        h.runs[0].font.color.rgb = RGBColor(0x1A, 0x56, 0xDB)

        i = 0
        while i < len(content_lines):
            raw = content_lines[i]
            stripped = raw.strip()

            if not stripped:
                i += 1
                continue

            # Sub-heading (###)
            if stripped.startswith("### "):
                sh = doc.add_heading(stripped[4:], level=2)
                sh.runs[0].font.color.rgb = RGBColor(0x37, 0x41, 0x51)
                i += 1
                continue

            # Bullet point (- or *)
            if re.match(r'^[-*]\s', stripped):
                p = doc.add_paragraph(style="List Bullet")
                _add_formatted_runs(p, stripped[2:])
                i += 1
                continue

            # Numbered list (1. / 1) / 1:)
            if re.match(r'^\d+[.)]\s', stripped):
                p = doc.add_paragraph(style="List Number")
                text_after_num = re.sub(r'^\d+[.)]\s*', '', stripped)
                _add_formatted_runs(p, text_after_num)
                i += 1
                continue

            # Plain paragraph
            p = doc.add_paragraph()
            _add_formatted_runs(p, stripped)
            i += 1

        doc.add_paragraph()  # section spacer

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


# ── Prompt ───────────────────────────────────────────────────────────────────

PREP_PROMPT = """You are an expert technical recruitment consultant specialising in cyber security roles across the Australian market, particularly Sydney. You are preparing a candidate for an interview and your goal is to maximise their chance of receiving an offer.

Use the information below to build a thorough, personalised interview prep pack.

CANDIDATE CV:
{cv}

ROLE / JOB DESCRIPTION:
{jd}

COMPANY NAME: {company}
INTERVIEW STAGE: {stage}
INTERVIEWER(S): {interviewers}

---

Produce a prep pack with ALL of the following sections. Use clear markdown headings. Be specific -- generic advice is useless.

## 1. Company Snapshot
- What the company does, their core business, size, and market position
- Recent news, funding, acquisitions, or notable achievements (based on what you know)
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
- Realistic salary range for this role in the Sydney cyber security market (based on your knowledge)
- How and when to raise salary in the conversation
- How to respond if they ask "what are you looking for?" before an offer
- How to negotiate if the first offer is below expectations
- One or two lines to use verbatim

Do not use em dashes anywhere in your response. Do not use the word "genuinely". Be direct, practical, and specific to this candidate and role."""


def generate_prep_pack(cv: str, jd: str, company: str, stage: str, interviewers: str, api_key: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)

    prompt = PREP_PROMPT.format(
        cv=cv[:5000] if len(cv) > 5000 else cv,
        jd=jd[:3000] if len(jd) > 3000 else jd,
        company=company,
        stage=stage,
        interviewers=interviewers if interviewers.strip() else "Not specified",
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    return scrub(raw)


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("🎤 Interview Prep Pack")
st.markdown("Generate a candidate-specific prep guide: company research, likely questions, talking points, and salary coaching.")

# API key
api_key = st.session_state.get("api_key", "")
if not api_key:
    api_key = st.text_input("Anthropic API Key", type="password",
                             help="Or set it on the Home page to persist across tools")
    if api_key:
        st.session_state.api_key = api_key

st.divider()

# ── Inputs ────────────────────────────────────────────────────────────────────

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Candidate CV")
    cv_tab1, cv_tab2 = st.tabs(["Upload file", "Paste text"])

    with cv_tab1:
        cv_file = st.file_uploader(
            "Upload CV (PDF, DOCX, or TXT)",
            type=["pdf", "docx", "txt"],
            help="PDF and DOCX work best",
            key="cv_file"
        )

    with cv_tab2:
        cv_text_input = st.text_area(
            "Paste the CV text here",
            height=250,
            placeholder="Paste the candidate's CV content...",
            key="cv_paste"
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
    jd = st.text_area(
        "Paste the job description here",
        height=430,
        placeholder="Paste the full job description. The more detail, the better the prep pack."
    )

st.divider()

run = st.button("Generate Prep Pack", type="primary", use_container_width=True)

# ── Run ───────────────────────────────────────────────────────────────────────

if run:
    if not api_key:
        st.error("Add your Anthropic API key above or on the Home page.")
        st.stop()

    # Resolve CV text
    cv_content = ""
    if cv_file is not None:
        with st.spinner("Reading CV..."):
            cv_content = extract_text(cv_file)
    elif cv_text_input.strip():
        cv_content = cv_text_input.strip()

    if not cv_content:
        st.error("Provide the candidate's CV: either upload a file or paste the text.")
        st.stop()

    if not jd.strip():
        st.error("Paste the job description before generating.")
        st.stop()

    if not company.strip():
        st.error("Enter the company name.")
        st.stop()

    with st.spinner("Building prep pack... this takes 30-60 seconds"):
        try:
            result = generate_prep_pack(
                cv=cv_content,
                jd=jd,
                company=company.strip(),
                stage=stage,
                interviewers=interviewers,
                api_key=api_key,
            )
        except anthropic.AuthenticationError:
            st.error("Invalid API key. Check it and try again.")
            st.stop()
        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.stop()

    st.success("Prep pack ready!")
    st.divider()

    # ── Download buttons ──────────────────────────────────────────────────────

    safe_name = company.strip().replace(" ", "_")
    docx_bytes = build_docx(result, company.strip(), stage)

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

    # ── Parse and render each section as an expander ──────────────────────────

    lines = result.split("\n")
    current_section = []
    current_heading = None
    all_sections = []

    for line in lines:
        if line.startswith("## "):
            if current_heading is not None:
                all_sections.append((current_heading, "\n".join(current_section).strip()))
            current_heading = line[3:].strip()
            current_section = []
        else:
            current_section.append(line)

    if current_heading is not None:
        all_sections.append((current_heading, "\n".join(current_section).strip()))

    section_icons = {
        "1": "🏢",
        "2": "🎯",
        "3": "💻",
        "4": "🗣️",
        "5": "⭐",
        "6": "❓",
        "7": "💰",
    }

    for heading, content in all_sections:
        num = heading.split(".")[0].strip() if "." in heading else ""
        icon = section_icons.get(num, "📌")
        with st.expander(f"{icon} {heading}", expanded=True):
            st.markdown(content)
