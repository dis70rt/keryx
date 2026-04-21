"""RAG-powered sender context retrieval.

Instead of dumping the entire resume + projects into the Copywriter's prompt,
we embed them into a local ChromaDB vector store and retrieve only the most
relevant chunks based on the target's tech stack and skills.
"""

import re
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings


class SenderRAG:
    """Manages a persistent local vector store of the sender's context.

    Uses ChromaDB's built-in default embedding function (all-MiniLM-L6-v2)
    which runs locally on CPU — no GPU or external API needed.
    """

    COLLECTION_NAME = "sender_context"

    def __init__(self, persist_dir: Path) -> None:
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    # ── Indexing ───────────────────────────────────────────────

    def build_index(self, resume_text: str, projects_text: str) -> int:
        """Chunk and embed the sender's resume and projects.

        Returns the total number of chunks indexed.
        Skips re-indexing if the collection already has documents.
        """
        if self._collection.count() > 0:
            return self._collection.count()

        chunks: list[str] = []
        ids: list[str] = []
        metadatas: list[dict] = []

        # Resume: split by bullet points or line breaks
        resume_bullets = _split_resume(resume_text)
        for i, bullet in enumerate(resume_bullets):
            bullet = bullet.strip()
            if len(bullet) < 15:
                continue
            chunks.append(bullet)
            ids.append(f"resume_{i}")
            metadatas.append({"source": "resume", "type": "experience"})

        # Projects: each project is its own chunk
        project_entries = _split_projects(projects_text)
        for i, entry in enumerate(project_entries):
            entry = entry.strip()
            if len(entry) < 15:
                continue
            chunks.append(entry)
            ids.append(f"project_{i}")
            metadatas.append({"source": "projects", "type": "project"})

        if not chunks:
            return 0

        self._collection.add(
            documents=chunks,
            ids=ids,
            metadatas=metadatas,
        )
        return len(chunks)

    # ── Retrieval ──────────────────────────────────────────────

    def retrieve(self, query: str, k: int = 3) -> str:
        """Retrieve the top-k most relevant sender context chunks.

        Args:
            query: A string built from the target's skills and tech stack.
            k: Number of chunks to retrieve.

        Returns:
            A formatted string of the most relevant sender context.
        """
        if self._collection.count() == 0:
            return "No sender context indexed."

        results = self._collection.query(
            query_texts=[query],
            n_results=min(k, self._collection.count()),
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        if not docs:
            return "No relevant sender context found."

        formatted_parts: list[str] = []
        for doc, meta in zip(docs, metas):
            source_label = meta.get("source", "unknown").upper()
            formatted_parts.append(f"[{source_label}] {doc}")

        return "\n\n".join(formatted_parts)

    def reset(self) -> None:
        """Delete and recreate the collection (for re-indexing)."""
        self._client.delete_collection(self.COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )


# ── Chunking helpers ──────────────────────────────────────────


def _split_resume(text: str) -> list[str]:
    """Split cleaned resume text into meaningful bullet-level chunks.

    Groups section headers with their content so each chunk has context.
    """
    lines = text.strip().splitlines()
    chunks: list[str] = []
    current_section = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect section headers (all-caps lines or lines ending with colon)
        if stripped.isupper() or re.match(r"^[A-Z][a-zA-Z\s]+:?$", stripped):
            current_section = stripped.rstrip(":")
            continue

        # Prefix each bullet with its section for context
        if current_section:
            chunks.append(f"{current_section}: {stripped}")
        else:
            chunks.append(stripped)

    return chunks


def _split_projects(text: str) -> list[str]:
    """Split project context (one project per line, prefixed with '-')."""
    entries: list[str] = []
    for line in text.strip().splitlines():
        line = line.strip()
        if line.startswith("- "):
            entries.append(line[2:])
        elif line:
            entries.append(line)
    return entries
