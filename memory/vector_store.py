import chromadb
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LongTermMemory:
    def __init__(self, db_path="./chroma_db"):
        """
        Initializes the ChromaDB persistent client. 
        This creates a local folder to store embeddings so memory persists across runs.
        """
        # Ensure the directory exists
        os.makedirs(db_path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Create or load the collection for financial data
        # We use cosine similarity which is standard for text embeddings
        self.collection = self.client.get_or_create_collection(
            name="financial_research",
            metadata={"hnsw:space": "cosine"} 
        )
        logger.info(f"Long-Term Memory initialized. DB Path: {db_path}")

    # Required metadata keys enforced by the Day 1 schema design
    REQUIRED_METADATA_KEYS = {"ticker", "source_type", "date", "confidence", "researcher_session", "verified"}

    def store_finding(self, doc_id: str, content: str, metadata: dict):
        """
        Embeds and stores a research finding into long-term memory.
        Enforces the Day 1 schema: ticker, source_type, date, confidence, researcher_session, verified.
        NOTE: ChromaDB only supports str/int/float metadata values — 'verified' is stored as int (1/0).
        """
        # Schema enforcement
        missing_keys = self.REQUIRED_METADATA_KEYS - set(metadata.keys())
        if missing_keys:
            raise ValueError(f"store_finding: Missing required metadata keys: {missing_keys}")

        # ChromaDB does not accept Python bool — cast to int
        sanitized = dict(metadata)
        if isinstance(sanitized.get("verified"), bool):
            sanitized["verified"] = int(sanitized["verified"])

        try:
            self.collection.add(
                documents=[content],
                metadatas=[sanitized],
                ids=[doc_id]
            )
            logger.info(f"Stored document '{doc_id}' into memory.")
        except Exception as e:
            logger.error(f"Failed to store memory for {doc_id}: {e}")

    def search_memory(self, query_text: str, ticker_filter: str = None, n_results: int = 3) -> dict:
        """
        Searches memory using semantic similarity.
        Includes an optional metadata filter to restrict searches to a specific company.
        Returns empty result dict safely if the collection is empty or query fails.
        """
        where_clause = {"ticker": ticker_filter} if ticker_filter else None
        logger.info(f"Searching memory for: '{query_text}' (Ticker Filter: {ticker_filter})")

        try:
            # Guard: ChromaDB raises if n_results > number of docs in collection
            count = self.collection.count()
            safe_n = min(n_results, count)
            if safe_n == 0:
                logger.info("Memory collection is empty — skipping query.")
                return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

            results = self.collection.query(
                query_texts=[query_text],
                n_results=safe_n,
                where=where_clause
            )
            return results
        except Exception as e:
            logger.warning(f"Memory search failed (returning empty): {e}")
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

# Quick test block to verify the database builds and searches correctly
if __name__ == "__main__":
    memory = LongTermMemory()
    
    # 1. Store a dummy financial fact
    memory.store_finding(
        doc_id="tsla-q3-2024-01",
        content="Tesla announced a shift in strategy focusing on robotaxis over the traditional Model 2.",
        metadata={
            "ticker": "TSLA",
            "source_type": "news",
            "date": "2024-04-05",
            "confidence": 0.9,
            "researcher_session": "test-session-01",
            "verified": True  # Will be auto-cast to int(1) by store_finding
        }
    )
    
    # 2. Retrieve it using semantic search (notice the words don't match exactly, but the meaning does)
    print("\nExecuting Semantic Search...")
    search_results = memory.search_memory("autonomous vehicle business plans", ticker_filter="TSLA")
    
    if search_results['documents'] and search_results['documents'][0]:
        print(f"\nMatch Found: {search_results['documents'][0][0]}")
    else:
        print("\nNo match found.")
