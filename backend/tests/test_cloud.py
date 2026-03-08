import os
import sys


def _setup_backend_imports():
    backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)


def _create_user(username, password, email="test@example.com", role="user", verified=True):
    _setup_backend_imports()
    import database
    from auth import get_password_hash

    db = database.SessionLocal()
    try:
        user = database.User(
            username=username,
            email=email,
            full_name=username.title(),
            hashed_password=get_password_hash(password),
            role=role,
            is_verified=verified,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _login(client, username, password):
    response = client.post("/auth/token", data={"username": username, "password": password})
    return response.json()["access_token"]


def test_cloud_list_and_import(client, monkeypatch, tmp_path):
    _create_user("frank", "frankpass", email="frank@example.com", verified=True)
    token = _login(client, "frank", "frankpass")

    _setup_backend_imports()
    import main

    monkeypatch.setattr(main.GoogleDriveConnector, "list_files", lambda user_id: [{"id": "file1", "name": "Doc1", "size": "10 KB"}])
    monkeypatch.setattr(main.GoogleDriveConnector, "download_file", lambda user_id, file_id, save_path: save_path.write_bytes(b"fake"))

    list_resp = client.get(
        "/cloud/google_drive/files",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()["files"]) == 1

    import_resp = client.post(
        "/cloud/google_drive/import",
        headers={"Authorization": f"Bearer {token}"},
        json={"provider": "google_drive", "file_ids": ["file1"]}
    )
    assert import_resp.status_code == 200
    assert len(import_resp.json()["imported_files"]) == 1


def test_cloud_oauth_routes(client, monkeypatch):
    user = _create_user("gina", "ginapass", email="gina@example.com", verified=True)
    token = _login(client, "gina", "ginapass")

    _setup_backend_imports()
    import main

    captured = {}

    def fake_auth_url(user_id, state):
        return f"http://example.com/oauth?state={state}&user_id={user_id}"

    def fake_handle_callback(code, user_id):
        captured["code"] = code
        captured["user_id"] = user_id

    monkeypatch.setattr(main.GoogleDriveConnector, "get_auth_url", fake_auth_url)
    monkeypatch.setattr(main.GoogleDriveConnector, "handle_callback", fake_handle_callback)

    providers = client.get("/cloud/providers", headers={"Authorization": f"Bearer {token}"})
    assert providers.status_code == 200
    assert any(provider["id"] == "google_drive" for provider in providers.json()["providers"])

    auth_url_resp = client.get(
        "/cloud/google_drive/auth-url",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert auth_url_resp.status_code == 200
    auth_url = auth_url_resp.json()["auth_url"]
    state = auth_url.split("state=")[1].split("&")[0]

    callback = client.get(f"/auth/google/callback?state={state}&code=test-code")
    assert callback.status_code == 200
    assert captured == {"code": "test-code", "user_id": user.id}
