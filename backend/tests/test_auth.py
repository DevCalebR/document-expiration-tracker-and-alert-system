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


def test_register_verify_login(client):
    response = client.post("/auth/register", json={
        "username": "alice",
        "email": "alice@example.com",
        "full_name": "Alice Example",
        "password": "password123"
    })
    assert response.status_code == 200

    _setup_backend_imports()
    import database
    db = database.SessionLocal()
    try:
        user = db.query(database.User).filter(database.User.username == "alice").first()
        assert user is not None
        token = user.verification_token
    finally:
        db.close()

    verify = client.post("/auth/verify-email", json={
        "username": "alice",
        "token": token
    })
    assert verify.status_code == 200

    login = client.post("/auth/token", data={
        "username": "alice",
        "password": "password123"
    })
    assert login.status_code == 200
    assert "access_token" in login.json()


def test_admin_only_audit_logs(client):
    _create_user("admin", "adminpass", role="admin", email="admin@example.com", verified=True)
    _create_user("bob", "bobpass", email="bob@example.com", verified=True)

    admin_login = client.post("/auth/token", data={"username": "admin", "password": "adminpass"})
    user_login = client.post("/auth/token", data={"username": "bob", "password": "bobpass"})

    admin_token = admin_login.json()["access_token"]
    user_token = user_login.json()["access_token"]

    admin_logs = client.get("/audit/logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_logs.status_code == 200

    user_logs = client.get("/audit/logs", headers={"Authorization": f"Bearer {user_token}"})
    assert user_logs.status_code == 403
