import streamlit as st
import anthropic


LINKEDIN_INMAIL_LIMIT = 1900
LINKEDIN_CONNECTION_LIMIT = 300

BD_PROMPT = """You are an expert technical recruitment consultant writing business development outreach to potential clients. Your messages win meetings because they feel human, relevant, and specific â€” never like a mass mailout.

YOUR NAME: {recruiter_name}
YOUR COMPANY: {recruiter_company}
YOUR NICHE: {niche}

TARGET COMPANY: {company_info}
TARGET PERSONA: {persona}
TRIGGER / REASON FOR REACHING OUT: {trigger}

MESSAGE TYPE: {message_type}
TONE: {tone}

Write {num_variants} distinct BD outreach message variant(s). Each should:
1. Open with something specific to THIS company or person â€” reference their growth, a hire they made, a challenge their industry faces, or the trigger event. Never open with "I hope this finds you well" or "My name is X and I work at Y."
2. Establish your niche credibility quickly â€” you're a specialist, not a generalist
3. Make it about a problem they likely have, not about what you want
4. Be concise â€” decision makers delete long messages
5. End with one specific, easy ask (a 15-minute call, a question, not "let me know if you need help")
6. Sound like a person wrote it, not a recruitment agency template

CRITICAL RULES:
- Never use em dashes (â€” or --)
- Never use the word "leverage"
- Never use the word "genuinely"
- Never use "I wanted to reach out"
- Never use "touch base"
- No bullet points in the message body
- No sign-off lines like "Best regards" unless it is an email

{type_specific_instructions}

Format your response as:

VARIANT 1:
{subject_line_instruction}
---
[message body]
---
CHARACTER COUNT: [count]

VARIANT 2:
{subject_line_instruction}
---
[message body]
---
CHARACTER COUNT: [count]

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


def generate_bd_outreach(company_info, persona, trigger, niche, message_type, tone,
                          recruiter_name, recruiter_company, num_variants, api_key):
    client = anthropic.Anthropic(api_key=api_key)

    type_instr, subj_line_instr = TYPE_INSTRUCTIONS[message_type]

    prompt = BD_PROMPT.format(
        recruiter_name=recruiter_name or "the recruiter",
        recruiter_company=recruiter_company or "our firm",
        niche=niche or "technical recruitment",
        company_info=company_info,
        persona=persona,
        trigger=trigger,
        message_type=message_type,
        tone=f"{tone} â€” {TONE_DESCRIPTORS[tone]}",
        num_variants=num_variants,
        type_specific_instructions=type_instr,
        subject_line_instruction=subj_line_instr,
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def parse_variants(raw_text):
    variants = []
    blocks = raw_text.split("VARIANT ")
    for block in blocks[1:]:
        lines = block.strip().split("\n")
        content = "\n".join(lines[1:]).strip()
        if "CHARACTER COUNT:" in content:
            parts = content.rsplit("CHARACTER COUNT:", 1)
            body = parts[0].strip().strip("---").strip()
            try:
                char_count = int(parts[1].strip())
            except ValueError:
                char_count = len(body)
        else:
            body = content.strip("---").strip()
            char_count = len(body)

        subject = None
        if body.startswith("SUBJECT:"):
            subject_line, _, rest = body.partition("\n")
            subject = subject_line.replace("SUBJECT:", "").strip()
            body = rest.strip().strip("---").strip()

        # Strip banned words/characters that slipped through
        body = body.replace("â€”", "-").replace("--", "-")
        body = body.replace("genuinely", "truly")

        variants.append({"subject": subject, "body": body, "char_count": char_count})
    return variants


# â”€â”€ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

st.title("BD Outreach")
st.markdown("Write business development messages that get meetings, not ignored.")

api_key = st.session_state.get("api_key", "")
if not api_key:
    api_key = st.text_input("Anthropic API Key", type="password",
                             help="Or set it on the Home page")
    if api_key:
        st.session_state.api_key = api_key

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

    tone = st.selectbox(
        "Tone",
        ["Professional", "Warm & Conversational", "Direct"]
    )

    num_variants = st.slider("Number of variants", min_value=1, max_value=3, value=2)

    st.markdown("**Your details**")
    recruiter_name = st.text_input("Your name", placeholder="Joel Heywood")
    recruiter_company = st.text_input("Your company", placeholder="Novus Pathway")
    niche = st.text_input(
        "Your niche / specialisation",
        placeholder="e.g. Cyber security recruitment across Australia",
        help="This establishes your credibility in the message"
    )

st.divider()

run = st.button("Generate BD Outreach", type="primary", use_container_width=True)

if run:
    if not api_key:
        st.error("Add your Anthropic API key above or on the Home page.")
        st.stop()
    if not company_info.strip():
        st.error("Add some information about the target company.")
        st.stop()
    if not persona.strip():
        st.error("Specify who you are messaging.")
        st.stop()
    if not trigger.strip():
        st.error("Add a reason for reaching out â€” this is what makes the message feel relevant.")
        st.stop()

    with st.spinner("Writing BD messages..."):
        raw = generate_bd_outreach(
            company_info, persona, trigger, niche,
            message_type, tone, recruiter_name, recruiter_company,
            num_variants, api_key
        )

    variants = parse_variants(raw)

    if not variants:
        st.warning("Couldn't parse variants â€” showing raw output.")
        st.text(raw)
        st.stop()

    char_limit = (LINKEDIN_CONNECTION_LIMIT if message_type == "LinkedIn Connection Request"
                  else LINKEDIN_INMAIL_LIMIT if "LinkedIn" in message_type else None)

    st.subheader(f"{len(variants)} message variant(s) â€” {message_type}")

    for i, v in enumerate(variants, 1):
        label = f"Variant {i}"
        if v.get("subject"):
            label += f" â€” Subject: *{v['subject']}*"

        with st.expander(label, expanded=True):
            if v.get("subject"):
                st.markdown(f"**Subject:** {v['subject']}")
                st.divider()

            st.text_area(
                "Message",
                value=v["body"],
                height=200,
                key=f"bd_variant_{i}",
                label_visibility="collapsed"
            )

            count = v["char_count"] if v["char_count"] > 0 else len(v["body"])
            if char_limit:
                if count > char_limit:
                    st.error(f"{count} characters â€” {count - char_limit} over the {char_limit} limit")
                else:
                    st.success(f"{count} / {char_limit} characters")
            else:
                st.caption(f"{count} characters")

