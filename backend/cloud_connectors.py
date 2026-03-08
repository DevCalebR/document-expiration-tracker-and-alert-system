import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlencode

import dropbox
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from msal import ConfidentialClientApplication

from config import settings
from database import CloudToken, SessionLocal
from token_crypto import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)


class CloudConnectionError(Exception):
    pass


class CloudProviderNotConfiguredError(CloudConnectionError):
    pass


class CloudProviderNotConnectedError(CloudConnectionError):
    pass


PROVIDER_LABELS = {
    "google_drive": "Google Drive",
    "dropbox": "Dropbox",
    "onedrive": "OneDrive",
}


def provider_is_configured(provider: str) -> bool:
    if provider == "google_drive":
        return all(
            [settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET, settings.GOOGLE_REDIRECT_URI]
        )
    if provider == "dropbox":
        return all([settings.DROPBOX_APP_KEY, settings.DROPBOX_APP_SECRET, settings.DROPBOX_REDIRECT_URI])
    if provider == "onedrive":
        return all(
            [
                settings.MICROSOFT_CLIENT_ID,
                settings.MICROSOFT_CLIENT_SECRET,
                settings.MICROSOFT_REDIRECT_URI,
            ]
        )
    return False


def ensure_provider_configured(provider: str) -> None:
    if not provider_is_configured(provider):
        raise CloudProviderNotConfiguredError(
            f"{PROVIDER_LABELS.get(provider, provider)} OAuth is not configured."
        )


def provider_connected(user_id: int, provider: str) -> bool:
    db = SessionLocal()
    try:
        return (
            db.query(CloudToken)
            .filter(CloudToken.user_id == user_id, CloudToken.provider == provider)
            .first()
            is not None
        )
    finally:
        db.close()


def disconnect_provider(user_id: int, provider: str) -> bool:
    db = SessionLocal()
    try:
        deleted = (
            db.query(CloudToken)
            .filter(CloudToken.user_id == user_id, CloudToken.provider == provider)
            .delete()
        )
        db.commit()
        return bool(deleted)
    finally:
        db.close()


def get_provider_status(user_id: int, provider: str) -> Dict:
    return {
        "id": provider,
        "name": PROVIDER_LABELS.get(provider, provider),
        "configured": provider_is_configured(provider),
        "connected": provider_connected(user_id, provider),
    }


def _load_token_record(user_id: int, provider: str) -> CloudToken:
    db = SessionLocal()
    try:
        token_record = (
            db.query(CloudToken)
            .filter(CloudToken.user_id == user_id, CloudToken.provider == provider)
            .first()
        )
        if not token_record:
            raise CloudProviderNotConnectedError(
                f"No {PROVIDER_LABELS.get(provider, provider)} connection found."
            )
        db.expunge(token_record)
        return token_record
    finally:
        db.close()


def _save_tokens(
    user_id: int,
    provider: str,
    access_token: str,
    refresh_token: str | None = None,
    expires_at: datetime | None = None,
) -> None:
    db = SessionLocal()
    try:
        token = (
            db.query(CloudToken)
            .filter(CloudToken.user_id == user_id, CloudToken.provider == provider)
            .first()
        )
        if not token:
            token = CloudToken(user_id=user_id, provider=provider)
            db.add(token)

        token.access_token = encrypt_secret(access_token)
        token.refresh_token = encrypt_secret(refresh_token)
        token.expires_at = expires_at
        db.commit()
    finally:
        db.close()


def _decrypted_tokens(user_id: int, provider: str) -> Dict:
    record = _load_token_record(user_id, provider)
    return {
        "access_token": decrypt_secret(record.access_token),
        "refresh_token": decrypt_secret(record.refresh_token),
        "expires_at": record.expires_at,
    }


class GoogleDriveConnector:
    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    @staticmethod
    def get_auth_url(user_id: int, state: str) -> str:
        ensure_provider_configured("google_drive")
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                }
            },
            scopes=GoogleDriveConnector.SCOPES,
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
            prompt="consent",
        )
        return authorization_url

    @staticmethod
    def handle_callback(code: str, user_id: int) -> None:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                }
            },
            scopes=GoogleDriveConnector.SCOPES,
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        flow.fetch_token(code=code)

        credentials = flow.credentials
        _save_tokens(
            user_id=user_id,
            provider="google_drive",
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=credentials.expiry,
        )

    @staticmethod
    def list_files(user_id: int) -> List[Dict]:
        ensure_provider_configured("google_drive")
        tokens = _decrypted_tokens(user_id, "google_drive")
        credentials = Credentials(
            token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        service = build("drive", "v3", credentials=credentials)
        results = service.files().list(
            pageSize=50,
            fields="files(id, name, mimeType, size)",
            q="mimeType='application/pdf' or mimeType='image/png' or mimeType='image/jpeg'",
        ).execute()
        files = results.get("files", [])
        return [
            {
                "id": item["id"],
                "name": item["name"],
                "size": f"{int(item.get('size', 0)) / 1024:.0f} KB" if item.get("size") else "Unknown",
            }
            for item in files
        ]

    @staticmethod
    def download_file(user_id: int, file_id: str, save_path: Path) -> None:
        tokens = _decrypted_tokens(user_id, "google_drive")
        credentials = Credentials(
            token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        service = build("drive", "v3", credentials=credentials)
        request = service.files().get_media(fileId=file_id)

        with open(save_path, "wb") as handle:
            downloader = MediaIoBaseDownload(handle, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()


class DropboxConnector:
    @staticmethod
    def get_auth_url(user_id: int, state: str) -> str:
        ensure_provider_configured("dropbox")
        params = urlencode(
            {
                "client_id": settings.DROPBOX_APP_KEY,
                "response_type": "code",
                "redirect_uri": settings.DROPBOX_REDIRECT_URI,
                "state": state,
                "token_access_type": "offline",
            }
        )
        return f"https://www.dropbox.com/oauth2/authorize?{params}"

    @staticmethod
    def handle_callback(code: str, user_id: int) -> None:
        ensure_provider_configured("dropbox")
        response = requests.post(
            "https://api.dropboxapi.com/oauth2/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": settings.DROPBOX_APP_KEY,
                "client_secret": settings.DROPBOX_APP_SECRET,
                "redirect_uri": settings.DROPBOX_REDIRECT_URI,
            },
            timeout=20,
        )
        if response.status_code != 200:
            raise CloudConnectionError("Dropbox token exchange failed.")

        payload = response.json()
        expires_at = None
        if payload.get("expires_in"):
            expires_at = datetime.utcnow() + timedelta(seconds=int(payload["expires_in"]))

        _save_tokens(
            user_id=user_id,
            provider="dropbox",
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            expires_at=expires_at,
        )

    @staticmethod
    def list_files(user_id: int) -> List[Dict]:
        ensure_provider_configured("dropbox")
        tokens = _decrypted_tokens(user_id, "dropbox")
        dbx = dropbox.Dropbox(tokens["access_token"])
        result = dbx.files_list_folder("", recursive=True)

        files = []
        for entry in result.entries:
            if isinstance(entry, dropbox.files.FileMetadata) and entry.name.lower().endswith(
                (".pdf", ".png", ".jpg", ".jpeg")
            ):
                files.append(
                    {
                        "id": entry.id,
                        "name": entry.name,
                        "size": f"{entry.size / 1024:.0f} KB",
                    }
                )
        return files

    @staticmethod
    def download_file(user_id: int, file_id: str, save_path: Path) -> None:
        tokens = _decrypted_tokens(user_id, "dropbox")
        dbx = dropbox.Dropbox(tokens["access_token"])
        _, response = dbx.files_download(file_id)
        save_path.write_bytes(response.content)


class OneDriveConnector:
    @staticmethod
    def get_auth_url(user_id: int, state: str) -> str:
        ensure_provider_configured("onedrive")
        authority = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}"
        app = ConfidentialClientApplication(
            settings.MICROSOFT_CLIENT_ID,
            authority=authority,
            client_credential=settings.MICROSOFT_CLIENT_SECRET,
        )
        return app.get_authorization_request_url(
            scopes=["Files.Read"],
            redirect_uri=settings.MICROSOFT_REDIRECT_URI,
            state=state,
        )

    @staticmethod
    def handle_callback(code: str, user_id: int) -> None:
        authority = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}"
        app = ConfidentialClientApplication(
            settings.MICROSOFT_CLIENT_ID,
            authority=authority,
            client_credential=settings.MICROSOFT_CLIENT_SECRET,
        )
        result = app.acquire_token_by_authorization_code(
            code,
            scopes=["Files.Read"],
            redirect_uri=settings.MICROSOFT_REDIRECT_URI,
        )
        if "access_token" not in result:
            raise CloudConnectionError(result.get("error_description") or "OneDrive token exchange failed.")

        expires_at = None
        if result.get("expires_in"):
            expires_at = datetime.utcnow() + timedelta(seconds=int(result["expires_in"]))

        _save_tokens(
            user_id=user_id,
            provider="onedrive",
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token"),
            expires_at=expires_at,
        )

    @staticmethod
    def list_files(user_id: int) -> List[Dict]:
        ensure_provider_configured("onedrive")
        tokens = _decrypted_tokens(user_id, "onedrive")
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me/drive/root/children",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=20,
        )
        if response.status_code != 200:
            raise CloudConnectionError("OneDrive file listing failed.")

        files = []
        for item in response.json().get("value", []):
            if "file" in item and item["name"].lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
                files.append(
                    {
                        "id": item["id"],
                        "name": item["name"],
                        "size": f"{item.get('size', 0) / 1024:.0f} KB",
                    }
                )
        return files

    @staticmethod
    def download_file(user_id: int, file_id: str, save_path: Path) -> None:
        tokens = _decrypted_tokens(user_id, "onedrive")
        response = requests.get(
            f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=20,
        )
        if response.status_code != 200:
            raise CloudConnectionError("OneDrive download failed.")
        save_path.write_bytes(response.content)
