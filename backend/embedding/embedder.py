from sentence_transformers import SentenceTransformer
import numpy as np
import torch
import os

# Since we have unlimited memory, let PyTorch use all available CPU threads
torch.set_num_threads(os.cpu_count() or 4)
torch.set_grad_enabled(False) # We are only doing inference, disable gradients completely to save memory

# all-MiniLM-L6-v2 is already very fast, let PyTorch decide the best device (CPU/MPS/CUDA)
model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_chunks(chunks):
    """
    Takes a list of chunk dictionaries and adds an 'embedding' key to each.
    """
    if not chunks:
        return chunks
        
    texts = [chunk['text'] for chunk in chunks]
    
    # Unlimited memory: Increase batch size to 64 for maximum throughput
    # normalize_embeddings=True makes the FAISS L2 distance mathematically equivalent to Cosine Similarity
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True)
    
    try:
        import gc
        gc.collect()
    except Exception:
        pass
    
    for i, chunk in enumerate(chunks):
        chunk['embedding'] = embeddings[i]
        
    return chunks
