"""Shared helpers for all HirePath tools."""

import io
import json
import re

import anthropic
import streamlit as st

# One place to change the model for the whole app.
MODEL = "claude-sonnet-4-6"

# Server-side web search — runs on Anthropic's infrastructure. Each search is
# billed by Anthropic ($10 / 1,000 searches) on top of normal token costs.
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 8}

LINKEDIN_INMAIL_LIMIT = 1900
LINKEDIN_CONNECTION_LIMIT = 300


# ── Session helpers ───────────────────────────────────────────────────────────

def get_api_key() -> str:
    return st.session_state.get("api_key", "")


def require_api_key() -> str:
    """Return the API key, or stop the page with a helpful error."""
    key = get_api_key()
    if not key:
        st.error("Add your Anthropic API key in the sidebar first.")
        st.stop()
    return key


def recruiter_details() -> tuple[str, str, str]:
    """Name, company, niche — set once in the sidebar, shared by every tool."""
    return (
        st.session_state.get("recruiter_name", ""),
        st.session_state.get("recruiter_company", ""),
        st.session_state.get("recruiter_niche", ""),
    )


# ── File text extraction ──────────────────────────────────────────────────────

def extract_text(uploaded_file) -> str:
    data = uploaded_file.read()
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith(".docx"):
        from docx import Document
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    return data.decode("utf-8", errors="ignore")


def paste_or_upload(label: str, *, key: str, height: int = 250,
                    placeholder: str = "", upload_hint: str = "") -> str:
    """Input that accepts a drag-and-dropped file (PDF/DOCX/TXT) or pasted text.
    The uploaded file wins if both are provided. Returns the extracted text."""
    upload_tab, paste_tab = st.tabs(["📎 Drop a file", "📋 Paste text"])

    pasted = ""
    with paste_tab:
        pasted = st.text_area(label, height=height, placeholder=placeholder,
                              key=f"{key}_paste", label_visibility="collapsed")

    uploaded_text = ""
    with upload_tab:
        f = st.file_uploader(label, type=["pdf", "docx", "txt"],
                             key=f"{key}_file", label_visibility="collapsed",
                             help=upload_hint or "Drag and drop a PDF, Word, or text file")
        if f:
            uploaded_text = extract_text(f)
            st.caption(f"Using **{f.name}** — {len(uploaded_text):,} characters extracted. "
                       "Remove the file to use pasted text instead.")

    return uploaded_text.strip() or pasted.strip()


# ── Output scrubbing ──────────────────────────────────────────────────────────

_SCRUB = [
    ("—", "-"),          # em dash
    ("genuinely", "truly"),
    ("Genuinely", "Truly"),
    ("leverage", "use"),
    ("Leverage", "Use"),
]


def scrub(text: str) -> str:
    for old, new in _SCRUB:
        text = text.replace(old, new)
    return text


# ── Claude calls ──────────────────────────────────────────────────────────────

def _client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key)


def generate(api_key: str, prompt: str, max_tokens: int = 4096,
             tools: list | None = None, system: str | None = None) -> str:
    """Single-prompt generation. Handles the pause_turn continuation that
    server-side web search can produce. Returns concatenated text output."""
    client = _client(api_key)
    kwargs = {}
    if tools:
        kwargs["tools"] = tools
    if system:
        kwargs["system"] = system

    messages = [{"role": "user", "content": prompt}]
    parts: list[str] = []
    for _ in range(5):
        resp = client.messages.create(
            model=MODEL, max_tokens=max_tokens, messages=messages, **kwargs
        )
        parts.extend(block.text for block in resp.content if block.type == "text")
        if resp.stop_reason == "pause_turn":
            messages = messages + [{"role": "assistant", "content": resp.content}]
            continue
        break
    return "\n".join(parts).strip()


def generate_streaming(api_key: str, prompt: str, placeholder,
                       max_tokens: int = 4096, tools: list | None = None) -> str:
    """Like generate(), but streams text into a Streamlit placeholder so the
    user sees output as it is written. Returns the full text."""
    client = _client(api_key)
    kwargs = {"tools": tools} if tools else {}

    messages = [{"role": "user", "content": prompt}]
    full = ""
    for _ in range(5):
        with client.messages.stream(
            model=MODEL, max_tokens=max_tokens, messages=messages, **kwargs
        ) as stream:
            for text in stream.text_stream:
                full += text
                placeholder.markdown(full + " ▌")
            final = stream.get_final_message()
        if final.stop_reason == "pause_turn":
            messages = messages + [{"role": "assistant", "content": final.content}]
            continue
        break
    placeholder.empty()
    return full.strip()


def friendly_error(e: Exception) -> str:
    if isinstance(e, anthropic.AuthenticationError):
        return "Invalid API key. Check it in the sidebar and try again."
    if isinstance(e, anthropic.RateLimitError):
        return "Rate limit reached. Wait a minute and try again."
    if isinstance(e, anthropic.APIStatusError):
        if e.status_code >= 500:
            return "Anthropic's API is temporarily unavailable. Try again shortly."
        return f"API error: {e.message}"
    if isinstance(e, anthropic.APIConnectionError):
        return "Network error. Check your connection and try again."
    return f"Something went wrong: {e}"


def extract_json(raw: str):
    """Pull a JSON object or array out of a response that may contain
    markdown fences or surrounding prose (common when web search is used)."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    starts = [(raw.find(o), o, c) for o, c in (("{", "}"), ("[", "]")) if raw.find(o) != -1]
    if starts:
        starts.sort()
        _, open_ch, close_ch = starts[0]
        start = raw.find(open_ch)
        end = raw.rfind(close_ch)
        if end > start:
            return json.loads(raw[start:end + 1])
    raise json.JSONDecodeError("No JSON found in response", raw, 0)


# ── Outreach variant parsing / rendering ─────────────────────────────────────

def parse_variants(raw_text: str) -> list[dict]:
    """Split 'VARIANT n:' formatted output into subject/body dicts."""
    variants = []
    for block in raw_text.split("VARIANT ")[1:]:
        lines = block.strip().split("\n")
        content = "\n".join(lines[1:]).strip()

        # Strip a trailing character-count line if the model added one
        content = re.sub(r"CHARACTER COUNT:.*$", "", content, flags=re.IGNORECASE).strip()
        body = content.strip("-").strip()

        subject = None
        if body.startswith("SUBJECT:"):
            subject_line, _, rest = body.partition("\n")
            subject = subject_line.replace("SUBJECT:", "").strip()
            body = rest.strip().strip("-").strip()

        body = scrub(body)
        if body:
            variants.append({"subject": subject, "body": body})
    return variants


def render_variants(variants: list[dict], message_type: str, key_prefix: str):
    """Render outreach variants with copy buttons and live character counts."""
    if message_type == "LinkedIn Connection Request":
        char_limit = LINKEDIN_CONNECTION_LIMIT
    elif "LinkedIn" in message_type:
        char_limit = LINKEDIN_INMAIL_LIMIT
    else:
        char_limit = None

    st.subheader(f"{len(variants)} message variant(s) — {message_type}")
    for i, v in enumerate(variants, 1):
        st.markdown(f"**Variant {i}**" + (f" — Subject: *{v['subject']}*" if v.get("subject") else ""))
        if v.get("subject"):
            st.code(v["subject"], language=None)
        st.code(v["body"], language=None, wrap_lines=True)

        count = len(v["body"])
        if char_limit:
            if count > char_limit:
                st.error(f"{count} characters — {count - char_limit} over the {char_limit} limit")
            else:
                st.success(f"{count} / {char_limit} characters")
        else:
            st.caption(f"{count} characters")
        st.divider()


# ── Markdown → Word export ────────────────────────────────────────────────────

def _add_formatted_runs(paragraph, text: str):
    """Parse **bold** and *italic* inline markers into styled runs."""
    segments = re.split(r"(\*\*.*?\*\*)", text)
    for seg in segments:
        if seg.startswith("**") and seg.endswith("**"):
            run = paragraph.add_run(seg[2:-2])
            run.bold = True
        else:
            italic_segs = re.split(r"(\*.*?\*)", seg)
            for iseg in italic_segs:
                if iseg.startswith("*") and iseg.endswith("*") and len(iseg) > 2:
                    run = paragraph.add_run(iseg[1:-1])
                    run.italic = True
                else:
                    clean = re.sub(r"`(.*?)`", r"\1", iseg)
                    if clean:
                        paragraph.add_run(clean)


def markdown_to_docx(md_text: str, title: str, subtitle: str = "") -> bytes:
    """Convert simple markdown (## headings, bullets, numbered lists, bold,
    italic) into a branded Word document."""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_p.add_run(title)
    title_run.bold = True
    title_run.font.size = Pt(22)
    title_run.font.color.rgb = RGBColor(0x1A, 0x56, 0xDB)

    if subtitle:
        sub_p = doc.add_paragraph()
        sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_run = sub_p.add_run(subtitle)
        sub_run.font.size = Pt(12)
        sub_run.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)

    doc.add_paragraph()

    for raw_line in md_text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            h = doc.add_heading(line[3:].strip(), level=1)
            h.runs[0].font.color.rgb = RGBColor(0x1A, 0x56, 0xDB)
        elif line.startswith("### "):
            sh = doc.add_heading(line[4:].strip(), level=2)
            sh.runs[0].font.color.rgb = RGBColor(0x37, 0x41, 0x51)
        elif line.startswith("# "):
            h = doc.add_heading(line[2:].strip(), level=1)
            h.runs[0].font.color.rgb = RGBColor(0x1A, 0x56, 0xDB)
        elif re.match(r"^[-*]\s", line):
            p = doc.add_paragraph(style="List Bullet")
            _add_formatted_runs(p, line[2:])
        elif re.match(r"^\d+[.)]\s", line):
            p = doc.add_paragraph(style="List Number")
            _add_formatted_runs(p, re.sub(r"^\d+[.)]\s*", "", line))
        else:
            p = doc.add_paragraph()
            _add_formatted_runs(p, line)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()
