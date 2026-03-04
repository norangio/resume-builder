"""Per-user profile and career docs management."""

import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).parent.parent
USERS_DIR = BASE_DIR / "users"
EXAMPLE_DOCS_DIR = BASE_DIR / "career_docs"


def _user_dir(username: str) -> Path:
    d = USERS_DIR / username
    d.mkdir(parents=True, exist_ok=True)
    return d


def _career_docs_dir(username: str) -> Path:
    d = _user_dir(username) / "career_docs"
    d.mkdir(parents=True, exist_ok=True)
    return d


# --- Profile (candidate contact info) ---


def load_profile(username: str) -> dict[str, str]:
    path = _user_dir(username) / "profile.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_profile(username: str, data: dict[str, str]) -> None:
    path = _user_dir(username) / "profile.json"
    path.write_text(json.dumps(data, indent=2))


def has_profile(username: str) -> bool:
    profile = load_profile(username)
    return bool(profile.get("name") and profile.get("email"))


# --- Career docs ---


def load_career_docs(username: str) -> tuple[str, str] | None:
    """Return (timeline, skills_doc) or None if not set up."""
    docs_dir = _career_docs_dir(username)
    timeline_path = docs_dir / "01-career-timeline.md"
    skills_path = docs_dir / "02-skills-and-achievements.md"

    if not timeline_path.exists() or not skills_path.exists():
        return None

    timeline = timeline_path.read_text().strip()
    skills = skills_path.read_text().strip()

    if not timeline or not skills:
        return None

    return timeline, skills


def save_career_docs(username: str, timeline: str, skills: str) -> None:
    docs_dir = _career_docs_dir(username)
    (docs_dir / "01-career-timeline.md").write_text(timeline)
    (docs_dir / "02-skills-and-achievements.md").write_text(skills)


def has_career_docs(username: str) -> bool:
    return load_career_docs(username) is not None


def load_example_docs() -> tuple[str, str]:
    """Load example career doc templates for first-time setup."""
    timeline = (EXAMPLE_DOCS_DIR / "01-career-timeline.example.md").read_text()
    skills = (EXAMPLE_DOCS_DIR / "02-skills-and-achievements.example.md").read_text()
    return timeline, skills
