import os
import io
import json
import asyncio
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
TOKEN_FILE = 'token.json'
SYNC_DIR = 'synced_docs'

def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            # If token is corrupted, remove it
            os.remove(TOKEN_FILE)
            creds = None
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                # If refresh fails, remove token and re-auth
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                creds = None
                
        if not creds:
            raise Exception("Not authenticated. Please login with Google first.")
                
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    from googleapiclient.discovery import build
    
    # Just use the default build which automatically handles credentials
    return build('drive', 'v3', credentials=creds)

def download_file(service, file_id, file_name, mime_type, modified_time, synced_files, user_email):
    request = None
    if mime_type == 'application/vnd.google-apps.document':
        request = service.files().export_media(fileId=file_id, mimeType='application/pdf')
        ext = '.pdf'
    else:
        request = service.files().get_media(fileId=file_id)
        ext = os.path.splitext(file_name)[1]
        if not ext:
            ext = '.pdf' if mime_type == 'application/pdf' else '.txt'

    file_path = os.path.join(SYNC_DIR, f"{file_id}{ext}")

    try:
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        with open(file_path, 'wb') as f:
            f.write(fh.getvalue())
        
        # Update metadata in MongoDB
        from db import files_collection
        doc = {
            "user_email": user_email,
            "file_id": file_id,
            "name": file_name,
            "path": file_path,
            "mimeType": mime_type,
            "modifiedTime": modified_time,
            "source": "gdrive"
        }
        files_collection.update_one(
            {"user_email": user_email, "file_id": file_id},
            {"$set": doc},
            upsert=True
        )
        
        return {
            "id": file_id,
            "name": file_name,
            "path": file_path,
            "mimeType": mime_type
        }
    except Exception as e:
        print(f"Failed to download {file_name}: {e}")
        return None

def sync_google_drive():
    service = get_drive_service()
    if not os.path.exists(SYNC_DIR):
        os.makedirs(SYNC_DIR)

    from db import files_collection
    try:
        about = service.about().get(fields="user").execute()
        user_email = about['user']['emailAddress']
    except Exception as e:
        print("Could not get user email", e)
        user_email = "default_user"

    # Fetch previously synced files from Mongo
    synced_files_cursor = files_collection.find({"user_email": user_email})
    synced_files = {f["file_id"]: f for f in synced_files_cursor}

    query = "mimeType='application/pdf' or mimeType='application/vnd.google-apps.document' or mimeType='text/plain'"
    results = service.files().list(
        q=query,
        pageSize=15,
        fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
        orderBy="modifiedTime desc"
    ).execute()
    items = results.get('files', [])

    downloaded = []
    
    import concurrent.futures
    
    def process_item(item):
        # Create a thread-local service
        local_service = get_drive_service()
        
        file_id = item['id']
        file_name = item['name']
        mime_type = item['mimeType']
        modified_time = item['modifiedTime']

        if file_id in synced_files and synced_files[file_id].get('modifiedTime') == modified_time:
            print(f"Skipping {file_name} because it is already synced and unmodified.")
            return None

        print(f"Downloading {file_name}...")
        return download_file(local_service, file_id, file_name, mime_type, modified_time, synced_files, user_email)

    # Do NOT use ThreadPoolExecutor on free tier. Downloading in parallel 
    # spikes memory massively. Process them sequentially instead.
    for item in items:
        result = process_item(item)
        if result:
            downloaded.append(result)

    return downloaded
