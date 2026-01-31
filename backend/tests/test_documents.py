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


def test_upload_process_extract_and_delete(client, monkeypatch, tmp_path):
    _create_user("carol", "carolpass", email="carol@example.com", verified=True)
    token = _login(client, "carol", "carolpass")

    upload = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("doc.png", b"fake", "image/png")}
    )
    assert upload.status_code == 200
    saved_name = upload.json()["saved_filename"]

    _setup_backend_imports()
    import main

    def fake_extract_text(_):
        return {"pages": 1, "content": [{"page": 1, "text": "Expires 12/31/2030"}]}, None

    monkeypatch.setattr(main, "extract_text_from_file", fake_extract_text)

    processed = client.get(
        f"/process?filenames={saved_name}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert processed.status_code == 200
    assert processed.json()["files_processed"] == 1
    assert processed.json()["summary"][0]["dates_detected"] == 1

    extracted = client.get(
        f"/extract-text?filename={saved_name}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert extracted.status_code == 200
    assert extracted.json()["pages"] == 1

    deleted = client.delete(
        f"/files/{saved_name}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert deleted.status_code == 200


def test_ai_analyze_endpoint(client):
    _create_user("dana", "danapass", email="dana@example.com", verified=True)
    token = _login(client, "dana", "danapass")

    payload = {
        "results": [
            {"results": [{"date_raw": "01/01/2020", "date_iso": "2020-01-01", "is_expired": True, "days_until_expiration": -10}]}
        ]
    }
    response = client.post(
        "/ai/analyze",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )
    assert response.status_code == 200
    assert "total_dates" in response.json()


def test_expiring_soon_endpoint(client, monkeypatch):
    _create_user("erin", "erinpass", email="erin@example.com", verified=True)
    token = _login(client, "erin", "erinpass")

    upload = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("doc.png", b"fake", "image/png")}
    )
    saved_name = upload.json()["saved_filename"]

    _setup_backend_imports()
    import main

    def fake_extract_text(_):
        return {"pages": 1, "content": [{"page": 1, "text": "Expires 01/01/2030"}]}, None

    monkeypatch.setattr(main, "extract_text_from_file", fake_extract_text)

    client.get(
        f"/process?filenames={saved_name}",
        headers={"Authorization": f"Bearer {token}"}
    )

    expiring = client.get(
        "/documents/expiring-soon?days=3650",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert expiring.status_code == 200
    assert len(expiring.json()["results"]) == 1
