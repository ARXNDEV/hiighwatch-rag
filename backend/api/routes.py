from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from connectors.gdrive import sync_google_drive, SCOPES, TOKEN_FILE
from google_auth_oauthlib.flow import Flow
from processing.parser import process_files
from embedding.embedder import embed_chunks
from search.vector_store import add_to_faiss, search_faiss, get_document_metadata
from groq import Groq
import os
import hashlib

router = APIRouter()

# Simple in-memory cache for LLM responses
llm_cache = {}
oauth_states = {}

@router.get("/auth/status")
def auth_status():
    try:
        is_authenticated = os.path.exists(TOKEN_FILE)
        return {"authenticated": is_authenticated}
    except Exception as e:
        return {"authenticated": False, "error": str(e)}

@router.get("/auth/login")
def auth_login():
    try:
        FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
        API_URL = os.getenv("API_URL", "http://localhost:8000")
        
        # We store the oauth state in a JSON file to survive FastAPI hot reloads
        # IMPORTANT: explicitly request access_type='offline' AND prompt='consent'
        # so Google ALWAYS returns a refresh_token, even if the user has authorized before.
        
        credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
        if not os.path.exists(credentials_path):
            raise Exception(f"OAuth credentials file not found at {credentials_path}. Please download it from Google Cloud Console.")
            
        flow = Flow.from_client_secrets_file(
            credentials_path,
            scopes=SCOPES,
            redirect_uri=f"{API_URL}/auth/callback"
        )
        auth_url, state = flow.authorization_url(
            prompt='consent', 
            access_type='offline',
            include_granted_scopes='true'
        )
        
        import json
        states_file = "oauth_states.json"
        
        # Load existing states
        states = {}
        if os.path.exists(states_file):
            with open(states_file, "r") as f:
                try:
                    content = f.read().strip()
                    if content:
                        states = json.loads(content)
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse oauth_states.json: {e}. Starting fresh.")
                    states = {}
                except Exception as e:
                    print(f"Warning: Error reading oauth_states.json: {e}")
                    pass
                    
        # Save new state
        states[state] = flow.code_verifier
        with open(states_file, "w") as f:
            json.dump(states, f)
        
        return {"url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/storage/stats")
def get_storage_stats():
    try:
        from search.vector_store import index
        import os
        
        # Get FAISS vector count
        vector_count = index.ntotal if index else 0
        
        # Estimate FAISS file size
        faiss_size_bytes = 0
        if os.path.exists("faiss_index.bin"):
            faiss_size_bytes = os.path.getsize("faiss_index.bin")
            
        # Get total size of synced files directory
        docs_size_bytes = 0
        docs_count = 0
        if os.path.exists("synced_docs"):
            for f in os.listdir("synced_docs"):
                fp = os.path.join("synced_docs", f)
                if os.path.isfile(fp):
                    docs_size_bytes += os.path.getsize(fp)
                    docs_count += 1
                        
        return {
            "vectors": vector_count,
            "faiss_size_kb": round(faiss_size_bytes / 1024, 2),
            "docs_size_kb": round(docs_size_bytes / 1024, 2),
            "docs_count": docs_count
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "vectors": 0,
            "faiss_size_kb": 0,
            "docs_size_kb": 0,
            "docs_count": 0
        }
@router.get("/chat/history")
def get_chat_history():
    try:
        from connectors.gdrive import get_drive_service
        try:
            service = get_drive_service()
            about = service.about().get(fields="user").execute()
            user_email = about['user']['emailAddress']
        except Exception:
            # If get_drive_service fails (e.g. not logged in), just return empty
            return {"history": []}
            
        cursor = chats_collection.find({"user_email": user_email})
        # Try to sort, but handle if it's the mock collection which doesn't sort well
        try:
            cursor = cursor.sort("timestamp", 1)
        except Exception:
            pass
        history = []
        for chat in cursor:
            # Format to match frontend Message interface
            msg = {
                "role": chat["role"],
                "content": chat["content"]
            }
            if chat.get("sources"):
                msg["sources"] = chat["sources"]
            history.append(msg)
            
        return {"history": history}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"history": []}

@router.get("/auth/callback")
def auth_callback(state: str, code: str):
    try:
        FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
        API_URL = os.getenv("API_URL", "http://localhost:8000")
        
        import json
        states_file = "oauth_states.json"
        states = {}
        if os.path.exists(states_file):
            with open(states_file, "r") as f:
                try:
                    content = f.read().strip()
                    if content:
                        states = json.loads(content)
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse oauth_states.json in callback: {e}")
                    states = {}
                except Exception as e:
                    print(f"Warning: Error reading oauth_states.json in callback: {e}")
                    pass

        if state not in states:
            # If state is completely missing, redirect to home with error
            return RedirectResponse(url=f"{FRONTEND_URL}/?error=invalid_state")
            
        credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
        if not os.path.exists(credentials_path):
            raise Exception(f"OAuth credentials file not found at {credentials_path}. Please download it from Google Cloud Console.")
            
        flow = Flow.from_client_secrets_file(
            credentials_path,
            scopes=SCOPES,
            redirect_uri=f"{API_URL}/auth/callback",
            state=state
        )
        
        # Restore the exact PKCE code_verifier from the JSON file
        flow.code_verifier = states[state]
        
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
        # Clean up the state
        del states[state]
        with open(states_file, "w") as f:
            json.dump(states, f)
            
        # VERY IMPORTANT: If we didn't get a refresh token, and there is an existing token file,
        # we should preserve the old refresh token.
        # But `from_authorized_user_file` and `credentials` handle most of this.
        
        return RedirectResponse(url=f"{FRONTEND_URL}/dashboard?sync=true")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class AskRequest(BaseModel):
    query: str
    filter_metadata: Optional[Dict[str, str]] = None  # Added for metadata filtering

class Source(BaseModel):
    doc_id: str
    name: str
    chunk_text: str

class AskResponse(BaseModel):
    answer: str
    sources: List[Source]
    cached: bool = False

from db import files_collection, chats_collection
from datetime import datetime

@router.post("/disconnect-drive")
def disconnect_drive_endpoint():
    try:
        token_file = "token.json"
        states_file = "oauth_states.json"
        
        # Remove token.json to force re-authentication
        if os.path.exists(token_file):
            os.remove(token_file)
            
        # Clean up local files
        sync_dir = "synced_docs"
        if os.path.exists(sync_dir):
            for f in os.listdir(sync_dir):
                fp = os.path.join(sync_dir, f)
                if os.path.isfile(fp):
                    os.remove(fp)
            
        # Remove old states
        if os.path.exists(states_file):
            os.remove(states_file)
            
        return {"status": "success", "message": "Successfully disconnected. You can now sync with a new account."}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

def background_sync_process(downloaded_files):
    try:
        import time
        start_time = time.time()
        print(f"Background: Extracting text from {len(downloaded_files)} files...")
        chunks = process_files(downloaded_files)
        
        if not chunks:
            print("Background: Files downloaded but no text extracted.")
            return

        print(f"Background: Embedding {len(chunks)} chunks...")
        embedded_chunks = embed_chunks(chunks)

        print("Background: Adding chunks to FAISS...")
        add_to_faiss(embedded_chunks)

        end_time = time.time()
        print(f"Background: Sync completed in {round(end_time - start_time, 2)} seconds")
    except Exception as e:
        import traceback
        print("Background Sync Error:")
        traceback.print_exc()

@router.post("/sync-drive")
def sync_drive_endpoint(background_tasks: BackgroundTasks, force: bool = False):
    try:
        import time
        start_time = time.time()
        
        if force:
            from connectors.gdrive import get_drive_service
            service = get_drive_service()
            try:
                about = service.about().get(fields="user").execute()
                user_email = about['user']['emailAddress']
                files_collection.delete_many({"user_email": user_email})
            except Exception as e:
                print(f"Failed to get user email for force sync: {e}")
                
            # DO NOT try to delete metadata.json since we use MongoDB now
            # Just clear the local folder if we are forcing
            import shutil
            sync_dir = "synced_docs"
            if os.path.exists(sync_dir):
                for f in os.listdir(sync_dir):
                    fp = os.path.join(sync_dir, f)
                    if os.path.isfile(fp):
                        os.remove(fp)
                
        # 1. Fetch files from Google Drive
        print("Starting Google Drive Sync...")
        downloaded_files = sync_google_drive()
        
        if not downloaded_files:
            return {"status": "success", "files_processed": 0, "message": "No new files to sync.", "files": []}

        # 2. Queue for background processing
        background_tasks.add_task(background_sync_process, downloaded_files)

        end_time = time.time()
        print(f"Drive API completed in {round(end_time - start_time, 2)} seconds. Background indexing started.")

        return {
            "status": "success",
            "files_processed": len(downloaded_files),
            "message": f"Successfully queued {len(downloaded_files)} files. AI is indexing them in the background.",
            "files": [{"id": f["id"], "name": f["name"]} for f in downloaded_files]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = str(e)
        if "Google Drive API has not been used" in error_msg:
            error_msg = "Google Drive API is not enabled. Visit https://console.cloud.google.com/apis/library/drive.googleapis.com to enable it."
        # If we hit an out of memory error, throw a clear exception
        if "killed" in error_msg.lower() or "memory" in error_msg.lower():
            error_msg = "The server ran out of memory while processing your PDFs. Try syncing fewer or smaller files."
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest):
    try:
        from connectors.gdrive import get_drive_service
        service = get_drive_service()
        try:
            about = service.about().get(fields="user").execute()
            user_email = about['user']['emailAddress']
        except Exception:
            user_email = "default_user"

        # Save user query to MongoDB
        chats_collection.insert_one({
            "user_email": user_email,
            "role": "user",
            "content": req.query,
            "timestamp": datetime.utcnow()
        })

        # Cache key based on query and filters
        cache_key = hashlib.md5(f"{req.query}_{req.filter_metadata}".encode()).hexdigest()
        if cache_key in llm_cache:
            return AskResponse(
                answer=llm_cache[cache_key]['answer'],
                sources=llm_cache[cache_key]['sources'],
                cached=True
            )

        # 1. Search FAISS for top-5 chunks, with optional metadata filtering
        top_chunks = search_faiss(req.query, k=5, filters=req.filter_metadata)
        
        if not top_chunks:
            return AskResponse(
                answer="I couldn't find any relevant information in your synced documents.",
                sources=[],
                cached=False
            )

        # 2. Format context for the LLM
        context_parts = []
        sources = []
        for chunk in top_chunks:
            doc_id = chunk["doc_id"]
            text = chunk["text"]
            metadata = get_document_metadata(doc_id)
            doc_name = metadata.get("name", "Unknown Document") if metadata else "Unknown Document"
            
            context_parts.append(f"Document: {doc_name}\nContent:\n{text}")
            
            # Avoid duplicate sources in the output list if they have the same doc_id
            if not any(s.doc_id == doc_id for s in sources):
                sources.append(Source(doc_id=doc_id, name=doc_name, chunk_text=text))

        context_block = "\n\n---\n\n".join(context_parts)
        
        # Build chat history for Groq
        cursor = chats_collection.find({"user_email": user_email})
        try:
            cursor = cursor.sort("timestamp", 1)
        except Exception:
            pass
        # Only take the last 10 messages for context window size limits
        chat_history_list = list(cursor)[-10:]
        
        system_prompt = """You are Highwatch, an advanced, highly intelligent conversational AI assistant (similar to ChatGPT) integrated directly into the user's Google Drive. 
Your primary goal is to help the user understand, analyze, and extract insights from their synced documents.

Rules:
1. Act naturally conversational, helpful, and highly articulate.
2. When answering questions, prioritize using the provided 'Context' (which contains text extracted from their Drive files).
3. If the answer is in the Context, synthesize it beautifully and clearly.
4. If the user asks a follow-up question or makes a conversational remark, use the conversation history to respond intelligently.
5. If you truly do not know the answer based on the Context or History, politely explain that you cannot find that information in their currently synced Drive files, but offer to help with something else. DO NOT hallucinate facts about their documents.
6. Use markdown formatting (bolding, bullet points, etc.) to make your answers easy to read."""

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add history
        for chat in chat_history_list:
            role = "user" if chat["role"] == "user" else "assistant"
            # Don't include the current query in the history loop since we'll add it below
            if chat["content"] != req.query:
                messages.append({"role": role, "content": chat["content"]})

        # Add the current prompt with context
        prompt_with_context = f"""Context:
{context_block}

Question:
{req.query}"""

        messages.append({"role": "user", "content": prompt_with_context})

        # 3. Query Groq API
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        if not os.getenv("GROQ_API_KEY"):
            raise Exception("GROQ_API_KEY is not set.")

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.4,
            max_tokens=2048,
        )

        answer = completion.choices[0].message.content
        
        # Save to cache
        llm_cache[cache_key] = {
            "answer": answer,
            "sources": sources
        }

        # Save AI response to MongoDB
        chats_collection.insert_one({
            "user_email": user_email,
            "role": "ai",
            "content": answer,
            "sources": [s.dict() for s in sources],
            "timestamp": datetime.utcnow()
        })

        return AskResponse(answer=answer, sources=sources, cached=False)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
