# rag_system.py (Enhanced Version)
import faiss
import numpy as np
import json
import os
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Any
from datetime import datetime
import hashlib

# Load the embedding model
EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')

class RAGSystem:
    def __init__(self, data_path: str = "scraped_data", auto_refresh: bool = True):
        self.data_path = data_path
        self.auto_refresh = auto_refresh
        self.documents = []
        self.document_metadata = []  # Store metadata for each document chunk
        self.embeddings = None
        self.index = None
        self.last_refresh = None
        self.data_hash = None  # Track if data changed
        self._load_and_index_data()

    def _get_data_hash(self) -> str:
        """Generate hash of all JSON files to detect changes."""
        if not os.path.exists(self.data_path):
            return ""
        
        file_hashes = []
        for filename in sorted(os.listdir(self.data_path)):
            if filename.endswith(".json"):
                file_path = os.path.join(self.data_path, filename)
                with open(file_path, 'rb') as f:
                    file_hashes.append(hashlib.md5(f.read()).hexdigest())
        
        return hashlib.md5(''.join(file_hashes).encode()).hexdigest()

    def _should_refresh(self) -> bool:
        """Check if data should be refreshed."""
        if not self.auto_refresh:
            return False
        
        current_hash = self._get_data_hash()
        return current_hash != self.data_hash

    def _create_document_chunks(self, data: Dict[str, Any], ticker: str) -> List[Dict[str, Any]]:
        """Convert JSON data into semantically meaningful chunks."""
        chunks = []
        company_name = data.get('company_name', ticker)
        
        # Chunk 1: Company Overview & Key Ratios
        if data.get('ratios'):
            ratios_text = f"Company: {company_name} ({ticker})\n"
            ratios_text += "Key Financial Ratios:\n"
            
            for ratio_name, ratio_value in data['ratios'].items():
                if ratio_value is not None:
                    ratios_text += f"- {ratio_name}: {ratio_value}\n"
            
            chunks.append({
                'text': ratios_text,
                'type': 'ratios',
                'ticker': ticker,
                'company': company_name
            })
        
        # Chunk 2: Financial Performance (Recent years)
        if data.get('profit_loss'):
            pl_text = f"Company: {company_name} ({ticker})\n"
            pl_text += "Financial Performance:\n"
            
            for metric, years_data in data['profit_loss'].items():
                if isinstance(years_data, dict):
                    pl_text += f"\n{metric}:\n"
                    for year, value in years_data.items():
                        if value is not None:
                            pl_text += f"  {year}: {value}\n"
            
            chunks.append({
                'text': pl_text,
                'type': 'financials',
                'ticker': ticker,
                'company': company_name
            })
        
        # Chunk 3: Recent News (if available)
        if data.get('news'):
            news_text = f"Company: {company_name} ({ticker})\n"
            news_text += "Recent News:\n"
            
            for news_item in data['news'][:5]:  # Limit to 5 most recent
                title = news_item.get('title', '')
                date = news_item.get('date', '')
                description = news_item.get('description', '')
                
                news_text += f"\n- {title}"
                if date:
                    news_text += f" ({date})"
                if description:
                    news_text += f"\n  {description}\n"
            
            chunks.append({
                'text': news_text,
                'type': 'news',
                'ticker': ticker,
                'company': company_name
            })
        
        # Chunk 4: Corporate Events
        if data.get('events') or data.get('announcements'):
            events_text = f"Company: {company_name} ({ticker})\n"
            events_text += "Corporate Events & Announcements:\n"
            
            for event_item in (data.get('events', []) + data.get('announcements', []))[:5]:
                title = event_item.get('title', '')
                date = event_item.get('date', '')
                event_type = event_item.get('type', '')
                
                events_text += f"\n- {title}"
                if date:
                    events_text += f" ({date})"
                if event_type:
                    events_text += f" [Type: {event_type}]"
                
                description = event_item.get('description', '')
                if description:
                    events_text += f"\n  {description}\n"
            
            chunks.append({
                'text': events_text,
                'type': 'events',
                'ticker': ticker,
                'company': company_name
            })
        
        return chunks

    def _load_and_index_data(self):
        """Loads data from JSON files and creates a FAISS index with improved chunking."""
        if not os.path.exists(self.data_path):
            print("Scraped data directory not found. Please run data_scraper.py first.")
            return

        self.documents = []
        self.document_metadata = []
        
        print("Loading and indexing scraped data...")
        
        for filename in sorted(os.listdir(self.data_path)):
            if filename.endswith(".json") and not filename.startswith("_backup"):
                ticker = filename.replace(".json", "")
                file_path = os.path.join(self.data_path, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Create semantic chunks
                    chunks = self._create_document_chunks(data, ticker)
                    
                    for chunk in chunks:
                        self.documents.append(chunk['text'])
                        self.document_metadata.append({
                            'ticker': chunk['ticker'],
                            'company': chunk['company'],
                            'type': chunk['type'],
                            'filename': filename
                        })
                
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
                    continue

        if not self.documents:
            print("No documents found in scraped_data.")
            return

        # Generate embeddings
        print(f"Generating embeddings for {len(self.documents)} document chunks...")
        self.embeddings = EMBEDDING_MODEL.encode(self.documents, show_progress_bar=True)
        
        # Create a FAISS index
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(np.array(self.embeddings).astype('float32'))
        
        self.last_refresh = datetime.now()
        self.data_hash = self._get_data_hash()
        
        print(f"RAG system initialized with {len(self.documents)} document chunks from {len(set(m['ticker'] for m in self.document_metadata))} companies.")

    def refresh_if_needed(self):
        """Refresh the index if data has changed."""
        if self._should_refresh():
            print("Data changes detected. Refreshing RAG system...")
            self._load_and_index_data()

    def get_context(self, query: str, k: int = 3, filter_ticker: str = None) -> str:
        """
        Retrieves the most relevant context from the knowledge base.
        
        Args:
            query: The user query
            k: Number of documents to retrieve
            filter_ticker: Optional ticker to filter results
        """
        if self.auto_refresh:
            self.refresh_if_needed()
        
        if not self.index or len(self.documents) == 0:
            return "No data available. Please ensure data scraping has been completed."

        query_embedding = EMBEDDING_MODEL.encode([query]).astype('float32')
        
        # Search for more documents initially to allow filtering
        search_k = min(k * 3, len(self.documents))
        distances, indices = self.index.search(query_embedding, search_k)
        
        retrieved_chunks = []
        seen_types = set()
        
        for i, idx in enumerate(indices[0]):
            if idx >= len(self.documents):
                continue
            
            metadata = self.document_metadata[idx]
            
            # Filter by ticker if specified
            if filter_ticker and metadata['ticker'] != filter_ticker:
                continue
            
            # Prefer diverse chunk types
            chunk_type = metadata['type']
            if len(retrieved_chunks) < k or chunk_type not in seen_types:
                retrieved_chunks.append({
                    'text': self.documents[idx],
                    'metadata': metadata,
                    'similarity_score': distances[0][i]
                })
                seen_types.add(chunk_type)
            
            if len(retrieved_chunks) >= k:
                break
        
        if not retrieved_chunks:
            return f"No relevant information found for the query: {query}"
        
        # Format the context
        context = "=== RELEVANT COMPANY DATA ===\n\n"
        
        for i, chunk in enumerate(retrieved_chunks):
            metadata = chunk['metadata']
            context += f"--- {metadata['company']} ({metadata['ticker']}) - {metadata['type'].title()} ---\n"
            context += chunk['text']
            context += f"\n[Similarity Score: {chunk['similarity_score']:.3f}]\n\n"
        
        return context.strip()

    def get_company_summary(self, ticker: str) -> str:
        """Get a comprehensive summary for a specific company."""
        if self.auto_refresh:
            self.refresh_if_needed()
        
        company_chunks = []
        for i, metadata in enumerate(self.document_metadata):
            if metadata['ticker'] == ticker:
                company_chunks.append({
                    'text': self.documents[i],
                    'type': metadata['type']
                })
        
        if not company_chunks:
            return f"No data found for {ticker}"
        
        summary = f"=== COMPREHENSIVE DATA FOR {ticker} ===\n\n"
        
        # Order by type preference
        type_order = ['ratios', 'financials', 'news', 'events']
        chunks_by_type = {}
        for chunk in company_chunks:
            chunk_type = chunk['type']
            if chunk_type not in chunks_by_type:
                chunks_by_type[chunk_type] = []
            chunks_by_type[chunk_type].append(chunk['text'])
        
        for chunk_type in type_order:
            if chunk_type in chunks_by_type:
                for text in chunks_by_type[chunk_type]:
                    summary += text + "\n\n"
        
        return summary.strip()

    def get_available_tickers(self) -> List[str]:
        """Get list of all available tickers in the knowledge base."""
        if self.auto_refresh:
            self.refresh_if_needed()
        
        return sorted(set(metadata['ticker'] for metadata in self.document_metadata))

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        if not self.document_metadata:
            return {"error": "No data loaded"}
        
        tickers = set(metadata['ticker'] for metadata in self.document_metadata)
        types = {}
        for metadata in self.document_metadata:
            chunk_type = metadata['type']
            types[chunk_type] = types.get(chunk_type, 0) + 1
        
        return {
            "total_chunks": len(self.documents),
            "total_companies": len(tickers),
            "companies": sorted(tickers),
            "chunk_types": types,
            "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None
        }

# Example usage and testing
if __name__ == '__main__':
    # Initialize RAG system
    rag = RAGSystem()
    
    # Print stats
    stats = rag.get_stats()
    print("RAG System Stats:")
    print(f"Total companies: {stats['total_companies']}")
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Chunk types: {stats['chunk_types']}")
    print(f"Available tickers: {stats['companies']}")
    
    # Test queries
    test_queries = [
        "What is the P/E ratio for Reliance Industries?",
        "Show me recent news about TCS",
        "Compare the financial performance of INFY and TCS",
        "Any recent events or announcements from HDFCBANK?"
    ]
    
    print("\n=== Testing Queries ===")
    for query in test_queries:
        print(f"\nQuery: {query}")
        context = rag.get_context(query, k=2)
        print("Retrieved Context:")
        print(context[:500] + "..." if len(context) > 500 else context)
        print("-" * 80)