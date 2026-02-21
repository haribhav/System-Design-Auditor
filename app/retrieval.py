from __future__ import annotations

from langchain_core.documents import Document

from app.config import get_settings
from app.store import get_vectorstore


def retrieve_context(collection: str, query: str, top_k: int, file_filter: str | None = None) -> tuple[list[dict], str]:
    settings = get_settings()
    vectorstore = get_vectorstore(collection, require_embeddings=True)

    filters = {"source_file": file_filter} if file_filter else None
    docs: list[Document] = vectorstore.similarity_search(query=query, k=top_k, filter=filters)

    context_items: list[dict] = []
    total_chars = 0

    for doc in docs:
        quote = doc.page_content[: settings.max_chunk_chars]
        if total_chars + len(quote) > settings.max_context_chars:
            break
        total_chars += len(quote)
        context_items.append(
            {
                "source_file": doc.metadata.get("source_file", "unknown"),
                "page": int(doc.metadata.get("page", 0)),
                "quote": quote,
            }
        )

    context_text = "\n\n".join(
        f"[source_file={item['source_file']} page={item['page']}]\n{item['quote']}" for item in context_items
    )
    return context_items, context_text
