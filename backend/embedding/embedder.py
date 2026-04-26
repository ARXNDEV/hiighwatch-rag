from sentence_transformers import SentenceTransformer
import numpy as np

# Load a lightweight, fast, and high-quality embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_chunks(chunks):
    """
    Takes a list of chunk dictionaries and adds an 'embedding' key to each.
    """
    if not chunks:
        return chunks
        
    texts = [chunk['text'] for chunk in chunks]
    # batch_size=32 makes it much faster on CPU
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=True)
    
    for i, chunk in enumerate(chunks):
        chunk['embedding'] = embeddings[i]
        
    return chunks
