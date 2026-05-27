"""
scripts/ingest_regulations.py

Loads markdown regulation files from data/regulations/, splits them into chunks,
embeds them using OpenAI, and stores them in a local ChromaDB vector store.

Run this once (or whenever regulations are updated):
  python -m scripts.ingest_regulations
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Resolve paths relative to this script's location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "regulations")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")


def ingest_regulations() -> None:
    print(f"Loading regulations from: {DATA_DIR}")

    if not os.path.exists(DATA_DIR) or not os.listdir(DATA_DIR):
        print("ERROR: No regulation files found. Add .md files to data/regulations/ first.")
        return

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key or api_key == "your_google_api_key_here":
        print("WARNING: GOOGLE_API_KEY not set — will attempt local ONNX embedding fallback.")
        api_key = ""  # _get_embeddings_with_fallback handles this gracefully

    # ── Imports (deferred so the script can be imported without heavy deps) ──
    from langchain_community.document_loaders import DirectoryLoader, TextLoader
    from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_community.vectorstores import Chroma

    # ── Load ─────────────────────────────────────────────────────────────────
    loader = DirectoryLoader(
        DATA_DIR,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},  # Prevent UnicodeDecodeError on Windows
    )
    docs = loader.load()
    print(f"Loaded {len(docs)} document(s).")

    if not docs:
        print("No documents found to ingest.")
        return

    # ── Split by Markdown headers first ──────────────────────────────────────
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    md_splits = []
    for doc in docs:
        splits = md_splitter.split_text(doc.page_content)
        for split in splits:
            # Preserve source path in metadata for retrieval attribution
            split.metadata["source"] = doc.metadata.get("source", "unknown")
        md_splits.extend(splits)

    print(f"Split into {len(md_splits)} header-based section(s).")

    # ── Further split to stay within embedding context windows ───────────────
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    final_chunks = text_splitter.split_documents(md_splits)
    print(f"Created {len(final_chunks)} final chunk(s).")

    # ── Embed & store ─────────────────────────────────────────────────────────
    print("Initialising embeddings (Gemini with tenacity retry → local ONNX fallback)...")
    # Import the resilient helper so ingestion survives 504 timeouts
    import sys, os as _os
    sys.path.insert(0, BASE_DIR)
    from agent.regulatory_tracker import _get_embeddings_with_fallback
    embeddings = _get_embeddings_with_fallback(api_key)
    if embeddings is None:
        print("ERROR: Could not initialise any embedding function. Aborting.")
        return

    print(f"Writing to ChromaDB at: {CHROMA_DIR}")
    Chroma.from_documents(
        documents=final_chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
    )
    print("[OK] Ingestion complete. Vector store persisted.")


if __name__ == "__main__":
    ingest_regulations()
