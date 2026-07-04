import streamlit as st

from utils import (friendly_error, generate, get_api_key, parse_variants,
                   paste_or_upload, recruiter_details, render_variants)

OUTREACH_PROMPT = """You are an expert technical recruitment consultant writing personalised outreach messages. Your messages are known for feeling personal - never templated or spammy.

CANDIDATE INFORMATION:
{candidate_info}

ROLE DETAILS:
{role_details}

YOUR NAME: {recruiter_name}
YOUR COMPANY: {recruiter_company}

MESSAGE TYPE: {message_type}
TONE: {tone}

Write {num_variants} distinct outreach message variant(s). Each should:
1. Open with something specific to THIS candidate - reference their actual background, a career move, a skill, a company they've worked at. Never open with "I came across your profile" or "Hope this message finds you well."
2. Be about them first, the role second
3. Pitch the role concisely - focus on what makes it compelling (not just a job ad)
4. End with a soft, low-pressure call to action (not "please let me know if you're interested")
5. Feel like it was written for this specific person, not copy-pasted

CRITICAL RULES:
- Never use em dashes or double hyphens
- Never use the word "leverage"
- Never use the word "genuinely"
- Never use "I wanted to reach out"
- Never use "touch base"
- No bullet points in the message body

{type_specific_instructions}

Format your response as:

VARIANT 1:
{subject_line_instruction}---
[message body]
---

VARIANT 2:
{subject_line_instruction}---
[message body]
---

(and so on for each variant)

Do not include any explanation or commentary outside of this format."""

TYPE_INSTRUCTIONS = {
    "LinkedIn InMail": (
        "Keep the body under 1,900 characters. Include a subject line.",
        "SUBJECT: [subject line, max 200 chars]\n",
    ),
    "LinkedIn Connection Request": (
        "CRITICAL: Keep the message under 300 characters total - this is a hard LinkedIn limit. Be punchy and intriguing. No subject line.",
        "",
    ),
    "Email": (
        "Write a compelling subject line. Keep the body conversational - emails that read like emails, not job ads.",
        "SUBJECT: [subject line]\n",
    ),
}

TONE_DESCRIPTORS = {
    "Professional": "Polished and confident. Formal enough for a senior hire, but not stiff.",
    "Warm & Conversational": "Friendly and human. Reads like a message from someone who wants to connect.",
    "Direct": "Get to the point fast. No fluff. Respect their time.",
}

# ── UI ────────────────────────────────────────────────────────────────────────

st.title("✉️ Candidate Outreach")
st.markdown("Generate personalised LinkedIn and email messages that actually get replies.")

api_key = get_api_key()
recruiter_name, recruiter_company, _ = recruiter_details()

st.divider()

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Candidate")
    candidate_info = paste_or_upload(
        "Their LinkedIn bio, CV, or a description of them",
        key="outreach_candidate",
        height=200,
        placeholder="e.g. 5 years as a SOC Analyst at CrowdStrike, recently moved to a Threat Intelligence Lead role at a Big 4 consultancy. CISSP certified. Based in Sydney. Posts regularly about cloud security on LinkedIn.",
        upload_hint="Drop their CV, or paste a LinkedIn bio in the other tab",
    )

    st.subheader("Role")
    role_details = st.text_area(
        "Describe the opportunity",
        height=150,
        placeholder="e.g. Senior Security Engineer at a fast-growing fintech in Sydney CBD. $180-200k + equity. Greenfield security program, reporting to CISO. Hybrid 3 days in office."
    )

with col_right:
    st.subheader("Settings")

    message_type = st.selectbox(
        "Message type",
        ["LinkedIn InMail", "LinkedIn Connection Request", "Email"],
        help="Connection requests are capped at 300 characters"
    )

    tone = st.selectbox("Tone", list(TONE_DESCRIPTORS))

    num_variants = st.slider("Number of variants", min_value=1, max_value=3, value=2)

    st.caption(f"Sending as **{recruiter_name or 'you'}** from **{recruiter_company or 'your company'}** "
               "- change under *Your details* in the sidebar.")

st.divider()

run = st.button("Generate Outreach", type="primary", use_container_width=True)

if run:
    if not api_key:
        st.error("Add your Anthropic API key in the sidebar first.")
        st.stop()
    if not candidate_info.strip():
        st.error("Add some candidate information.")
        st.stop()
    if not role_details.strip():
        st.error("Describe the role.")
        st.stop()

    type_instr, subj_instr = TYPE_INSTRUCTIONS[message_type]
    prompt = OUTREACH_PROMPT.format(
        candidate_info=candidate_info,
        role_details=role_details,
        recruiter_name=recruiter_name or "the recruiter",
        recruiter_company=recruiter_company or "our firm",
        message_type=message_type,
        tone=f"{tone} - {TONE_DESCRIPTORS[tone]}",
        num_variants=num_variants,
        type_specific_instructions=type_instr,
        subject_line_instruction=subj_instr,
    )

    with st.spinner("Writing personalised messages..."):
        try:
            raw = generate(api_key, prompt, max_tokens=2048)
        except Exception as e:
            st.error(friendly_error(e))
            st.stop()

    variants = parse_variants(raw)
    st.session_state.cand_outreach = {
        "variants": variants, "message_type": message_type, "raw": raw,
    }

# ── Results (persist across reruns) ──────────────────────────────────────────

state = st.session_state.get("cand_outreach")
if state:
    if state["variants"]:
        render_variants(state["variants"], state["message_type"], key_prefix="cand")
    else:
        st.warning("Couldn't parse variants - showing raw output.")
        st.code(state["raw"], language=None, wrap_lines=True)
