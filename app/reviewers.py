from __future__ import annotations

import json

from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.prompts import MODULE_PROMPT_TEMPLATE, TRIAGE_PROMPT


def _extract_json(text: str) -> dict:
    cleaned = text.strip().strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


def _invoke_json(llm: ChatOpenAI, prompt: str) -> dict:
    response = llm.invoke(prompt)
    content = response.content if isinstance(response.content, str) else str(response.content)
    try:
        return _extract_json(content)
    except Exception:
        retry = llm.invoke(prompt + "\n\nReturn JSON only, no markdown.")
        retry_content = retry.content if isinstance(retry.content, str) else str(retry.content)
        return _extract_json(retry_content)


def _build_llm() -> ChatOpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for analysis operations")
    return ChatOpenAI(model=settings.model_name, api_key=settings.openai_api_key, temperature=0)


def run_triage(context_text: str, user_query: str) -> dict:
    llm = _build_llm()
    prompt = (
        f"{TRIAGE_PROMPT}\n\n"
        f"User query:\n{user_query}\n\n"
        f"Retrieved context:\n{context_text}\n"
    )
    return _invoke_json(llm, prompt)


def run_module_review(module_name: str, context_text: str, user_query: str) -> dict:
    llm = _build_llm()
    module_prompt = MODULE_PROMPT_TEMPLATE.format(module_name=module_name)
    prompt = (
        f"{module_prompt}\n\n"
        f"User query:\n{user_query}\n\n"
        f"Retrieved context:\n{context_text}\n"
    )
    return _invoke_json(llm, prompt)
