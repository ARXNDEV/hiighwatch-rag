from sentence_transformers import SentenceTransformer
import numpy as np

# Load a lightweight, fast, and high-quality embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_chunks(chunks):
    """
    Takes a list of chunk dictionaries and adds an 'embedding' key to each.
    """
    texts = [chunk['text'] for chunk in chunks]
    embeddings = model.encode(texts, show_progress_bar=True)
    
    for i, chunk in enumerate(chunks):
        chunk['embedding'] = embeddings[i]
        
    return chunks
