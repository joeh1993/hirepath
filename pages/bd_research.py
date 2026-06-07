import streamlit as st
import anthropic


BD_RESEARCH_PROMPT = """You are a senior technical recruitment consultant preparing a call brief for a business development call. The recruiter needs to sound informed, ask smart questions, and position themselves as a specialist â€” not a generalist agency cold-calling.

COMPANY: {company_name}
WHAT THE RECRUITER KNOWS: {known_info}
HIRING NICHE / ROLES THEY PLACE: {niche}
PERSONA THEY ARE SPEAKING TO: {persona}
GOAL OF THE CALL: {call_goal}
RECRUITER NAME: {recruiter_name}
RECRUITER COMPANY: {recruiter_company}

Write a structured call brief with the following sections. Be specific and actionable â€” generic advice is useless. Where you have knowledge of this company, use it. Where you don't, reason from what you know about companies of this type, size, and industry.

---

## Company Snapshot
3-4 sentences. What they do, their market position, size/stage if known, anything notable. The recruiter should be able to read this and sound informed in the first 30 seconds of a call.

## Why They Are Worth Calling
Based on what the recruiter has shared, explain specifically why this company is a good BD target right now. What signals suggest they have hiring needs or pain points your recruiter can solve?

## Likely Hiring Challenges
What specific recruitment pain points does a company like this typically face? Think about: the talent market for their roles, competition for candidates, internal HR capability, typical hiring speed. Be specific to their industry and size, not generic.

## Conversation Starters
Give 3 specific openers the recruiter could use in the first 2 minutes. These should reference something real about the company or their industry â€” not "I've been following your growth" or "I work with companies like yours."

## Smart Questions to Ask
5 questions that will uncover budget, urgency, process, and decision-making authority â€” while making the recruiter sound like a market specialist, not an order-taker. Mix commercial questions with insight-led ones.

## How to Position {recruiter_company}
Tailor the pitch specifically for this company. What angle works best here â€” speed, niche expertise, candidate network, market knowledge? Give the recruiter 3-4 sentences they could actually say on the call.

## Likely Objections and How to Handle Them
List 3 likely pushbacks (e.g. "we have a PSL", "we hire direct", "we're not hiring right now") with a short, confident response to each. Not aggressive â€” smart and consultative.

## One Thing to Remember
One specific insight or angle that will make this call stand out from the 10 other recruiters who probably called this week.

---

CRITICAL RULES:
- No em dashes (â€” or --)
- No word "genuinely"
- No word "leverage"
- No "touch base" or "circle back"
- Be direct and specific throughout
- Write for a recruiter who has 5 minutes to read this before a call"""


def generate_bd_research(company_name, known_info, niche, persona, call_goal,
                          recruiter_name, recruiter_company, api_key):
    client = anthropic.Anthropic(api_key=api_key)

    prompt = BD_RESEARCH_PROMPT.format(
        company_name=company_name,
        known_info=known_info or "Nothing specific â€” use your knowledge of the company and industry.",
        niche=niche or "technical / cyber security recruitment",
        persona=persona or "Hiring Manager",
        call_goal=call_goal,
        recruiter_name=recruiter_name or "the recruiter",
        recruiter_company=recruiter_company or "our firm",
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )

    output = message.content[0].text
    output = output.replace("â€”", "-").replace("--", "-")
    output = output.replace("genuinely", "clearly")
    output = output.replace("leverage", "use")
    return output


# â”€â”€ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

st.title("BD Research & Call Prep")
st.markdown("Get a full call brief before any BD conversation â€” sound informed, ask smart questions, win the meeting.")

api_key = st.session_state.get("api_key", "")
if not api_key:
    api_key = st.text_input("Anthropic API Key", type="password",
                             help="Or set it on the Home page")
    if api_key:
        st.session_state.api_key = api_key

st.divider()

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("The Company")

    company_name = st.text_input(
        "Company name",
        placeholder="e.g. Canva, CBA, Atlassian, AUCloud"
    )

    known_info = st.text_area(
        "What do you already know about them?",
        height=150,
        placeholder="e.g. Series B fintech, ~300 employees, been posting security roles on LinkedIn for 2 months with no agency logos. Based in Sydney CBD. Think they have a CISO but no dedicated security team beneath them yet."
    )

    st.subheader("The Call")

    persona = st.text_input(
        "Who are you speaking to?",
        placeholder="e.g. CISO, CTO, Head of Engineering, HR Director, Talent Acquisition Lead"
    )

    call_goal = st.selectbox(
        "Goal of this call",
        [
            "First introduction â€” establish the relationship",
            "Pitch for a specific open role",
            "Follow up after sending a speculative candidate",
            "Re-engage a lapsed client",
            "Qualify whether they have hiring needs",
        ]
    )

with col_right:
    st.subheader("Your Details")

    recruiter_name = st.text_input("Your name", placeholder="Joel Heywood")
    recruiter_company = st.text_input("Your company", placeholder="Novus Pathway")
    niche = st.text_input(
        "Your niche",
        placeholder="e.g. Cyber security recruitment across Australia",
        help="Used to tailor the pitch angle and questions"
    )

    st.divider()
    st.markdown("##### How this tool works")
    st.markdown("""
The brief is built from:
- What you tell it about the company
- Claude's training knowledge of the company and industry
- Frameworks for what companies of this type typically face

For best results, add as much context as you know in the field above. The more specific you are, the sharper the brief.
""")

st.divider()

run = st.button("Generate Call Brief", type="primary", use_container_width=True)

if run:
    if not api_key:
        st.error("Add your Anthropic API key above or on the Home page.")
        st.stop()
    if not company_name.strip():
        st.error("Enter the company name.")
        st.stop()
    if not persona.strip():
        st.error("Specify who you are speaking to.")
        st.stop()

    with st.spinner(f"Researching {company_name} and building your call brief..."):
        brief = generate_bd_research(
            company_name, known_info, niche, persona,
            call_goal, recruiter_name, recruiter_company, api_key
        )

    st.divider()
    st.subheader(f"Call Brief: {company_name}")
    st.caption("Read this in the 5 minutes before your call. Key sections are expandable.")

    # Parse and display each section
    sections = brief.split("## ")
    if len(sections) > 1:
        for section in sections[1:]:
            lines = section.strip().split("\n", 1)
            title = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ""

            # Highlight the most important sections
            expanded = title in ["Conversation Starters", "Smart Questions to Ask", "One Thing to Remember"]

            with st.expander(f"**{title}**", expanded=expanded):
                st.markdown(body)
    else:
        # Fallback: just show the raw output
        st.markdown(brief)

    st.divider()
    with st.expander("Full brief (copy all)"):
        st.text_area("", value=brief, height=400, label_visibility="collapsed")
        st.caption("Select all (Ctrl+A) to copy the full brief.")

