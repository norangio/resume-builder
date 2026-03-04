"""HTTP Basic Auth for the web app."""

import json
import secrets
from pathlib import Path

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

USERS_FILE = Path(__file__).parent.parent / "users.json"

security = HTTPBasic()


def _load_users() -> dict[str, str]:
    if not USERS_FILE.exists():
        return {}
    return json.loads(USERS_FILE.read_text())


def get_current_user(
    credentials: HTTPBasicCredentials = Depends(security),
) -> str:
    """FastAPI dependency that returns the authenticated username."""
    users = _load_users()
    stored_hash = users.get(credentials.username)

    if stored_hash is None or not bcrypt.checkpw(
        credentials.password.encode(), stored_hash.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
