# rag_system.py
import faiss
import numpy as np
import json
import os
from sentence_transformers import SentenceTransformer

# Load the embedding model
EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')

class RAGSystem:
    def __init__(self, data_path: str = "scraped_data"):
        self.data_path = data_path
        self.documents = []
        self.embeddings = None
        self.index = None
        self._load_and_index_data()

    def _load_and_index_data(self):
        """Loads data from JSON files and creates a FAISS index."""
        if not os.path.exists(self.data_path):
            print("Scraped data directory not found. Please run data_scraper.py first.")
            return

        for filename in os.listdir(self.data_path):
            if filename.endswith(".json"):
                file_path = os.path.join(self.data_path, filename)
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                    # Create a simple text document from the JSON data
                    doc_text = f"Company: {data.get('company_name', '')}\n"
                    for key, value in data.items():
                        if key != 'company_name':
                            doc_text += f"{key}: {value}\n"
                            
                    self.documents.append(doc_text)

        if not self.documents:
            print("No documents found in scraped_data.")
            return

        # Generate embeddings
        self.embeddings = EMBEDDING_MODEL.encode(self.documents)
        
        # Create a FAISS index
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(np.array(self.embeddings).astype('float32'))
        print(f"RAG system initialized with {len(self.documents)} documents.")

    def get_context(self, query: str, k: int = 2) -> str:
        """Retrieves the most relevant context from the knowledge base."""
        if not self.index:
            return ""

        query_embedding = EMBEDDING_MODEL.encode([query]).astype('float32')
        distances, indices = self.index.search(query_embedding, k)
        
        context = ""
        for i in indices[0]:
            if i < len(self.documents):
                context += self.documents[i] + "\n---\n"
        
        return context.strip()

# Example usage (for testing)
if __name__ == '__main__':
    rag = RAGSystem()
    query = "What is the P/E ratio for Reliance Industries?"
    context = rag.get_context(query)
    print("Retrieved Context:")
    print(context)