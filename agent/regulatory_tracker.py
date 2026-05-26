import os
from typing import Dict, Any

from dotenv import load_dotenv
from core.state import ComplianceState

load_dotenv()

# Directory for ChromaDB — resolved relative to this file's location
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")

_GOOGLE_KEY_PRESENT = (
    bool(os.getenv("GOOGLE_API_KEY"))
    and os.getenv("GOOGLE_API_KEY") != "your_google_api_key_here"
)

_FP_DB_CACHE = None

def get_false_positives_db():
    global _FP_DB_CACHE
    if not _GOOGLE_KEY_PRESENT:
        return None
    if _FP_DB_CACHE is not None:
        return _FP_DB_CACHE
    from langchain_community.vectorstores import Chroma
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
    _FP_DB_CACHE = Chroma(
        persist_directory=CHROMA_DIR, 
        embedding_function=embeddings,
        collection_name="false_positives"
    )
    return _FP_DB_CACHE


def get_regulatory_tracker_node():
    """
    Factory that returns the Regulatory Tracker LangGraph node function.
    The vector store connection is initialised **once** here (not on every call),
    but only if the ChromaDB directory exists AND an OpenAI key is configured.
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
        from langchain_community.vectorstores import Chroma
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-2",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
        vectorstore = Chroma(
            persist_directory=CHROMA_DIR, embedding_function=embeddings
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        print(f"INFO [RegulatoryTracker]: Connected to ChromaDB at '{CHROMA_DIR}'.")

    def regulatory_tracker_node(state: ComplianceState) -> Dict[str, Any]:
        print("--- AGENT 1: REGULATORY TRACKER ---")
        
        # Anti-burst jitter delay before hitting the embedding API during execution
        import time
        time.sleep(2)

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
            for doc in retriever.invoke(q):
                content = doc.page_content.strip()
                if content not in seen:
                    seen.add(content)
                    # Extract jurisdiction from doc metadata if available
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
