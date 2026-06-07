import streamlit as st
import anthropic


LINKEDIN_INMAIL_LIMIT = 1900
LINKEDIN_CONNECTION_LIMIT = 300

OUTREACH_PROMPT = """You are an expert technical recruitment consultant writing personalised outreach messages. Your messages are known for feeling genuinely personal â€” never templated or spammy.

CANDIDATE INFORMATION:
{candidate_info}

ROLE DETAILS:
{role_details}

YOUR NAME: {recruiter_name}
YOUR COMPANY: {recruiter_company}

MESSAGE TYPE: {message_type}
TONE: {tone}

Write {num_variants} distinct outreach message variant(s). Each should:
1. Open with something specific to THIS candidate â€” reference their actual background, a career move, a skill, a company they've worked at. Never open with "I came across your profile" or "Hope this message finds you well."
2. Be genuinely about them first, the role second
3. Pitch the role concisely â€” focus on what makes it compelling (not just a job ad)
4. End with a soft, low-pressure call to action (not "please let me know if you're interested")
5. Feel like it was written for this specific person, not copy-pasted

CRITICAL RULES:
- Never use em dashes (â€” or --)
- Never use the word "leverage"
- Never use the word "genuinely"
- Never use "I wanted to reach out"
- Never use "touch base"
- No bullet points in the message body

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

(and so on for each variant)

Do not include any explanation or commentary outside of this format."""

TYPE_INSTRUCTIONS = {
    "LinkedIn InMail": (
        "Keep the body under 1,900 characters. No subject line needed â€” just the message body.",
        "SUBJECT: [subject line, max 200 chars]\n",
        "SUBJECT: [subject line, max 200 chars]\n"
    ),
    "LinkedIn Connection Request": (
        "CRITICAL: Keep the message under 300 characters total â€” this is a hard LinkedIn limit. Be punchy and intriguing. No subject line.",
        "",
        ""
    ),
    "Email": (
        "Write a compelling subject line. Keep the body conversational â€” emails that read like emails, not job ads.",
        "SUBJECT: [subject line]\n",
        "SUBJECT: [subject line]\n"
    ),
}

TONE_DESCRIPTORS = {
    "Professional": "Polished and confident. Formal enough for a senior hire, but not stiff.",
    "Warm & Conversational": "Friendly and human. Reads like a message from someone who genuinely wants to connect.",
    "Direct": "Get to the point fast. No fluff. Respect their time.",
}


def generate_outreach(candidate_info, role_details, message_type, tone, recruiter_name, recruiter_company, num_variants, api_key):
    client = anthropic.Anthropic(api_key=api_key)

    type_instr, subj_line_instr, _ = TYPE_INSTRUCTIONS[message_type]

    prompt = OUTREACH_PROMPT.format(
        candidate_info=candidate_info,
        role_details=role_details,
        recruiter_name=recruiter_name or "the recruiter",
        recruiter_company=recruiter_company or "our firm",
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


def parse_variants(raw_text, message_type):
    """Split raw Claude output into individual variant blocks."""
    variants = []
    blocks = raw_text.split("VARIANT ")
    for block in blocks[1:]:
        lines = block.strip().split("\n")
        # First line is the variant number â€” skip it
        content = "\n".join(lines[1:]).strip()
        # Strip trailing character count line
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

        # Extract subject line if present
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

st.title("Outreach Generator")
st.markdown("Generate personalised LinkedIn and email messages that actually get replies.")

api_key = st.session_state.get("api_key", "")
if not api_key:
    api_key = st.text_input("Anthropic API Key", type="password",
                             help="Or set it on the Home page")
    if api_key:
        st.session_state.api_key = api_key

st.divider()

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Candidate")
    candidate_info = st.text_area(
        "Paste their LinkedIn bio, CV summary, or describe them",
        height=200,
        placeholder="e.g. 5 years as a SOC Analyst at CrowdStrike, recently moved to a Threat Intelligence Lead role at a Big 4 consultancy. CISSP certified. Based in Sydney. Posts regularly about cloud security on LinkedIn."
    )

    st.subheader("Role")
    role_details = st.text_area(
        "Describe the opportunity",
        height=150,
        placeholder="e.g. Senior Security Engineer at a fast-growing fintech in Sydney CBD. $180-200k + equity. Greenfield security program, reporting to CISO. Hybrid 3 days in office. Client is open to considering people from consulting backgrounds."
    )

with col_right:
    st.subheader("Settings")

    message_type = st.selectbox(
        "Message type",
        ["LinkedIn InMail", "LinkedIn Connection Request", "Email"],
        help="Connection requests are capped at 300 characters"
    )

    tone = st.selectbox(
        "Tone",
        ["Professional", "Warm & Conversational", "Direct"]
    )

    num_variants = st.slider("Number of variants", min_value=1, max_value=3, value=2)

    st.markdown("**Your details** *(appear in the sign-off)*")
    recruiter_name = st.text_input("Your name", placeholder="Joel Heywood")
    recruiter_company = st.text_input("Your company", placeholder="Novus Pathway")

st.divider()

run = st.button("Generate Outreach", type="primary", use_container_width=True)

if run:
    if not api_key:
        st.error("Add your Anthropic API key above or on the Home page.")
        st.stop()
    if not candidate_info.strip():
        st.error("Add some candidate information.")
        st.stop()
    if not role_details.strip():
        st.error("Describe the role.")
        st.stop()

    with st.spinner("Writing personalised messages..."):
        raw = generate_outreach(
            candidate_info, role_details, message_type, tone,
            recruiter_name, recruiter_company, num_variants, api_key
        )

    variants = parse_variants(raw, message_type)

    if not variants:
        st.warning("Couldn't parse variants â€” showing raw output.")
        st.text(raw)
        st.stop()

    st.subheader(f"{len(variants)} message variant(s) â€” {message_type}")

    char_limit = LINKEDIN_CONNECTION_LIMIT if message_type == "LinkedIn Connection Request" else LINKEDIN_INMAIL_LIMIT if "LinkedIn" in message_type else None

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
                key=f"variant_{i}",
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

