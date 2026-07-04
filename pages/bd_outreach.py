import streamlit as st

from utils import (friendly_error, generate, get_api_key, parse_variants,
                   recruiter_details, render_variants)

BD_PROMPT = """You are an expert technical recruitment consultant writing business development outreach to potential clients. Your messages win meetings because they feel human, relevant, and specific - never like a mass mailout.

YOUR NAME: {recruiter_name}
YOUR COMPANY: {recruiter_company}
YOUR NICHE: {niche}

TARGET COMPANY: {company_info}
TARGET PERSONA: {persona}
TRIGGER / REASON FOR REACHING OUT: {trigger}

MESSAGE TYPE: {message_type}
TONE: {tone}

Write {num_variants} distinct BD outreach message variant(s). Each should:
1. Open with something specific to THIS company or person - reference their growth, a hire they made, a challenge their industry faces, or the trigger event. Never open with "I hope this finds you well" or "My name is X and I work at Y."
2. Establish your niche credibility quickly - you're a specialist, not a generalist
3. Make it about a problem they likely have, not about what you want
4. Be concise - decision makers delete long messages
5. End with one specific, easy ask (a 15-minute call, a question, not "let me know if you need help")
6. Sound like a person wrote it, not a recruitment agency template

CRITICAL RULES:
- Never use em dashes or double hyphens
- Never use the word "leverage"
- Never use the word "genuinely"
- Never use "I wanted to reach out"
- Never use "touch base"
- No bullet points in the message body
- No sign-off lines like "Best regards" unless it is an email

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

(and so on)

No commentary or explanation outside this format."""

TYPE_INSTRUCTIONS = {
    "LinkedIn InMail": (
        "Keep the body under 1,900 characters. Include a subject line.",
        "SUBJECT: [subject line, max 200 chars]\n",
    ),
    "LinkedIn Connection Request": (
        "CRITICAL: Under 300 characters total. No subject line. Make every word count.",
        "",
    ),
    "Email": (
        "Write a compelling subject line. Emails can be slightly longer but keep it tight.",
        "SUBJECT: [subject line]\n",
    ),
}

TONE_DESCRIPTORS = {
    "Professional": "Polished and confident. You know your market.",
    "Warm & Conversational": "Friendly and human. Like a message from someone worth knowing.",
    "Direct": "No fluff. Busy people appreciate brevity.",
}

# ── UI ────────────────────────────────────────────────────────────────────────

st.title("🤝 BD Outreach")
st.markdown("Write business development messages that get meetings, not ignored.")

api_key = get_api_key()
recruiter_name, recruiter_company, niche = recruiter_details()

st.divider()

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Target Company")
    company_info = st.text_area(
        "What do you know about the company?",
        height=150,
        placeholder="e.g. Fintech scaleup based in Sydney CBD, Series B funded (~$40m raised), ~200 employees and growing fast. Have been posting a lot of security roles on LinkedIn recently. No dedicated CISO yet as far as I can tell."
    )

    persona = st.text_input(
        "Who are you messaging?",
        placeholder="e.g. CTO, CISO, Head of Engineering, HR Director, Hiring Manager"
    )

    trigger = st.text_area(
        "Why are you reaching out now?",
        height=100,
        placeholder="e.g. They've posted 3 security roles in the last month with no agency on the ads. Likely struggling to hire direct. Their industry has had a couple of high-profile breaches recently."
    )

with col_right:
    st.subheader("Settings")

    message_type = st.selectbox(
        "Message type",
        ["LinkedIn InMail", "LinkedIn Connection Request", "Email"]
    )

    tone = st.selectbox("Tone", list(TONE_DESCRIPTORS))

    num_variants = st.slider("Number of variants", min_value=1, max_value=3, value=2)

    st.caption(f"Sending as **{recruiter_name or 'you'}** from **{recruiter_company or 'your company'}**, "
               f"niche: *{niche or 'not set'}* - change under *Your details* in the sidebar.")

st.divider()

run = st.button("Generate BD Outreach", type="primary", use_container_width=True)

if run:
    if not api_key:
        st.error("Add your Anthropic API key in the sidebar first.")
        st.stop()
    if not company_info.strip():
        st.error("Add some information about the target company.")
        st.stop()
    if not persona.strip():
        st.error("Specify who you are messaging.")
        st.stop()
    if not trigger.strip():
        st.error("Add a reason for reaching out - this is what makes the message feel relevant.")
        st.stop()

    type_instr, subj_instr = TYPE_INSTRUCTIONS[message_type]
    prompt = BD_PROMPT.format(
        recruiter_name=recruiter_name or "the recruiter",
        recruiter_company=recruiter_company or "our firm",
        niche=niche or "technical recruitment",
        company_info=company_info,
        persona=persona,
        trigger=trigger,
        message_type=message_type,
        tone=f"{tone} - {TONE_DESCRIPTORS[tone]}",
        num_variants=num_variants,
        type_specific_instructions=type_instr,
        subject_line_instruction=subj_instr,
    )

    with st.spinner("Writing BD messages..."):
        try:
            raw = generate(api_key, prompt, max_tokens=2048)
        except Exception as e:
            st.error(friendly_error(e))
            st.stop()

    variants = parse_variants(raw)
    st.session_state.bd_outreach = {
        "variants": variants, "message_type": message_type, "raw": raw,
    }

# ── Results (persist across reruns) ──────────────────────────────────────────

state = st.session_state.get("bd_outreach")
if state:
    if state["variants"]:
        render_variants(state["variants"], state["message_type"], key_prefix="bd")
    else:
        st.warning("Couldn't parse variants - showing raw output.")
        st.code(state["raw"], language=None, wrap_lines=True)
