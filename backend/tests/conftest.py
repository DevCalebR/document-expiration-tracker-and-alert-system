import os
import importlib
import sys
import pytest


@pytest.fixture(scope="session", autouse=True)
def _set_test_env(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("docexpire_test")
    os.environ["APP_ENV"] = "test"
    os.environ["APP_DEBUG"] = "False"
    os.environ["APP_SECRET_KEY"] = "test-secret-key-change-this-1234"
    os.environ["FRONTEND_URL"] = "http://localhost:5173"
    os.environ["CORS_ALLOW_ORIGINS"] = "http://localhost:5173"
    os.environ["ALLOWED_HOSTS"] = "localhost,127.0.0.1,testserver"
    os.environ["REDIS_URL"] = "fakeredis://"
    os.environ["RQ_ASYNC"] = "False"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-change-this-1234"
    os.environ["DATABASE_URL"] = os.getenv(
        "TEST_DATABASE_URL",
        f"sqlite:///{tmp_dir / 'docexpire_test.db'}",
    )
    os.environ["STORAGE_PROVIDER"] = "memory"
    os.environ["STORAGE_BUCKET"] = "test-bucket"
    os.environ["TEMP_DIR_OVERRIDE"] = str(tmp_dir / "tmp")
    # Ensure tables are created once for the test DB
    backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    import database
    database.init_db()
    return tmp_dir


@pytest.fixture()
def client():
    backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    # Stub optional OCR/PDF deps if not installed in the test environment
    import importlib.util
    import types
    if "pytesseract" not in sys.modules and importlib.util.find_spec("pytesseract") is None:
        pytesseract_stub = types.ModuleType("pytesseract")
        pytesseract_stub.image_to_string = lambda _img: ""
        sys.modules["pytesseract"] = pytesseract_stub
    if "pdf2image" not in sys.modules and importlib.util.find_spec("pdf2image") is None:
        pdf2image_stub = types.ModuleType("pdf2image")
        pdf2image_stub.convert_from_path = lambda _path: []
        sys.modules["pdf2image"] = pdf2image_stub
    if "PIL" not in sys.modules and importlib.util.find_spec("PIL") is None:
        pil_stub = types.ModuleType("PIL")
        image_stub = types.ModuleType("PIL.Image")
        image_stub.open = lambda _path: None
        pil_stub.Image = image_stub
        sys.modules["PIL"] = pil_stub
        sys.modules["PIL.Image"] = image_stub
    # Stub cloud deps if missing
    google_stub = sys.modules.get("google") or types.ModuleType("google")
    google_stub.__path__ = []
    sys.modules["google"] = google_stub
    oauth2_stub = types.ModuleType("google.oauth2")
    credentials_stub = types.ModuleType("google.oauth2.credentials")
    service_account_stub = types.ModuleType("google.oauth2.service_account")
    class _Creds:
        def __init__(self, **_kwargs):
            pass
    credentials_stub.Credentials = _Creds
    service_account_stub.Credentials = _Creds
    sys.modules["google.oauth2"] = oauth2_stub
    sys.modules["google.oauth2.credentials"] = credentials_stub
    sys.modules["google.oauth2.service_account"] = service_account_stub
    ga_stub = types.ModuleType("google_auth_oauthlib")
    flow_stub = types.ModuleType("google_auth_oauthlib.flow")
    class _Flow:
        def __init__(self, *args, **kwargs):
            self.credentials = types.SimpleNamespace(token="", refresh_token="", expiry=None)
        @classmethod
        def from_client_config(cls, *_args, **_kwargs):
            return cls()
        def authorization_url(self, *args, **kwargs):
            return "http://example.com", "state"
        def fetch_token(self, **_kwargs):
            return None
    flow_stub.Flow = _Flow
    sys.modules["google_auth_oauthlib"] = ga_stub
    sys.modules["google_auth_oauthlib.flow"] = flow_stub
    gapi_stub = types.ModuleType("googleapiclient")
    discovery_stub = types.ModuleType("googleapiclient.discovery")
    http_stub = types.ModuleType("googleapiclient.http")
    discovery_stub.build = lambda *args, **kwargs: types.SimpleNamespace(files=lambda: types.SimpleNamespace(list=lambda **_k: types.SimpleNamespace(execute=lambda: {"files": []}), get_media=lambda fileId=None: None))
    class _Downloader:
        def __init__(self, *_args, **_kwargs):
            pass
        def next_chunk(self):
            return None, True
    http_stub.MediaIoBaseDownload = _Downloader
    sys.modules["googleapiclient"] = gapi_stub
    sys.modules["googleapiclient.discovery"] = discovery_stub
    sys.modules["googleapiclient.http"] = http_stub
    if "dropbox" not in sys.modules and importlib.util.find_spec("dropbox") is None:
        dropbox_stub = types.ModuleType("dropbox")
        class _FlowNoRedirect:
            def __init__(self, *args, **kwargs):
                pass
            def start(self):
                return "http://example.com"
            def finish(self, _code):
                return types.SimpleNamespace(access_token="", refresh_token="", expires_in=3600)
        class _Dropbox:
            def __init__(self, *args, **kwargs):
                pass
            def files_list_folder(self, *_args, **_kwargs):
                return types.SimpleNamespace(entries=[])
            def files_download(self, *_args, **_kwargs):
                return None, types.SimpleNamespace(content=b"")
        files_stub = types.ModuleType("dropbox.files")
        class _FileMetadata:
            def __init__(self):
                self.name = ""
                self.id = ""
                self.size = 0
        files_stub.FileMetadata = _FileMetadata
        dropbox_stub.DropboxOAuth2FlowNoRedirect = _FlowNoRedirect
        dropbox_stub.Dropbox = _Dropbox
        dropbox_stub.oauth = types.SimpleNamespace(DropboxOAuth2FlowNoRedirect=_FlowNoRedirect)
        dropbox_stub.files = files_stub
        sys.modules["dropbox"] = dropbox_stub
        sys.modules["dropbox.files"] = files_stub
    if "msal" not in sys.modules and importlib.util.find_spec("msal") is None:
        msal_stub = types.ModuleType("msal")
        class _ClientApp:
            def __init__(self, *args, **kwargs):
                pass
            def get_authorization_request_url(self, *args, **kwargs):
                return "http://example.com"
            def acquire_token_by_authorization_code(self, *args, **kwargs):
                return {"access_token": "", "expires_in": 3600}
        msal_stub.ConfidentialClientApplication = _ClientApp
        sys.modules["msal"] = msal_stub
    if "anthropic" not in sys.modules and importlib.util.find_spec("anthropic") is None:
        anthropic_stub = types.ModuleType("anthropic")
        class _Anthropic:
            def __init__(self, *args, **kwargs):
                pass
            class messages:
                @staticmethod
                def create(*_args, **_kwargs):
                    return types.SimpleNamespace(content=[])
        anthropic_stub.Anthropic = _Anthropic
        sys.modules["anthropic"] = anthropic_stub
    if "apscheduler" not in sys.modules and importlib.util.find_spec("apscheduler") is None:
        apscheduler_stub = types.ModuleType("apscheduler")
        schedulers_stub = types.ModuleType("apscheduler.schedulers")
        background_stub = types.ModuleType("apscheduler.schedulers.background")
        class _Scheduler:
            def __init__(self):
                self.running = False
            def add_job(self, *args, **kwargs):
                return None
            def start(self):
                self.running = True
            def shutdown(self):
                self.running = False
        background_stub.BackgroundScheduler = _Scheduler
        sys.modules["apscheduler"] = apscheduler_stub
        sys.modules["apscheduler.schedulers"] = schedulers_stub
        sys.modules["apscheduler.schedulers.background"] = background_stub

    import main
    import database
    import auth
    import inspect
    import httpx
    from passlib.context import CryptContext
    from fastapi.testclient import TestClient

    auth.pwd_context = CryptContext(schemes=["plaintext"], deprecated="auto")

    importlib.reload(database)
    importlib.reload(main)

    if "app" not in inspect.signature(httpx.Client.__init__).parameters:
        original_init = httpx.Client.__init__
        def _patched_init(self, *args, **kwargs):
            kwargs.pop("app", None)
            return original_init(self, *args, **kwargs)
        httpx.Client.__init__ = _patched_init

    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _clean_db():
    backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    import database
    import job_queue
    import storage

    job_queue._REDIS_CONNECTION = None
    storage._STORAGE_CLIENT = None
    database.Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()
    try:
        db.query(database.DocumentDate).delete()
        db.query(database.Document).delete()
        db.query(database.AuditLog).delete()
        db.query(database.CloudToken).delete()
        db.query(database.User).delete()
        db.commit()
    finally:
        db.close()
