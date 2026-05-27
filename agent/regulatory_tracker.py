import os
import logging
from typing import Dict, Any, List

from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    RetryError,
)

from core.state import ComplianceState


class _LocalEmbeddingAdapter:
    """
    Wraps chromadb's DefaultEmbeddingFunction (ONNXMiniLM_L6_V2) in the
    LangChain embedding interface expected by langchain_community.vectorstores.Chroma.

    ChromaDB's function signature:  fn(texts: List[str]) -> List[List[float]]
    LangChain's required interface:  .embed_query(text) / .embed_documents(texts)
    """

    def __init__(self) -> None:
        import os as _os
        # ChromaDB downloads the ONNX model to $HOME/.cache by default.
        # In the container appuser has no writable home, so redirect to /tmp.
        _os.environ.setdefault("CHROMA_CACHE_DIR", "/tmp/chroma_cache")
        from chromadb.utils import embedding_functions
        _ef = embedding_functions.DefaultEmbeddingFunction()
        # Override the hard-coded download path before the model is fetched
        _ef.DOWNLOAD_PATH = "/tmp/chroma_cache/onnx_models"
        _os.makedirs(_ef.DOWNLOAD_PATH, exist_ok=True)
        self._fn = _ef
        logger.info("[RegulatoryTracker] LocalEmbeddingAdapter using ONNXMiniLM_L6_V2 (no API needed).")

    def embed_query(self, text: str) -> List[float]:
        return self._fn([text])[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return list(self._fn(texts))

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tenacity retry policy — targets any network / gRPC timeout from Google APIs
# Waits: 2s → 4s → 8s  (capped at 60s), gives up after 3 attempts.
# ---------------------------------------------------------------------------
_EMBEDDING_RETRY = dict(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=False,          # we catch RetryError ourselves for fallback
)


@retry(**_EMBEDDING_RETRY)
def _embed_query_with_retry(emb, text: str) -> list:
    """Wrap a single embed_query call so tenacity can retry it on 504s."""
    return emb.embed_query(text)


@retry(**_EMBEDDING_RETRY)
def _retriever_invoke_with_retry(retriever, query: str) -> list:
    """Wrap retriever.invoke so every ChromaDB similarity search is retried."""
    return retriever.invoke(query)


@retry(**_EMBEDDING_RETRY)
def _similarity_search_with_retry(db, text: str, k: int = 1) -> list:
    """Wrap db.similarity_search so false-positive lookups are retried."""
    return db.similarity_search(text, k=k)


def _make_embeddings(api_key: str):
    """
    Build a GoogleGenerativeAIEmbeddings object and smoke-test it.
    Tenacity decorators on the callers handle the retry loop; this function
    is intentionally thin so each decorator controls its own retry budget.
    """
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    emb = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2",
        google_api_key=api_key,
        request_options={"timeout": 60},
    )
    _embed_query_with_retry(emb, "compliance test")   # raises on failure → retry
    return emb


def _get_embeddings_with_fallback(api_key: str):
    """
    Try Gemini embeddings (with tenacity retries). If all attempts are
    exhausted fall back to ChromaDB's bundled local model (no API needed).
    """
    try:
        emb = _make_embeddings(api_key)
        logger.info("[RegulatoryTracker] Gemini embeddings initialised successfully.")
        return emb
    except RetryError as exc:
        logger.warning(
            "[RegulatoryTracker] Gemini embeddings failed after all retries (%s). "
            "Falling back to local ChromaDB default embeddings.",
            exc.last_attempt.exception(),
        )
    except Exception as exc:
        logger.warning(
            "[RegulatoryTracker] Unexpected embedding error (%s). "
            "Falling back to local ChromaDB default embeddings.", exc,
        )

    try:
        adapter = _LocalEmbeddingAdapter()
        return adapter
    except Exception as local_exc:
        logger.error(
            "[RegulatoryTracker] Local embedding fallback also failed: %s", local_exc
        )
        return None


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")

_GOOGLE_KEY_PRESENT = (
    bool(os.getenv("GOOGLE_API_KEY"))
    and os.getenv("GOOGLE_API_KEY") != "your_google_api_key_here"
)

_FP_DB_CACHE = None


def get_false_positives_db():
    """Return a cached Chroma collection for human-rejected false positives."""
    global _FP_DB_CACHE
    if not _GOOGLE_KEY_PRESENT:
        return None
    if _FP_DB_CACHE is not None:
        return _FP_DB_CACHE

    embeddings = _get_embeddings_with_fallback(os.getenv("GOOGLE_API_KEY", ""))
    if embeddings is None:
        return None

    from langchain_community.vectorstores import Chroma
    _FP_DB_CACHE = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
        collection_name="false_positives",
    )
    return _FP_DB_CACHE


def get_regulatory_tracker_node():
    """
    Factory that returns the Regulatory Tracker LangGraph node function.
    The vector store connection is initialised **once** here (not on every call),
    but only if the ChromaDB directory exists AND a Google API key is configured.
    """

    retriever = None  # Safe default

    if not _GOOGLE_KEY_PRESENT:
        print(
            "WARNING [RegulatoryTracker]: GOOGLE_API_KEY is not set. "
            "ChromaDB retrieval will be skipped. Rules will be empty."
        )
    elif not os.path.exists(CHROMA_DIR):
        print(
            "WARNING [RegulatoryTracker]: ChromaDB directory not found at "
            f"'{CHROMA_DIR}'. Run scripts/ingest_regulations.py first."
        )
    else:
        embeddings = _get_embeddings_with_fallback(os.getenv("GOOGLE_API_KEY", ""))
        if embeddings is None:
            print("WARNING [RegulatoryTracker]: All embedding attempts failed. ChromaDB will be skipped.")
        else:
            from langchain_community.vectorstores import Chroma
            vectorstore = Chroma(
                persist_directory=CHROMA_DIR, embedding_function=embeddings
            )
            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            print(f"INFO [RegulatoryTracker]: Connected to ChromaDB at '{CHROMA_DIR}'.")

    def regulatory_tracker_node(state: ComplianceState) -> Dict[str, Any]:
        print("--- AGENT 1: REGULATORY TRACKER ---")

        if not retriever:
            return {"active_rules": []}

        # Build context-aware queries from whatever data is present in the state
        query_texts: list[str] = []

        if state.get("current_transaction"):
            query_texts.append("wash trading market abuse equity surveillance")
        if state.get("current_loan"):
            query_texts.append("lending suitability churning AML loan fraud")
        if state.get("current_communication"):
            query_texts.append(
                "off-channel communications WhatsApp guarantee insider trading"
            )

        # Fallback: pull general compliance rules
        if not query_texts:
            query_texts.append("general compliance financial regulations")

        # Retrieve and deduplicate by page content
        seen: set[str] = set()
        active_rules: list[Dict[str, Any]] = []

        for q in query_texts:
            try:
                docs = _retriever_invoke_with_retry(retriever, q)
            except RetryError as exc:
                logger.error(
                    "[RegulatoryTracker] retriever.invoke failed after all retries "
                    "for query '%s': %s", q, exc.last_attempt.exception()
                )
                docs = []

            for doc in docs:
                content = doc.page_content.strip()
                if content not in seen:
                    seen.add(content)
                    jurisdiction = doc.metadata.get("Header 2", "MIXED")
                    active_rules.append(
                        {
                            "rule_id": f"RAG_RULE_{len(active_rules):03d}",
                            "jurisdiction": jurisdiction,
                            "description": content,
                            "parameters": {},
                        }
                    )

        print(
            f"INFO [RegulatoryTracker]: Retrieved {len(active_rules)} rule(s) from VectorDB."
        )
        return {"active_rules": active_rules}

    return regulatory_tracker_node
