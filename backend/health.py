from typing import Tuple, Dict

from sqlalchemy import text

from database import engine
from job_queue import get_redis_connection


def check_database() -> Tuple[bool, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def check_redis() -> Tuple[bool, str]:
    try:
        client = get_redis_connection()
        client.ping()
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def dependency_status() -> Dict[str, Dict[str, str]]:
    db_ok, db_msg = check_database()
    redis_ok, redis_msg = check_redis()
    return {
        "database": {"status": "ok" if db_ok else "error", "detail": db_msg},
        "redis": {"status": "ok" if redis_ok else "error", "detail": redis_msg},
    }
