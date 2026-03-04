"""Helper script to add users for the web app.

Usage: python add_user.py <username> <password>
"""

import json
import sys
from pathlib import Path

import bcrypt

USERS_FILE = Path(__file__).parent / "users.json"
USERS_DIR = Path(__file__).parent / "users"


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python add_user.py <username> <password>")
        sys.exit(1)

    username, password = sys.argv[1], sys.argv[2]

    # Load or create users file
    if USERS_FILE.exists():
        users = json.loads(USERS_FILE.read_text())
    else:
        users = {}

    # Hash password and save
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    users[username] = hashed
    USERS_FILE.write_text(json.dumps(users, indent=2))

    # Create user directory
    user_dir = USERS_DIR / username / "career_docs"
    user_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'Updated' if username in users else 'Added'} user: {username}")
    print(f"User directory: {USERS_DIR / username}")


if __name__ == "__main__":
    main()
