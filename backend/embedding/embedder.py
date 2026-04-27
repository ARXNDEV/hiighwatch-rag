from sentence_transformers import SentenceTransformer
import numpy as np
import torch

# Force torch to use minimum threads to prevent CPU thrashing and memory spikes on Render free tier
torch.set_num_threads(1)
torch.set_grad_enabled(False) # We are only doing inference, disable gradients completely to save huge memory

# all-MiniLM-L6-v2 is already very fast, but forcing it to CPU explicitly prevents PyTorch from searching for GPUs
model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')

def embed_chunks(chunks):
    """
    Takes a list of chunk dictionaries and adds an 'embedding' key to each.
    """
    if not chunks:
        return chunks
        
    texts = [chunk['text'] for chunk in chunks]
    
    # Batch size 16 is the sweet spot for CPU inference speed vs memory on 512MB RAM limits
    # normalize_embeddings=True makes the FAISS L2 distance mathematically equivalent to Cosine Similarity
    embeddings = model.encode(texts, batch_size=16, show_progress_bar=True, normalize_embeddings=True)
    
    try:
        import gc
        gc.collect()
    except Exception:
        pass
    
    for i, chunk in enumerate(chunks):
        chunk['embedding'] = embeddings[i]
        
    return chunks
