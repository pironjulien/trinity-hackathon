"""
CORPUS/BRAIN/CODEBASE_INDEXER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: CODE RAG INDEXER 📚
PURPOSE: Index Trinity codebase for semantic search.
USAGE: python -m corpus.brain.cortex_mapper (or call index_codebase())
══════════════════════════════════════════════════════════════════════════════
"""

import ast
import asyncio
from pathlib import Path
from typing import Optional, Any
from loguru import logger

from corpus.dna.genome import ROOT_DIR, BRAIN_MEMORY_VECTOR_DIR

# ChromaDB Collection
COLLECTION_NAME = "trinity_codebase"
VECTOR_DB_PATH = str(BRAIN_MEMORY_VECTOR_DIR)


# SOTA 2026: Use ChromaDB's default local embedder (all-MiniLM-L6-v2)
# Benefits: Free, fast (~10ms), offline, consistent for code search
# The ONNX model is cached at ~/.cache/chroma/onnx_models/


class CodeChunk:
    """Represents a code chunk for embedding."""

    def __init__(
        self,
        file_path: str,
        node_type: str,  # "function", "class", "module"
        name: str,
        content: str,
        docstring: Optional[str] = None,
        start_line: int = 0,
        end_line: int = 0,
    ):
        self.file_path = file_path
        self.node_type = node_type
        self.name = name
        self.content = content
        self.docstring = docstring
        self.start_line = start_line
        self.end_line = end_line
        self.chunk_id = f"{file_path}:{name}:L{start_line}"

    def to_text(self) -> str:
        """Convert to embeddable text."""
        parts = [
            f"# File: {self.file_path}",
            f"# Type: {self.node_type}",
            f"# Name: {self.name}",
        ]
        if self.docstring:
            parts.append(f"# Doc: {self.docstring[:200]}")
        parts.append(self.content[:2000])  # Limit content size
        return "\n".join(parts)

    def to_metadata(self) -> dict[str, Any]:
        """Metadata for ChromaDB."""
        return {
            "file_path": self.file_path,
            "node_type": self.node_type,
            "name": self.name,
            "start_line": self.start_line,
            "end_line": self.end_line,
        }


def extract_chunks_from_file(file_path: Path) -> list[CodeChunk]:
    """Parse Python file and extract function/class chunks."""
    chunks = []

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
        lines = content.split("\n")
        relative_path = str(file_path.relative_to(ROOT_DIR))

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Extract function
                docstring = ast.get_docstring(node)
                start = node.lineno - 1
                end = node.end_lineno or start + 10
                func_content = "\n".join(lines[start:end])

                chunks.append(
                    CodeChunk(
                        file_path=relative_path,
                        node_type="function",
                        name=node.name,
                        content=func_content,
                        docstring=docstring,
                        start_line=node.lineno,
                        end_line=end,
                    )
                )

            elif isinstance(node, ast.ClassDef):
                # Extract class (header + docstring)
                docstring = ast.get_docstring(node)
                start = node.lineno - 1
                # Just class definition, not full body
                end = min(start + 30, node.end_lineno or start + 30)
                class_content = "\n".join(lines[start:end])

                chunks.append(
                    CodeChunk(
                        file_path=relative_path,
                        node_type="class",
                        name=node.name,
                        content=class_content,
                        docstring=docstring,
                        start_line=node.lineno,
                        end_line=end,
                    )
                )

    except SyntaxError as e:
        logger.warning(f"📚 Syntax error in {file_path}: {e}")
    except Exception as e:
        logger.error(f"📚 Error parsing {file_path}: {e}")

    return chunks


def crawl_codebase(directories: list[str] | None = None) -> list[CodeChunk]:
    """Crawl directories and extract all code chunks."""
    if directories is None:
        directories = ["corpus", "jobs"]

    all_chunks = []

    for dir_name in directories:
        dir_path = ROOT_DIR / dir_name
        if not dir_path.exists():
            logger.warning(f"📚 Directory not found: {dir_path}")
            continue

        # Find all Python files
        py_files = list(dir_path.rglob("*.py"))
        logger.info(f"📚 Found {len(py_files)} Python files in {dir_name}/")

        for py_file in py_files:
            # Skip __pycache__, tests, etc.
            if "__pycache__" in str(py_file) or "test" in py_file.name.lower():
                continue

            chunks = extract_chunks_from_file(py_file)
            all_chunks.extend(chunks)

    logger.info(f"📚 Extracted {len(all_chunks)} code chunks total")
    return all_chunks


async def index_codebase(
    directories: list[str] | None = None,
    force_reindex: bool = False,
) -> int:
    """
    Main indexing function.
    Crawls codebase, embeds chunks, stores in ChromaDB.

    Returns: Number of indexed chunks.
    """
    import chromadb

    # Initialize ChromaDB
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)

    if force_reindex:
        try:
            client.delete_collection(COLLECTION_NAME)
            logger.info(f"📚 Deleted existing collection: {COLLECTION_NAME}")
        except Exception:
            pass

    # Use default embedder (MiniLM) - free & fast local inference
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Check existing count
    existing_count = collection.count()
    if existing_count > 0 and not force_reindex:
        logger.info(
            f"📚 Collection already has {existing_count} items. Use force_reindex=True to rebuild."
        )
        return existing_count

    # Crawl and chunk
    chunks = crawl_codebase(directories)

    if not chunks:
        logger.warning("📚 No chunks to index")
        return 0

    # Batch add to ChromaDB (using default MiniLM embedder)

    batch_size = 50
    indexed = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]

        ids = [c.chunk_id for c in batch]
        documents = [c.to_text() for c in batch]
        metadatas: list[dict[str, Any]] = [c.to_metadata() for c in batch]

        try:
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,  # type: ignore[arg-type]
            )
            indexed += len(batch)
            logger.debug(f"📚 Indexed batch {i // batch_size + 1}: {len(batch)} chunks")
        except Exception as e:
            logger.error(f"📚 Batch indexing failed: {e}")

    logger.info(f"📚 Indexing complete: {indexed} chunks indexed")
    return indexed


async def search_codebase(query: str, n_results: int = 5) -> list[dict]:
    """
    Semantic search over indexed codebase.
    Returns relevant code chunks with metadata.
    """
    import chromadb

    try:
        client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as e:
        logger.warning(
            f"📚 Collection not found. Run index_codebase() first. Error: {e}"
        )
        return []

    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
        )

        if not results["documents"] or not results["documents"][0]:
            return []

        matches = []
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
        distances = results["distances"][0] if results["distances"] else [0] * len(docs)

        for doc, meta, dist in zip(docs, metas, distances):
            matches.append(
                {
                    "content": doc[:500],  # Truncate for display
                    "file": meta.get("file_path", "?"),
                    "name": meta.get("name", "?"),
                    "type": meta.get("node_type", "?"),
                    "line": meta.get("start_line", 0),
                    "score": 1 - (dist / 2),  # Convert distance to similarity
                }
            )

        return matches

    except Exception as e:
        logger.error(f"📚 Search failed: {e}")
        return []


# CLI Entry Point
if __name__ == "__main__":

    async def main():
        logger.info("📚 Starting codebase indexing...")
        count = await index_codebase(force_reindex=True)
        logger.info(f"📚 Done! Indexed {count} chunks.")

        # Test search
        results = await search_codebase("routing logic gattaca")
        logger.info(f"📚 Test search found {len(results)} results")
        for r in results[:2]:
            logger.info(f"  → {r['file']}:{r['name']} (score: {r['score']:.2f})")

    asyncio.run(main())
