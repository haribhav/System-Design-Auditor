from __future__ import annotations

import uuid
from collections import Counter
from pathlib import Path

from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings
from app.store import get_vectorstore


def _stable_chunk_id(source_file: str, page: int, chunk_text: str) -> str:
    payload = f"{source_file}|{page}|{chunk_text.strip()}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, payload))


def _split_documents(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(docs)


def ingest_pdf(upload_file: UploadFile, collection: str) -> dict:
    settings = get_settings()
    destination = settings.uploads_dir / Path(upload_file.filename).name
    destination.write_bytes(upload_file.file.read())

    loader = PyPDFLoader(str(destination))
    loaded_docs = loader.load()

    for doc in loaded_docs:
        doc.metadata = {**doc.metadata, "source_file": destination.name, "page": int(doc.metadata.get("page", 0))}

    split_docs = _split_documents(loaded_docs)

    ids: list[str] = []
    for doc in split_docs:
        source_file = doc.metadata.get("source_file", destination.name)
        page = int(doc.metadata.get("page", 0))
        ids.append(_stable_chunk_id(source_file, page, doc.page_content))

    vectorstore = get_vectorstore(collection, require_embeddings=True)
    vectorstore.add_documents(split_docs, ids=ids)

    chunk_count_by_file = Counter(doc.metadata.get("source_file", "unknown") for doc in split_docs)

    return {
        "collection": collection,
        "source_file": destination.name,
        "pages": len(loaded_docs),
        "chunks": len(split_docs),
        "chunk_count_by_file": dict(chunk_count_by_file),
    }


def list_ingested_files(collection: str) -> dict:
    vectorstore = get_vectorstore(collection, require_embeddings=False)
    raw = vectorstore._collection.get(include=["metadatas"])
    metadatas = raw.get("metadatas", []) or []

    counts: Counter[str] = Counter()
    for metadata in metadatas:
        if not metadata:
            continue
        counts[metadata.get("source_file", "unknown")] += 1

    return {"collection": collection, "files": [{"source_file": k, "chunks": v} for k, v in sorted(counts.items())]}
