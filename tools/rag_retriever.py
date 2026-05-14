"""
RAG (Retrieval-Augmented Generation) retriever for Open-Source Ghostwriter.

Pipeline:
    Step 1 – Parse the git diff to identify changed Python files.
    Step 2 – Read the full source content of each changed file.
    Step 3 – Chunk each file into function/class-level text blocks using AST.
    Step 4 – Embed each chunk using a local sentence-transformer model.
    Step 5 – Store all embeddings in an in-memory FAISS index.
    Step 6 – Query the index using the Analyzer's JSON summary.
    Step 7 – Return the top-k most relevant code chunks as plain text.
"""

from __future__ import annotations

import ast
import json
import logging
import re
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Lazy-loaded singletons (loaded once, reused across requests) ────────────
_embedding_model = None


def _get_embedding_model():
    """Load the sentence-transformer model once and cache it."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("RAG: loading embedding model (all-MiniLM-L6-v2)…")
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("RAG: embedding model loaded.")
    return _embedding_model


# ── Step 1: Identify changed files from the diff ────────────────────────────

def _extract_changed_files(diff: str) -> list[str]:
    """Parse a unified diff and return a list of changed file paths.

    Only returns Python (.py) files since we chunk using AST.
    Non-Python files are not chunked by AST but are still readable.
    """
    # Matches lines like: +++ b/src/calculator.py
    pattern = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)
    files = pattern.findall(diff)
    # Return unique list preserving order
    seen = set()
    unique = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique


# ── Step 2: Read full file content ──────────────────────────────────────────

def _read_file_safe(repo_path: str, relative_path: str) -> Optional[str]:
    """Read a file from the repo. Returns None if file doesn't exist."""
    full_path = Path(repo_path) / relative_path
    if not full_path.exists():
        logger.warning("RAG: file not found – %s", full_path)
        return None
    try:
        return full_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        logger.warning("RAG: could not read %s – %s", full_path, e)
        return None


# ── Step 3: Chunk files into function/class-level sections ──────────────────

def _chunk_python_file(source_code: str, file_path: str) -> list[str]:
    """Use Python's AST to split source code into function/class chunks.

    Each chunk is a self-contained text block (a complete function or class).
    Falls back to line-based chunking if AST parsing fails (e.g. syntax errors).
    """
    chunks = []
    lines = source_code.splitlines()

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        logger.warning("RAG: AST parse failed for %s – using line chunks.", file_path)
        # Fallback: split into 40-line chunks
        chunk_size = 40
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i: i + chunk_size]
            chunks.append("\n".join(chunk_lines))
        return chunks

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Only process top-level and class-level definitions
            start = node.lineno - 1          # 0-indexed
            end = node.end_lineno            # 1-indexed inclusive
            chunk_lines = lines[start:end]
            chunk_text = f"# File: {file_path}\n" + "\n".join(chunk_lines)
            chunks.append(chunk_text)

    # If AST found nothing (e.g., a file with only module-level code), use the whole file
    if not chunks:
        chunks.append(f"# File: {file_path}\n{source_code}")

    return chunks


def _chunk_generic_file(source_code: str, file_path: str) -> list[str]:
    """Chunk non-Python files by fixed-size line windows."""
    lines = source_code.splitlines()
    chunk_size = 50
    chunks = []
    for i in range(0, len(lines), chunk_size):
        chunk_lines = lines[i: i + chunk_size]
        chunk_text = f"# File: {file_path}\n" + "\n".join(chunk_lines)
        chunks.append(chunk_text)
    return chunks


# ── Steps 4 & 5: Embed chunks and build FAISS index ─────────────────────────

def _build_faiss_index(chunks: list[str]):
    """Embed all chunks and build an in-memory FAISS index.

    Returns:
        (index, chunks) tuple or (None, []) if faiss is unavailable.
    """
    import faiss

    model = _get_embedding_model()
    logger.info("RAG: embedding %d chunks…", len(chunks))

    embeddings = model.encode(chunks, show_progress_bar=False, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype="float32")

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)  # Inner Product = cosine similarity (with normalized vecs)
    index.add(embeddings)

    logger.info("RAG: FAISS index built with %d vectors (dim=%d).", index.ntotal, dimension)
    return index, chunks


# ── Step 6: Query the FAISS index ───────────────────────────────────────────

def _query_index(index, chunks: list[str], query: str, top_k: int = 5) -> list[str]:
    """Embed the query and retrieve the top-k most relevant chunks."""
    model = _get_embedding_model()
    query_vec = model.encode([query], normalize_embeddings=True)
    query_vec = np.array(query_vec, dtype="float32")

    distances, indices = index.search(query_vec, min(top_k, len(chunks)))
    results = [chunks[i] for i in indices[0] if i < len(chunks)]
    return results


# ── Step 7: Public entry point ───────────────────────────────────────────────

def retrieve_context(
    repo_path: str,
    diff: str,
    analysis: str,
    top_k: int = 5,
) -> str:
    """Full RAG pipeline: diff → changed files → chunks → FAISS → retrieved context.

    Args:
        repo_path:  Local path to the cloned repository.
        diff:       Raw unified diff string from git.
        analysis:   JSON string from the Analyzer LLM node.
        top_k:      Number of top code chunks to retrieve.

    Returns:
        A formatted string of the most relevant source code chunks,
        ready to be injected into the Writer's prompt.
    """
    # Step 1 — find changed files
    changed_files = _extract_changed_files(diff)
    if not changed_files:
        logger.info("RAG: no changed files detected in diff.")
        return ""

    logger.info("RAG: changed files detected – %s", changed_files)

    # Step 2 & 3 — read and chunk each file
    all_chunks: list[str] = []
    for rel_path in changed_files:
        content = _read_file_safe(repo_path, rel_path)
        if content is None:
            continue
        if rel_path.endswith(".py"):
            file_chunks = _chunk_python_file(content, rel_path)
        else:
            file_chunks = _chunk_generic_file(content, rel_path)
        all_chunks.extend(file_chunks)
        logger.info("RAG: %s → %d chunks", rel_path, len(file_chunks))

    if not all_chunks:
        logger.info("RAG: no chunks produced – skipping retrieval.")
        return ""

    # Steps 4 & 5 — embed and index
    index, chunks = _build_faiss_index(all_chunks)

    # Step 6 — build query from analyzer JSON
    try:
        parsed = json.loads(analysis)
        changes = parsed.get("changes", [])
        query_parts = [parsed.get("summary", "")]
        for change in changes:
            query_parts.append(change.get("name", ""))
            query_parts.append(change.get("summary", ""))
        query = " ".join(filter(None, query_parts))
    except (json.JSONDecodeError, AttributeError):
        query = analysis[:500]  # fallback: use raw text

    if not query.strip():
        query = "code changes documentation update"

    logger.info("RAG: querying index with: %s", query[:100])
    top_chunks = _query_index(index, chunks, query, top_k=top_k)

    # Step 7 — format as a readable context block
    if not top_chunks:
        return ""

    context_parts = ["The following source code is from the changed files and is relevant to the documentation update:\n"]
    for i, chunk in enumerate(top_chunks, 1):
        context_parts.append(f"--- Relevant Code Chunk {i} ---\n```python\n{chunk}\n```")

    retrieved_context = "\n\n".join(context_parts)
    logger.info("RAG: retrieved %d relevant chunks (%d chars).", len(top_chunks), len(retrieved_context))
    return retrieved_context
