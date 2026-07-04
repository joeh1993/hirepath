import streamlit as st

from utils import (WEB_SEARCH_TOOL, friendly_error, generate_streaming,
                   get_api_key, recruiter_details, scrub)

BD_RESEARCH_PROMPT = """You are a senior technical recruitment consultant preparing a call brief for a business development call. The recruiter needs to sound informed, ask smart questions, and position themselves as a specialist - not a generalist agency cold-calling.

COMPANY: {company_name}
WHAT THE RECRUITER KNOWS: {known_info}
HIRING NICHE / ROLES THEY PLACE: {niche}
PERSONA THEY ARE SPEAKING TO: {persona}
GOAL OF THE CALL: {call_goal}
RECRUITER NAME: {recruiter_name}
RECRUITER COMPANY: {recruiter_company}

You have web search available. USE IT before writing the brief:
- Search for the company's recent news, funding, leadership changes, and breaches or incidents
- Search for their current job ads (especially security / technical roles) on LinkedIn, SEEK, or their careers page
- Verify anything the recruiter told you where possible
Base the brief on what you actually find. If a search turns up nothing, say so rather than inventing detail. Clearly distinguish verified facts from reasonable inference.

Write a structured call brief with the following sections. Be specific and actionable - generic advice is useless.

## Company Snapshot
3-4 sentences. What they do, their market position, size/stage, anything notable and RECENT. The recruiter should be able to read this and sound informed in the first 30 seconds of a call.

## Why They Are Worth Calling
Based on what the recruiter shared plus what you found, explain specifically why this company is a good BD target right now. Cite the concrete signals (live job ads, funding, incidents, hires).

## Likely Hiring Challenges
What specific recruitment pain points does a company like this face? Think about: the talent market for their roles, competition for candidates, internal HR capability, typical hiring speed. Be specific to their industry and size, not generic.

## Conversation Starters
Give 3 specific openers the recruiter could use in the first 2 minutes. These should reference something real and current about the company or their industry - not "I've been following your growth."

## Smart Questions to Ask
5 questions that will uncover budget, urgency, process, and decision-making authority - while making the recruiter sound like a market specialist, not an order-taker. Mix commercial questions with insight-led ones.

## How to Position {recruiter_company}
Tailor the pitch specifically for this company. What angle works best here - speed, niche expertise, candidate network, market knowledge? Give the recruiter 3-4 sentences they could actually say on the call.

## Likely Objections and How to Handle Them
List 3 likely pushbacks (e.g. "we have a PSL", "we hire direct", "we're not hiring right now") with a short, confident response to each. Not aggressive - smart and consultative.

## One Thing to Remember
One specific insight or angle that will make this call stand out from the 10 other recruiters who probably called this week.

CRITICAL RULES:
- No em dashes or double hyphens
- Never use the words "genuinely" or "leverage"
- No "touch base" or "circle back"
- Be direct and specific throughout
- Write for a recruiter who has 5 minutes to read this before a call"""


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("🔍 BD Research & Call Prep")
st.markdown("A full call brief before any BD conversation - grounded in **live web search**, "
            "not just the model's memory.")

api_key = get_api_key()
recruiter_name, recruiter_company, niche = recruiter_details()

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
        placeholder="e.g. Series B fintech, ~300 employees, been posting security roles on LinkedIn for 2 months with no agency logos. Based in Sydney CBD."
    )

with col_right:
    st.subheader("The Call")

    persona = st.text_input(
        "Who are you speaking to?",
        placeholder="e.g. CISO, CTO, Head of Engineering, HR Director, Talent Acquisition Lead"
    )

    call_goal = st.selectbox(
        "Goal of this call",
        [
            "First introduction - establish the relationship",
            "Pitch for a specific open role",
            "Follow up after sending a speculative candidate",
            "Re-engage a lapsed client",
            "Qualify whether they have hiring needs",
        ]
    )

    st.markdown("##### How this tool works")
    st.markdown("""
The brief is built from:
- **Live web search** - recent news, funding, current job ads
- What you tell it about the company
- Market knowledge of companies of this type and size

Verified facts and inference are flagged separately in the brief.
""")

st.divider()

run = st.button("Generate Call Brief", type="primary", use_container_width=True)

if run:
    if not api_key:
        st.error("Add your Anthropic API key in the sidebar first.")
        st.stop()
    if not company_name.strip():
        st.error("Enter the company name.")
        st.stop()
    if not persona.strip():
        st.error("Specify who you are speaking to.")
        st.stop()

    prompt = BD_RESEARCH_PROMPT.format(
        company_name=company_name,
        known_info=known_info or "Nothing specific - research them from scratch.",
        niche=niche or "technical / cyber security recruitment",
        persona=persona,
        call_goal=call_goal,
        recruiter_name=recruiter_name or "the recruiter",
        recruiter_company=recruiter_company or "our firm",
    )

    st.caption(f"Researching {company_name} with live web search - this takes 30-90 seconds. "
               "The brief streams in below as it's written.")
    placeholder = st.empty()
    try:
        brief = generate_streaming(api_key, prompt, placeholder,
                                   max_tokens=4096, tools=[WEB_SEARCH_TOOL])
    except Exception as e:
        st.error(friendly_error(e))
        st.stop()

    st.session_state.bd_brief = {"company": company_name, "brief": scrub(brief)}

# ── Results (persist across reruns) ──────────────────────────────────────────

state = st.session_state.get("bd_brief")
if state:
    brief = state["brief"]
    st.divider()
    st.subheader(f"Call Brief: {state['company']}")
    st.caption("Read this in the 5 minutes before your call. Key sections are expanded.")

    sections = brief.split("## ")
    if len(sections) > 1:
        for section in sections[1:]:
            lines = section.strip().split("\n", 1)
            title = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ""
            expanded = any(t in title for t in
                           ["Conversation Starters", "Smart Questions", "One Thing to Remember"])
            with st.expander(f"**{title}**", expanded=expanded):
                st.markdown(body)
    else:
        st.markdown(brief)

    st.divider()
    with st.expander("Full brief (copy all)"):
        st.code(brief, language=None, wrap_lines=True)
