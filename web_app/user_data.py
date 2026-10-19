"""Per-user profile and career docs management."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from resume_builder.config import settings
from resume_builder.schema import ResumeContent

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
    docs = load_career_docs(username)
    return docs is not None and not career_docs_are_example(*docs)


def load_example_docs() -> tuple[str, str]:
    """Load example career doc templates for first-time setup."""
    timeline = (EXAMPLE_DOCS_DIR / "01-career-timeline.example.md").read_text()
    skills = (EXAMPLE_DOCS_DIR / "02-skills-and-achievements.example.md").read_text()
    return timeline, skills


def career_docs_are_example(timeline: str, skills: str) -> bool:
    """True when the saved docs are still the untouched example templates."""
    ex_timeline, ex_skills = load_example_docs()
    return timeline.strip() == ex_timeline.strip() and skills.strip() == ex_skills.strip()


# --- Drafts (one JSON file per generated resume, keyed by draft id) ---


def _drafts_dir(username: str) -> Path:
    d = settings.drafts_dir / username
    d.mkdir(parents=True, exist_ok=True)
    return d


def _valid_draft_id(draft_id: str) -> bool:
    try:
        return str(uuid.UUID(draft_id)) == draft_id
    except ValueError:
        return False


def save_draft(username: str, draft_id: str, content: ResumeContent, label: str | None = None) -> None:
    d = _drafts_dir(username)
    (d / f"{draft_id}.json").write_text(content.model_dump_json(indent=2))
    meta_path = d / f"{draft_id}.meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta.setdefault("created", datetime.now().isoformat(timespec="seconds"))
    if label is not None:
        meta["label"] = label
    meta["updated"] = datetime.now().isoformat(timespec="seconds")
    meta_path.write_text(json.dumps(meta, indent=2))


def load_draft(username: str, draft_id: str) -> ResumeContent | None:
    if not _valid_draft_id(draft_id):
        return None
    path = _drafts_dir(username) / f"{draft_id}.json"
    if not path.exists():
        return None
    return ResumeContent.model_validate_json(path.read_text())


def list_drafts(username: str, limit: int = 10) -> list[dict[str, Any]]:
    """Most recent drafts first: [{id, label, created, updated}]."""
    drafts = []
    for meta_path in _drafts_dir(username).glob("*.meta.json"):
        draft_id = meta_path.name.removesuffix(".meta.json")
        if not _valid_draft_id(draft_id) or not (meta_path.parent / f"{draft_id}.json").exists():
            continue
        meta = json.loads(meta_path.read_text())
        drafts.append({"id": draft_id, **meta})
    drafts.sort(key=lambda d: d.get("updated", ""), reverse=True)
    return drafts[:limit]
