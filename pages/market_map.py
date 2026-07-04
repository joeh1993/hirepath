import io
import json

import streamlit as st

from utils import (WEB_SEARCH_TOOL, extract_json, friendly_error, generate,
                   get_api_key)

# ── Prompt ───────────────────────────────────────────────────────────────────

MARKET_MAP_PROMPT = """You are a senior cyber security recruitment consultant with deep knowledge of the Australian technology and security market, particularly Sydney and the east coast. You are building a market map to help a recruiter identify and prioritise target companies.

ROLE TYPE: {role_type}
SENIORITY: {seniority}
LOCATION: {location}
INDUSTRY VERTICALS: {verticals}
COMPANY SIZE PREFERENCE: {sizes}
PURPOSE: {purpose}
ADDITIONAL CONTEXT: {context}

You have web search available. USE IT to ground this map in reality:
- Search for companies in {location} currently advertising {role_type} roles (LinkedIn, SEEK, careers pages)
- Search for recent news that creates hiring demand: funding rounds, breaches, compliance deadlines, new security leaders
- Verify that companies you name actually have a presence in {location}
Only put a company in Tier 1 if you found a live, current signal for it. If a company is included on inference alone, say so in its "signal" field (e.g. "Inferred - no live signal found, verify before calling").

Return a JSON object in EXACTLY this format. No preamble, no explanation, no markdown fences.

{{
  "summary": "2-3 sentence overview of this market segment in {location}. What is the hiring climate, how competitive is the talent pool, and what is driving demand right now?",
  "market_insights": [
    "Key insight 1 about this market",
    "Key insight 2 about this market",
    "Key insight 3 about this market",
    "Key insight 4 about this market"
  ],
  "tier_1": [
    {{
      "company": "Company name",
      "sector": "e.g. Financial Services",
      "size": "e.g. 500-2000 employees",
      "why_they_hire": "Why this company specifically hires this role. Be specific.",
      "team_size": "Estimated security team size e.g. 5-10",
      "who_to_target": "Job title(s) of the hiring decision maker",
      "bd_angle": "One sentence on the best way to approach this company",
      "signal": "The live signal you found (job ad, funding, breach, hire) with rough date - or 'Inferred' if none"
    }}
  ],
  "tier_2": [ (same object shape) ],
  "tier_3": [ (same object shape) ],
  "candidate_sourcing_tips": [
    "Tip 1 for finding candidates of this type in this market",
    "Tip 2",
    "Tip 3"
  ]
}}

RULES:
- Tier 1: 6-8 companies. Highest priority. Live hiring signal found via search.
- Tier 2: 8-10 companies. Good prospects. Likely hiring soon or ongoing need.
- Tier 3: 5-7 companies. Longer-term targets. Worth monitoring or a lighter touch.
- Use real Australian companies. Make sure the details are accurate to what you found or know.
- Be specific to {location} and the Australian market. Do not give generic global companies unless they have a significant {location} presence.
- Tailor everything to the role type and seniority provided.
- Do not use em dashes. Do not use the word "genuinely".
- Return ONLY the JSON object."""


# ── DOCX export ───────────────────────────────────────────────────────────────

def build_docx(data: dict, role_type: str, seniority: str, location: str) -> bytes:
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    def set_cell_bg(cell, hex_color: str):
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_color)
        tcPr.append(shd)

    def add_table_row(table, row_data: list, bold=False, bg=None, font_color=None):
        row = table.add_row()
        for i, text in enumerate(row_data):
            cell = row.cells[i]
            cell.text = str(text) if text else ""
            if bg:
                set_cell_bg(cell, bg)
            for para in cell.paragraphs:
                for run in para.runs:
                    run.bold = bold
                    run.font.size = Pt(9)
                    if font_color:
                        run.font.color.rgb = RGBColor(*font_color)

    doc = Document()

    for section in doc.sections:
        section.top_margin    = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin   = Cm(2)
        section.right_margin  = Cm(2)

    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = title_p.add_run("Market Map")
    tr.bold = True
    tr.font.size = Pt(20)
    tr.font.color.rgb = RGBColor(0x1A, 0x56, 0xDB)

    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_p.add_run(f"{seniority} {role_type}   |   {location}").font.size = Pt(11)

    doc.add_paragraph()

    doc.add_heading("Market Overview", level=1).runs[0].font.color.rgb = RGBColor(0x1A, 0x56, 0xDB)
    doc.add_paragraph(data.get("summary", ""))

    if data.get("market_insights"):
        doc.add_heading("Key Market Insights", level=2)
        for insight in data["market_insights"]:
            p = doc.add_paragraph(style="List Bullet")
            p.add_run(insight)

    doc.add_paragraph()

    tier_config = [
        ("tier_1", "Tier 1 Targets",  "1A56DB", "DBEAFE"),
        ("tier_2", "Tier 2 Targets",  "065F46", "D1FAE5"),
        ("tier_3", "Tier 3 Targets",  "92400E", "FEF3C7"),
    ]

    col_headers = ["Company", "Sector", "Size", "Why They Hire", "Team Size", "Who to Target", "BD Angle", "Signal"]
    col_widths_cm = [3.0, 2.5, 2.5, 4.5, 2.0, 3.0, 4.5, 3.5]

    for tier_key, tier_label, hdr_color, row_color in tier_config:
        companies = data.get(tier_key, [])
        if not companies:
            continue

        doc.add_heading(f"{tier_label} ({len(companies)} companies)", level=1).runs[0].font.color.rgb = RGBColor(
            int(hdr_color[0:2], 16), int(hdr_color[2:4], 16), int(hdr_color[4:6], 16)
        )

        table = doc.add_table(rows=1, cols=len(col_headers))
        table.style = "Table Grid"

        for i, width in enumerate(col_widths_cm):
            for cell in table.columns[i].cells:
                cell.width = Cm(width)

        hdr_row = table.rows[0]
        for i, header in enumerate(col_headers):
            cell = hdr_row.cells[i]
            cell.text = header
            set_cell_bg(cell, hdr_color)
            for para in cell.paragraphs:
                for run in para.runs:
                    run.bold = True
                    run.font.size = Pt(9)
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        for idx, company in enumerate(companies):
            row_data = [
                company.get("company", ""),
                company.get("sector", ""),
                company.get("size", ""),
                company.get("why_they_hire", ""),
                company.get("team_size", ""),
                company.get("who_to_target", ""),
                company.get("bd_angle", ""),
                company.get("signal", ""),
            ]
            bg = row_color if idx % 2 == 0 else "FFFFFF"
            add_table_row(table, row_data, bg=bg)

        doc.add_paragraph()

    if data.get("candidate_sourcing_tips"):
        doc.add_heading("Candidate Sourcing Tips", level=1).runs[0].font.color.rgb = RGBColor(0x1A, 0x56, 0xDB)
        for tip in data["candidate_sourcing_tips"]:
            p = doc.add_paragraph(style="List Bullet")
            p.add_run(tip)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("🗺️ Market Map Builder")
st.markdown("Identify and prioritise target companies for a specific role type - grounded in "
            "**live web search** for current job ads and hiring signals.")

api_key = get_api_key()

st.divider()

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Role Profile")

    role_type = st.selectbox(
        "Role type",
        options=[
            "Security Engineer",
            "SOC Analyst",
            "Penetration Tester / Ethical Hacker",
            "GRC Consultant",
            "Cloud Security Engineer",
            "Application Security Engineer",
            "CISO / Head of Security",
            "Security Architect",
            "Identity & Access Management (IAM) Specialist",
            "Threat Intelligence Analyst",
            "DevSecOps Engineer",
            "Incident Response Analyst",
            "Security Operations Manager",
            "Data Privacy / DPO",
            "Other (describe below)",
        ]
    )

    seniority = st.selectbox(
        "Seniority level",
        options=["Junior (0-2 yrs)", "Mid-level (2-5 yrs)", "Senior (5-8 yrs)",
                 "Lead / Manager (8+ yrs)", "Executive / CISO"]
    )

    location = st.selectbox(
        "Primary market",
        options=["Sydney", "Melbourne", "Brisbane", "Perth", "Canberra", "Australia-wide"]
    )

    st.subheader("Purpose")
    purpose = st.radio(
        "What are you mapping for?",
        options=[
            "BD targeting - companies to call for a new brief",
            "Candidate sourcing - companies where this talent sits",
            "Both BD and candidate sourcing",
        ],
    )

with col_right:
    st.subheader("Target Criteria")

    verticals = st.multiselect(
        "Industry verticals (select all that apply)",
        options=[
            "Financial Services & Banking",
            "Government & Defence",
            "Healthcare & Life Sciences",
            "Technology & SaaS",
            "Critical Infrastructure & Energy",
            "Consulting & Managed Security Services (MSSP)",
            "Retail & eCommerce",
            "Telecommunications",
            "Education",
            "Mining & Resources",
        ],
        default=["Financial Services & Banking", "Technology & SaaS", "Government & Defence"],
        help="Leave blank to cover all sectors"
    )

    sizes = st.multiselect(
        "Company size",
        options=[
            "Startup (under 50 employees)",
            "Scale-up (50-200 employees)",
            "Mid-market (200-1000 employees)",
            "Enterprise (1000+ employees)",
        ],
        default=["Mid-market (200-1000 employees)", "Enterprise (1000+ employees)"],
    )

    context = st.text_area(
        "Anything else to factor in? (optional)",
        height=120,
        placeholder="e.g. Client has asked us not to approach CBA or Westpac. Focus on companies with recent cyber incidents or compliance drivers like APRA CPS 234."
    )

st.divider()
run = st.button("Build Market Map", type="primary", use_container_width=True)

if run:
    if not api_key:
        st.error("Add your Anthropic API key in the sidebar first.")
        st.stop()

    prompt = MARKET_MAP_PROMPT.format(
        role_type=role_type,
        seniority=seniority,
        location=location,
        verticals=", ".join(verticals) if verticals else "All sectors",
        sizes=", ".join(sizes) if sizes else "All sizes",
        purpose=purpose,
        context=context or "No additional context provided.",
    )

    with st.spinner(f"Searching live job ads and mapping the {seniority} {role_type} market "
                    f"in {location}... this takes 1-2 minutes"):
        try:
            raw = generate(api_key, prompt, max_tokens=8000, tools=[WEB_SEARCH_TOOL])
            data = extract_json(raw)
        except json.JSONDecodeError:
            st.error("Claude returned output that couldn't be parsed. Try again.")
            st.stop()
        except Exception as e:
            st.error(friendly_error(e))
            st.stop()

    st.session_state.market_map = {
        "data": data, "role_type": role_type, "seniority": seniority, "location": location,
    }

# ── Results (persist across reruns) ──────────────────────────────────────────

state = st.session_state.get("market_map")
if state:
    data = state["data"]
    role_type = state["role_type"]
    seniority = state["seniority"]
    location = state["location"]

    st.divider()
    st.subheader(f"{seniority} {role_type} Market — {location}")
    st.caption("⚠️ Built from live search plus market knowledge. Companies marked "
               "'Inferred' had no live signal - verify before calling.")

    if data.get("summary"):
        st.info(data["summary"])

    if data.get("market_insights"):
        with st.expander("📊 Key Market Insights", expanded=True):
            for insight in data["market_insights"]:
                st.markdown(f"- {insight}")

    st.divider()

    safe_role = role_type.replace("/", "-").replace(" ", "_")
    docx_bytes = build_docx(data, role_type, seniority, location)

    dl1, dl2, _ = st.columns([1, 1, 2])
    with dl1:
        st.download_button(
            label="⬇️ Download Word (.docx)",
            data=docx_bytes,
            file_name=f"market_map_{safe_role}_{location}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            type="primary",
        )
    with dl2:
        st.download_button(
            label="⬇️ Download JSON",
            data=json.dumps(data, indent=2),
            file_name=f"market_map_{safe_role}_{location}.json",
            mime="application/json",
            use_container_width=True,
        )

    st.divider()

    tier_config = [
        ("tier_1", "🟢 Tier 1 — Priority Targets"),
        ("tier_2", "🟡 Tier 2 — Good Prospects"),
        ("tier_3", "🟠 Tier 3 — Watch List"),
    ]

    for tier_key, tier_label in tier_config:
        companies = data.get(tier_key, [])
        if not companies:
            continue

        st.subheader(f"{tier_label} ({len(companies)} companies)")

        for company in companies:
            name = company.get("company", "Unknown")
            sector = company.get("sector", "")
            size = company.get("size", "")
            with st.expander(f"**{name}** — {sector} | {size}", expanded=True):
                c1, c2 = st.columns([1, 1])
                with c1:
                    st.markdown(f"**Why they hire:** {company.get('why_they_hire', '')}")
                    st.markdown(f"**Security team size:** {company.get('team_size', '')}")
                    st.markdown(f"**Who to target:** {company.get('who_to_target', '')}")
                with c2:
                    st.markdown(f"**BD angle:** {company.get('bd_angle', '')}")
                    st.markdown(f"**Signal:** {company.get('signal', '')}")

        st.divider()

    if data.get("candidate_sourcing_tips"):
        with st.expander("💡 Candidate Sourcing Tips", expanded=True):
            for tip in data["candidate_sourcing_tips"]:
                st.markdown(f"- {tip}")
