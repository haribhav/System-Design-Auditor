import json
import os
from typing import Any

import requests
import streamlit as st

st.set_page_config(page_title="System Design Reviewer Demo", layout="wide")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DEFAULT_QUERY = "Review this design for production readiness"


def risk_badge(risk: str) -> str:
    risk_lower = (risk or "unknown").lower()
    if risk_lower == "high":
        return "🔴 high"
    if risk_lower == "medium":
        return "🟠 medium"
    if risk_lower == "low":
        return "🟢 low"
    return f"⚪ {risk_lower}"


def render_evidence_list(evidence: list[dict[str, Any]]) -> None:
    if not evidence:
        st.caption("No citations provided")
        return
    for ev in evidence:
        source_file = ev.get("source_file", "unknown")
        page = ev.get("page", 0)
        quote = ev.get("quote", "")
        st.markdown(f"- `{source_file}` p.{page}: {quote}")


def render_module(module_name: str, module_data: dict[str, Any]) -> None:
    score = module_data.get("score", "n/a")
    risk = module_data.get("risk", "unknown")
    with st.expander(f"{module_name} — score: {score}/10 — risk: {risk_badge(risk)}", expanded=False):
        findings = module_data.get("findings", [])
        if findings:
            st.subheader("Findings")
            for item in findings:
                st.markdown(f"**{item.get('title', 'Untitled')}** ({item.get('severity', 'unknown')})")
                st.write(item.get("details", ""))
                st.caption(f"Impact: {item.get('impact', '')}")
                render_evidence_list(item.get("evidence", []))

        recommendations = module_data.get("recommendations", [])
        if recommendations:
            st.subheader("Recommendations")
            for item in recommendations:
                st.markdown(f"**{item.get('title', 'Untitled')}** (effort: {item.get('effort', 'unknown')})")
                for step in item.get("steps", []):
                    st.markdown(f"- {step}")
                render_evidence_list(item.get("evidence", []))

        for field in ["questions_for_author", "missing_info", "assumptions"]:
            values = module_data.get(field, [])
            if values:
                st.subheader(field.replace("_", " ").title())
                for v in values:
                    st.markdown(f"- {v}")


st.title("System Design Reviewer — Demo Dashboard")
st.caption("Upload a PDF, ingest it, then run triage/targeted/deep analysis.")

with st.sidebar:
    st.header("Configuration")
    base_url = st.text_input("API Base URL", value=API_BASE_URL)
    ingest_token = st.text_input("Ingest Token", type="password")
    collection = st.text_input("Collection", value="default")
    mode = st.selectbox("Mode", options=["triage", "targeted", "deep"], index=1)
    top_k = st.number_input("top_k", min_value=1, max_value=20, value=6, step=1)
    budget_modules = st.slider("budget_modules", min_value=1, max_value=9, value=3)
    file_filter = st.text_input("file_filter (optional)", value="")

st.subheader("1) Upload and ingest PDF")
uploaded = st.file_uploader("Choose a PDF file", type=["pdf"])

if st.button("Ingest PDF", type="primary", disabled=uploaded is None):
    if not ingest_token:
        st.error("Please set ingest token in the sidebar.")
    elif uploaded is None:
        st.error("Please upload a PDF first.")
    else:
        files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
        headers = {"x-ingest-token": ingest_token}
        try:
            resp = requests.post(
                f"{base_url}/ingest",
                params={"collection": collection},
                headers=headers,
                files=files,
                timeout=120,
            )
            st.write(resp.status_code)
            st.json(resp.json())
        except Exception as exc:
            st.error(f"Ingest failed: {exc}")

st.subheader("2) Run analysis")
query = st.text_area("Query", value=DEFAULT_QUERY, height=100)

if st.button("Analyze", type="secondary"):
    payload = {
        "collection": collection,
        "query": query,
        "mode": mode,
        "top_k": int(top_k),
        "file_filter": file_filter or None,
        "budget_modules": int(budget_modules),
    }
    try:
        resp = requests.post(f"{base_url}/analyze", json=payload, timeout=180)
        if resp.status_code >= 400:
            st.error(f"Analyze failed [{resp.status_code}]: {resp.text}")
        else:
            data = resp.json()
            overall = data.get("overall", {})
            modules = data.get("modules", {})

            c1, c2 = st.columns(2)
            c1.metric("Overall Score", overall.get("score", 0))
            c2.metric("Confidence", overall.get("confidence", 0))

            triage = data.get("triage", {})
            with st.expander("Triage Output", expanded=True):
                st.json(triage)

            st.subheader("Module Reviews")
            if not modules:
                st.info("No modules executed for this mode.")
            for module_name, module_data in modules.items():
                render_module(module_name, module_data)

            with st.expander("Raw Response JSON"):
                st.code(json.dumps(data, indent=2), language="json")
    except Exception as exc:
        st.error(f"Analyze request failed: {exc}")
