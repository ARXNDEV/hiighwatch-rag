from sentence_transformers import SentenceTransformer
import numpy as np
import torch

torch.set_num_threads(1)

model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_chunks(chunks):
    """
    Takes a list of chunk dictionaries and adds an 'embedding' key to each.
    """
    if not chunks:
        return chunks
        
    texts = [chunk['text'] for chunk in chunks]
    # Increase batch size from 4 to 8 to process vectors faster, memory should hold up now that files are sequential
    embeddings = model.encode(texts, batch_size=8, show_progress_bar=True)
    
    try:
        import gc
        gc.collect()
    except Exception:
        pass
    
    for i, chunk in enumerate(chunks):
        chunk['embedding'] = embeddings[i]
        
    return chunks
