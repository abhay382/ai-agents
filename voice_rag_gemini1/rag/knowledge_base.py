"""
rag/knowledge_base.py
RAG knowledge base using ChromaDB with its built-in embedding function.
NO torch, NO sentence-transformers, NO build errors.
Uses chromadb.utils.embedding_functions.DefaultEmbeddingFunction
which runs via onnxruntime — pure pip install, works on any Windows/Mac/Linux.
"""
from __future__ import annotations
import hashlib
from pathlib import Path

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from rich.console import Console
from rich.progress import track

console = Console()

CHUNK_SIZE    = 500
CHUNK_OVERLAP = 80


class KnowledgeBase:
    """ChromaDB RAG store — no torch needed, pure onnxruntime embeddings."""

    def __init__(self, persist_dir: str = "data/chroma_db"):
        self.persist_dir = persist_dir
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        console.print("[dim]Loading embedding model (onnxruntime, no torch)...[/dim]")

        # DefaultEmbeddingFunction uses all-MiniLM-L6-v2 via onnxruntime
        # Downloads ~23 MB on first run, then cached locally
        self._embed_fn = DefaultEmbeddingFunction()

        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name="agent_knowledge",
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )
        console.print(f"[green]✓ Knowledge base ready[/green] ({self.collection.count()} chunks stored)")

    # ─── Ingestion ────────────────────────────────────────────────────────────

    def add_text(self, text: str, source: str = "manual") -> int:
        """Split text into chunks and store. Returns number of chunks added."""
        chunks = self._split(text)
        if not chunks:
            return 0
        return self._upsert(chunks, source)

    def add_file(self, path: str) -> int:
        """Ingest a .txt, .md, or .pdf file."""
        p = Path(path)
        if not p.exists():
            console.print(f"[red]File not found:[/red] {path}")
            return 0
        suffix = p.suffix.lower()
        if suffix in (".txt", ".md"):
            text = p.read_text(encoding="utf-8", errors="ignore")
        elif suffix == ".pdf":
            text = self._read_pdf(path)
        else:
            console.print(f"[yellow]Skipping unsupported file:[/yellow] {p.name}")
            return 0
        added = self.add_text(text, source=p.name)
        console.print(f"[green]✓ Ingested[/green] {p.name} → {added} chunks")
        return added

    def add_folder(self, folder: str) -> int:
        """Ingest all .txt / .md / .pdf files in a folder."""
        total = 0
        files = list(Path(folder).rglob("*"))
        for f in track(files, description="Ingesting files…"):
            if f.suffix.lower() in (".txt", ".md", ".pdf"):
                total += self.add_file(str(f))
        return total

    # ─── Retrieval ────────────────────────────────────────────────────────────

    def query(self, question: str, top_k: int = 4) -> list[dict]:
        """Return top-k relevant chunks for a question."""
        if self.collection.count() == 0:
            return []
        results = self.collection.query(
            query_texts=[question],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append({
                "text":   doc,
                "source": meta.get("source", "unknown"),
                "score":  round(1 - dist, 3),
            })
        return chunks

    def format_context(self, question: str, top_k: int = 4) -> str:
        """Return formatted context string to inject into the prompt."""
        chunks = self.query(question, top_k)
        if not chunks:
            return ""
        lines = ["[KNOWLEDGE BASE CONTEXT]"]
        for i, c in enumerate(chunks, 1):
            lines.append(f"\n--- Source {i}: {c['source']} (relevance {c['score']}) ---")
            lines.append(c["text"])
        lines.append("[END CONTEXT]")
        return "\n".join(lines)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _split(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        chunks, start = [], 0
        while start < len(text):
            chunks.append(text[start:start + CHUNK_SIZE])
            start += CHUNK_SIZE - CHUNK_OVERLAP
        return [c.strip() for c in chunks if c.strip()]

    def _upsert(self, chunks: list[str], source: str) -> int:
        ids = [hashlib.md5(f"{source}::{c}".encode()).hexdigest() for c in chunks]
        self.collection.upsert(
            ids=ids,
            documents=chunks,
            metadatas=[{"source": source}] * len(chunks),
        )
        return len(chunks)

    @staticmethod
    def _read_pdf(path: str) -> str:
        try:
            import pypdf
            reader = pypdf.PdfReader(path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            console.print("[yellow]Install pypdf to use PDFs:[/yellow] pip install pypdf")
            return ""
