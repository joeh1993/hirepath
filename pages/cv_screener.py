import io
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic
import pandas as pd
import streamlit as st

from utils import (MODEL, extract_json, extract_text, friendly_error,
                   get_api_key, paste_or_upload)

SCREEN_PROMPT = """You are an expert technical recruitment consultant with 10+ years of experience placing engineers and tech professionals. Evaluate this ONE candidate against the job description provided.

JOB DESCRIPTION:
{jd}

CANDIDATE CV (file: {filename}):
{cv}

Assess the candidate and return a single JSON object in this exact format:
{{
  "name": "Full name extracted from CV, or the filename if not found",
  "score": <integer 1-10, where 10 is a perfect match>,
  "tier": "Strong Yes | Yes | Maybe | No",
  "strengths": ["specific strength 1", "specific strength 2", "specific strength 3"],
  "gaps": ["specific gap 1", "specific gap 2"],
  "years_experience": <integer, estimated total relevant experience>,
  "current_role": "their current or most recent job title",
  "recommendation": "One punchy sentence on whether to progress them and why."
}}

Scoring guide:
- 9-10: Exceptional match, ticks every box, would excite any client
- 7-8: Strong match, minor gaps that are trainable
- 5-6: Partial match, worth a conversation
- 3-4: Significant gaps but some relevant experience
- 1-2: Poor fit

Be direct and specific - vague feedback is useless. Focus on technical skills, experience level, and role fit. Consider the candidate's FULL career history, not just their current role.
Return ONLY the JSON object. No preamble, no explanation, no markdown code fences."""

TIER_ICON = {"Strong Yes": "🟢", "Yes": "🟡", "Maybe": "🟠", "No": "🔴"}


def screen_one(client: anthropic.Anthropic, jd: str, filename: str, cv_text: str) -> dict:
    prompt = SCREEN_PROMPT.format(jd=jd[:10000], filename=filename, cv=cv_text[:30000])
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(b.text for b in resp.content if b.type == "text")
    result = extract_json(raw)
    result["file"] = filename
    return result


def results_dataframe(results: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{
        "Name": r.get("name", "Unknown"),
        "Score": r.get("score", ""),
        "Tier": r.get("tier", ""),
        "Current Role": r.get("current_role", ""),
        "Years Exp": r.get("years_experience", ""),
        "Strengths": "; ".join(r.get("strengths", [])),
        "Gaps": "; ".join(r.get("gaps", [])),
        "Recommendation": r.get("recommendation", ""),
        "File": r.get("file", ""),
    } for r in results])


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("📋 CV Screener")
st.markdown("Paste a job description, upload candidate CVs, and get a ranked, exportable shortlist. "
            "Each CV is screened individually so long CVs are read in full.")

api_key = get_api_key()

st.divider()

col_jd, col_cv = st.columns([1, 1])

with col_jd:
    st.subheader("Job Description")
    jd = paste_or_upload(
        "Job description",
        key="cvs_jd",
        height=350,
        placeholder="Include: role title, required skills, years of experience, responsibilities...",
        upload_hint="Drop the client's JD as a PDF, Word, or text file",
    )

with col_cv:
    st.subheader("Candidate CVs")
    uploaded_files = st.file_uploader(
        "Upload one or more CVs",
        accept_multiple_files=True,
        type=["pdf", "docx", "txt"],
        help="PDF and DOCX are best. Each CV is screened in its own request, in parallel."
    )
    if uploaded_files:
        st.caption(f"{len(uploaded_files)} file(s) ready to screen")

st.divider()

run = st.button("Screen Candidates", type="primary", use_container_width=True)

if run:
    if not api_key:
        st.error("Add your Anthropic API key in the sidebar first.")
        st.stop()
    if not jd.strip():
        st.error("Add the job description first - drop a file or paste it.")
        st.stop()
    if not uploaded_files:
        st.error("Upload at least one CV.")
        st.stop()

    progress = st.progress(0, text="Reading CVs...")
    candidates = []
    for i, f in enumerate(uploaded_files):
        candidates.append((f.name, extract_text(f)))
        progress.progress((i + 1) / (len(uploaded_files) * 2), text=f"Read: {f.name}")

    client = anthropic.Anthropic(api_key=api_key)
    results, errors = [], []
    total = len(candidates)
    done = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(screen_one, client, jd, name, text): name
            for name, text in candidates
        }
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                results.append(fut.result())
            except Exception as e:
                errors.append((name, friendly_error(e)))
            done += 1
            progress.progress(0.5 + done / (total * 2), text=f"Screened {done}/{total}")

    progress.empty()
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    st.session_state.cv_results = {"jd": jd, "results": results, "errors": errors}

# ── Results (persist across reruns so clicking around doesn't lose them) ─────

state = st.session_state.get("cv_results")
if state:
    results = state["results"]
    errors = state["errors"]

    for name, msg in errors:
        st.warning(f"Could not screen **{name}**: {msg}")

    if results:
        st.subheader(f"Results — {len(results)} candidate(s) screened")

        table_data = [{
            "": TIER_ICON.get(r.get("tier", ""), "⚪"),
            "Name": r.get("name", "Unknown"),
            "Score": f"{r.get('score', '?')}/10",
            "Tier": r.get("tier", "—"),
            "Current Role": r.get("current_role", "—"),
            "Exp (yrs)": r.get("years_experience", "—"),
        } for r in results]
        st.dataframe(table_data, use_container_width=True, hide_index=True)

        # Exports
        df = results_dataframe(results)
        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
        xlsx_buf = io.BytesIO()
        with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Shortlist")
        xlsx_buf.seek(0)

        dl1, dl2, _ = st.columns([1, 1, 2])
        with dl1:
            st.download_button("⬇️ Download Excel (.xlsx)", data=xlsx_buf.getvalue(),
                               file_name="cv_screening_shortlist.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True, type="primary")
        with dl2:
            st.download_button("⬇️ Download CSV", data=csv_bytes,
                               file_name="cv_screening_shortlist.csv",
                               mime="text/csv", use_container_width=True)

        st.divider()
        st.subheader("Detailed Assessments")

        for r in results:
            icon = TIER_ICON.get(r.get("tier", ""), "⚪")
            label = f"{icon} {r.get('name', 'Unknown')} — {r.get('score', '?')}/10 | {r.get('tier', '—')}"
            with st.expander(label):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Strengths**")
                    for s in r.get("strengths", []):
                        st.markdown(f"✓ {s}")
                with c2:
                    st.markdown("**Gaps**")
                    gaps = r.get("gaps", [])
                    if gaps:
                        for g in gaps:
                            st.markdown(f"✗ {g}")
                    else:
                        st.markdown("None identified")
                st.markdown(f"**Recommendation:** {r.get('recommendation', '—')}")
