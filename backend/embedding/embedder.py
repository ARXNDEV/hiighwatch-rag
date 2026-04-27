from sentence_transformers import SentenceTransformer
import numpy as np
import torch

# Force PyTorch to use a single thread to save memory on Render Free Tier
torch.set_num_threads(1)

# Load a lightweight, fast, and high-quality embedding model
# all-MiniLM-L6-v2 uses ~90MB of RAM
model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_chunks(chunks):
    """
    Takes a list of chunk dictionaries and adds an 'embedding' key to each.
    """
    if not chunks:
        return chunks
        
    texts = [chunk['text'] for chunk in chunks]
    # Reduce batch_size from 32 to 8 to prevent memory spikes during inference
    embeddings = model.encode(texts, batch_size=8, show_progress_bar=True)
    
    for i, chunk in enumerate(chunks):
        chunk['embedding'] = embeddings[i]
        
    return chunks
