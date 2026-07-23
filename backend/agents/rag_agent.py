import chromadb

from core.config import settings

COLLECTION = "knowledge_base"  # chroma requires 3-63 chars
_client = None  # ponytail: lazy singleton, chromadb.PersistentClient is a factory fn


def _collection():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
    return _client.get_or_create_collection(COLLECTION)


def _chunk(text: str, max_chars: int = 500) -> list[str]:
    """Split on paragraph boundaries, packing paragraphs into ~max_chars chunks."""
    chunks, buf = [], ""
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if buf and len(buf) + len(para) + 2 > max_chars:
            chunks.append(buf)
            buf = para
        else:
            buf = f"{buf}\n\n{para}" if buf else para
    if buf:
        chunks.append(buf)
    return chunks


def seed_if_empty(seed_file: str | None = None) -> int:
    col = _collection()
    if col.count() > 0:
        return 0
    path = seed_file or settings.KB_SEED_FILE
    with open(path, encoding="utf-8") as f:
        chunks = _chunk(f.read())
    col.add(
        documents=chunks,
        ids=[f"kb-{i}" for i in range(len(chunks))],
        metadatas=[{"source": path} for _ in chunks],
    )
    return len(chunks)


def retrieve(query: str, k: int = 3) -> str:
    col = _collection()
    if col.count() == 0:
        return ""
    res = col.query(query_texts=[query], n_results=min(k, col.count()))
    docs = res.get("documents", [[]])[0]
    return "\n\n".join(docs)
