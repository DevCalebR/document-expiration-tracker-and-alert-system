from typing import List, Dict
from datetime import datetime, timedelta
import io
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import dropbox
from msal import ConfidentialClientApplication
import requests
from config import settings
from database import CloudToken, get_db, SessionLocal

class GoogleDriveConnector:
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    @staticmethod
    def get_auth_url(user_id: int) -> str:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise Exception("Google Drive API credentials not configured")
            
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
                }
            },
            scopes=GoogleDriveConnector.SCOPES
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=str(user_id)
        )
        return authorization_url
    
    @staticmethod
    def handle_callback(code: str, user_id: int):
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
                }
            },
            scopes=GoogleDriveConnector.SCOPES
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        db = SessionLocal()
        token = CloudToken(
            user_id=user_id,
            provider="google_drive",
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=credentials.expiry
        )
        db.add(token)
        db.commit()
        db.close()
    
    @staticmethod
    def list_files(user_id: int) -> List[Dict]:
        db = SessionLocal()
        token_record = db.query(CloudToken).filter(
            CloudToken.user_id == user_id,
            CloudToken.provider == "google_drive"
        ).first()
        db.close()
        
        if not token_record:
            return []
        
        credentials = Credentials(
            token=token_record.access_token,
            refresh_token=token_record.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        
        service = build('drive', 'v3', credentials=credentials)
        results = service.files().list(
            pageSize=50,
            fields="files(id, name, mimeType, size)",
            q="mimeType='application/pdf' or mimeType='image/png' or mimeType='image/jpeg'"
        ).execute()
        
        files = results.get('files', [])
        return [
            {
                "id": f["id"],
                "name": f["name"],
                "size": f"{int(f.get('size', 0)) / 1024:.0f} KB" if f.get('size') else "Unknown"
            }
            for f in files
        ]
    
    @staticmethod
    def download_file(user_id: int, file_id: str, save_path: Path):
        db = SessionLocal()
        token_record = db.query(CloudToken).filter(
            CloudToken.user_id == user_id,
            CloudToken.provider == "google_drive"
        ).first()
        db.close()
        
        if not token_record:
            raise Exception("No Google Drive connection found")
        
        credentials = Credentials(
            token=token_record.access_token,
            refresh_token=token_record.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        
        service = build('drive', 'v3', credentials=credentials)
        request = service.files().get_media(fileId=file_id)
        
        with open(save_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

class DropboxConnector:
    @staticmethod
    def get_auth_url(user_id: int) -> str:
        if not settings.DROPBOX_APP_KEY or not settings.DROPBOX_APP_SECRET:
            raise Exception("Dropbox API credentials not configured")
            
        flow = dropbox.oauth.DropboxOAuth2FlowNoRedirect(
            settings.DROPBOX_APP_KEY,
            settings.DROPBOX_APP_SECRET,
            token_access_type='offline'
        )
        authorize_url = flow.start()
        return authorize_url
    
    @staticmethod
    def handle_callback(code: str, user_id: int):
        flow = dropbox.oauth.DropboxOAuth2FlowNoRedirect(
            settings.DROPBOX_APP_KEY,
            settings.DROPBOX_APP_SECRET,
            token_access_type='offline'
        )
        oauth_result = flow.finish(code)
        
        db = SessionLocal()
        token = CloudToken(
            user_id=user_id,
            provider="dropbox",
            access_token=oauth_result.access_token,
            refresh_token=oauth_result.refresh_token,
            expires_at=datetime.utcnow() + timedelta(seconds=oauth_result.expires_in) if oauth_result.expires_in else None
        )
        db.add(token)
        db.commit()
        db.close()
    
    @staticmethod
    def list_files(user_id: int) -> List[Dict]:
        db = SessionLocal()
        token_record = db.query(CloudToken).filter(
            CloudToken.user_id == user_id,
            CloudToken.provider == "dropbox"
        ).first()
        db.close()
        
        if not token_record:
            return []
        
        dbx = dropbox.Dropbox(token_record.access_token)
        result = dbx.files_list_folder("", recursive=True)
        
        files = []
        for entry in result.entries:
            if isinstance(entry, dropbox.files.FileMetadata):
                if entry.name.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                    files.append({
                        "id": entry.id,
                        "name": entry.name,
                        "size": f"{entry.size / 1024:.0f} KB"
                    })
        
        return files
    
    @staticmethod
    def download_file(user_id: int, file_id: str, save_path: Path):
        db = SessionLocal()
        token_record = db.query(CloudToken).filter(
            CloudToken.user_id == user_id,
            CloudToken.provider == "dropbox"
        ).first()
        db.close()
        
        if not token_record:
            raise Exception("No Dropbox connection found")
        
        dbx = dropbox.Dropbox(token_record.access_token)
        metadata, response = dbx.files_download(file_id)
        
        with open(save_path, 'wb') as f:
            f.write(response.content)

class OneDriveConnector:
    @staticmethod
    def get_auth_url(user_id: int) -> str:
        if not settings.MICROSOFT_CLIENT_ID or not settings.MICROSOFT_CLIENT_SECRET:
            raise Exception("OneDrive API credentials not configured")
            
        authority = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}"
        app = ConfidentialClientApplication(
            settings.MICROSOFT_CLIENT_ID,
            authority=authority,
            client_credential=settings.MICROSOFT_CLIENT_SECRET
        )
        
        auth_url = app.get_authorization_request_url(
            scopes=["Files.Read"],
            redirect_uri=settings.MICROSOFT_REDIRECT_URI,
            state=str(user_id)
        )
        return auth_url
    
    @staticmethod
    def handle_callback(code: str, user_id: int):
        authority = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}"
        app = ConfidentialClientApplication(
            settings.MICROSOFT_CLIENT_ID,
            authority=authority,
            client_credential=settings.MICROSOFT_CLIENT_SECRET
        )
        
        result = app.acquire_token_by_authorization_code(
            code,
            scopes=["Files.Read"],
            redirect_uri=settings.MICROSOFT_REDIRECT_URI
        )
        
        db = SessionLocal()
        token = CloudToken(
            user_id=user_id,
            provider="onedrive",
            access_token=result['access_token'],
            refresh_token=result.get('refresh_token'),
            expires_at=datetime.utcnow() + timedelta(seconds=result['expires_in'])
        )
        db.add(token)
        db.commit()
        db.close()
    
    @staticmethod
    def list_files(user_id: int) -> List[Dict]:
        db = SessionLocal()
        token_record = db.query(CloudToken).filter(
            CloudToken.user_id == user_id,
            CloudToken.provider == "onedrive"
        ).first()
        db.close()
        
        if not token_record:
            return []
        
        headers = {'Authorization': f'Bearer {token_record.access_token}'}
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me/drive/root/children',
            headers=headers
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        files = []
        
        for item in data.get('value', []):
            if 'file' in item:
                name = item['name']
                if name.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                    files.append({
                        "id": item['id'],
                        "name": name,
                        "size": f"{item.get('size', 0) / 1024:.0f} KB"
                    })
        
        return files
    
    @staticmethod
    def download_file(user_id: int, file_id: str, save_path: Path):
        db = SessionLocal()
        token_record = db.query(CloudToken).filter(
            CloudToken.user_id == user_id,
            CloudToken.provider == "onedrive"
        ).first()
        db.close()
        
        if not token_record:
            raise Exception("No OneDrive connection found")
        
        headers = {'Authorization': f'Bearer {token_record.access_token}'}
        response = requests.get(
            f'https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content',
            headers=headers
        )
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
